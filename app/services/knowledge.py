import uuid

from sqlalchemy.orm import Session

from app.models import KnowledgeArticle
from app.repositories.knowledge import KnowledgeRepository


class KnowledgeService:
    def __init__(self, db: Session):
        self.repo = KnowledgeRepository(db)

    def search(self, query: str, limit: int = 5) -> list[dict]:
        results = self.repo.search(query, limit)
        return [
            {"title": article.title, "body": article.body, "category": article.category}
            for article, _rank in results
        ]

    def list_all(self) -> list[KnowledgeArticle]:
        return self.repo.list_all()

    def get(self, article_id: uuid.UUID) -> KnowledgeArticle | None:
        return self.repo.get(article_id)

    def create(self, title: str, body: str, category: str) -> KnowledgeArticle:
        return self.repo.create(title, body, category)

    def update(self, article_id: uuid.UUID, **fields) -> KnowledgeArticle | None:
        article = self.repo.get(article_id)
        if not article:
            return None
        return self.repo.update(article, **fields)

    def delete(self, article_id: uuid.UUID) -> bool:
        article = self.repo.get(article_id)
        if not article:
            return False
        self.repo.delete(article)
        return True

