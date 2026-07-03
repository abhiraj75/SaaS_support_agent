import pytest

from app.seed import CUSTOMER_1_ID, CUSTOMER_2_ID
from app.tools.get_subscription import GetSubscription
from app.tools.registry import ToolRegistry


def test_subscription_question_routes_to_get_subscription(client):
    response = client.post("/chat", json={
        "customer_id": str(CUSTOMER_1_ID),
        "message": "What subscription plan am I on?",
    })
    assert response.status_code == 200

    data = response.json()
    tools_used = [a["tool"] for a in data["actions_taken"]]
    assert "get_subscription" in tools_used


def test_payment_question_routes_to_get_payment_status(client):
    response = client.post("/chat", json={
        "customer_id": str(CUSTOMER_2_ID),
        "message": "What is the status of my last payment?",
    })
    assert response.status_code == 200

    data = response.json()
    tools_used = [a["tool"] for a in data["actions_taken"]]
    assert "get_payment_status" in tools_used


def test_backend_tool_rejects_without_session_customer_id(db):
    """The session-bound account invariant: dispatch refuses a backend tool call without customer_id."""
    registry = ToolRegistry()
    registry.register(GetSubscription())

    with pytest.raises(ValueError, match="requires a session customer_id"):
        registry.dispatch("get_subscription", {}, None, db)
