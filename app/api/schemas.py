import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


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


class ToolInvocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tool_name: str
    arguments: dict
    result: dict | None
    status: str


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    created_at: datetime
    tool_invocations: list[ToolInvocationResponse]


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    status: str
    created_at: datetime
    messages: list[MessageResponse]


class FeedbackRequest(BaseModel):
    message_id: uuid.UUID
    rating: str
    comment: str | None = None


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    message_id: uuid.UUID
    rating: str
    comment: str | None
    created_at: datetime


class ArticleCreateRequest(BaseModel):
    title: str
    body: str
    category: str


class ArticleUpdateRequest(BaseModel):
    title: str | None = None
    body: str | None = None
    category: str | None = None


class ArticleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    body: str
    category: str
    created_at: datetime
    updated_at: datetime

