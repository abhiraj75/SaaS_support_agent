import uuid

from sqlalchemy.orm import Session

from app.exceptions import ConversationNotFound
from app.models import Conversation, Message, ToolInvocation
from app.repositories.conversation import ConversationRepository


class ConversationService:
    def __init__(self, db: Session):
        self.repo = ConversationRepository(db)

    def load_or_create(self, customer_id: uuid.UUID, conversation_id: uuid.UUID | None = None) -> Conversation:
        if conversation_id:
            conv = self.repo.get(conversation_id)
            if not conv or conv.customer_id != customer_id:
                raise ConversationNotFound(conversation_id)
            return conv
        return self.repo.create(customer_id)

    def add_message(self, conversation_id: uuid.UUID, role: str, content: str) -> Message:
        return self.repo.add_message(conversation_id, role, content)

    def get_history(self, conversation_id: uuid.UUID, limit: int = 10) -> list[Message]:
        return self.repo.get_recent_messages(conversation_id, limit)

    def get_invocations_for_messages(self, message_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[ToolInvocation]]:
        invocations = self.repo.get_invocations_for_messages(message_ids)
        by_message: dict[uuid.UUID, list[ToolInvocation]] = {}
        for inv in invocations:
            by_message.setdefault(inv.message_id, []).append(inv)
        return by_message

    def record_tool_invocation(
        self,
        conversation_id: uuid.UUID,
        message_id: uuid.UUID | None,
        tool_name: str,
        arguments: dict,
        result: dict | None,
        status: str,
    ) -> ToolInvocation:
        return self.repo.add_tool_invocation(conversation_id, message_id, tool_name, arguments, result, status)
