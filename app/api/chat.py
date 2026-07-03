from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import ChatRequest, ChatResponse
from app.database import get_db
from app.services.orchestrator import Orchestrator

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    orchestrator = Orchestrator(db)
    return orchestrator.handle_message(
        customer_id=request.customer_id,
        message=request.message,
        conversation_id=request.conversation_id,
    )
