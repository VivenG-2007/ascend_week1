from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db
from app.deps import get_agent, get_tts_service
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import handle_turn
from app.services.llm_agent import Agent
from app.services.ratelimit import chat_limit
from app.services.tts import TextToSpeech

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(chat_limit)])
def chat(req: ChatRequest, db: Session = Depends(get_db), agent: Agent = Depends(get_agent),
         tts: TextToSpeech | None = Depends(get_tts_service)) -> ChatResponse:
    started = perf_counter()
    max_chars = get_settings().max_question_chars
    if len(req.question) > max_chars:
        raise HTTPException(status_code=422, detail=f"Question is too long (maximum {max_chars} characters).")
    return handle_turn(db, agent, question=req.question, language=req.language, session_id=req.session_id,
                       department=req.department, speak=req.speak, tts=tts, started=started)
