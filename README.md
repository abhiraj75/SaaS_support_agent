# Support Agent

AI-powered customer support agent built with FastAPI, PostgreSQL, and Gemini. Routes customer questions to the right tool (knowledge base search, subscription lookup, payment status, password reset, payment retry) and maintains conversation context across turns.

## Setup

### Prerequisites

- Docker and Docker Compose
- A [Gemini API key](https://ai.google.dev/gemini-api/docs/api-key)

### Run

```bash
git clone https://github.com/abhiraj75/SaaS_Agent.git
cd SaaS_Agent

# Set your API key
echo "GEMINI_API_KEY=your-key-here" > .env

# Start Postgres + app (runs migrations and seeds automatically)
docker compose up -d
```

The app runs on `http://localhost:8000`. The seed populates two customers, eight knowledge articles, subscriptions, and payment records.

### Verify

```bash
curl http://localhost:8000/health
# {"status":"ok"}

curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "a1000000-0000-0000-0000-000000000001", "message": "What is your refund policy?"}'
```

### Run tests

Tests require a running Postgres instance and a valid `GEMINI_API_KEY` for the live routing tests. Mock-based tests (spend gate, Phase 4, Phase 5) run without an API key.

```bash
pip install -r requirements.txt
DATABASE_URL="postgresql://agent:agent@localhost:5432/support_agent" \
GEMINI_API_KEY="your-key" \
pytest tests/ -v
```

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