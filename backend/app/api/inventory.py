from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import require_dealer_access
from app.schemas import InventoryOut, InventoryRiskOut
from app.agents.inventory_agent import InventoryAgent

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/{dealer_id}", response_model=List[InventoryOut])
def get_inventory(dealer_id: int, db: Session = Depends(get_db), _=Depends(require_dealer_access)):
    agent = InventoryAgent(db)
    return agent.get_inventory(dealer_id)


@router.get("/{dealer_id}/risk", response_model=List[InventoryRiskOut])
def get_inventory_risk(dealer_id: int, db: Session = Depends(get_db), _=Depends(require_dealer_access)):
    agent = InventoryAgent(db)
    return agent.compute_all_risks(dealer_id)
