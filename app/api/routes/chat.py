"""
Chat Routes — Clinical conversations with Mado.
- POST /       : Send a message, get a reply, save both turns to chat_messages table
- GET /{id}/history : Retrieve full conversation history for a patient
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime
from app.schemas.chat_schema import ChatRequest, ChatResponse, ChatHistoryResponse
from app.agents.orchestrator import route_clinical
from app.db.supabase_client import get_supabase

router = APIRouter(prefix="/chat", tags=["Chat - العيادة الرقمية"])


def _save_message(
    patient_id: str,
    role: str,
    content: str,
    agent_used: str | None = None,
    sources: list[str] | None = None,
) -> None:
    """Persist a single chat turn to the chat_messages table."""
    supabase = get_supabase()
    supabase.table("chat_messages").insert({
        "patient_id": patient_id,
        "role": role,
        "content": content,
        "agent_used": agent_used,
        "sources": sources or [],
    }).execute()


@router.post("/", response_model=ChatResponse)
async def chat_with_mado(payload: ChatRequest):
    """
    Send a message to Mado's clinical agents.
    The orchestrator classifies intent and routes to the correct
    specialist (diabetes / blood_pressure / glands / general).
    Both the user message and the assistant reply are persisted
    in the chat_messages table for history and future fine-tuning.
    """
    # 1. Save the user's message
    _save_message(
        patient_id=payload.patient_id,
        role="user",
        content=payload.message,
    )

    # 2. Route to the correct clinical agent
    response = await route_clinical(payload)

    # 3. Save the assistant's reply (with agent metadata)
    _save_message(
        patient_id=payload.patient_id,
        role="assistant",
        content=response.reply,
        agent_used=response.agent_used,
        sources=response.sources,
    )

    return response


@router.get("/{patient_id}/history", response_model=ChatHistoryResponse)
async def get_chat_history(patient_id: str, limit: int = 50):
    """
    Retrieve conversation history for a patient.
    Returns messages ordered oldest → newest (chronological).
    Use `limit` to control how many messages to return (default: 50).
    """
    supabase = get_supabase()
    result = (
        supabase.table("chat_messages")
        .select("*")
        .eq("patient_id", patient_id)
        .order("created_at", desc=False)
        .limit(limit)
        .execute()
    )
    if result.data is None:
        raise HTTPException(status_code=404, detail="No chat history found for this patient")

    return ChatHistoryResponse(
        patient_id=patient_id,
        messages=result.data,
        total=len(result.data),
    )
