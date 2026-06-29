from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.chat_message import ChatMessage
from app.services.chat_engine import ask_chatbot


router = APIRouter(prefix="/chat", tags=["Natural Language Chatbot"])


class ChatRequest(BaseModel):
    tenant_id: str
    question: str


@router.post("/ask")
def ask_question(
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    return ask_chatbot(
        db=db,
        tenant_id=request.tenant_id,
        question=request.question,
    )


@router.get("/history")
def get_chat_history(
    tenant_id: str = Query(...),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.tenant_id == tenant_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": item.id,
            "tenant_id": item.tenant_id,
            "question": item.question,
            "answer": item.answer,
            "intent": item.intent,
            "data": item.data,
            "created_at": item.created_at,
        }
        for item in messages
    ]