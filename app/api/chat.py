import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import ChatRequest, ChatResponse, ConversationResponse
from app.database import get_db
from app.exceptions import ConversationNotFound
from app.models import Conversation
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


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def get_conversation(conversation_id: uuid.UUID, db: Session = Depends(get_db)):
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise ConversationNotFound(conversation_id)
    return conv
