from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_user, require_dealer_access
from app.schemas import (
    TankerOut,
    DriverOut,
    TankerCreate,
    TankerUpdate,
    DriverCreate,
    DriverUpdate,
)
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


@router.post("/tankers", response_model=TankerOut)
def create_tanker(
    payload: TankerCreate,
    db: Session = Depends(get_db),
    current_user: m.User = Depends(get_current_user),
):
    existing = db.query(m.Tanker).filter(
        m.Tanker.dealer_id == current_user.dealer_id,
        m.Tanker.code == payload.code.strip().upper(),
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Tanker with code {payload.code} already exists")

    tanker = m.Tanker(
        dealer_id=current_user.dealer_id,
        code=payload.code.strip().upper(),
        capacity_l=payload.capacity_l,
        status=payload.status.upper(),
        mileage_km=payload.mileage_km,
        age_years=payload.age_years,
        current_location=payload.current_location,
    )
    db.add(tanker)
    db.commit()
    db.refresh(tanker)
    return tanker


@router.patch("/tankers/{tanker_id}", response_model=TankerOut)
def update_tanker(
    tanker_id: int,
    payload: TankerUpdate,
    db: Session = Depends(get_db),
    current_user: m.User = Depends(get_current_user),
):
    tanker = db.query(m.Tanker).filter(
        m.Tanker.id == tanker_id,
        m.Tanker.dealer_id == current_user.dealer_id,
    ).first()
    if not tanker:
        raise HTTPException(status_code=404, detail="Tanker not found")

    if payload.capacity_l is not None:
        tanker.capacity_l = payload.capacity_l
    if payload.status is not None:
        tanker.status = payload.status.upper()
    if payload.mileage_km is not None:
        tanker.mileage_km = payload.mileage_km
    if payload.age_years is not None:
        tanker.age_years = payload.age_years
    if payload.current_location is not None:
        tanker.current_location = payload.current_location

    db.commit()
    db.refresh(tanker)
    return tanker


@router.delete("/tankers/{tanker_id}")
def delete_tanker(
    tanker_id: int,
    db: Session = Depends(get_db),
    current_user: m.User = Depends(get_current_user),
):
    tanker = db.query(m.Tanker).filter(
        m.Tanker.id == tanker_id,
        m.Tanker.dealer_id == current_user.dealer_id,
    ).first()
    if not tanker:
        raise HTTPException(status_code=404, detail="Tanker not found")

    active_dispatch = db.query(m.Dispatch).filter(
        m.Dispatch.tanker_id == tanker_id,
        m.Dispatch.status.in_(["PLANNED", "APPROVED", "ACTIVE"]),
    ).first()
    if active_dispatch:
        raise HTTPException(status_code=400, detail="Cannot delete tanker assigned to active dispatch")

    db.delete(tanker)
    db.commit()
    return {"message": f"Tanker {tanker.code} deleted successfully"}


@router.get("/{dealer_id}/drivers", response_model=List[DriverOut])
def all_drivers(dealer_id: int, db: Session = Depends(get_db), _=Depends(require_dealer_access)):
    return db.query(m.Driver).filter(m.Driver.dealer_id == dealer_id).all()


@router.post("/drivers", response_model=DriverOut)
def create_driver(
    payload: DriverCreate,
    db: Session = Depends(get_db),
    current_user: m.User = Depends(get_current_user),
):
    driver = m.Driver(
        dealer_id=current_user.dealer_id,
        name=payload.name.strip(),
        license_number=payload.license_number.strip().upper(),
        license_expiry=payload.license_expiry,
        status=payload.status.upper(),
    )
    db.add(driver)
    db.commit()
    db.refresh(driver)
    return driver


@router.patch("/drivers/{driver_id}", response_model=DriverOut)
def update_driver(
    driver_id: int,
    payload: DriverUpdate,
    db: Session = Depends(get_db),
    current_user: m.User = Depends(get_current_user),
):
    driver = db.query(m.Driver).filter(
        m.Driver.id == driver_id,
        m.Driver.dealer_id == current_user.dealer_id,
    ).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    if payload.name is not None:
        driver.name = payload.name.strip()
    if payload.license_number is not None:
        driver.license_number = payload.license_number.strip().upper()
    if payload.license_expiry is not None:
        driver.license_expiry = payload.license_expiry
    if payload.status is not None:
        driver.status = payload.status.upper()

    db.commit()
    db.refresh(driver)
    return driver


@router.delete("/drivers/{driver_id}")
def delete_driver(
    driver_id: int,
    db: Session = Depends(get_db),
    current_user: m.User = Depends(get_current_user),
):
    driver = db.query(m.Driver).filter(
        m.Driver.id == driver_id,
        m.Driver.dealer_id == current_user.dealer_id,
    ).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    active_dispatch = db.query(m.Dispatch).filter(
        m.Dispatch.driver_id == driver_id,
        m.Dispatch.status.in_(["PLANNED", "APPROVED", "ACTIVE"]),
    ).first()
    if active_dispatch:
        raise HTTPException(status_code=400, detail="Cannot delete driver assigned to active dispatch")

    db.delete(driver)
    db.commit()
    return {"message": f"Driver {driver.name} deleted successfully"}
