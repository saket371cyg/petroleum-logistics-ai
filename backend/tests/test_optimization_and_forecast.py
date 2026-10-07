from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models as m
from app.core.db import Base
from app.optimization.hill_climbing import DispatchCandidatePools, benchmark_hill_climb
from app.agents.demand_forecast_agent import DemandForecastAgent


@pytest.fixture
def sales_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    dealer = m.Dealer(id=1, name="Forecast Dealer", location="Test City")
    session.add(dealer)
    for day in range(45):
        sale_date = date(2026, 1, 1) + timedelta(days=day)
        session.add(
            m.DailySales(
                dealer_id=1,
                fuel_type="DIESEL",
                sale_date=sale_date,
                quantity_l=1200 + ((day % 7) * 40),
            )
        )
    session.commit()
    return session


def test_hill_climb_benchmark_returns_summary():
    pools = DispatchCandidatePools(
        tankers=[{"id": 1, "capacity_l": 18000}, {"id": 2, "capacity_l": 25000}],
        drivers=[{"id": 10}, {"id": 11}],
        slots=[
            {"id": 21, "slot_start": datetime.utcnow() + timedelta(hours=2)},
            {"id": 22, "slot_start": datetime.utcnow() + timedelta(hours=4)},
        ],
    )

    summary = benchmark_hill_climb(
        pools=pools,
        order_qty_l=15000,
        distance_km=90,
        eta_adjustment_hours=1.5,
        deadline=datetime.utcnow() + timedelta(hours=7),
        now=datetime.utcnow(),
        restarts=3,
    )

    assert summary["restarts"] == 3
    assert summary["best_total_cost"] >= 0
    assert "best_state" in summary
    assert 0.0 <= summary["success_rate"] <= 1.0


def test_demand_forecast_falls_back_without_model(sales_session):
    agent = DemandForecastAgent(sales_session)

    def _missing_model(*args, **kwargs):
        raise FileNotFoundError("No trained model")

    agent._load_model = _missing_model
    forecast = agent.predict(1, "DIESEL", horizon_days=5)

    assert forecast.model_version == "baseline_v1"
    assert len(forecast.points) == 5
    assert all(point.predicted_qty_l >= 0 for point in forecast.points)
