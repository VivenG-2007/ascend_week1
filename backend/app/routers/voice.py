"""
Public Voice Endpoint for Push-To-Talk Voice AI
"""
import time
import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Message
from app.schemas.chat import ChatResponse, SourceCitation, TicketInfo
from app.services.stt import transcribe_audio_bytes
from app.services.tts import synthesize_speech
from app.services.llm_agent import execute_agent_turn
from app.config import settings

from app.services.auth import get_optional_current_user

router = APIRouter(prefix="/api", tags=["Voice"])

@router.post("/voice", response_model=ChatResponse)
async def voice_endpoint(
    audio: UploadFile = File(...),
    language: Optional[str] = Form("en"),
    session_id: Optional[str] = Form(None),
    voice_name: Optional[str] = Form(None),
    user_name: Optional[str] = Form(None),
    user_email: Optional[str] = Form(None),
    user_phone: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    auth_user: Optional[dict] = Depends(get_optional_current_user)
):
    start_time = time.perf_counter()

    audio_bytes = await audio.read()
    if not audio_bytes or len(audio_bytes) < 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Received empty or unreadable audio."
        )

    # Resolve user details
    user_info = auth_user or {}
    if user_name and not user_info.get("full_name"):
        user_info["full_name"] = user_name
    if user_email and not user_info.get("email"):
        user_info["email"] = user_email
    if user_phone and not user_info.get("phone"):
        user_info["phone"] = user_phone

    # 1. Speech-to-Text (Azure AI Speech)
    try:
        transcript, detected_lang, stt_ms = transcribe_audio_bytes(audio_bytes, language or "en")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Speech recognition failed: {str(e)}"
        )

    # 2. Agent Reasoning & Grounded RAG Turn
    agent_result = execute_agent_turn(
        message=transcript,
        language=detected_lang,
        db=db,
        use_mini=False,
        user_info=user_info if user_info else None
    )

    # 3. Text-to-Speech (Azure AI Speech Neural Voice)
    audio_b64, tts_ms = synthesize_speech(
        agent_result["answer_text"],
        detected_lang,
        voice_name=voice_name
    )

    total_latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
    s_id = session_id or str(uuid.uuid4())

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

    # Persist in DB
    user_msg = Message(
        session_id=s_id,
        role="user",
        text=transcript,
        language=detected_lang,
        stt_ms=stt_ms,
        latency_ms=0.0
    )
    bot_msg = Message(
        session_id=s_id,
        role="assistant",
        text=agent_result["answer_text"],
        language=detected_lang,
        sources=[s.model_dump() for s in source_citations],
        confidence=agent_result.get("confidence", 1.0),
        stt_ms=stt_ms,
        llm_ms=agent_result["llm_ms"],
        tts_ms=tts_ms,
        latency_ms=total_latency_ms,
        ticket_id=ticket_obj.id if ticket_obj else None
    )
    db.add(user_msg)
    db.add(bot_msg)
    db.commit()

    return ChatResponse(
        transcript=transcript,
        language=detected_lang,
        answer_text=agent_result["answer_text"],
        audio_base64=audio_b64,
        audio_url=None,
        sources=source_citations,
        ticket=ticket_obj,
        confidence=agent_result.get("confidence"),
        latency_ms=total_latency_ms,
        stt_ms=stt_ms,
        llm_ms=agent_result["llm_ms"],
        tts_ms=tts_ms
    )


class TeluguVoiceComparisonRequest(BaseModel):
    text: Optional[str] = "గీతాంజలి ఇంజనీరింగ్ కళాశాలలో సెమిస్టర్ ఫీజు చెల్లించడానికి చివరి తేదీ ఎప్పుడు?"


@router.get("/voice/telugu-voices")
def get_telugu_voices():
    """Returns official Azure AI Speech Telugu Neural voice options and documentation."""
    from app.services.tts import TELUGU_NEURAL_VOICES
    return {
        "status": "success",
        "supported_voices": TELUGU_NEURAL_VOICES,
        "configured_default": settings.AZURE_SPEECH_TTS_VOICE_TE,
        "microsoft_learn_reference": "https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=tts#text-to-speech"
    }


@router.post("/voice/compare-telugu-voices")
def compare_telugu_voices(payload: Optional[TeluguVoiceComparisonRequest] = None):
    """
    Synthesizes real Telugu text with both te-IN-ShrutiNeural and te-IN-MohanNeural
    allowing direct side-by-side listening and latency comparison.
    """
    from app.services.tts import TELUGU_NEURAL_VOICES
    query_text = (
        payload.text.strip()
        if payload and payload.text
        else "గీతాంజలి ఇంజనీరింగ్ కళాశాలలో సెమిస్టర్ ఫీజు చెల్లించడానికి చివరి తేదీ ఎప్పుడు?"
    )

    results = {}
    for voice_id, meta in TELUGU_NEURAL_VOICES.items():
        audio_b64, latency_ms = synthesize_speech(query_text, language="te", voice_name=voice_id)
        results[voice_id] = {
            "voice_name": voice_id,
            "gender": meta["gender"],
            "style": meta["style"],
            "latency_ms": latency_ms,
            "audio_base64_available": audio_b64 is not None,
            "audio_base64": audio_b64
        }

    return {
        "query_text": query_text,
        "language": "te-IN",
        "comparison": results,
        "recommendation": {
            "helpdesk_conversational": "te-IN-ShrutiNeural (warm female tone, highly rated for interactive student bots)",
            "announcements_circulars": "te-IN-MohanNeural (formal male tone, clear and authoritative for administrative notices)"
        }
    }
