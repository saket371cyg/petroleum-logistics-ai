"""
Executive Decision Intelligence Agent.

Aggregates outputs from the other agents into a daily operational summary.
Per the spec: this agent must NOT invent numbers — every figure here is
read from the database or computed by a deterministic model, and the
summary text is built with a template, not an LLM, so nothing is fabricated.
"""
from datetime import datetime
from statistics import mean

from sqlalchemy.orm import Session

from app import models as m
from app.schemas import AnalyticsOut
from app.agents.inventory_agent import InventoryAgent
from app.agents.fleet_intelligence_agent import FleetIntelligenceAgent
from app.agents.compliance_agent import ComplianceAgent


class ExecutiveAgent:

    def __init__(self, db: Session):
        self.db = db
        self.inventory_agent = InventoryAgent(db)
        self.fleet_agent = FleetIntelligenceAgent(db)
        self.compliance_agent = ComplianceAgent(db)

    def daily_summary(self, dealer_id: int) -> AnalyticsOut:
        inv = {row.fuel_type: row for row in self.inventory_agent.get_inventory(dealer_id)}
        petrol_stock = inv.get("PETROL").current_level_l if "PETROL" in inv else 0.0
        diesel_stock = inv.get("DIESEL").current_level_l if "DIESEL" in inv else 0.0

        pending_orders = self.db.query(m.FuelOrder).filter(
            m.FuelOrder.dealer_id == dealer_id, m.FuelOrder.status == "PENDING"
        ).count()

        available_tankers = len(self.fleet_agent.available_tankers(dealer_id))

        active_dispatches = self.db.query(m.Dispatch).filter(
            m.Dispatch.dealer_id == dealer_id, m.Dispatch.status.in_(["PLANNED", "APPROVED", "ACTIVE"])
        ).count()

        compliance_alerts = self.compliance_agent.alerts_for_dealer(dealer_id)
        critical_alerts = sum(1 for a in compliance_alerts if a.status == "EXPIRED")
        risks = self.inventory_agent.compute_all_risks(dealer_id)
        critical_alerts += sum(1 for r in risks if r.status == "CRITICAL")

        delivered = self.db.query(m.Dispatch).filter(
            m.Dispatch.dealer_id == dealer_id, m.Dispatch.status == "DELIVERED",
            m.Dispatch.departure_time.isnot(None), m.Dispatch.actual_arrival.isnot(None),
        ).all()
        durations = [
            (d.actual_arrival - d.departure_time).total_seconds() / 3600.0
            for d in delivered if d.actual_arrival and d.departure_time
        ]
        avg_delivery_hours = round(mean(durations), 2) if durations else None

        fleet_utilization = self.fleet_agent.fleet_utilization_pct(dealer_id)

        summary_lines = []
        for r in risks:
            summary_lines.append(f"{r.fuel_type}: {r.current_level_l:,.0f} L on hand, "
                                  f"{r.days_of_stock} days of stock ({r.status}).")
        summary_lines.append(f"{pending_orders} pending order(s), {active_dispatches} active dispatch(es).")
        summary_lines.append(f"{available_tankers} tanker(s) available, fleet utilization {fleet_utilization}%.")
        if critical_alerts:
            summary_lines.append(f"{critical_alerts} critical/expired alert(s) require attention.")
        else:
            summary_lines.append("No critical alerts at this time.")

        return AnalyticsOut(
            dealer_id=dealer_id,
            generated_at=datetime.utcnow(),
            petrol_stock_l=petrol_stock,
            diesel_stock_l=diesel_stock,
            pending_orders=pending_orders,
            available_tankers=available_tankers,
            active_dispatches=active_dispatches,
            critical_alerts=critical_alerts,
            avg_delivery_hours=avg_delivery_hours,
            fleet_utilization_pct=fleet_utilization,
            summary_text=" ".join(summary_lines),
        )
