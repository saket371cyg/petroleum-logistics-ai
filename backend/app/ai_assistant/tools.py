"""Tool schemas and executor for the agentic assistant.

The LLM is never trusted to choose its own dealer_id. Every tool receives the
authenticated dealer from the session and therefore stays within tenant
boundaries.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.agents.compliance_agent import ComplianceAgent
from app.agents.demand_forecast_agent import DemandForecastAgent
from app.agents.executive_agent import ExecutiveAgent
from app.agents.fleet_intelligence_agent import FleetIntelligenceAgent
from app.agents.inventory_agent import InventoryAgent
from app.agents.maintenance_agent import MaintenanceAgent
from app.agents.order_recommendation_agent import OrderRecommendationAgent
from app.ai_assistant.knowledge_base import KnowledgeBaseRetriever


def get_tool_schemas() -> List[Dict[str, Any]]:
    """Return JSON-schema tool definitions used by the Anthropic client."""
    return [
        {
            "name": "get_inventory_risk",
            "description": "Get fuel inventory status and risk for a dealer.",
            "input_schema": {
                "type": "object",
                "properties": {"fuel_type": {"type": "string", "description": "Exact configured fuel type; omit to analyze all fuels."}},
            },
        },
        {
            "name": "get_demand_forecast",
            "description": "Get a demand forecast for the selected dealer and fuel type.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "fuel_type": {"type": "string", "description": "Exact configured fuel type; omit to forecast all fuels."},
                    "horizon_days": {"type": "integer", "minimum": 1, "maximum": 30},
                },
            },
        },
        {
            "name": "recommend_order",
            "description": "Recommend a fuel order for the selected dealer.",
            "input_schema": {
                "type": "object",
                "properties": {"fuel_type": {"type": "string", "description": "Exact configured fuel type; omit to compare all fuels."}},
            },
        },
        {
            "name": "list_available_tankers",
            "description": "List currently available tanker assets for a dealer.",
            "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "list_available_drivers",
            "description": "List available drivers for a dealer.",
            "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "get_compliance_alerts",
            "description": "Return compliance alerts for the selected dealer.",
            "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "get_maintenance_alerts",
            "description": "Return maintenance alerts for the selected dealer.",
            "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "get_weather_traffic_risk",
            "description": "Return weather and traffic risk for the selected dealer.",
            "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "plan_dispatch",
            "description": "Return a dry-run dispatch plan without committing any changes.",
            "input_schema": {"type": "object", "properties": {"order_id": {"type": "integer"}}, "required": ["order_id"]},
        },
        {
            "name": "get_daily_summary",
            "description": "Return a daily operational summary for the selected dealer.",
            "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "search_knowledge_base",
            "description": "Search the local offline knowledge base for policy and safety guidance.",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    ]


def execute_tool(name: str, arguments: Dict[str, Any], dealer_id: int, db: Session) -> Dict[str, Any]:
    """Execute a whitelisted tool with the tenant-scoped dealer_id attached."""
    dealer_id = int(dealer_id)
    if name == "get_inventory_risk":
        fuel_type = (arguments or {}).get("fuel_type")
        agent = InventoryAgent(db)
        return [risk.model_dump() for risk in agent.compute_all_risks(dealer_id)] if not fuel_type or fuel_type == "ALL" else agent.compute_risk(dealer_id, fuel_type).model_dump()

    if name == "get_demand_forecast":
        fuel_type = (arguments or {}).get("fuel_type")
        horizon_days = int((arguments or {}).get("horizon_days", 7))
        agent = DemandForecastAgent(db)
        if fuel_type:
            try:
                return agent.predict(dealer_id, fuel_type, horizon_days=horizon_days).model_dump()
            except (FileNotFoundError, ValueError, TypeError, IndexError) as error:
                return {"fuel_type": fuel_type, "status": "INSUFFICIENT_DATA", "reason": str(error)}
        forecasts = []
        for inventory in InventoryAgent(db).get_inventory(dealer_id):
            try:
                forecasts.append(agent.predict(dealer_id, inventory.fuel_type, horizon_days=horizon_days).model_dump())
            except (FileNotFoundError, ValueError, TypeError, IndexError) as error:
                forecasts.append({"fuel_type": inventory.fuel_type, "status": "INSUFFICIENT_DATA", "reason": str(error)})
        return forecasts

    if name == "recommend_order":
        fuel_type = (arguments or {}).get("fuel_type")
        agent = OrderRecommendationAgent(db)
        if not fuel_type:
            return agent.analyze_all_fuels(dealer_id)
        return agent.recommend(dealer_id, fuel_type).model_dump()

    if name == "list_available_tankers":
        tankers = FleetIntelligenceAgent(db).available_tankers(dealer_id)
        return [{"id": t.id, "code": t.code, "status": t.status, "capacity_l": t.capacity_l} for t in tankers]

    if name == "list_available_drivers":
        drivers = FleetIntelligenceAgent(db).available_drivers(dealer_id)
        return [{"id": d.id, "name": d.name, "license_number": d.license_number, "status": d.status} for d in drivers]

    if name == "get_compliance_alerts":
        alerts = ComplianceAgent(db).alerts_for_dealer(dealer_id)
        return [alert.model_dump() for alert in alerts]

    if name == "get_maintenance_alerts":
        alerts = MaintenanceAgent(db).alerts_for_dealer(dealer_id)
        return [alert.model_dump() for alert in alerts]

    if name == "get_weather_traffic_risk":
        weather = {"source": "synthetic", "risk_level": "LOW", "notes": "No live feed configured."}
        return weather

    if name == "plan_dispatch":
        order_id = int((arguments or {}).get("order_id", 0))
        return {"dry_run": True, "order_id": order_id, "status": "planned", "dealer_id": dealer_id}

    if name == "get_daily_summary":
        summary = ExecutiveAgent(db).daily_summary(dealer_id)
        return summary.model_dump()

    if name == "search_knowledge_base":
        query = (arguments or {}).get("query", "")
        retriever = KnowledgeBaseRetriever()
        return {"results": retriever.search(query, top_k=3)}

    raise ValueError(f"Tool {name!r} is not whitelisted")
