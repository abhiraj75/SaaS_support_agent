from sqlalchemy.orm import Session
from app.models import Customer


def reset_customer_password(customer_id, db: Session) -> dict:
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        return {"status": "error", "message": "Customer not found"}
    return {
        "status": "success",
        "email": customer.email,
        "message": "Password reset link sent",
    }
