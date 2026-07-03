import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)


class KnowledgeArticle(Base):
    __tablename__ = "knowledge_articles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    category = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    status = Column(String, nullable=False, server_default="active")
    pending_action = Column(JSONB, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at, Message.id")


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")
    tool_invocations = relationship("ToolInvocation", back_populates="message")


class ToolInvocation(Base):
    __tablename__ = "tool_invocations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=True)
    tool_name = Column(String, nullable=False)
    arguments = Column(JSONB, nullable=False, default=dict)
    result = Column(JSONB, nullable=True)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    message = relationship("Message", back_populates="tool_invocations")


class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False, unique=True)
    rating = Column(String, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    plan = Column(String, nullable=False)
    status = Column(String, nullable=False)
    current_period_end = Column(DateTime, nullable=False)


class PaymentRecord(Base):
    __tablename__ = "payment_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String, nullable=False)
    failure_reason = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
