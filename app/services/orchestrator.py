import uuid

from sqlalchemy.orm import Session

from app.exceptions import ToolLoopExceeded
from app.llm import adapter
from app.llm.prompts import SYSTEM_PROMPT
from app.models import ToolInvocation
from app.services.conversation import ConversationService
from app.tools.get_payment_status import GetPaymentStatus
from app.tools.get_subscription import GetSubscription
from app.tools.registry import ToolRegistry
from app.tools.reset_password import ResetPassword
from app.tools.retry_payment import RetryPayment
from app.tools.search_kb import SearchKnowledgeBase

MAX_TOOL_ITERATIONS = 5


def _build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(SearchKnowledgeBase())
    registry.register(GetSubscription())
    registry.register(GetPaymentStatus())
    registry.register(RetryPayment())
    registry.register(ResetPassword())
    return registry


def _build_message_list(messages, invocations_by_message) -> list[dict]:
    """Reconstruct the Gemini-compatible message sequence from DB state.

    For each assistant message, inserts the preceding tool call / response pairs
    so Gemini sees the full function_call → function_response → model text flow.
    """
    result = []
    for msg in messages:
        if msg.role == "user":
            result.append({"role": "user", "content": msg.content})
        elif msg.role == "assistant":
            for inv in invocations_by_message.get(msg.id, []):
                result.append({"role": "tool_call", "name": inv.tool_name, "args": inv.arguments})
                result.append({"role": "tool_response", "name": inv.tool_name, "result": inv.result or {}})
            result.append({"role": "assistant", "content": msg.content})
    return result


class Orchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.conversation_service = ConversationService(db)
        self.registry = _build_registry()

    def handle_message(
        self,
        customer_id: uuid.UUID,
        message: str,
        conversation_id: uuid.UUID | None = None,
    ) -> dict:
        conversation = self.conversation_service.load_or_create(customer_id, conversation_id)

        # Snapshot before this turn — determines whether a pending_action
        # is a carryover from a previous turn (eligible for confirmation)
        # or doesn't exist yet (eligible for offer).
        had_pending_action = conversation.pending_action is not None
        gate_acted = False

        self.conversation_service.add_message(conversation.id, "user", message)

        history = self.conversation_service.get_history(conversation.id)
        message_ids = [m.id for m in history if m.role == "assistant"]
        invocations_by_message = self.conversation_service.get_invocations_for_messages(message_ids)

        messages = _build_message_list(history, invocations_by_message)
        declarations = self.registry.get_declarations()

        pending_invocations: list[ToolInvocation] = []

        for _ in range(MAX_TOOL_ITERATIONS):
            response = adapter.generate(messages, declarations, SYSTEM_PROMPT)

            if response["type"] == "text":
                assistant_msg = self.conversation_service.add_message(
                    conversation.id, "assistant", response["content"]
                )
                for inv in pending_invocations:
                    inv.message_id = assistant_msg.id

                # Expire stale pending_action from a prior turn if untouched
                if had_pending_action and not gate_acted:
                    conversation.pending_action = None

                self.db.commit()

                return {
                    "conversation_id": str(conversation.id),
                    "reply": response["content"],
                    "actions_taken": [
                        {"tool": inv.tool_name, "arguments": inv.arguments}
                        for inv in pending_invocations
                    ],
                }

            tool_name = response["tool_name"]
            arguments = response["arguments"]

            # Spend gate: retry_payment requires a confirmation turn.
            # On first call (no prior pending_action), record the offer but don't dispatch.
            # On a confirming turn (pending_action set in a prior turn), dispatch.
            if tool_name == "retry_payment":
                gate_acted = True
                if (
                    had_pending_action
                    and conversation.pending_action
                    and conversation.pending_action.get("tool_name") == "retry_payment"
                ):
                    conversation.pending_action = None
                    # Fall through to normal dispatch
                else:
                    conversation.pending_action = {
                        "tool_name": "retry_payment",
                        "arguments": arguments,
                    }
                    result = {"status": "pending_confirmation"}
                    inv = self.conversation_service.record_tool_invocation(
                        conversation_id=conversation.id,
                        message_id=None,
                        tool_name=tool_name,
                        arguments=arguments,
                        result=result,
                        status="ok",
                    )
                    pending_invocations.append(inv)
                    messages.append({"role": "tool_call", "name": tool_name, "args": arguments})
                    messages.append({"role": "tool_response", "name": tool_name, "result": result})
                    continue

            try:
                result = self.registry.dispatch(tool_name, arguments, customer_id, self.db)
                status = "ok"
            except Exception as exc:
                result = {"error": str(exc)}
                status = "error"

            inv = self.conversation_service.record_tool_invocation(
                conversation_id=conversation.id,
                message_id=None,
                tool_name=tool_name,
                arguments=arguments,
                result=result,
                status=status,
            )
            pending_invocations.append(inv)

            messages.append({"role": "tool_call", "name": tool_name, "args": arguments})
            messages.append({"role": "tool_response", "name": tool_name, "result": result})

        raise ToolLoopExceeded()
