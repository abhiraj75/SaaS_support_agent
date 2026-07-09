# Support Agent

AI-powered customer support agent built with FastAPI, PostgreSQL, and Gemini. Routes customer questions to the right tool (knowledge base search, subscription lookup, payment status, password reset, payment retry) and maintains conversation context across turns.

## Setup

### Prerequisites

- Docker and Docker Compose
- A [Gemini API key](https://ai.google.dev/gemini-api/docs/api-key)
- Python 3.12+ (only for local dev and running tests)

### Option A — Docker (everything containerized)

```bash
git clone https://github.com/abhiraj75/SaaS_Agent.git
cd SaaS_Agent

echo "GEMINI_API_KEY=your-key-here" > .env

docker compose up -d
```

This starts Postgres and the app, runs migrations, and seeds data. The app is at `http://localhost:8000`.

### Option B — Local dev (Postgres in Docker, app on host)

```bash
git clone https://github.com/abhiraj75/SaaS_Agent.git
cd SaaS_Agent

echo "GEMINI_API_KEY=your-key-here" > .env

# Start Postgres only
docker compose up -d db

# Set up the Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run migrations and seed
export $(cat .env | xargs)
export DATABASE_URL="postgresql://agent:agent@localhost:5432/support_agent"
alembic upgrade head
python -m app.seed

# Start the server
uvicorn app.main:app --reload --port 8000
```

### Seeded data

The seed creates two customers, eight knowledge articles, subscriptions, and payment records.

| Customer | ID | Plan | Notes |
|----------|----|------|-------|
| Alice Johnson | `a1000000-0000-0000-0000-000000000001` | Professional | Payments current |
| Bob Smith | `a2000000-0000-0000-0000-000000000002` | Starter | Has a failed payment (`card_expired`) |

### Verify

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
# {"status": "ok"}
```

Ask about the refund policy (routes to `search_knowledge_base`):

```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "a1000000-0000-0000-0000-000000000001", "message": "What is your refund policy?"}' \
  | python3 -m json.tool
```

Expected output (reply text varies, `actions_taken` is deterministic):

```json
{
    "conversation_id": "...",
    "reply": "We offer a full refund within 30 days of purchase for annual plans...",
    "actions_taken": [
        {"tool": "search_knowledge_base", "arguments": {"query": "refund policy"}}
    ]
}
```

Check subscription (routes to `get_subscription`):

```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "a1000000-0000-0000-0000-000000000001", "message": "What plan am I on?"}' \
  | python3 -m json.tool
```

```json
{
    "conversation_id": "...",
    "reply": "You are on the Professional plan...",
    "actions_taken": [
        {"tool": "get_subscription", "arguments": {}}
    ]
}
```

Multi-turn - pass back the `conversation_id` from a previous response to continue the conversation:

```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "a1000000-0000-0000-0000-000000000001", "message": "When does it renew?", "conversation_id": "<conversation_id from above>"}' \
  | python3 -m json.tool
```

```json
{
    "conversation_id": "<same conversation_id>",
    "reply": "Your Professional plan renews on ...",
    "actions_taken": [
        {"tool": "get_subscription", "arguments": {}}
    ]
}
```

### Run tests

Tests need Postgres running (from either setup option above). Live routing tests call the real Gemini API and need a valid key; the deterministic tests (spend gate, context follow-up, feedback, KB CRUD) run without one.

```bash
source .venv/bin/activate
DATABASE_URL="postgresql://agent:agent@localhost:5432/support_agent" \
GEMINI_API_KEY="your-key" \
pytest tests/ -v
```

Each test runs inside a transaction that rolls back on teardown, so the suite leaves no residual rows. The live routing tests can fail under free-tier quota pressure; the deterministic tests cover the same logic without a key.

## API

Interactive docs at `/docs` (Swagger UI) and `/openapi.json`.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/chat` | Send a message, receive an agent response |
| `GET` | `/conversations/{id}` | Retrieve conversation with ordered messages and tool invocations |
| `POST` | `/feedback` | Submit or update feedback on an assistant message |
| `GET` | `/articles` | List all knowledge articles |
| `POST` | `/articles` | Create an article |
| `GET` | `/articles/{id}` | Get a single article |
| `PUT` | `/articles/{id}` | Update an article |
| `DELETE` | `/articles/{id}` | Delete an article |
| `GET` | `/health` | Health check |

### Chat request

```json
{
  "customer_id": "a1000000-0000-0000-0000-000000000001",
  "message": "What plan am I on?",
  "conversation_id": null
}
```

### Chat response

```json
{
  "conversation_id": "uuid",
  "reply": "You are on the Professional plan.",
  "actions_taken": [{"tool": "get_subscription", "arguments": {}}]
}
```

### Error responses

Failures are returned as `{"error": "..."}` from boundary handlers, not raw stack traces.

| Status | When |
|--------|------|
| `404` | Conversation ID not found |
| `422` | Agent hit the tool-iteration cap without producing a reply |
| `502` | Model returned an unusable response (empty or safety-blocked) |
| `503` | Model is rate-limited or unavailable — includes a `Retry-After` header when the provider supplies one. The adapter retries transient rate limits before surfacing this |

The Gemini free tier has low per-minute and per-day request limits; a burst of chat requests can hit them and return `503` until the window resets.

## Architecture

```
POST /chat
  │
  ▼
Router (chat.py)
  │
  ▼
Orchestrator ─── loop (max 5 iterations) ───┐
  │                                          │
  ├─ LLM Adapter (Gemini)                   │
  │    ↓                                     │
  ├─ Tool Registry ─── dispatch ──┐          │
  │                                │          │
  │   search_knowledge_base       │          │
  │   get_subscription            ├─ result ─┘
  │   get_payment_status          │
  │   reset_password              │
  │   retry_payment (gated)       │
  │                                │
  ├─ Conversation Service         │
  │   (messages, invocations)     │
  │                                │
  └─ Spend Gate                   │
      (pending_action on          │
       retry_payment only)        │
                                   ▼
                              PostgreSQL
```

## ER Diagram

```
┌──────────────┐     ┌────────────────┐     ┌──────────────────┐
│  customers   │     │ conversations  │     │    messages       │
├──────────────┤     ├────────────────┤     ├──────────────────┤
│ id (PK)      │◄────│ customer_id(FK)│     │ id (PK)          │
│ email        │     │ id (PK)        │◄────│ conversation_id   │
│ name         │     │ status         │     │ role              │
└──────┬───────┘     │ pending_action │     │ content           │
       │             │ created_at     │     │ created_at        │
       │             └────────────────┘     └────────┬─────────┘
       │                                             │
       │             ┌─────────────────┐    ┌────────┴─────────┐
       │             │   feedbacks     │    │ tool_invocations  │
       │             ├─────────────────┤    ├──────────────────┤
       │             │ id (PK)         │    │ id (PK)          │
       │             │ message_id (FK) │◄───│ conversation_id   │
       │             │ rating          │    │ message_id (FK)   │
       │             │ comment         │    │ tool_name         │
       │             │ created_at      │    │ arguments (JSONB) │
       │             └─────────────────┘    │ result (JSONB)    │
       │                                    │ status            │
       │                                    │ created_at        │
       │                                    └──────────────────┘
       │
       │  ┌──────────────────┐     ┌──────────────────┐
       ├──│  subscriptions   │     │ knowledge_articles│
       │  ├──────────────────┤     ├──────────────────┤
       │  │ id (PK)          │     │ id (PK)          │
       │  │ customer_id (FK) │     │ title             │
       │  │ plan             │     │ body              │
       │  │ status           │     │ category          │
       │  │ current_period_  │     │ created_at        │
       │  │   end            │     │ updated_at        │
       │  └──────────────────┘     └──────────────────┘
       │
       │  ┌──────────────────┐
       └──│ payment_records  │
          ├──────────────────┤
          │ id (PK)          │
          │ customer_id (FK) │
          │ amount           │
          │ status           │
          │ failure_reason   │
          │ created_at       │
          └──────────────────┘
```