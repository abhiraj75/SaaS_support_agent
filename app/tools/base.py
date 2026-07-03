import uuid
from abc import ABC, abstractmethod

from pydantic import BaseModel
from sqlalchemy.orm import Session


class Tool(ABC):
    name: str
    description: str
    arg_model: type[BaseModel]

    @abstractmethod
    def execute(self, args: BaseModel, customer_id: uuid.UUID | None, db: Session) -> dict:
        ...
