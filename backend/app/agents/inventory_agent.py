"""
Inventory Intelligence Agent.

Days of Stock = Current Inventory / Predicted Daily Demand
Status thresholds (from settings):
  days_of_stock <= STOCK_CRITICAL_DAYS -> CRITICAL
  days_of_stock <= STOCK_WARNING_DAYS  -> WARNING
  else                                  -> NORMAL
"""
from sqlalchemy.orm import Session

from app import models as m
from app.core.config import settings
from app.schemas import InventoryRiskOut
from app.agents.demand_forecast_agent import DemandForecastAgent


class InventoryAgent:

    def __init__(self, db: Session):
        self.db = db
        self.forecast_agent = DemandForecastAgent(db)

    def get_inventory(self, dealer_id: int):
        return self.db.query(m.FuelInventory).filter(m.FuelInventory.dealer_id == dealer_id).all()

    def compute_risk(self, dealer_id: int, fuel_type: str) -> InventoryRiskOut:
        inv = (
            self.db.query(m.FuelInventory)
            .filter(m.FuelInventory.dealer_id == dealer_id, m.FuelInventory.fuel_type == fuel_type)
            .first()
        )
        if inv is None:
            raise ValueError(f"No inventory record for dealer {dealer_id} / {fuel_type}")

        try:
            predicted_daily_demand = self.forecast_agent.predicted_daily_demand(dealer_id, fuel_type)
        except (FileNotFoundError, ValueError):
            # Fallback if no model/history yet: naive demand estimate from safety stock sizing.
            predicted_daily_demand = max(inv.safety_stock_l / max(settings.DEFAULT_SAFETY_STOCK_DAYS, 1), 1.0)

        days_of_stock = inv.current_level_l / max(predicted_daily_demand, 1.0)

        if days_of_stock <= settings.STOCK_CRITICAL_DAYS:
            status = "CRITICAL"
        elif days_of_stock <= settings.STOCK_WARNING_DAYS:
            status = "WARNING"
        else:
            status = "NORMAL"

        return InventoryRiskOut(
            fuel_type=fuel_type,
            current_level_l=inv.current_level_l,
            predicted_daily_demand_l=round(predicted_daily_demand, 1),
            days_of_stock=round(days_of_stock, 2),
            status=status,
            reorder_point_l=inv.reorder_point_l,
        )

    def compute_all_risks(self, dealer_id: int):
        fuel_types = [row.fuel_type for row in self.get_inventory(dealer_id)]
        return [self.compute_risk(dealer_id, ft) for ft in fuel_types]
