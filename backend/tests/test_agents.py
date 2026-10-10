"""
Basic tests for the Inventory and Order Recommendation agents, using an
isolated in-memory SQLite DB so tests don't touch the dev database.
"""
import os
import sys
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import Base
from app.core.dates import utc_now
from app import models as m
from app.agents.inventory_agent import InventoryAgent
from app.agents.order_recommendation_agent import OrderRecommendationAgent
from app.schemas import InventoryRiskOut


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    dealer = m.Dealer(id=1, name="Test Dealer", location="Test City")
    session.add(dealer)

    inv = m.FuelInventory(
        dealer_id=1, fuel_type="DIESEL",
        current_level_l=5000, tank_capacity_l=50000,
        safety_stock_l=10000, reorder_point_l=15000,
    )
    session.add(inv)

    # 30 days of flat sales history so the forecast agent's fallback isn't needed to test math
    for i in range(30):
        session.add(m.DailySales(dealer_id=1, fuel_type="DIESEL", sale_date=date(2026, 1, i + 1), quantity_l=1000))

    session.commit()
    yield session
    session.close()


def test_inventory_risk_critical_when_stock_low(db_session):
    agent = InventoryAgent(db_session)
    risk = agent.compute_risk(1, "DIESEL")
    assert risk.fuel_type == "DIESEL"
    assert risk.days_of_stock > 0
    assert risk.status in ("NORMAL", "WARNING", "CRITICAL")


def test_order_recommendation_never_negative(db_session):
    agent = OrderRecommendationAgent(db_session)
    rec = agent.recommend(1, "DIESEL")
    assert rec.recommended_quantity_l >= 0


def test_order_recommendation_flags_positive_quantity_even_when_risk_is_normal(db_session):
    inventory = db_session.query(m.FuelInventory).filter_by(dealer_id=1, fuel_type="DIESEL").first()
    predicted_daily_demand = InventoryAgent(db_session).compute_risk(1, "DIESEL").predicted_daily_demand_l
    inventory.current_level_l = predicted_daily_demand * 4
    db_session.commit()

    risk = InventoryAgent(db_session).compute_risk(1, "DIESEL")
    recommendation = OrderRecommendationAgent(db_session).recommend(1, "DIESEL")

    assert risk.status == "NORMAL"
    assert recommendation.recommended_quantity_l > 0
    assert recommendation.should_order is True


def test_order_recommendation_never_exceeds_capacity(db_session):
    agent = OrderRecommendationAgent(db_session)
    rec = agent.recommend(1, "DIESEL")
    inv = db_session.query(m.FuelInventory).filter_by(dealer_id=1, fuel_type="DIESEL").first()
    assert rec.recommended_quantity_l <= (inv.tank_capacity_l - inv.current_level_l) + 1e-6


def test_full_tank_with_unmet_target_is_capacity_limited(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """Do not describe a full tank with forecast deficit as no-order-needed."""
    inventory = db_session.query(m.FuelInventory).filter_by(dealer_id=1, fuel_type="DIESEL").first()
    inventory.current_level_l = inventory.tank_capacity_l
    db_session.commit()
    agent = OrderRecommendationAgent(db_session)
    monkeypatch.setattr(
        agent.inventory_agent,
        "compute_risk",
        lambda _dealer_id, _fuel_type: InventoryRiskOut(
            fuel_type="DIESEL",
            current_level_l=inventory.current_level_l,
            predicted_daily_demand_l=10000,
            days_of_stock=5,
            status="NORMAL",
            reorder_point_l=15000,
        ),
    )

    result = agent.analyze_fuel(1, "DIESEL")

    assert result["recommended_quantity_l"] == 0
    assert result["capacity_limited"] is True
    assert result["target_inventory_deficit_l"] == 10000
    assert result["recommended_action"] == "CAPACITY_LIMITED"


def test_recommendation_uses_feasible_first_tranche_when_tanker_is_smaller(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Recommend a deliverable first tranche and expose the remaining target quantity."""
    inventory = db_session.query(m.FuelInventory).filter_by(dealer_id=1, fuel_type="DIESEL").first()
    inventory.current_level_l = 40000
    db_session.add_all(
        [
            m.Tanker(id=10, dealer_id=1, code="T-6000", capacity_l=6000, status="AVAILABLE", mileage_km=0, age_years=1, last_service_date=date.today()),
            m.Driver(id=10, dealer_id=1, name="Test Driver", license_number="DL-6000", license_expiry=date.today() + timedelta(days=365), status="AVAILABLE"),
            m.Refinery(id=10, name="Test Refinery", location="Test City", distance_km_default=50),
            m.LoadingSlot(id=10, refinery_id=10, slot_start=utc_now() + timedelta(hours=2), slot_end=utc_now() + timedelta(hours=3), status="OPEN"),
        ]
    )
    db_session.commit()
    agent = OrderRecommendationAgent(db_session)
    monkeypatch.setattr(
        agent.inventory_agent,
        "compute_risk",
        lambda _dealer_id, _fuel_type: InventoryRiskOut(
            fuel_type="DIESEL",
            current_level_l=40000,
            predicted_daily_demand_l=10000,
            days_of_stock=4,
            status="NORMAL",
            reorder_point_l=15000,
        ),
    )

    result = agent.analyze_fuel(1, "DIESEL")

    assert result["full_recommended_quantity_l"] == 10000
    assert result["recommended_quantity_l"] == 6000
    assert result["remaining_order_quantity_l"] == 4000
    assert result["transport_capacity_limited"] is True
    assert result["delivery_feasibility"]["feasible"] is True
    assert result["recommended_action"] == "PARTIAL_ORDER"
