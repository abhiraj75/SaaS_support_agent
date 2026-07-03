import uuid

from sqlalchemy.orm import Session

from app.models import Feedback


class FeedbackRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_message(self, message_id: uuid.UUID) -> Feedback | None:
        return (
            self.db.query(Feedback)
            .filter(Feedback.message_id == message_id)
            .first()
        )

    def upsert(self, message_id: uuid.UUID, rating: str, comment: str | None) -> Feedback:
        existing = self.get_by_message(message_id)
        if existing:
            existing.rating = rating
            existing.comment = comment
            self.db.flush()
            return existing
        feedback = Feedback(message_id=message_id, rating=rating, comment=comment)
        self.db.add(feedback)
        self.db.flush()
        return feedback
