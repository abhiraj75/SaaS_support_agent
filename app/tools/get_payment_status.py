import uuid

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.tools.base import Tool
from mock_backend.payments import get_customer_payment_status


class GetPaymentStatusArgs(BaseModel):
    pass


class GetPaymentStatus(Tool):
    name = "get_payment_status"
    description = (
        "Look up the current customer's recent payment history including "
        "payment amounts, statuses, and any failure reasons."
    )
    arg_model = GetPaymentStatusArgs
    requires_customer_id = True

    def execute(self, args: GetPaymentStatusArgs, customer_id: uuid.UUID | None, db: Session) -> dict:
        records = get_customer_payment_status(customer_id, db)
        if not records:
            return {"error": "No payment records found for this customer"}
        return {"payments": records}
