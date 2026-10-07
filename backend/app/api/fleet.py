from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_user, require_dealer_access
from app.schemas import TankerOut, DriverOut
from app.agents.fleet_intelligence_agent import FleetIntelligenceAgent
from app import models as m

router = APIRouter(prefix="/fleet", tags=["fleet"])


@router.get("/available", response_model=List[TankerOut])
def available_tankers(db: Session = Depends(get_db), current_user: m.User = Depends(get_current_user)):
    agent = FleetIntelligenceAgent(db)
    return agent.available_tankers(current_user.dealer_id)


@router.get("/{dealer_id}", response_model=List[TankerOut])
def all_tankers(dealer_id: int, db: Session = Depends(get_db), _=Depends(require_dealer_access)):
    return db.query(m.Tanker).filter(m.Tanker.dealer_id == dealer_id).all()


@router.get("/{dealer_id}/drivers", response_model=List[DriverOut])
def all_drivers(dealer_id: int, db: Session = Depends(get_db), _=Depends(require_dealer_access)):
    return db.query(m.Driver).filter(m.Driver.dealer_id == dealer_id).all()
