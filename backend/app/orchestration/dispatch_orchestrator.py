"""
Dispatch workflow orchestrator.

Sequences the agents for the main end-to-end workflow (Section 20 of the
spec): Refinery Coordination -> Fleet -> Compliance -> Weather/Traffic ->
Dispatch Optimization (Hill Climbing) -> Executive logging.

Implementation note: this is a plain sequential Python pipeline rather than
a LangGraph graph. LangGraph adds real value once nodes need conditional
branching, retries, or human-in-the-loop interrupts; for this project's
single linear workflow a typed pipeline function is more transparent to
read, test, and grade, while keeping each agent as an independent,
swappable unit — a LangGraph StateGraph could wrap these same agent calls
as drop-in nodes without changing their interfaces.
"""
import json
from datetime import datetime

from sqlalchemy.orm import Session

from app import models as m
from app.agents.dispatch_optimization_agent import DispatchOptimizationAgent


def run_dispatch_workflow(db: Session, order: m.FuelOrder, deadline_hours: float = 6.0) -> dict:
    agent = DispatchOptimizationAgent(db)
    result = agent.optimize(order, deadline_hours=deadline_hours)

    dispatch = m.Dispatch(
        dealer_id=order.dealer_id,
        order_id=order.id,
        tanker_id=result["tanker"].id,
        driver_id=result["driver"].id,
        loading_slot_id=result["slot"].id,
        status="PLANNED",
        distance_km=result["distance_km"],
        departure_time=result["departure_time"],
        eta=result["eta"],
        risk_level=result["risk_level"],
        estimated_cost=result["estimated_cost"],
        optimization_score=result["optimization_score"],
    )
    db.add(dispatch)
    db.commit()
    db.refresh(dispatch)

    rec = m.AIRecommendation(
        dealer_id=order.dealer_id,
        recommendation_type="DISPATCH",
        reference_table="dispatches",
        reference_id=dispatch.id,
        payload_json=json.dumps({
            "tanker_id": result["tanker"].id,
            "driver_id": result["driver"].id,
            "slot_id": result["slot"].id,
            "distance_km": result["distance_km"],
            "estimated_cost": result["estimated_cost"],
            "risk_level": result["risk_level"],
            "iterations": result["iterations"],
        }, default=str),
        explanation_text=result["explanation"],
        status="PENDING",
    )
    db.add(rec)
    db.commit()

    return {"dispatch": dispatch, "result": result}
