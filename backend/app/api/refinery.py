from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_user
from app.schemas import LoadingSlotOut
from app.agents.refinery_coordination_agent import RefineryCoordinationAgent
from app import models as m

router = APIRouter(prefix="/refinery-slots", tags=["refinery"])


@router.get("", response_model=List[LoadingSlotOut])
def list_slots(db: Session = Depends(get_db), current_user: m.User = Depends(get_current_user)):
    agent = RefineryCoordinationAgent(db)
    return agent.list_open_slots()
