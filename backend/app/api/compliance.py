from datetime import date, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_user, require_dealer_access
from app.schemas import (
    ComplianceAlertOut,
    MaintenanceAlertOut,
    MaintenanceRecordCreate,
    ComplianceRecordCreate,
    ComplianceRenewRequest,
)
from app.agents.compliance_agent import ComplianceAgent
from app.agents.maintenance_agent import MaintenanceAgent
from app import models as m

router = APIRouter(tags=["compliance-maintenance"])


@router.get("/compliance/{dealer_id}", response_model=List[ComplianceAlertOut])
def compliance_alerts(dealer_id: int, db: Session = Depends(get_db), _=Depends(require_dealer_access)):
    agent = ComplianceAgent(db)
    return agent.alerts_for_dealer(dealer_id)


@router.post("/compliance/renew")
def renew_compliance(
    payload: ComplianceRenewRequest,
    db: Session = Depends(get_db),
    current_user: m.User = Depends(get_current_user),
):
    record = db.query(m.ComplianceRecord).filter(
        m.ComplianceRecord.entity_type == payload.entity_type.upper(),
        m.ComplianceRecord.entity_id == payload.entity_id,
        m.ComplianceRecord.doc_type == payload.doc_type.upper(),
    ).first()

    today = date.today()
    status = "VALID" if payload.new_expiry_date >= today else "EXPIRED"

    if not record:
        record = m.ComplianceRecord(
            entity_type=payload.entity_type.upper(),
            entity_id=payload.entity_id,
            doc_type=payload.doc_type.upper(),
            expiry_date=payload.new_expiry_date,
            status=status,
        )
        db.add(record)
    else:
        record.expiry_date = payload.new_expiry_date
        record.status = status

    # Also sync Driver.license_expiry if entity is driver and doc is LICENSE
    if payload.entity_type.upper() == "DRIVER" and payload.doc_type.upper() == "LICENSE":
        driver = db.query(m.Driver).filter(
            m.Driver.id == payload.entity_id,
            m.Driver.dealer_id == current_user.dealer_id,
        ).first()
        if driver:
            driver.license_expiry = payload.new_expiry_date

    db.commit()
    db.refresh(record)
    return {
        "message": f"Document {record.doc_type} renewed to {record.expiry_date}",
        "status": record.status,
    }


@router.post("/compliance")
def create_compliance_record(
    payload: ComplianceRecordCreate,
    db: Session = Depends(get_db),
    current_user: m.User = Depends(get_current_user),
):
    today = date.today()
    status = "VALID" if payload.expiry_date >= today else "EXPIRED"
    record = m.ComplianceRecord(
        entity_type=payload.entity_type.upper(),
        entity_id=payload.entity_id,
        doc_type=payload.doc_type.upper(),
        expiry_date=payload.expiry_date,
        status=status,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"message": "Compliance record created successfully", "id": record.id}


@router.get("/maintenance/{dealer_id}", response_model=List[MaintenanceAlertOut])
def maintenance_alerts(dealer_id: int, db: Session = Depends(get_db), _=Depends(require_dealer_access)):
    agent = MaintenanceAgent(db)
    return agent.alerts_for_dealer(dealer_id)


@router.post("/maintenance/log")
def log_maintenance(
    payload: MaintenanceRecordCreate,
    db: Session = Depends(get_db),
    current_user: m.User = Depends(get_current_user),
):
    tanker = db.query(m.Tanker).filter(
        m.Tanker.id == payload.tanker_id,
        m.Tanker.dealer_id == current_user.dealer_id,
    ).first()
    if not tanker:
        raise HTTPException(status_code=404, detail="Tanker not found")

    svc_date = payload.service_date or date.today()
    mileage = payload.mileage_at_service if payload.mileage_at_service is not None else tanker.mileage_km
    due_date = payload.next_due_date or (svc_date + timedelta(days=180))

    record = m.MaintenanceRecord(
        tanker_id=tanker.id,
        service_date=svc_date,
        mileage_at_service=mileage,
        issue_notes=payload.issue_notes or "Routine preventive maintenance & inspection",
        next_due_date=due_date,
    )
    db.add(record)

    tanker.last_service_date = svc_date
    if mileage > tanker.mileage_km:
        tanker.mileage_km = mileage
    if tanker.status == "MAINTENANCE":
        tanker.status = "AVAILABLE"

    db.commit()
    db.refresh(record)

    agent = MaintenanceAgent(db)
    score, level, rec_date, reason = agent._risk_for_tanker(tanker)
    return {
        "message": f"Maintenance logged for {tanker.code}. Risk reduced to {score}/100 ({level}).",
        "tanker_id": tanker.id,
        "tanker_code": tanker.code,
        "risk_score": score,
        "risk_level": level,
        "status": tanker.status,
    }
