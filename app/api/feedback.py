from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import FeedbackRequest, FeedbackResponse
from app.database import get_db
from app.repositories.feedback import FeedbackRepository

router = APIRouter()


@router.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(request: FeedbackRequest, db: Session = Depends(get_db)):
    repo = FeedbackRepository(db)
    feedback = repo.upsert(request.message_id, request.rating, request.comment)
    db.commit()
    return feedback
