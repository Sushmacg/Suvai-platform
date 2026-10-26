from fastapi import APIRouter, Depends, HTTPException

from app.ai import service
from app.ai.llm import AssistantUnavailable, build_llm
from app.ai.schemas import ChatRequest, ChatResponse
from app.ai.settings import get_ai_settings
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_role

# Admin-only. All provider calls stay here on the server.
router = APIRouter(
    prefix="/assistant", tags=["assistant"], dependencies=[Depends(require_role("admin"))]
)


def get_llm():
    try:
        return build_llm(get_ai_settings())
    except AssistantUnavailable as exc:
        raise HTTPException(exc.status_code, exc.message)


@router.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, llm=Depends(get_llm), db: Session = Depends(get_db)):
    try:
        answer = service.ask(llm, body.question, db)
    except AssistantUnavailable as exc:
        raise HTTPException(exc.status_code, exc.message)
    return {"answer": answer}