import uuid

from pydantic import BaseModel


class ChatRequest(BaseModel):
    customer_id: uuid.UUID
    message: str
    conversation_id: uuid.UUID | None = None


class ActionTaken(BaseModel):
    tool: str
    arguments: dict


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    actions_taken: list[ActionTaken]
