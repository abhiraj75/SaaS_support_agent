import uuid

from app.models import ToolInvocation
from app.seed import CUSTOMER_1_ID


def test_kb_question_routes_to_search_and_writes_audit_row(client, db):
    """A refund-policy question must route to search_knowledge_base and leave a ToolInvocation row."""
    response = client.post("/chat", json={
        "customer_id": str(CUSTOMER_1_ID),
        "message": "What is your refund policy?",
    })
    assert response.status_code == 200

    data = response.json()
    assert data["conversation_id"]
    assert data["reply"]

    tools_used = [a["tool"] for a in data["actions_taken"]]
    assert "search_knowledge_base" in tools_used

    conv_id = uuid.UUID(data["conversation_id"])
    invocations = db.query(ToolInvocation).filter(ToolInvocation.conversation_id == conv_id).all()
    assert any(inv.tool_name == "search_knowledge_base" and inv.status == "ok" for inv in invocations)
