"""
Basic tests for the Inventory and Order Recommendation agents, using an
isolated in-memory SQLite DB so tests don't touch the dev database.
"""
import os
import sys
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import Base
from app import models as m
from app.agents.inventory_agent import InventoryAgent
from app.agents.order_recommendation_agent import OrderRecommendationAgent


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


def test_order_recommendation_never_exceeds_capacity(db_session):
    agent = OrderRecommendationAgent(db_session)
    rec = agent.recommend(1, "DIESEL")
    inv = db_session.query(m.FuelInventory).filter_by(dealer_id=1, fuel_type="DIESEL").first()
    assert rec.recommended_quantity_l <= (inv.tank_capacity_l - inv.current_level_l) + 1e-6
