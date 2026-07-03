"""Initial schema — all tables plus FTS index on knowledge_articles."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "customers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String, nullable=False, unique=True),
        sa.Column("name", sa.String, nullable=False),
    )

    op.create_table(
        "knowledge_articles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("category", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.execute(
        "CREATE INDEX ix_knowledge_articles_fts "
        "ON knowledge_articles "
        "USING GIN (to_tsvector('english', coalesce(title, '') || ' ' || coalesce(body, '')))"
    )

    op.create_table(
        "conversations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("status", sa.String, nullable=False, server_default="active"),
        sa.Column("pending_action", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", UUID(as_uuid=True), sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("role", sa.String, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "tool_invocations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", UUID(as_uuid=True), sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("message_id", UUID(as_uuid=True), sa.ForeignKey("messages.id"), nullable=True),
        sa.Column("tool_name", sa.String, nullable=False),
        sa.Column("arguments", JSONB, nullable=False),
        sa.Column("result", JSONB, nullable=True),
        sa.Column("status", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "feedbacks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("message_id", UUID(as_uuid=True), sa.ForeignKey("messages.id"), nullable=False, unique=True),
        sa.Column("rating", sa.String, nullable=False),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("plan", sa.String, nullable=False),
        sa.Column("status", sa.String, nullable=False),
        sa.Column("current_period_end", sa.DateTime, nullable=False),
    )

    op.create_table(
        "payment_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String, nullable=False),
        sa.Column("failure_reason", sa.String, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade():
    for table in [
        "payment_records", "subscriptions", "feedbacks",
        "tool_invocations", "messages", "conversations",
        "knowledge_articles", "customers",
    ]:
        op.drop_table(table)
