"""
Order Recommendation Agent.

Target Inventory = Predicted Demand x Coverage Days + Safety Stock
Recommended Order = Target Inventory - Current Inventory
Clamped to [0, tank_capacity - current_inventory].
"""
from sqlalchemy.orm import Session

from app import models as m
from app.core.config import settings
from app.schemas import OrderRecommendationOut
from app.agents.inventory_agent import InventoryAgent


class OrderRecommendationAgent:

    def __init__(self, db: Session):
        self.db = db
        self.inventory_agent = InventoryAgent(db)

    def recommend(self, dealer_id: int, fuel_type: str,
                  coverage_days: float = None) -> OrderRecommendationOut:
        coverage_days = coverage_days or settings.DEFAULT_COVERAGE_DAYS

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
        raw_order = target_inventory - inv.current_level_l

        max_possible = max(inv.tank_capacity_l - inv.current_level_l, 0)
        recommended_qty = min(max(raw_order, 0), max_possible)

        should_order = recommended_qty > 0 and risk.status in ("WARNING", "CRITICAL")

        explanation = (
            f"{fuel_type} demand is forecast at {predicted_demand:,.0f} L/day. "
            f"Target inventory to cover {coverage_days:.0f} days plus safety stock "
            f"({inv.safety_stock_l:,.0f} L) is {target_inventory:,.0f} L. "
            f"Current level is {inv.current_level_l:,.0f} L "
            f"({risk.days_of_stock} days of stock remaining, status={risk.status}). "
        )
        if recommended_qty <= 0:
            explanation += "Current stock already meets or exceeds target; no order recommended."
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
