from sqlalchemy.orm import Session

from app.models import PaymentRecord


def get_customer_payment_status(customer_id, db: Session) -> list[dict]:
    records = (
        db.query(PaymentRecord)
        .filter(PaymentRecord.customer_id == customer_id)
        .order_by(PaymentRecord.created_at.desc())
        .all()
    )
    return [
        {
            "amount": str(r.amount),
            "status": r.status,
            "failure_reason": r.failure_reason,
        }
        for r in records
    ]


def retry_customer_payment(customer_id, db: Session) -> dict:
    failed = (
        db.query(PaymentRecord)
        .filter(PaymentRecord.customer_id == customer_id, PaymentRecord.status == "failed")
        .order_by(PaymentRecord.created_at.desc())
        .first()
    )
    if not failed:
        return {"status": "error", "message": "No failed payment to retry"}

    new = PaymentRecord(
        customer_id=customer_id,
        amount=failed.amount,
        status="succeeded",
    )
    db.add(new)
    db.flush()
    return {"status": "succeeded", "amount": str(failed.amount)}
