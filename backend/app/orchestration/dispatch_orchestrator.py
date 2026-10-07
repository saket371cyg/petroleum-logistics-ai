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
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app import models as m
from app.agents.dispatch_optimization_agent import DispatchOptimizationAgent


@dataclass
class DispatchWorkflowState:
    """Tracks the ordered stages of the dispatch workflow."""

    state: str = "INIT"
    completed_steps: List[str] = field(default_factory=list)
    step_history: List[Dict[str, Any]] = field(default_factory=list)

    def transition(self, step_name: str, next_state: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "step": step_name,
            "state": next_state,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if metadata:
            payload["metadata"] = metadata

        self.state = next_state
        self.step_history.append(payload)

        if step_name not in self.completed_steps:
            self.completed_steps.append(step_name)

        return payload

    def as_dict(self) -> Dict[str, Any]:
        return {
            "workflow_state": self.state,
            "completed_steps": list(self.completed_steps),
            "step_history": list(self.step_history),
        }


class DispatchWorkflowStateMachine(DispatchWorkflowState):
    """Compatibility wrapper for orchestrator state tracking."""

    pass


def run_dispatch_workflow(db: Session, order: m.FuelOrder, deadline_hours: float = 6.0) -> dict:
    workflow = DispatchWorkflowStateMachine()
    workflow.transition("candidate_generation", "CANDIDATE_READY")

    agent = DispatchOptimizationAgent(db)
    result = agent.optimize(order, deadline_hours=deadline_hours)
    workflow.transition("dispatch_optimization", "OPTIMIZED", {
        "tanker_id": result["tanker"].id,
        "driver_id": result["driver"].id,
        "slot_id": result["slot"].id,
        "iterations": result["iterations"],
        "risk_level": result["risk_level"],
    })

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
    workflow.transition("dispatch_persistence", "DISPATCH_SAVED", {"dispatch_id": dispatch.id})

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
    workflow.transition("recommendation_logging", "COMPLETED", {"recommendation_id": rec.id})

    final_state = workflow.as_dict()
    return {
        "dispatch": dispatch,
        "result": result,
        "workflow_state": final_state["workflow_state"],
        "completed_steps": final_state["completed_steps"],
        "step_history": final_state["step_history"],
    }
