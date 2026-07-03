from sqlalchemy.orm import Session

from app.models import Subscription


def get_customer_subscription(customer_id, db: Session) -> dict | None:
    sub = db.query(Subscription).filter(Subscription.customer_id == customer_id).first()
    if not sub:
        return None
    return {
        "plan": sub.plan,
        "status": sub.status,
        "current_period_end": sub.current_period_end.isoformat(),
    }
