import uuid

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.tools.base import Tool
from mock_backend.subscriptions import get_customer_subscription


class GetSubscriptionArgs(BaseModel):
    pass


class GetSubscription(Tool):
    name = "get_subscription"
    description = (
        "Look up the current customer's subscription details including plan, "
        "status, and billing period end date."
    )
    arg_model = GetSubscriptionArgs
    requires_customer_id = True

    def execute(self, args: GetSubscriptionArgs, customer_id: uuid.UUID | None, db: Session) -> dict:
        result = get_customer_subscription(customer_id, db)
        if not result:
            return {"error": "No subscription found for this customer"}
        return result
