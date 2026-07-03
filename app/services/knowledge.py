from sqlalchemy.orm import Session

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
