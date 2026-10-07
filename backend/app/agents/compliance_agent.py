"""
Compliance Agent — purely rule-based (no LLM), as required: expiry-date
comparisons are deterministic and must never be left to a language model.
"""
from datetime import date, timedelta
from typing import List

from sqlalchemy.orm import Session

from app import models as m
from app.schemas import ComplianceAlertOut

EXPIRING_SOON_WINDOW_DAYS = 30


class ComplianceAgent:

    def __init__(self, db: Session):
        self.db = db

    def _refresh_statuses(self):
        """Recompute status against today's date (data may have been seeded in the past)."""
        today = date.today()
        records = self.db.query(m.ComplianceRecord).all()
        for r in records:
            if r.expiry_date < today:
                r.status = "EXPIRED"
            elif (r.expiry_date - today).days <= EXPIRING_SOON_WINDOW_DAYS:
                r.status = "EXPIRING_SOON"
            else:
                r.status = "VALID"
        self.db.commit()

    def is_eligible(self, entity_type: str, entity_id: int) -> bool:
        self._refresh_statuses()
        expired = self.db.query(m.ComplianceRecord).filter(
            m.ComplianceRecord.entity_type == entity_type,
            m.ComplianceRecord.entity_id == entity_id,
            m.ComplianceRecord.status == "EXPIRED",
        ).first()
        return expired is None

    def alerts_for_dealer(self, dealer_id: int) -> List[ComplianceAlertOut]:
        self._refresh_statuses()
        today = date.today()

        tanker_ids = {t.id: t.code for t in self.db.query(m.Tanker).filter(m.Tanker.dealer_id == dealer_id).all()}
        driver_ids = {d.id: d.name for d in self.db.query(m.Driver).filter(m.Driver.dealer_id == dealer_id).all()}

        alerts = []
        records = self.db.query(m.ComplianceRecord).filter(m.ComplianceRecord.status != "VALID").all()
        for r in records:
            if r.entity_type == "TANKER" and r.entity_id in tanker_ids:
                label = tanker_ids[r.entity_id]
            elif r.entity_type == "DRIVER" and r.entity_id in driver_ids:
                label = driver_ids[r.entity_id]
            else:
                continue
            alerts.append(ComplianceAlertOut(
                entity_type=r.entity_type,
                entity_id=r.entity_id,
                entity_label=label,
                doc_type=r.doc_type,
                expiry_date=r.expiry_date,
                status=r.status,
                days_to_expiry=(r.expiry_date - today).days,
            ))
        return sorted(alerts, key=lambda a: a.days_to_expiry)
