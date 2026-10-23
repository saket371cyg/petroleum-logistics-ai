from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import require_dealer_access
from app.core.dates import utc_now
from app.schemas import InventoryOut, InventoryRiskOut, InventoryUpdate, InventorySimulateConsumption
from app.agents.inventory_agent import InventoryAgent
from app import models as m

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/{dealer_id}", response_model=List[InventoryOut])
def get_inventory(dealer_id: int, db: Session = Depends(get_db), _=Depends(require_dealer_access)):
    agent = InventoryAgent(db)
    return agent.get_inventory(dealer_id)


@router.get("/{dealer_id}/risk", response_model=List[InventoryRiskOut])
def get_inventory_risk(dealer_id: int, db: Session = Depends(get_db), _=Depends(require_dealer_access)):
    agent = InventoryAgent(db)
    return agent.compute_all_risks(dealer_id)


@router.put("/{dealer_id}/{fuel_type}", response_model=InventoryOut)
def update_inventory(
    dealer_id: int,
    fuel_type: str,
    payload: InventoryUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_dealer_access),
):
    inv = db.query(m.FuelInventory).filter(
        m.FuelInventory.dealer_id == dealer_id,
        m.FuelInventory.fuel_type == fuel_type.upper(),
    ).first()
    if not inv:
        raise HTTPException(status_code=404, detail=f"Inventory for {fuel_type} not found")

    if payload.current_level_l is not None:
        if payload.current_level_l < 0:
            raise HTTPException(status_code=400, detail="Stock level cannot be negative")
        if payload.current_level_l > inv.tank_capacity_l:
            raise HTTPException(
                status_code=400,
                detail=f"Stock level cannot exceed tank capacity ({inv.tank_capacity_l:,.0f} L)",
            )
        inv.current_level_l = payload.current_level_l

    if payload.safety_stock_l is not None:
        if payload.safety_stock_l < 0:
            raise HTTPException(status_code=400, detail="Safety stock cannot be negative")
        inv.safety_stock_l = payload.safety_stock_l

    if payload.reorder_point_l is not None:
        if payload.reorder_point_l < 0:
            raise HTTPException(status_code=400, detail="Reorder point cannot be negative")
        inv.reorder_point_l = payload.reorder_point_l

    inv.updated_at = utc_now()
    db.commit()
    db.refresh(inv)
    return inv


@router.post("/{dealer_id}/simulate-consumption", response_model=List[InventoryOut])
def simulate_consumption(
    dealer_id: int,
    payload: InventorySimulateConsumption,
    db: Session = Depends(get_db),
    _=Depends(require_dealer_access),
):
    agent = InventoryAgent(db)
    inventories = agent.get_inventory(dealer_id)
    if payload.fuel_type:
        inventories = [i for i in inventories if i.fuel_type == payload.fuel_type.upper()]

    for inv in inventories:
        risk = agent.compute_risk(dealer_id, inv.fuel_type)
        daily_demand = max(risk.predicted_daily_demand_l, 1000.0)
        reduction = daily_demand * payload.days
        inv.current_level_l = max(0.0, inv.current_level_l - reduction)
        inv.updated_at = utc_now()

    db.commit()
    for inv in inventories:
        db.refresh(inv)
    return agent.get_inventory(dealer_id)
