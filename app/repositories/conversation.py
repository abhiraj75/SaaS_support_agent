import uuid

from sqlalchemy.orm import Session

from app.exceptions import ConversationNotFound
from app.models import Conversation, Message, ToolInvocation


class ConversationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, conversation_id: uuid.UUID) -> Conversation | None:
        return self.db.get(Conversation, conversation_id)

    def create(self, customer_id: uuid.UUID) -> Conversation:
        conv = Conversation(customer_id=customer_id)
        self.db.add(conv)
        self.db.flush()
        return conv

    def add_message(self, conversation_id: uuid.UUID, role: str, content: str) -> Message:
        msg = Message(conversation_id=conversation_id, role=role, content=content)
        self.db.add(msg)
        self.db.flush()
        return msg

    def get_recent_messages(self, conversation_id: uuid.UUID, limit: int = 10) -> list[Message]:
        return (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.sequence_num.desc())
            .limit(limit)
            .all()[::-1]
        )

    def get_invocations_for_messages(self, message_ids: list[uuid.UUID]) -> list[ToolInvocation]:
        if not message_ids:
            return []
        return (
            self.db.query(ToolInvocation)
            .filter(ToolInvocation.message_id.in_(message_ids))
            .order_by(ToolInvocation.created_at)
            .all()
        )

    def add_tool_invocation(
        self,
        conversation_id: uuid.UUID,
        message_id: uuid.UUID | None,
        tool_name: str,
        arguments: dict,
        result: dict | None,
        status: str,
    ) -> ToolInvocation:
        inv = ToolInvocation(
            conversation_id=conversation_id,
            message_id=message_id,
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            status=status,
        )
        self.db.add(inv)
        self.db.flush()
        return inv
