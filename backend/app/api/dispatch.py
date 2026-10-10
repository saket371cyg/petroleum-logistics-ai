from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_user, require_dealer_access
from app.core.dates import utc_now
from app.schemas import DispatchOptimizeRequest, DispatchOptimizeResponse, DispatchOut
from app.orchestration.dispatch_orchestrator import run_dispatch_workflow
from app import models as m

router = APIRouter(prefix="/dispatch", tags=["dispatch"])


@router.post("/optimize", response_model=DispatchOptimizeResponse)
def optimize_dispatch(payload: DispatchOptimizeRequest, db: Session = Depends(get_db), current_user: m.User = Depends(get_current_user)):
    order = db.query(m.FuelOrder).filter(m.FuelOrder.id == payload.order_id, m.FuelOrder.dealer_id == current_user.dealer_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != "APPROVED":
        raise HTTPException(status_code=400, detail="Order must be APPROVED before dispatch optimization")

    try:
        outcome = run_dispatch_workflow(db, order, deadline_hours=payload.deadline_hours)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    dispatch = outcome["dispatch"]
    result = outcome["result"]

    return DispatchOptimizeResponse(
        dispatch_id=dispatch.id,
        recommended_tanker=result["tanker"].code,
        recommended_driver=result["driver"].name,
        loading_slot_start=result["slot"].slot_start,
        departure_time=result["departure_time"],
        eta=result["eta"],
        estimated_cost=result["estimated_cost"],
        risk_level=result["risk_level"],
        optimization_score=result["optimization_score"],
        iterations_run=result["iterations"],
        explanation=result["explanation"],
    )


@router.get("/{dealer_id}", response_model=List[DispatchOut])
def list_dispatches(dealer_id: int, db: Session = Depends(get_db), _=Depends(require_dealer_access)):
    return db.query(m.Dispatch).filter(m.Dispatch.dealer_id == dealer_id).order_by(m.Dispatch.created_at.desc()).all()


@router.post("/{dispatch_id}/approve", response_model=DispatchOut)
def approve_dispatch(dispatch_id: int, db: Session = Depends(get_db), current_user: m.User = Depends(get_current_user)):
    dispatch = db.query(m.Dispatch).filter(m.Dispatch.id == dispatch_id, m.Dispatch.dealer_id == current_user.dealer_id).first()
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    dispatch.status = "ACTIVE"

    tanker = db.query(m.Tanker).filter(m.Tanker.id == dispatch.tanker_id).first()
    if tanker:
        tanker.status = "IN_TRANSIT"

    slot = db.query(m.LoadingSlot).filter(m.LoadingSlot.id == dispatch.loading_slot_id).first()
    if slot:
        slot.status = "BOOKED"

    order = db.query(m.FuelOrder).filter(m.FuelOrder.id == dispatch.order_id).first()
    if order:
        order.status = "FULFILLED"

    db.commit()
    db.refresh(dispatch)
    return dispatch


@router.post("/{dispatch_id}/complete", response_model=DispatchOut)
def complete_dispatch(dispatch_id: int, db: Session = Depends(get_db), current_user: m.User = Depends(get_current_user)):
    """Simulates delivery completion for the demo flow (in production, triggered by a driver-app event)."""
    dispatch = db.query(m.Dispatch).filter(m.Dispatch.id == dispatch_id, m.Dispatch.dealer_id == current_user.dealer_id).first()
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    dispatch.status = "DELIVERED"
    dispatch.actual_arrival = utc_now()

    tanker = db.query(m.Tanker).filter(m.Tanker.id == dispatch.tanker_id).first()
    if tanker:
        tanker.status = "AVAILABLE"

    order = db.query(m.FuelOrder).filter(m.FuelOrder.id == dispatch.order_id).first()
    if order:
        inv = db.query(m.FuelInventory).filter(
            m.FuelInventory.dealer_id == dispatch.dealer_id,
            m.FuelInventory.fuel_type == order.fuel_type,
        ).first()
        if inv:
            inv.current_level_l = min(inv.tank_capacity_l, inv.current_level_l + order.quantity_l)

    db.commit()
    db.refresh(dispatch)
    return dispatch
