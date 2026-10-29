"""
Public Chat Router for CampusVoice Helpdesk
"""
import time
import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Message
from app.schemas.chat import ChatRequest, ChatResponse, SourceCitation, TicketInfo
from app.services.llm_agent import execute_agent_turn
from app.services.tts import synthesize_speech
from app.services.auth import get_optional_current_user

router = APIRouter(prefix="/api", tags=["Chat"])

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    db: Session = Depends(get_db),
    auth_user: Optional[dict] = Depends(get_optional_current_user)
):
    start_time = time.perf_counter()
    
    clean_message = request.message.strip()
    if not clean_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty."
        )

    # Determine user identity from JWT or payload
    user_info = auth_user or {}
    if request.user_name and not user_info.get("full_name"):
        user_info["full_name"] = request.user_name
    if request.user_email and not user_info.get("email"):
        user_info["email"] = request.user_email
    if request.user_phone and not user_info.get("phone"):
        user_info["phone"] = request.user_phone
    if request.user_id and not user_info.get("id"):
        user_info["id"] = request.user_id

    # Determine language (support explicit tag or Telugu character range heuristic)
    is_telugu = (request.language == "te") or any('\u0c00' <= char <= '\u0c7f' for char in clean_message)
    detected_lang = "te" if is_telugu else "en"

    # Execute LLM agent turn with full RAG, tools, guardrails, and user context
    agent_result = execute_agent_turn(
        message=clean_message,
        language=detected_lang,
        db=db,
        use_mini=False,
        user_info=user_info if user_info else None
    )

    # Optional TTS synthesis
    audio_b64, tts_ms = synthesize_speech(agent_result["answer_text"], detected_lang)

    total_latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
    session_id = request.session_id or str(uuid.uuid4())

    # Map sources
    source_citations = [
        SourceCitation(
            title=s["title"],
            department=s.get("department"),
            source_date=s.get("source_date"),
            page_number=s.get("page_number"),
            document_id=s.get("document_id"),
            replaces=s.get("replaces"),
            superseded=s.get("superseded", False)
        )
        for s in agent_result.get("sources", [])
    ]

    ticket_obj = None
    if agent_result.get("ticket"):
        t_data = agent_result["ticket"]
        ticket_obj = TicketInfo(
            id=t_data["id"],
            question=t_data["question"],
            department=t_data["department"],
            status=t_data["status"],
            summary=t_data.get("summary"),
            created_at=t_data.get("created_at"),
            user_name=t_data.get("user_name"),
            user_email=t_data.get("user_email"),
            user_phone=t_data.get("user_phone")
        )

    # Persist turn in database
    user_msg = Message(
        session_id=session_id,
        role="user",
        text=clean_message,
        language=detected_lang,
        latency_ms=0.0
    )
    bot_msg = Message(
        session_id=session_id,
        role="assistant",
        text=agent_result["answer_text"],
        language=detected_lang,
        sources=[s.model_dump() for s in source_citations],
        confidence=agent_result.get("confidence", 1.0),
        stt_ms=0.0,
        llm_ms=agent_result["llm_ms"],
        tts_ms=tts_ms,
        latency_ms=total_latency_ms,
        ticket_id=ticket_obj.id if ticket_obj else None
    )
    db.add(user_msg)
    db.add(bot_msg)
    db.commit()

    return ChatResponse(
        transcript=clean_message,
        language=detected_lang,
        answer_text=agent_result["answer_text"],
        audio_base64=audio_b64,
        audio_url=None,
        sources=source_citations,
        ticket=ticket_obj,
        confidence=agent_result.get("confidence"),
        latency_ms=total_latency_ms,
        stt_ms=0.0,
        llm_ms=agent_result["llm_ms"],
        tts_ms=tts_ms
    )
