"""
Chat Schemas — aligned with the chat_messages table in Supabase.
Stores full conversation history per patient for future fine-tuning.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ChatRequest(BaseModel):
    patient_id: str
    message: str
    image_base64: Optional[str] = None  # For vision queries
    language: str = "ar"               # "ar" = Arabic, "en" = English


class ChatResponse(BaseModel):
    reply: str
    agent_used: str       # Which agent handled the request
    sources: List[str] = []  # RAG sources used
    timestamp: datetime


class ChatMessageRecord(BaseModel):
    """Represents a single row in the chat_messages table."""
    id: str
    patient_id: str
    role: str             # 'user' | 'assistant'
    content: str
    agent_used: Optional[str] = None
    sources: List[str] = []
    created_at: datetime

    class Config:
        from_attributes = True


class ChatHistoryResponse(BaseModel):
    """Paginated chat history for a patient."""
    patient_id: str
    messages: List[ChatMessageRecord]
    total: int
