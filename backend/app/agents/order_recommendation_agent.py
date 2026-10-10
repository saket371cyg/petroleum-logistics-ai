"""
Order Recommendation Agent.

Target Inventory = Predicted Demand x Coverage Days + Safety Stock
Recommended Order = Target Inventory - Current Inventory
Clamped to [0, tank_capacity - current_inventory].
"""
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
import math
from math import ceil, floor
from typing import Any, Dict, List, Optional

from app import models as m
from app.core.config import settings
from app.core.dates import utc_now
from app.schemas import OrderRecommendationOut
from app.agents.inventory_agent import InventoryAgent
from app.agents.fleet_intelligence_agent import FleetIntelligenceAgent
from app.agents.maintenance_agent import MaintenanceAgent


class OrderRecommendationAgent:

    def __init__(self, db: Session):
        self.db = db
        self.inventory_agent = InventoryAgent(db)

    def recommend(
        self,
        dealer_id: int,
        fuel_type: str,
        coverage_days: Optional[float] = None,
        inbound_quantity_l: float = 0.0,
    ) -> OrderRecommendationOut:
        """Calculate an additional order quantity after accounting for open orders."""
        coverage_days = coverage_days or settings.DEFAULT_COVERAGE_DAYS
        inbound_quantity_l = max(float(inbound_quantity_l), 0.0)

        inv = (
            self.db.query(m.FuelInventory)
            .filter(m.FuelInventory.dealer_id == dealer_id, m.FuelInventory.fuel_type == fuel_type)
            .first()
        )
        if inv is None:
            raise ValueError(f"No inventory record for dealer {dealer_id} / {fuel_type}")

        risk = self.inventory_agent.compute_risk(dealer_id, fuel_type)
        predicted_demand = risk.predicted_daily_demand_l

        target_inventory = predicted_demand * coverage_days + inv.safety_stock_l
        projected_inventory = inv.current_level_l + inbound_quantity_l
        raw_order = target_inventory - projected_inventory

        max_possible = max(inv.tank_capacity_l - projected_inventory, 0)
        recommended_qty = min(max(raw_order, 0), max_possible)

        should_order = recommended_qty > 0

        explanation = (
            f"{fuel_type} demand is forecast at {predicted_demand:,.0f} L/day. "
            f"Target inventory to cover {coverage_days:.0f} days plus safety stock "
            f"({inv.safety_stock_l:,.0f} L) is {target_inventory:,.0f} L. "
            f"Current level is {inv.current_level_l:,.0f} L "
            f"({risk.days_of_stock} days of stock remaining, status={risk.status}). "
        )
        if inbound_quantity_l > 0:
            explanation += f"Open orders add {inbound_quantity_l:,.0f} L to projected supply. "
        if raw_order <= 0:
            explanation += "Current stock plus open orders meets or exceeds target; no additional order recommended."
        elif max_possible <= 0:
            explanation += (
                "Target inventory remains unmet, but current stock plus open orders already "
                "uses the available tank capacity; no feasible additional quantity can be recommended."
            )
        elif raw_order > max_possible:
            explanation += (
                f"Order capped to {recommended_qty:,.0f} L due to tank capacity "
                f"({inv.tank_capacity_l:,.0f} L)."
            )
        else:
            explanation += f"Recommended order: {recommended_qty:,.0f} L."

        return OrderRecommendationOut(
            fuel_type=fuel_type,
            should_order=should_order,
            recommended_quantity_l=round(recommended_qty, 0),
            target_inventory_l=round(target_inventory, 0),
            current_inventory_l=inv.current_level_l,
            explanation=explanation,
        )

    def analyze_all_fuels(self, dealer_id: int) -> List[Dict[str, Any]]:
        """Analyze and rank every configured fuel in a dealer's inventory."""
        inventories = (
            self.db.query(m.FuelInventory)
            .filter(m.FuelInventory.dealer_id == dealer_id)
            .order_by(m.FuelInventory.fuel_type.asc())
            .all()
        )
        results = [self._analyze_fuel(dealer_id, inventory) for inventory in inventories]
        return sorted(results, key=lambda item: (-item["priority_score"], item["fuel_type"]))

    def analyze_fuel(self, dealer_id: int, fuel_type: str) -> Dict[str, Any]:
        """Analyze one explicitly selected fuel using the same comparison metrics."""
        inventory = (
            self.db.query(m.FuelInventory)
            .filter(m.FuelInventory.dealer_id == dealer_id, m.FuelInventory.fuel_type == fuel_type)
            .first()
        )
        if inventory is None:
            return {}
        return self._analyze_fuel(dealer_id, inventory)

    def _analyze_fuel(self, dealer_id: int, inventory: m.FuelInventory) -> Dict[str, Any]:
        """Build data-backed risk, demand, inbound, and quantity metrics for one fuel."""
        fuel_type = inventory.fuel_type
        risk = self.inventory_agent.compute_risk(dealer_id, fuel_type)
        forecast = None
        try:
            forecast = self.inventory_agent.forecast_agent.predict(dealer_id, fuel_type, horizon_days=7)
        except (FileNotFoundError, ValueError, TypeError, IndexError):
            pass

        open_orders = (
            self.db.query(m.FuelOrder)
            .filter(
                m.FuelOrder.dealer_id == dealer_id,
                m.FuelOrder.fuel_type == fuel_type,
                m.FuelOrder.status.in_(["PENDING", "APPROVED"]),
            )
            .all()
        )
        order_ids = [order.id for order in open_orders]
        planned_dispatches = []
        if order_ids:
            planned_dispatches = (
                self.db.query(m.Dispatch)
                .filter(
                    m.Dispatch.order_id.in_(order_ids),
                    m.Dispatch.status.in_(["PLANNED", "APPROVED", "ACTIVE"]),
                )
                .order_by(m.Dispatch.eta.asc())
                .all()
            )

        planned_order_ids = {dispatch.order_id for dispatch in planned_dispatches}
        pending_quantity = sum(order.quantity_l for order in open_orders if order.status == "PENDING")
        approved_quantity = sum(order.quantity_l for order in open_orders if order.status == "APPROVED")
        open_quantity = pending_quantity + approved_quantity
        planned_quantity = sum(order.quantity_l for order in open_orders if order.id in planned_order_ids)
        recommendation = self.recommend(dealer_id, fuel_type, inbound_quantity_l=open_quantity)
        fleet_agent = FleetIntelligenceAgent(self.db)
        maintenance_agent = MaintenanceAgent(self.db)
        available_tankers = fleet_agent.available_tankers(dealer_id) if recommendation.should_order else []
        maintenance_safe_tankers = [
            tanker for tanker in available_tankers if maintenance_agent.is_safe_to_dispatch(tanker)
        ]
        requested_quantity = float(recommendation.recommended_quantity_l)
        largest_tanker_capacity = max((tanker.capacity_l for tanker in maintenance_safe_tankers), default=0.0)
        feasible_order_quantity = (
            min(requested_quantity, float(floor(largest_tanker_capacity)))
            if recommendation.should_order and maintenance_safe_tankers
            else requested_quantity
        )
        transport_capacity_limited = feasible_order_quantity < requested_quantity
        candidate_tankers = [
            tanker for tanker in maintenance_safe_tankers
            if tanker.capacity_l >= feasible_order_quantity
        ]
        candidate_drivers = fleet_agent.available_drivers(dealer_id) if recommendation.should_order else []
        future_slots = (
            self.db.query(m.LoadingSlot)
            .filter(m.LoadingSlot.status == "OPEN", m.LoadingSlot.slot_start >= utc_now())
            .order_by(m.LoadingSlot.slot_start.asc())
            .all()
            if recommendation.should_order else []
        )
        delivery_feasible = bool(candidate_tankers and candidate_drivers and future_slots) if recommendation.should_order else None
        feasibility_reasons: List[str] = []
        if recommendation.should_order and not candidate_tankers:
            if not available_tankers:
                feasibility_reasons.append("No available compliant tanker.")
            elif not maintenance_safe_tankers:
                feasibility_reasons.append("All available tankers are at high maintenance risk.")
            else:
                largest_capacity = max(tanker.capacity_l for tanker in maintenance_safe_tankers)
                feasibility_reasons.append(
                    f"No available maintenance-safe tanker can carry the recommended {requested_quantity:,.0f} L; "
                    f"largest eligible capacity is {largest_capacity:,.0f} L."
                )
        if recommendation.should_order and not candidate_drivers:
            feasibility_reasons.append("No available compliant driver.")
        if recommendation.should_order and not future_slots:
            feasibility_reasons.append("No future open loading slot.")

        predicted_daily = float(risk.predicted_daily_demand_l)
        current_coverage = inventory.current_level_l / predicted_daily if predicted_daily > 0 else None
        projected_inventory = inventory.current_level_l + open_quantity
        projected_coverage = projected_inventory / predicted_daily if predicted_daily > 0 else None
        safety_deficit = max(inventory.safety_stock_l - projected_inventory, 0.0)
        reorder_deficit = max(inventory.reorder_point_l - projected_inventory, 0.0)
        target_deficit = max(recommendation.target_inventory_l - projected_inventory, 0.0)
        capacity_headroom = max(inventory.tank_capacity_l - projected_inventory, 0.0)
        capacity_limited = target_deficit > 0 and capacity_headroom <= 0
        coverage_target_days = max(float(settings.DEFAULT_COVERAGE_DAYS), 1.0)
        coverage_pressure = self._ratio_deficit(
            coverage_target_days - (projected_coverage or 0.0), coverage_target_days
        )
        safety_pressure = self._ratio_deficit(safety_deficit, inventory.safety_stock_l)
        reorder_pressure = self._ratio_deficit(reorder_deficit, inventory.reorder_point_l)
        priority_score = round(100 * (0.5 * coverage_pressure + 0.3 * safety_pressure + 0.2 * reorder_pressure), 1)

        if projected_coverage is not None and projected_coverage <= settings.STOCK_CRITICAL_DAYS:
            urgency = "CRITICAL"
        elif projected_coverage is not None and projected_coverage <= settings.STOCK_WARNING_DAYS:
            urgency = "MEDIUM"
        else:
            urgency = "LOW"

        if recommendation.should_order and delivery_feasible:
            if transport_capacity_limited:
                recommended_action = "PARTIAL_ORDER"
            else:
                recommended_action = "ORDER_NOW" if urgency == "CRITICAL" else "ORDER_SOON"
        elif recommendation.should_order:
            recommended_action = "ORDER_BLOCKED"
        elif capacity_limited:
            recommended_action = "CAPACITY_LIMITED"
        elif open_quantity > 0:
            recommended_action = "WAIT_FOR_INBOUND"
        else:
            recommended_action = "NO_ORDER_REQUIRED"

        stockout_date = None
        if current_coverage is not None:
            stockout_date = (date.today() + timedelta(days=max(ceil(current_coverage), 0))).isoformat()

        score_explanation = (
            f"Priority score {priority_score}/100 weights projected coverage deficit 50%, "
            f"safety-stock deficit 30%, and reorder-point deficit 20%; open orders reduce projected deficit."
        )
        reasons = [recommendation.explanation, score_explanation]
        if forecast is None:
            reasons.append("Forecast model metrics are unavailable; demand uses the inventory agent's existing fallback.")

        lead_time_days = None
        lead_time_demand_l = None
        if delivery_feasible and future_slots:
            lead_time_days = max(0.25, round((future_slots[0].slot_start - utc_now()).total_seconds() / 86400.0, 2))
            lead_time_demand_l = round(predicted_daily * lead_time_days, 1)

        # Calibrated stock-out probability before replenishment arrival
        horizon = lead_time_days if lead_time_days else (1.0 if recommendation.should_order else (current_coverage or 1.0))
        rmse = forecast.rmse if (forecast and forecast.rmse) else max(predicted_daily * 0.12, 100.0)
        sigma_t = max(rmse * math.sqrt(horizon), 1.0)
        z = (projected_inventory - (predicted_daily * horizon)) / sigma_t
        stockout_prob = round(min(max(0.5 * (1.0 - math.erf(z / math.sqrt(2.0))), 0.0), 1.0), 3)

        # Operating headroom & min/max order bounds
        effective_consumption = predicted_daily * (lead_time_days or 1.0)
        stock_at_arrival = max(0.0, projected_inventory - effective_consumption)
        min_safe_quantity = max(0.0, inventory.safety_stock_l - stock_at_arrival)
        max_feasible_quantity = max(0.0, inventory.tank_capacity_l - stock_at_arrival)

        # Day-by-day consequence analysis
        daily_projection = []
        for d in range(1, 5):
            proj_stock = max(0.0, projected_inventory - (predicted_daily * d))
            sig_d = max(rmse * math.sqrt(float(d)), 1.0)
            z_d = (projected_inventory - (predicted_daily * d)) / sig_d
            p_d = round(min(max(0.5 * (1.0 - math.erf(z_d / math.sqrt(2.0))), 0.0), 1.0), 3)
            daily_projection.append({
                "day_offset": d,
                "date": (date.today() + timedelta(days=d)).isoformat(),
                "projected_stock_l": round(proj_stock, 0),
                "below_safety_stock": proj_stock < inventory.safety_stock_l,
                "stockout_probability": p_d,
                "status": "STOCKOUT" if proj_stock <= 0 else ("BELOW_SAFETY" if proj_stock < inventory.safety_stock_l else "SAFE"),
            })

        consequences = {
            "do_nothing_projection": daily_projection,
            "expected_stockout_date": stockout_date,
            "wait_two_days": {
                "projected_stock_after_2_days_l": round(max(0.0, projected_inventory - (predicted_daily * 2)), 0),
                "safety_stock_deficit_l": round(max(0.0, inventory.safety_stock_l - (projected_inventory - (predicted_daily * 2))), 0),
                "stockout_probability": daily_projection[1]["stockout_probability"] if len(daily_projection) > 1 else 0.0,
            },
            "order_too_much": {
                "tank_capacity_l": inventory.tank_capacity_l,
                "max_feasible_quantity_l": round(max_feasible_quantity, 0),
                "risk_summary": f"Exceeding {max_feasible_quantity:,.0f} L causes physical storage ullage overflow and locks dealer working capital.",
            },
        }

        return {
            "fuel_type": fuel_type,
            "current_inventory_l": inventory.current_level_l,
            "tank_capacity_l": inventory.tank_capacity_l,
            "average_consumption_l_per_day": self._average_daily_consumption(dealer_id, fuel_type),
            "forecast_demand_l_per_day": predicted_daily,
            "forecast_confidence": forecast.confidence if forecast else None,
            "demand_uncertainty_l_per_day": forecast.rmse if forecast else None,
            "forecast_source": forecast.model_version if forecast else "SAFETY_STOCK_BASELINE",
            "stock_coverage_days": round(current_coverage, 2) if current_coverage is not None else None,
            "projected_coverage_days": round(projected_coverage, 2) if projected_coverage is not None else None,
            "safety_stock_l": inventory.safety_stock_l,
            "reorder_threshold_l": inventory.reorder_point_l,
            "target_inventory_l": recommendation.target_inventory_l,
            "lead_time_days": lead_time_days,
            "lead_time_demand_l": lead_time_demand_l,
            "minimum_safe_quantity_l": round(min_safe_quantity, 0),
            "maximum_feasible_quantity_l": round(max_feasible_quantity, 0),
            "operating_headroom_note": (
                "Order quantity is constrained by the configured tank capacity. "
                "No separate operating headroom parameter is currently available in the database schema."
            ),
            "consequences": consequences,
            "safety_stock_deficit_l": round(safety_deficit, 1),
            "reorder_threshold_deficit_l": round(reorder_deficit, 1),
            "target_inventory_deficit_l": round(target_deficit, 1),
            "tank_capacity_headroom_l": round(capacity_headroom, 1),
            "capacity_limited": capacity_limited,
            "pending_order_quantity_l": round(pending_quantity, 1),
            "approved_order_quantity_l": round(approved_quantity, 1),
            "planned_delivery_quantity_l": round(planned_quantity, 1),
            "inbound_quantity_l": round(open_quantity, 1),
            "projected_inventory_after_inbound_l": round(projected_inventory, 1),
            "stockout_probability": stockout_prob,
            "projected_stockout_date": stockout_date,
            "risk_status": risk.status,
            "urgency": urgency,
            "priority_score": priority_score,
            "priority_score_explanation": score_explanation,
            "recommended_action": recommended_action,
            "recommended_quantity_l": int(feasible_order_quantity),
            "full_recommended_quantity_l": int(round(requested_quantity)),
            "remaining_order_quantity_l": int(max(round(requested_quantity - feasible_order_quantity), 0)),
            "transport_capacity_limited": transport_capacity_limited,
            "max_feasible_transport_quantity_l": int(floor(largest_tanker_capacity)) if maintenance_safe_tankers else None,
            "order_explanation": recommendation.explanation,
            "quantity_note": (
                f"First feasible delivery is capped at {feasible_order_quantity:,.0f} L by available tanker capacity; "
                f"{max(requested_quantity - feasible_order_quantity, 0):,.0f} L remains for follow-up."
                if transport_capacity_limited else None
            ),
            "delivery_feasibility": {
                "feasible": delivery_feasible,
                "tanker_count": len(candidate_tankers),
                "driver_count": len(candidate_drivers),
                "future_slot_count": len(future_slots),
                "reason": " ".join(feasibility_reasons) if feasibility_reasons else None,
            },
            "recommended_date": future_slots[0].slot_start.date().isoformat() if delivery_feasible else None,
            "recommended_tanker_id": candidate_tankers[0].id if delivery_feasible else None,
            "recommended_driver_id": candidate_drivers[0].id if delivery_feasible else None,
            "next_planned_eta": next((dispatch.eta.isoformat() for dispatch in planned_dispatches if dispatch.eta), None),
            "reasons": reasons,
        }

    @staticmethod
    def _ratio_deficit(deficit: float, target: float) -> float:
        """Return a bounded zero-to-one deficit ratio, or zero when target is absent."""
        if target <= 0:
            return 0.0
        return min(max(deficit / target, 0.0), 1.0)

    def _average_daily_consumption(self, dealer_id: int, fuel_type: str) -> Optional[float]:
        """Calculate observed average daily sales from available history."""
        sales = (
            self.db.query(m.DailySales)
            .filter(m.DailySales.dealer_id == dealer_id, m.DailySales.fuel_type == fuel_type)
            .order_by(m.DailySales.sale_date.desc())
            .limit(60)
            .all()
        )
        if not sales:
            return None
        daily_totals: Dict[date, float] = {}
        for sale in sales:
            daily_totals[sale.sale_date] = daily_totals.get(sale.sale_date, 0.0) + float(sale.quantity_l)
        return round(sum(daily_totals.values()) / len(daily_totals), 1)
