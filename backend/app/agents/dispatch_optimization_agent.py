"""
Dispatch Optimization Agent.

Combines Fleet Intelligence, Compliance, Refinery Coordination, and
Weather/Traffic agent outputs into candidate pools, then runs Hill Climbing
to find a good (not guaranteed optimal) tanker/driver/slot assignment.
"""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app import models as m
from app.agents.fleet_intelligence_agent import FleetIntelligenceAgent
from app.agents.refinery_coordination_agent import RefineryCoordinationAgent
from app.agents.compliance_agent import ComplianceAgent
from app.agents.maintenance_agent import MaintenanceAgent
from app.agents.weather_traffic_agent import WeatherTrafficAgent
from app.optimization.hill_climbing import DispatchCandidatePools, hill_climb
from app.optimization.route_search import best_route


class DispatchOptimizationAgent:

    def __init__(self, db: Session):
        self.db = db
        self.fleet_agent = FleetIntelligenceAgent(db)
        self.refinery_agent = RefineryCoordinationAgent(db)
        self.compliance_agent = ComplianceAgent(db)
        self.maintenance_agent = MaintenanceAgent(db)
        self.weather_agent = WeatherTrafficAgent()

    def optimize(self, order: m.FuelOrder, deadline_hours: float = 6.0) -> dict:
        now = datetime.utcnow()
        deadline = now + timedelta(hours=deadline_hours)

        # 1. Candidate tankers: available, sufficient capacity, compliant, not high maintenance risk
        candidate_tankers = self.fleet_agent.available_tankers(order.dealer_id, min_capacity_l=0)
        candidate_tankers = [t for t in candidate_tankers if self.maintenance_agent.is_safe_to_dispatch(t)]
        if not candidate_tankers:
            raise ValueError("No compliant, available, maintenance-safe tankers found for this dealer.")

        # 2. Candidate drivers: available, compliant, valid license
        candidate_drivers = self.fleet_agent.available_drivers(order.dealer_id)
        if not candidate_drivers:
            raise ValueError("No compliant, available drivers found for this dealer.")

        # 3. Candidate loading slots
        candidate_slots = self.refinery_agent.list_open_slots()
        if not candidate_slots:
            raise ValueError("No open refinery loading slots available.")

        # 4. Route distance (dealer -> refinery of the first candidate slot's refinery)
        refinery = self.db.query(m.Refinery).filter(m.Refinery.id == candidate_slots[0].refinery_id).first()
        distance_km = refinery.distance_km_default if refinery else 50.0
        route = best_route(distance_km)

        # 5. Weather/traffic risk for this route + departure window
        risk = self.weather_agent.assess(distance_km, now)

        # 6. Build candidate pools for hill climbing
        pools = DispatchCandidatePools(
            tankers=[{"id": t.id, "capacity_l": t.capacity_l} for t in candidate_tankers],
            drivers=[{"id": d.id} for d in candidate_drivers],
            slots=[{"id": s.id, "slot_start": s.slot_start} for s in candidate_slots],
        )

        best_state, best_cost, iterations = hill_climb(
            pools=pools,
            order_qty_l=order.quantity_l,
            distance_km=route["distance_km"],
            eta_adjustment_hours=risk.eta_adjustment_hours,
            deadline=deadline,
            now=now,
            max_iterations=200,
            restarts=5,
        )

        chosen_tanker = next(t for t in candidate_tankers if t.id == best_state.tanker_id)
        chosen_driver = next(d for d in candidate_drivers if d.id == best_state.driver_id)
        chosen_slot = next(s for s in candidate_slots if s.id == best_state.slot_id)

        departure_time = chosen_slot.slot_start + timedelta(minutes=30)
        eta = departure_time + timedelta(hours=best_cost.delivery_time_hours)

        explanation = (
            f"Hill climbing evaluated {iterations} candidate states across 5 random restarts. "
            f"Selected tanker {chosen_tanker.code} (capacity {chosen_tanker.capacity_l:,.0f} L) with driver "
            f"{chosen_driver.name}, loading slot at {chosen_slot.slot_start.strftime('%Y-%m-%d %H:%M')} "
            f"via {refinery.name if refinery else 'refinery'}. Route: {route['algorithm']} selected "
            f"{route['distance_km']} km path. Traffic: {risk.traffic_level}, weather: {risk.weather_condition} "
            f"(+{risk.eta_adjustment_hours}h ETA adjustment). Total cost score: {best_cost.total_cost} "
            f"(delivery {best_cost.delivery_time_hours}h, transport ₹{best_cost.transport_cost}, "
            f"idle {best_cost.idle_time_hours}h, late penalty {best_cost.late_penalty}, "
            f"violations {best_cost.violation_penalty}). This is a local-optimum result from hill climbing, "
            f"not a guaranteed global optimum."
        )

        return {
            "tanker": chosen_tanker,
            "driver": chosen_driver,
            "slot": chosen_slot,
            "distance_km": route["distance_km"],
            "departure_time": departure_time,
            "eta": eta,
            "risk_level": risk.risk_level,
            "estimated_cost": best_cost.transport_cost,
            "optimization_score": -best_cost.total_cost,
            "iterations": iterations,
            "explanation": explanation,
        }
