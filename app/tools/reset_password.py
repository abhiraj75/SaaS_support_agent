import uuid

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.tools.base import Tool
from mock_backend.passwords import reset_customer_password


class ResetPasswordArgs(BaseModel):
    pass


class ResetPassword(Tool):
    name = "reset_password"
    description = (
        "Reset the password for the current customer. "
        "Use this when the customer asks to reset or change their password."
    )
    arg_model = ResetPasswordArgs
    requires_customer_id = True

    def execute(self, args: ResetPasswordArgs, customer_id: uuid.UUID | None, db: Session) -> dict:
        return reset_customer_password(customer_id, db)
