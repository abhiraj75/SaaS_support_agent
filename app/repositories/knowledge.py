import uuid

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

    def list_all(self) -> list[KnowledgeArticle]:
        return self.db.query(KnowledgeArticle).order_by(KnowledgeArticle.created_at).all()

    def get(self, article_id: uuid.UUID) -> KnowledgeArticle | None:
        return self.db.get(KnowledgeArticle, article_id)

    def create(self, title: str, body: str, category: str) -> KnowledgeArticle:
        article = KnowledgeArticle(title=title, body=body, category=category)
        self.db.add(article)
        self.db.flush()
        return article

    def update(self, article: KnowledgeArticle, **fields) -> KnowledgeArticle:
        for key, value in fields.items():
            setattr(article, key, value)
        self.db.flush()
        return article

    def delete(self, article: KnowledgeArticle) -> None:
        self.db.delete(article)
        self.db.flush()

