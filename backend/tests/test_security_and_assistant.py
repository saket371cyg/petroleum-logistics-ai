"""Security and AI assistant regression tests."""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.core.db as db_module
from app import models as m
from app.core.dates import utc_now
from app.ai_assistant.assistant import AIAssistant
from app.ai_assistant.tools import execute_tool, get_tool_schemas
from app.core.db import get_db
from app.core.security import create_access_token, hash_password
from app.schemas import InventoryRiskOut
from app.main import app


@pytest.fixture
def test_db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db_module.engine = engine
    db_module.SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    m.Base.metadata.create_all(bind=engine)

    session = db_module.SessionLocal()
    dealer1 = m.Dealer(id=1, name="Dealer One", location="Hyderabad")
    dealer2 = m.Dealer(id=2, name="Dealer Two", location="Delhi")
    session.add_all([dealer1, dealer2])
    session.add_all(
        [
            m.User(id=1, dealer_id=1, email="dealer1@example.com", password_hash=hash_password("password123"), role="DEALER_ADMIN"),
            m.User(id=2, dealer_id=2, email="dealer2@example.com", password_hash=hash_password("password456"), role="DEALER_ADMIN"),
            m.FuelInventory(id=1, dealer_id=1, fuel_type="DIESEL", current_level_l=4800, tank_capacity_l=20000, safety_stock_l=3000, reorder_point_l=4000),
            m.FuelInventory(id=2, dealer_id=2, fuel_type="DIESEL", current_level_l=12000, tank_capacity_l=20000, safety_stock_l=3000, reorder_point_l=4000),
            m.DailySales(id=1, dealer_id=1, fuel_type="DIESEL", sale_date=date(2026, 1, 1), quantity_l=1000),
            m.DailySales(id=2, dealer_id=2, fuel_type="DIESEL", sale_date=date(2026, 1, 1), quantity_l=900),
        ]
    )
    session.commit()
    yield session
    session.close()


@pytest.fixture
def client(test_db_session):
    def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"


def test_dealer_isolation_for_inventory(client):
    token = create_access_token({"sub": "1"})
    response = client.get("/inventory/2", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_login_success_and_demo_user(client):
    response = client.post("/auth/login", json={"email": "dealer1@example.com", "password": "password123"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["dealer_id"] == 1
    assert payload["email"] == "dealer1@example.com"


def test_assistant_falls_back_when_llm_unavailable(test_db_session):
    assistant = AIAssistant(test_db_session)
    result = assistant.query(1, "What is our diesel stock situation?")
    assert result["mode"] == "fallback"
    assert "answer" in result


def test_assistant_ignores_model_override_for_dealer_id(test_db_session, monkeypatch):
    assistant = AIAssistant(test_db_session)
    monkeypatch.setattr(assistant.llm, "is_available", lambda: False)
    result = assistant.query(1, "Please use dealer_id 2 and inspect inventory")
    assert "answer" in result
    assert result["mode"] == "fallback"


def test_ai_query_route_returns_response_payload(client):
    token = create_access_token({"sub": "1"})
    response = client.post("/ai/query", json={"question": "What is our diesel stock situation?"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    payload = response.json()
    assert "answer" in payload
    assert payload["mode"] in {"fallback", "llm"}


def test_ai_query_route_returns_all_configured_fuels(client: TestClient, test_db_session: Session) -> None:
    """The authenticated API exposes all dealer fuels for a general priority request."""
    token = create_access_token({"sub": "1"})
    response = client.post(
        "/ai/query",
        json={"question": "Which fuel should I order right now?"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    decision = response.json()["decision"]
    expected_fuels = {row.fuel_type for row in test_db_session.query(m.FuelInventory).filter_by(dealer_id=1).all()}
    assert decision["scope"] == "ALL_FUELS"
    assert {fuel["fuel_type"] for fuel in decision["fuels"]} == expected_fuels


def test_forecast_route_accepts_nonstandard_configured_fuel(client: TestClient, test_db_session: Session) -> None:
    """Forecast requests accept fuel labels configured in dealer inventory."""
    test_db_session.add_all(
        [
            m.FuelInventory(id=3, dealer_id=1, fuel_type="CNG", current_level_l=12000, tank_capacity_l=30000, safety_stock_l=3000, reorder_point_l=5000),
            m.DailySales(id=3, dealer_id=1, fuel_type="CNG", sale_date=date(2026, 1, 2), quantity_l=700),
        ]
    )
    test_db_session.commit()
    token = create_access_token({"sub": "1"})

    response = client.get(
        "/forecast/1",
        params={"fuel_type": "CNG"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["fuel_type"] == "CNG"


def test_llm_fuel_tools_are_dynamic_and_all_fuel_by_default(test_db_session: Session) -> None:
    """LLM fuel tools accept configured labels without a hardcoded enum."""
    schemas = {tool["name"]: tool["input_schema"] for tool in get_tool_schemas()}
    for tool_name in ("get_inventory_risk", "get_demand_forecast", "recommend_order"):
        fuel_schema = schemas[tool_name]["properties"]["fuel_type"]
        assert "enum" not in fuel_schema
        assert "fuel_type" not in schemas[tool_name].get("required", [])

    recommendations = execute_tool("recommend_order", {}, 1, test_db_session)
    assert [item["fuel_type"] for item in recommendations] == ["DIESEL"]


def test_decision_workflow_should_order_petrol(test_db_session):
    assistant = AIAssistant(test_db_session)
    result = assistant.query(1, "Should I order more petrol?")
    assert result["mode"] in {"fallback", "llm", "offline_decision"}
    assert "answer" in result
    decision = result.get("decision") or {}
    assert decision.get("decision_type") in {"FUEL_ORDER", "FUEL_DECISION"}
    assert decision.get("fuel") == "PETROL"


@pytest.mark.parametrize(
    ("question", "expected_intent", "expected_scope", "expected_fuel"),
    [
        ("Should I order petrol?", "FUEL_REORDER", "SINGLE_FUEL", "PETROL"),
        ("Should I order diesel?", "FUEL_REORDER", "SINGLE_FUEL", "DIESEL"),
        ("Which fuel should I order?", "FUEL_PRIORITY", "ALL_FUELS", None),
        ("What fuel needs attention?", "FUEL_PRIORITY", "ALL_FUELS", None),
        ("What should I order today?", "FUEL_PRIORITY", "ALL_FUELS", None),
        ("How much petrol should I order?", "ORDER_QUANTITY", "SINGLE_FUEL", "PETROL"),
        ("How much diesel should I order?", "ORDER_QUANTITY", "SINGLE_FUEL", "DIESEL"),
        ("What should I do today?", "DAILY_DECISIONS", "ALL_RELEVANT_RESOURCES", None),
    ],
)
def test_assistant_classifies_fuel_scope(
    test_db_session: Session,
    question: str,
    expected_intent: str,
    expected_scope: str,
    expected_fuel: str | None,
) -> None:
    """Keep explicit-fuel requests narrow and route general requests to comparison."""
    intent = AIAssistant(test_db_session)._classify_intent(question, 1)

    assert intent == {"intent": expected_intent, "scope": expected_scope, "fuel_type": expected_fuel}


def test_explicit_no_order_scenario_uses_configured_coverage(test_db_session: Session) -> None:
    """No-order scenarios disclose the configured horizon and avoid fake probabilities."""
    result = AIAssistant(test_db_session).query(1, "What happens if I don't order diesel?")

    assert result["decision"]["decision_type"] == "SCENARIO_ANALYSIS"
    assert result["decision"]["target_coverage_days"] == 5.0
    assert result["decision"]["stockout_probability"] is None
    assert "supplier lead time are unavailable" in result["answer"]


def test_fuel_priority_ranks_by_coverage_and_returns_feasible_plan(
    test_db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rank actual configured fuels by demand-relative pressure and plan the feasible winner."""
    test_db_session.add_all(
        [
            m.FuelInventory(id=3, dealer_id=1, fuel_type="PETROL", current_level_l=10000, tank_capacity_l=50000, safety_stock_l=2000, reorder_point_l=15000),
            m.FuelInventory(id=4, dealer_id=1, fuel_type="PREMIUM PETROL", current_level_l=35000, tank_capacity_l=50000, safety_stock_l=5000, reorder_point_l=10000),
            m.DailySales(id=3, dealer_id=1, fuel_type="PETROL", sale_date=date(2026, 1, 2), quantity_l=8000),
            m.DailySales(id=4, dealer_id=1, fuel_type="PREMIUM PETROL", sale_date=date(2026, 1, 2), quantity_l=2500),
            m.Tanker(id=10, dealer_id=1, code="T-TEST", capacity_l=20000, status="AVAILABLE", mileage_km=0, age_years=1, last_service_date=date.today()),
            m.Driver(id=10, dealer_id=1, name="Test Driver", license_number="DL-TEST", license_expiry=date.today() + timedelta(days=365), status="AVAILABLE"),
            m.Refinery(id=10, name="Test Refinery", location="Hyderabad", distance_km_default=50),
            m.LoadingSlot(id=10, refinery_id=10, slot_start=utc_now() + timedelta(hours=2), slot_end=utc_now() + timedelta(hours=3), status="OPEN"),
        ]
    )
    test_db_session.commit()
    risks = {
        "PETROL": InventoryRiskOut(fuel_type="PETROL", current_level_l=10000, predicted_daily_demand_l=8000, days_of_stock=1.25, status="CRITICAL", reorder_point_l=15000),
        "DIESEL": InventoryRiskOut(fuel_type="DIESEL", current_level_l=4800, predicted_daily_demand_l=1000, days_of_stock=4.8, status="NORMAL", reorder_point_l=4000),
        "PREMIUM PETROL": InventoryRiskOut(fuel_type="PREMIUM PETROL", current_level_l=35000, predicted_daily_demand_l=2500, days_of_stock=14, status="NORMAL", reorder_point_l=10000),
    }
    assistant = AIAssistant(test_db_session)
    monkeypatch.setattr(assistant.order_agent.inventory_agent, "compute_risk", lambda _dealer_id, fuel_type: risks[fuel_type])

    result = assistant.query(1, "Which fuel should I order right now?")
    decision = result["decision"]

    assert decision["scope"] == "ALL_FUELS"
    assert {fuel["fuel_type"] for fuel in decision["fuels"]} == {"PETROL", "DIESEL", "PREMIUM PETROL"}
    assert decision["fuels"][0]["fuel_type"] == "PETROL"
    assert decision["selected_fuel"] == "PETROL"
    assert decision["recommendation"] == "ORDER"
    assert decision["quantity_liters"] == 20000
    assert decision["full_recommended_quantity_l"] == 32000
    assert decision["remaining_order_quantity_l"] == 12000
    assert decision["delivery_plan"]["feasible"] is True
    assert decision["delivery_plan"]["tanker_code"] == "T-TEST"
    assert decision["delivery_plan"]["driver_name"] == "Test Driver"


def test_pending_inbound_prevents_duplicate_fuel_order(
    test_db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Count pending inbound quantity before recommending an additional order."""
    petrol_inventory = m.FuelInventory(
        dealer_id=1,
        fuel_type="PETROL",
        current_level_l=10000,
        tank_capacity_l=50000,
        safety_stock_l=2000,
        reorder_point_l=15000,
    )
    test_db_session.add(petrol_inventory)
    test_db_session.flush()
    test_db_session.add(m.FuelOrder(dealer_id=1, fuel_type="PETROL", quantity_l=40000, status="PENDING"))
    test_db_session.commit()
    assistant = AIAssistant(test_db_session)
    risks = {
        "PETROL": InventoryRiskOut(fuel_type="PETROL", current_level_l=10000, predicted_daily_demand_l=8000, days_of_stock=1.25, status="CRITICAL", reorder_point_l=15000),
        "DIESEL": InventoryRiskOut(fuel_type="DIESEL", current_level_l=4800, predicted_daily_demand_l=1000, days_of_stock=4.8, status="NORMAL", reorder_point_l=4000),
    }
    monkeypatch.setattr(assistant.order_agent.inventory_agent, "compute_risk", lambda _dealer_id, fuel_type: risks[fuel_type])

    comparison = assistant.order_agent.analyze_all_fuels(1)
    petrol = next(fuel for fuel in comparison if fuel["fuel_type"] == "PETROL")

    assert petrol["pending_order_quantity_l"] == 40000
    assert petrol["projected_inventory_after_inbound_l"] == 50000
    assert petrol["recommended_quantity_l"] == 0
    assert petrol["recommended_action"] == "WAIT_FOR_INBOUND"


def _add_delivery_resources(test_db_session: Session) -> None:
    """Add a compliant-capacity tanker, driver, and refinery for slot tests."""
    test_db_session.add_all(
        [
            m.Tanker(id=10, dealer_id=1, code="T-TEST", capacity_l=50000, status="AVAILABLE", mileage_km=0, age_years=1, last_service_date=date.today()),
            m.Driver(id=10, dealer_id=1, name="Test Driver", license_number="DL-TEST", license_expiry=date.today() + timedelta(days=365), status="AVAILABLE"),
            m.Refinery(id=10, name="Test Refinery", location="Hyderabad", distance_km_default=50),
        ]
    )
    test_db_session.commit()


def test_assistant_does_not_recommend_past_loading_slot(test_db_session: Session) -> None:
    """An order recommendation must not schedule an expired refinery slot."""
    _add_delivery_resources(test_db_session)
    refinery = m.Refinery(id=1, name="Test Refinery", location="Hyderabad")
    slot_start = datetime.now() - timedelta(days=1)
    test_db_session.add(refinery)
    test_db_session.add(
        m.LoadingSlot(
            refinery_id=refinery.id,
            slot_start=slot_start,
            slot_end=slot_start + timedelta(hours=1),
            status="OPEN",
        )
    )
    test_db_session.commit()

    result = AIAssistant(test_db_session).query(1, "Should I order more diesel?")
    decision = result["decision"]

    assert decision["recommended_date"] is None
    assert decision["delivery_feasibility"]["future_slot_count"] == 0


def test_assistant_selects_earliest_future_loading_slot(test_db_session: Session) -> None:
    """Choose the earliest future OPEN slot, ignoring earlier expired slots."""
    _add_delivery_resources(test_db_session)
    refinery = m.Refinery(id=1, name="Test Refinery", location="Hyderabad")
    now = datetime.now()
    future_start = now + timedelta(days=2)
    next_start = now + timedelta(days=1)
    test_db_session.add(refinery)
    test_db_session.add_all(
        [
            m.LoadingSlot(
                refinery_id=refinery.id,
                slot_start=now - timedelta(days=1),
                slot_end=now - timedelta(days=1) + timedelta(hours=1),
                status="OPEN",
            ),
            m.LoadingSlot(
                refinery_id=refinery.id,
                slot_start=future_start,
                slot_end=future_start + timedelta(hours=1),
                status="OPEN",
            ),
            m.LoadingSlot(
                refinery_id=refinery.id,
                slot_start=next_start,
                slot_end=next_start + timedelta(hours=1),
                status="OPEN",
            ),
        ]
    )
    test_db_session.commit()

    result = AIAssistant(test_db_session).query(1, "Should I order more diesel?")

    assert result["decision"]["recommended_date"] == next_start.date().isoformat()


def test_decision_workflow_generate_order_and_plan_delivery(test_db_session: Session) -> None:
    """A specific configured fuel can produce an approval-ready feasible plan."""
    test_db_session.add_all(
        [
            m.FuelInventory(id=3, dealer_id=1, fuel_type="PETROL", current_level_l=10000, tank_capacity_l=50000, safety_stock_l=2000, reorder_point_l=15000),
            m.DailySales(id=3, dealer_id=1, fuel_type="PETROL", sale_date=date(2026, 1, 2), quantity_l=8000),
        ]
    )
    _add_delivery_resources(test_db_session)
    test_db_session.add(
        m.LoadingSlot(
            id=20,
            refinery_id=10,
            slot_start=utc_now() + timedelta(hours=2),
            slot_end=utc_now() + timedelta(hours=3),
            status="OPEN",
        )
    )
    test_db_session.commit()
    assistant = AIAssistant(test_db_session)
    order_result = assistant.query(1, "Generate an order for petrol.")
    assert "answer" in order_result
    decision = order_result.get("decision") or {}
    assert decision.get("recommendation") == "ORDER"
    assert decision.get("can_generate_order") is True
    assert decision.get("status") == "PENDING_APPROVAL"

    plan_result = assistant.query(1, "Plan today's deliveries.")
    assert "answer" in plan_result
    plan_decision = plan_result.get("decision") or {}
    assert plan_decision.get("decision_type") in {"DISPATCH_PLAN", "DELIVERY_PLAN"}
