from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_user, require_dealer_access
from app.schemas import AnalyticsOut, AIQueryRequest, AIQueryResponse
from app.agents.executive_agent import ExecutiveAgent
from app.ai_assistant.assistant import AIAssistant
from app import models as m

router = APIRouter(tags=["analytics"])


@router.get("/analytics/{dealer_id}", response_model=AnalyticsOut)
def analytics(dealer_id: int, db: Session = Depends(get_db), _=Depends(require_dealer_access)):
    agent = ExecutiveAgent(db)
    return agent.daily_summary(dealer_id)


@router.get("/dashboard", response_model=AnalyticsOut)
def dashboard(db: Session = Depends(get_db), current_user: m.User = Depends(get_current_user)):
    agent = ExecutiveAgent(db)
    return agent.daily_summary(current_user.dealer_id)


@router.post("/ai/query", response_model=AIQueryResponse)
def ai_query(payload: AIQueryRequest, db: Session = Depends(get_db), current_user: m.User = Depends(get_current_user)):
    assistant = AIAssistant(db)
    result = assistant.query(current_user.dealer_id, payload.question)
    return AIQueryResponse(
        answer=result["answer"],
        data_sources=result.get("data_sources", result.get("sources", [])),
        sources=result.get("sources", result.get("data_sources", [])),
        tool_trace=result.get("tool_trace", []),
        mode=result.get("mode", "fallback"),
    )
