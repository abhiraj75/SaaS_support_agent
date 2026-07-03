import uuid

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.services.knowledge import KnowledgeService
from app.tools.base import Tool


class SearchKBArgs(BaseModel):
    query: str


class SearchKnowledgeBase(Tool):
    name = "search_knowledge_base"
    description = (
        "Search the knowledge base for articles relevant to a customer question. "
        "Use this for product features, policies, billing questions, troubleshooting, "
        "and any general support topic."
    )
    arg_model = SearchKBArgs

    def execute(self, args: SearchKBArgs, customer_id: uuid.UUID | None, db: Session) -> dict:
        service = KnowledgeService(db)
        articles = service.search(args.query)
        return {"articles": articles}
