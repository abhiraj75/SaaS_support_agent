import uuid
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, UTC

from app.models import Conversation, Message, ToolInvocation
from app.seed import CUSTOMER_1_ID


def test_reset_password_executes_single_turn(client, db):
    """reset_password tool must execute single-turn (no gate) and record the tool invocation."""
    mock_gen = MagicMock(side_effect=[
        {"type": "tool_call", "tool_name": "reset_password", "arguments": {}},
        {"type": "text", "content": "I have sent a password reset link to your email."},
    ])

    with patch("app.services.orchestrator.adapter.generate", mock_gen):
        response = client.post("/chat", json={
            "customer_id": str(CUSTOMER_1_ID),
            "message": "Please reset my password",
        })

    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"]
    assert "reset_password" in [a["tool"] for a in data["actions_taken"]]
    assert "reset" in data["reply"].lower()

    conv_id = uuid.UUID(data["conversation_id"])
    inv = db.query(ToolInvocation).filter(
        ToolInvocation.conversation_id == conv_id,
        ToolInvocation.tool_name == "reset_password"
    ).first()
    assert inv is not None
    assert inv.status == "ok"
    assert inv.result["status"] == "success"


def test_get_conversation_returns_ordered_messages_and_invocations(client, db):
    """GET /conversations/{id} must return ordered messages with nested tool invocations from DB."""
    # 1. Create a conversation, message, and tool invocation manually in the DB with deterministic ordering
    conv = Conversation(customer_id=CUSTOMER_1_ID)
    db.add(conv)
    db.flush()

    now = datetime.now(UTC)
    m1 = Message(conversation_id=conv.id, role="user", content="Hello", created_at=now - timedelta(seconds=10))
    m2 = Message(conversation_id=conv.id, role="assistant", content="Hi there", created_at=now)
    db.add_all([m1, m2])
    db.flush()

    inv = ToolInvocation(
        conversation_id=conv.id,
        message_id=m2.id,
        tool_name="search_knowledge_base",
        arguments={"query": "hello"},
        result={"articles": []},
        status="ok"
    )
    db.add(inv)
    db.commit()

    # 2. Retrieve conversation details via API
    get_resp = client.get(f"/conversations/{conv.id}")
    assert get_resp.status_code == 200
    data = get_resp.json()

    assert data["id"] == str(conv.id)
    assert data["customer_id"] == str(CUSTOMER_1_ID)
    assert len(data["messages"]) == 2

    # Verify order
    msg1, msg2 = data["messages"][0], data["messages"][1]
    assert msg1["role"] == "user"
    assert msg1["content"] == "Hello"

    assert msg2["role"] == "assistant"
    assert len(msg2["tool_invocations"]) == 1
    assert msg2["tool_invocations"][0]["tool_name"] == "search_knowledge_base"


def test_windowed_history_carries_context_to_adapter(client):
    """A follow-up turn must include prior tool call/response pairs in the message list sent to Gemini."""
    mock_turn1 = MagicMock(side_effect=[
        {"type": "tool_call", "tool_name": "get_subscription", "arguments": {}},
        {"type": "text", "content": "You are on the starter plan."},
    ])

    # Turn 1: establish context
    with patch("app.services.orchestrator.adapter.generate", mock_turn1):
        r1 = client.post("/chat", json={
            "customer_id": str(CUSTOMER_1_ID),
            "message": "What plan am I on?",
        })
    conv_id = r1.json()["conversation_id"]

    # Turn 2: follow-up — intercept to inspect the message list
    mock_turn2 = MagicMock(side_effect=[
        {"type": "text", "content": "It expires on July 28."},
    ])

    with patch("app.services.orchestrator.adapter.generate", mock_turn2):
        client.post("/chat", json={
            "customer_id": str(CUSTOMER_1_ID),
            "message": "When does it expire?",
            "conversation_id": conv_id,
        })

    messages_sent = mock_turn2.call_args[0][0]

    # The message list must include: user turn, tool_call, tool_response, assistant turn, then new user turn
    roles = [m["role"] for m in messages_sent]
    assert "tool_call" in roles, "Prior tool call must be in history"
    assert "tool_response" in roles, "Prior tool response must be in history"

    tc_idx = roles.index("tool_call")
    tr_idx = roles.index("tool_response")
    assert messages_sent[tc_idx]["name"] == "get_subscription"
    assert messages_sent[tr_idx]["name"] == "get_subscription"
    assert messages_sent[-1] == {"role": "user", "content": "When does it expire?"}
