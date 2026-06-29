from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func

from app.core.database import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)

    tenant_id = Column(String, index=True, nullable=False)

    question = Column(String, nullable=False)
    answer = Column(String, nullable=False)

    intent = Column(String, index=True, nullable=False)
    data = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())