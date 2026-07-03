import uuid

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.tools.base import Tool
from mock_backend.payments import retry_customer_payment


class RetryPaymentArgs(BaseModel):
    pass


class RetryPayment(Tool):
    name = "retry_payment"
    description = (
        "Retry a failed payment for the current customer. "
        "Only use when the customer has explicitly confirmed they want to retry."
    )
    arg_model = RetryPaymentArgs
    requires_customer_id = True

    def execute(self, args: RetryPaymentArgs, customer_id: uuid.UUID | None, db: Session) -> dict:
        return retry_customer_payment(customer_id, db)
