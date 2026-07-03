from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import KnowledgeArticle


class KnowledgeRepository:
    def __init__(self, db: Session):
        self.db = db

    def search(self, query: str, limit: int = 5):
        ts_vector = func.to_tsvector(
            "english",
            func.coalesce(KnowledgeArticle.title, "") + " " + func.coalesce(KnowledgeArticle.body, ""),
        )
        ts_query = func.plainto_tsquery("english", query)
        rank = func.ts_rank(ts_vector, ts_query)

        return (
            self.db.query(KnowledgeArticle, rank.label("rank"))
            .filter(ts_vector.op("@@")(ts_query))
            .order_by(rank.desc())
            .limit(limit)
            .all()
        )
