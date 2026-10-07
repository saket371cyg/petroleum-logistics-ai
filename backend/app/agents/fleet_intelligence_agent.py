"""
Fleet Intelligence Agent.

Filters out tankers/drivers that are unavailable, under maintenance, or
non-compliant, leaving only genuinely usable candidates for dispatch.
"""
from datetime import date
from typing import List

from sqlalchemy.orm import Session

from app import models as m


class FleetIntelligenceAgent:

    def __init__(self, db: Session):
        self.db = db

    def _compliant_entity_ids(self, entity_type: str) -> set:
        rows = self.db.query(m.ComplianceRecord).filter(
            m.ComplianceRecord.entity_type == entity_type,
            m.ComplianceRecord.status == "EXPIRED",
        ).all()
        non_compliant = {r.entity_id for r in rows}
        return non_compliant

    def available_tankers(self, dealer_id: int, min_capacity_l: float = 0) -> List[m.Tanker]:
        non_compliant_ids = self._compliant_entity_ids("TANKER")
        tankers = (
            self.db.query(m.Tanker)
            .filter(
                m.Tanker.dealer_id == dealer_id,
                m.Tanker.status == "AVAILABLE",
                m.Tanker.capacity_l >= min_capacity_l,
            )
            .all()
        )
        return [t for t in tankers if t.id not in non_compliant_ids]

    def available_drivers(self, dealer_id: int) -> List[m.Driver]:
        non_compliant_ids = self._compliant_entity_ids("DRIVER")
        today = date.today()
        drivers = (
            self.db.query(m.Driver)
            .filter(m.Driver.dealer_id == dealer_id, m.Driver.status == "AVAILABLE")
            .all()
        )
        return [d for d in drivers if d.id not in non_compliant_ids and d.license_expiry >= today]

    def fleet_utilization_pct(self, dealer_id: int) -> float:
        all_tankers = self.db.query(m.Tanker).filter(m.Tanker.dealer_id == dealer_id).all()
        if not all_tankers:
            return 0.0
        busy = sum(1 for t in all_tankers if t.status == "IN_TRANSIT")
        return round(100 * busy / len(all_tankers), 1)
