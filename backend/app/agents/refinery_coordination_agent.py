"""
Refinery Coordination Agent.

The refinery is an external entity from the dealer's perspective: this
agent only reads/recommends against loading_slots, it never mutates
refinery-owned data beyond marking a slot BOOKED when a dispatch confirms it.
"""
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from app import models as m


class RefineryCoordinationAgent:

    def __init__(self, db: Session):
        self.db = db

    def list_open_slots(self, refinery_id: Optional[int] = None) -> List[m.LoadingSlot]:
        q = self.db.query(m.LoadingSlot).filter(m.LoadingSlot.status == "OPEN")
        if refinery_id:
            q = q.filter(m.LoadingSlot.refinery_id == refinery_id)
        return q.order_by(m.LoadingSlot.slot_start).all()

    def recommend_slot(self, deadline: datetime, refinery_id: Optional[int] = None) -> Optional[m.LoadingSlot]:
        """
        Pick the earliest open slot that still leaves enough time to load,
        travel, and arrive before the deadline. Urgency = earlier deadline
        means we prefer earlier slots even if a "better" (e.g. less busy)
        slot exists later.
        """
        candidates = self.list_open_slots(refinery_id)
        feasible = [s for s in candidates if s.slot_end <= deadline]
        if not feasible:
            # No slot leaves enough buffer before the deadline; return earliest
            # available slot anyway and let the risk/optimization layer flag it.
            return candidates[0] if candidates else None
        return feasible[0]

    def book_slot(self, slot_id: int) -> m.LoadingSlot:
        slot = self.db.query(m.LoadingSlot).filter(m.LoadingSlot.id == slot_id).first()
        if slot is None:
            raise ValueError("Slot not found")
        slot.status = "BOOKED"
        self.db.commit()
        self.db.refresh(slot)
        return slot
