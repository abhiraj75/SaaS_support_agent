# Decisions

## Architecture

**Sync stack.** FastAPI with synchronous handlers and synchronous SQLAlchemy 2.0. The orchestrator makes one blocking Gemini call per loop iteration. Async would add complexity without meaningful throughput gain here — the bottleneck is the LLM, not I/O multiplexing.

**Layered separation.** Routers handle HTTP concerns. Services hold business logic. Repositories own query construction. Tools are thin adapters over the mock backend. The orchestrator is the only component that knows about the LLM-tool loop. This keeps each layer testable in isolation and lets the mock backend swap for real clients without touching the agent.

**Single process, no workers.** Uvicorn runs one process. Horizontal scaling is outside scope but the stateless design (session state in Postgres, not in memory) supports it.

## Key design decisions

**Orchestrator owns the loop, not the SDK.** Automatic function calling is disabled. The orchestrator runs Gemini → tool → Gemini under a hard cap of 5 iterations. This gives us structural control over side effects: the spend gate intercepts `retry_payment` before dispatch, which would be impossible if the SDK executed tools autonomously.

**Spend gate is structural, not prompt-based.** The `retry_payment` gate lives in the orchestrator loop, not in the system prompt. The prompt includes advisory guidance on how to interpret `pending_confirmation` tool results, but removing it does not enable a turn-one charge. The gate checks `had_pending_action` — a snapshot taken at turn start — so even if the model calls `retry_payment` twice in one loop, the second call cannot self-confirm (the snapshot is still `False`). The intercepted tool result includes a descriptive message guiding the model to ask for confirmation, keeping the user experience correct without the gate depending on it. Test (c) proves this by stripping the prompt instruction and verifying the gate still holds.

**`customer_id` from the session, never from the model.** Backend tools receive `customer_id` injected by the orchestrator from the authenticated session. The model never sees or controls which account it operates on. The registry rejects any tool call marked `requires_customer_id=True` if the session `customer_id` is missing.

**Tool declarations from Pydantic schemas.** Each tool defines a Pydantic `arg_model`. The registry generates Gemini `FunctionDeclaration` parameter schemas via `model_json_schema()`. One type definition serves both API validation and tool declaration — no schema drift.

**Conversation history windowed to 10 messages.** The orchestrator fetches the last 10 messages (by `created_at`) and reconstructs the Gemini-compatible sequence including tool call/response pairs. This caps context size while preserving enough for follow-up questions. The window is a repository parameter, adjustable without touching the orchestrator.

**Feedback upserts by message.** The `Feedback` model has a unique constraint on `message_id`. Re-submitting feedback for the same assistant message updates the existing row rather than creating a duplicate. This is a domain constraint — one rating per response.

## Assumptions

- The Gemini API key is on a free tier with limited RPM/RPD. Tests that hit the live API may fail under quota pressure; mock-based tests cover the same logic deterministically.
- Two seeded customers are sufficient for demonstrating all flows. The seed is idempotent — it checks for existing data before inserting.
- FTS uses PostgreSQL's built-in `to_tsvector`/`plainto_tsquery` with the English dictionary. No external search service.
- The mock backend (subscriptions, payments, passwords) returns hardcoded success/failure responses. Real integrations would replace these functions without changing the tool interface.

## Trade-offs

- **No authentication layer.** `customer_id` comes from the request body, not from a JWT or session cookie. In production, a middleware would extract it from a verified token. The session-binding invariant (tools take `customer_id` from the session, not the model) is enforced regardless.
- **No async.** Simpler to reason about, but each request blocks a thread during the Gemini call. Under load, this limits concurrency. An async rewrite would be the first scaling step.
- **No rate limiting or retry on 429.** The app surfaces Gemini quota errors to the caller. A production system would queue requests or implement backoff.
- **Single migration file.** All tables in one initial migration. A production project would have incremental migrations per schema change.

## Limitations

- The spend gate only covers `retry_payment`. Adding more gated tools requires extending the `if tool_name == "retry_payment"` block. A registry-based approach (marking tools as `requires_confirmation=True`) would generalize this.
- No streaming responses. The model generates a complete response before returning. Streaming would improve perceived latency.
- No conversation list endpoint. You can retrieve a single conversation by ID but cannot list all conversations for a customer.
- KB search is English-only (PostgreSQL FTS dictionary). Multi-language support would need a different search backend or dictionary configuration.

## Given another week

- Generalize the spend gate to a registry flag so any tool can opt into confirmation.
- Add streaming via SSE for real-time response delivery.
- Add a `GET /customers/{id}/conversations` endpoint.
- Replace mock backend with real Stripe/Auth0 integrations behind feature flags.
- Add structured logging and request tracing.
- Add rate limiting middleware with per-customer quotas.
- Write a Postman/Bruno collection for manual API exploration.
