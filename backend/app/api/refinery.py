from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_user
from app.schemas import LoadingSlotOut, LoadingSlotCreate, RefineryOut
from app.agents.refinery_coordination_agent import RefineryCoordinationAgent
from app import models as m

router = APIRouter(prefix="/refinery-slots", tags=["refinery"])


@router.get("", response_model=List[LoadingSlotOut])
def list_slots(db: Session = Depends(get_db), current_user: m.User = Depends(get_current_user)):
    agent = RefineryCoordinationAgent(db)
    raw_slots = agent.list_open_slots()
    refineries = {r.id: r for r in db.query(m.Refinery).all()}

    enriched = []
    for s in raw_slots:
        ref = refineries.get(s.refinery_id)
        enriched.append(
            LoadingSlotOut(
                id=s.id,
                refinery_id=s.refinery_id,
                slot_start=s.slot_start,
                slot_end=s.slot_end,
                status=s.status,
                refinery_name=ref.name if ref else f"Refinery #{s.refinery_id}",
                refinery_location=ref.location if ref else "Unknown",
            )
        )
    return enriched


@router.get("/refineries", response_model=List[RefineryOut])
def list_refineries(db: Session = Depends(get_db), current_user: m.User = Depends(get_current_user)):
    return db.query(m.Refinery).all()


@router.post("", response_model=LoadingSlotOut)
def create_slot(
    payload: LoadingSlotCreate,
    db: Session = Depends(get_db),
    current_user: m.User = Depends(get_current_user),
):
    refinery = db.query(m.Refinery).filter(m.Refinery.id == payload.refinery_id).first()
    if not refinery:
        raise HTTPException(status_code=404, detail="Refinery not found")

    slot = m.LoadingSlot(
        refinery_id=payload.refinery_id,
        slot_start=payload.slot_start,
        slot_end=payload.slot_end,
        status=payload.status.upper(),
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)

    return LoadingSlotOut(
        id=slot.id,
        refinery_id=slot.refinery_id,
        slot_start=slot.slot_start,
        slot_end=slot.slot_end,
        status=slot.status,
        refinery_name=refinery.name,
        refinery_location=refinery.location,
    )
