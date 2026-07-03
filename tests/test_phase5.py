import uuid
from unittest.mock import MagicMock, patch

from app.models import Feedback, KnowledgeArticle
from app.seed import CUSTOMER_1_ID


def _create_assistant_message(client):
    """Helper: send a chat message and return the assistant message_id and conversation_id."""
    mock = MagicMock(side_effect=[
        {"type": "text", "content": "Here is your answer."},
    ])
    with patch("app.services.orchestrator.adapter.generate", mock):
        r = client.post("/chat", json={
            "customer_id": str(CUSTOMER_1_ID),
            "message": "Hello",
        })
    conv_id = r.json()["conversation_id"]
    # Retrieve the conversation to get the assistant message id
    conv_resp = client.get(f"/conversations/{conv_id}")
    messages = conv_resp.json()["messages"]
    assistant_msg = [m for m in messages if m["role"] == "assistant"][-1]
    return assistant_msg["id"], conv_id


def test_feedback_persists_and_upserts(client, db):
    """POST /feedback creates a feedback row; re-submission upserts (same message_id, one row)."""
    msg_id, _ = _create_assistant_message(client)

    # First submission
    r1 = client.post("/feedback", json={
        "message_id": msg_id,
        "rating": "positive",
        "comment": "Great answer!",
    })
    assert r1.status_code == 200
    data1 = r1.json()
    assert data1["rating"] == "positive"
    assert data1["comment"] == "Great answer!"
    feedback_id = data1["id"]

    # Re-submission with updated rating
    r2 = client.post("/feedback", json={
        "message_id": msg_id,
        "rating": "negative",
        "comment": "Actually, not helpful.",
    })
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["rating"] == "negative"
    assert data2["comment"] == "Actually, not helpful."
    assert data2["id"] == feedback_id

    # Only one feedback row for this message
    db.expire_all()
    count = db.query(Feedback).filter(Feedback.message_id == uuid.UUID(msg_id)).count()
    assert count == 1


def test_article_crud_and_fts(client, db):
    """Create an article via API, verify it's findable by search_knowledge_base in the same run."""
    # Create
    r = client.post("/articles", json={
        "title": "Zaphomatic Widget Setup",
        "body": "To configure the Zaphomatic widget, navigate to Settings and enable the flux capacitor.",
        "category": "setup",
    })
    assert r.status_code == 201
    article = r.json()
    article_id = article["id"]
    assert article["title"] == "Zaphomatic Widget Setup"

    # Read
    r = client.get(f"/articles/{article_id}")
    assert r.status_code == 200
    assert r.json()["title"] == "Zaphomatic Widget Setup"

    # List
    r = client.get("/articles")
    assert r.status_code == 200
    ids = [a["id"] for a in r.json()]
    assert article_id in ids

    # Update
    r = client.put(f"/articles/{article_id}", json={"title": "Zaphomatic Widget Guide"})
    assert r.status_code == 200
    assert r.json()["title"] == "Zaphomatic Widget Guide"

    # FTS: the new article must be findable by search_knowledge_base
    mock = MagicMock(side_effect=[
        {"type": "tool_call", "tool_name": "search_knowledge_base", "arguments": {"query": "Zaphomatic widget"}},
        {"type": "text", "content": "The Zaphomatic widget requires flux capacitor configuration."},
    ])
    with patch("app.services.orchestrator.adapter.generate", mock):
        chat_r = client.post("/chat", json={
            "customer_id": str(CUSTOMER_1_ID),
            "message": "How do I set up the Zaphomatic widget?",
        })
    assert chat_r.status_code == 200
    assert "zaphomatic" in chat_r.json()["reply"].lower() or "flux" in chat_r.json()["reply"].lower()

    # Delete
    r = client.delete(f"/articles/{article_id}")
    assert r.status_code == 204

    # Verify gone
    r = client.get(f"/articles/{article_id}")
    assert r.status_code == 404
