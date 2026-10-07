"""
Maintenance Prediction Agent — rule-based scoring for v1, as the spec allows.

risk_score (0-100) combines:
  - mileage since last service (higher -> higher risk)
  - vehicle age
  - days since last service
  - breakdown/issue history (count of non-routine issue notes)
"""
from datetime import date, timedelta
from typing import List

from sqlalchemy.orm import Session

from app import models as m
from app.schemas import MaintenanceAlertOut

MILEAGE_SINCE_SERVICE_THRESHOLD = 15000  # km before risk climbs
SERVICE_DUE_DAYS = 180


class MaintenanceAgent:

    def __init__(self, db: Session):
        self.db = db

    def _risk_for_tanker(self, tanker: m.Tanker) -> tuple:
        records = (
            self.db.query(m.MaintenanceRecord)
            .filter(m.MaintenanceRecord.tanker_id == tanker.id)
            .order_by(m.MaintenanceRecord.service_date.desc())
            .all()
        )
        last_service = records[0] if records else None
        days_since_service = (date.today() - last_service.service_date).days if last_service else 365
        mileage_since_service = (
            tanker.mileage_km - last_service.mileage_at_service if last_service else tanker.mileage_km
        )
        non_routine_issues = sum(1 for r in records if r.issue_notes and "Routine" not in r.issue_notes)

        score = 0.0
        score += min(40, 40 * mileage_since_service / MILEAGE_SINCE_SERVICE_THRESHOLD)
        score += min(25, 25 * days_since_service / SERVICE_DUE_DAYS)
        score += min(20, tanker.age_years * 2.5)
        score += min(15, non_routine_issues * 5)
        score = round(min(score, 100), 1)

        if score >= 70:
            level = "HIGH"
        elif score >= 40:
            level = "MEDIUM"
        else:
            level = "LOW"

        recommended_date = date.today() if level == "HIGH" else (
            last_service.next_due_date if last_service and last_service.next_due_date else date.today() + timedelta(days=30)
        )
        reason = (
            f"{mileage_since_service:,.0f} km since last service, "
            f"{days_since_service} days since last service, age {tanker.age_years} yrs, "
            f"{non_routine_issues} non-routine issue(s) on record."
        )
        return score, level, recommended_date, reason

    def alerts_for_dealer(self, dealer_id: int) -> List[MaintenanceAlertOut]:
        tankers = self.db.query(m.Tanker).filter(m.Tanker.dealer_id == dealer_id).all()
        alerts = []
        for t in tankers:
            score, level, rec_date, reason = self._risk_for_tanker(t)
            alerts.append(MaintenanceAlertOut(
                tanker_id=t.id, tanker_code=t.code, risk_score=score, risk_level=level,
                recommended_service_date=rec_date, reason=reason,
            ))
        return sorted(alerts, key=lambda a: -a.risk_score)

    def is_safe_to_dispatch(self, tanker: m.Tanker) -> bool:
        score, level, _, _ = self._risk_for_tanker(tanker)
        return level != "HIGH"
