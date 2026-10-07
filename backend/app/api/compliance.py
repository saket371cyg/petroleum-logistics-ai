from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import require_dealer_access
from app.schemas import ComplianceAlertOut, MaintenanceAlertOut
from app.agents.compliance_agent import ComplianceAgent
from app.agents.maintenance_agent import MaintenanceAgent

router = APIRouter(tags=["compliance-maintenance"])


@router.get("/compliance/{dealer_id}", response_model=List[ComplianceAlertOut])
def compliance_alerts(dealer_id: int, db: Session = Depends(get_db), _=Depends(require_dealer_access)):
    agent = ComplianceAgent(db)
    return agent.alerts_for_dealer(dealer_id)


@router.get("/maintenance/{dealer_id}", response_model=List[MaintenanceAlertOut])
def maintenance_alerts(dealer_id: int, db: Session = Depends(get_db), _=Depends(require_dealer_access)):
    agent = MaintenanceAgent(db)
    return agent.alerts_for_dealer(dealer_id)
