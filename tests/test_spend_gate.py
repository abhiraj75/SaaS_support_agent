import uuid
from unittest.mock import patch

from app.llm.prompts import SYSTEM_PROMPT
from app.models import Conversation, PaymentRecord, ToolInvocation
from app.seed import CUSTOMER_2_ID


def _mock_generate(responses):
    """Returns a generate function that yields predetermined responses in order."""
    it = iter(responses)
    return lambda *_args, **_kwargs: next(it)


def test_first_call_does_not_execute(client, db):
    """Gate (a): retry_payment on the offering turn does not create a PaymentRecord."""
    before = db.query(PaymentRecord).filter(PaymentRecord.customer_id == CUSTOMER_2_ID).count()

    mock = _mock_generate([
        {"type": "tool_call", "tool_name": "retry_payment", "arguments": {}},
        {"type": "text", "content": "I can retry your payment. Shall I proceed?"},
    ])
    with patch("app.services.orchestrator.adapter.generate", mock):
        r = client.post("/chat", json={
            "customer_id": str(CUSTOMER_2_ID),
            "message": "Retry my failed payment",
        })

    assert r.status_code == 200
    data = r.json()
    conv_id = uuid.UUID(data["conversation_id"])

    # No side effect — payment count unchanged
    db.expire_all()
    after = db.query(PaymentRecord).filter(PaymentRecord.customer_id == CUSTOMER_2_ID).count()
    assert after == before

    # Pending action recorded on the conversation
    conv = db.get(Conversation, conv_id)
    assert conv.pending_action is not None
    assert conv.pending_action["tool_name"] == "retry_payment"

    # Audit row exists for the offered turn
    invocations = db.query(ToolInvocation).filter(
        ToolInvocation.conversation_id == conv_id,
        ToolInvocation.tool_name == "retry_payment",
    ).all()
    assert len(invocations) == 1
    assert invocations[0].result["status"] == "pending_confirmation"


def test_confirming_turn_executes_and_clears(client, db):
    """Gate (b): on the confirming turn, retry_payment dispatches and pending_action clears."""
    mock = _mock_generate([
        # Turn 1: offer
        {"type": "tool_call", "tool_name": "retry_payment", "arguments": {}},
        {"type": "text", "content": "Shall I retry your payment?"},
        # Turn 2: confirm
        {"type": "tool_call", "tool_name": "retry_payment", "arguments": {}},
        {"type": "text", "content": "Payment retried successfully."},
    ])

    before = db.query(PaymentRecord).filter(PaymentRecord.customer_id == CUSTOMER_2_ID).count()

    with patch("app.services.orchestrator.adapter.generate", mock):
        r1 = client.post("/chat", json={
            "customer_id": str(CUSTOMER_2_ID),
            "message": "Retry my payment",
        })
        conv_id = r1.json()["conversation_id"]

        r2 = client.post("/chat", json={
            "customer_id": str(CUSTOMER_2_ID),
            "message": "Yes, go ahead",
            "conversation_id": conv_id,
        })

    assert r2.status_code == 200

    db.expire_all()

    # Side effect present — new PaymentRecord created
    after = db.query(PaymentRecord).filter(PaymentRecord.customer_id == CUSTOMER_2_ID).count()
    assert after == before + 1

    # Pending action cleared
    conv = db.get(Conversation, uuid.UUID(conv_id))
    assert conv.pending_action is None


def test_gate_is_structural_not_prompt(client, db):
    """Gate (c): stripping the prompt's offer instruction does not enable a turn-one charge."""
    stripped = SYSTEM_PROMPT.replace(
        "If a payment has failed and the customer wants to retry, call retry_payment. "
        "If the tool returns status 'pending_confirmation', the payment has NOT been "
        "retried yet. Tell the customer you can retry it and ask them to confirm. "
        "Do not tell the customer the payment was retried until the tool returns "
        "status 'succeeded'.\n\n",
        "",
    )

    before = db.query(PaymentRecord).filter(PaymentRecord.customer_id == CUSTOMER_2_ID).count()

    mock = _mock_generate([
        {"type": "tool_call", "tool_name": "retry_payment", "arguments": {}},
        {"type": "text", "content": "Retrying your payment now."},
    ])
    with (
        patch("app.services.orchestrator.adapter.generate", mock),
        patch("app.services.orchestrator.SYSTEM_PROMPT", stripped),
    ):
        r = client.post("/chat", json={
            "customer_id": str(CUSTOMER_2_ID),
            "message": "Retry my payment right now",
        })

    assert r.status_code == 200

    db.expire_all()

    # No side effect even without the prompt safety net
    after = db.query(PaymentRecord).filter(PaymentRecord.customer_id == CUSTOMER_2_ID).count()
    assert after == before

    # Pending action recorded — gate intercepted
    conv_id = uuid.UUID(r.json()["conversation_id"])
    conv = db.get(Conversation, conv_id)
    assert conv.pending_action is not None
    assert conv.pending_action["tool_name"] == "retry_payment"
