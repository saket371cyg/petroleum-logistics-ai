from datetime import date, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models as m
from app.core.db import Base
from app.core.dates import utc_now
from app.orchestration.dispatch_orchestrator import run_dispatch_workflow


def _build_order_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    dealer = m.Dealer(id=1, name="Test Dealer", location="Test City")
    session.add(dealer)
    session.flush()

    tanker = m.Tanker(
        id=1,
        dealer_id=dealer.id,
        code="T-900",
        capacity_l=20000,
        status="AVAILABLE",
        mileage_km=500,
        age_years=1.0,
    )
    driver = m.Driver(
        id=1,
        dealer_id=dealer.id,
        name="Test Driver",
        license_number="DL-12345",
        license_expiry=date.today() + timedelta(days=365),
        status="AVAILABLE",
    )
    refinery = m.Refinery(id=1, name="Test Refinery", location="Test City", distance_km_default=60.0)
    slot = m.LoadingSlot(
        id=1,
        refinery_id=refinery.id,
        slot_start=utc_now() + timedelta(hours=2),
        slot_end=utc_now() + timedelta(hours=4),
        status="OPEN",
    )
    session.add_all([tanker, driver, refinery, slot])
    session.add(
        m.MaintenanceRecord(
            tanker_id=tanker.id,
            service_date=date.today(),
            mileage_at_service=0,
            issue_notes="Routine service",
            next_due_date=date.today() + timedelta(days=180),
        )
    )
    session.add(
        m.FuelOrder(
            id=1,
            dealer_id=dealer.id,
            fuel_type="DIESEL",
            quantity_l=15000,
            status="APPROVED",
            explanation="Test order",
        )
    )
    session.commit()
    return session, dealer, tanker, driver, refinery, slot


def test_dispatch_workflow_tracks_state_machine():
    session, _, _, _, _, _ = _build_order_session()
    order = session.query(m.FuelOrder).first()

    outcome = run_dispatch_workflow(session, order)

    assert outcome["workflow_state"] == "COMPLETED"
    assert "dispatch" in outcome
    assert "result" in outcome
    assert outcome["step_history"][-1]["state"] == "COMPLETED"
    assert outcome["completed_steps"]
