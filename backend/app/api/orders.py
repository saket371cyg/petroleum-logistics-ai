from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_user, require_dealer_access
from app.core.dates import utc_now
from app.schemas import OrderCreate, OrderOut, OrderRecommendationOut
from app.agents.order_recommendation_agent import OrderRecommendationAgent
from app import models as m

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderOut)
def create_order(payload: OrderCreate, db: Session = Depends(get_db), current_user: m.User = Depends(get_current_user)):
    order = m.FuelOrder(
        dealer_id=current_user.dealer_id,
        fuel_type=payload.fuel_type,
        quantity_l=payload.quantity_l,
        status="PENDING",
        recommended_by_agent=False,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.get("/{dealer_id}", response_model=List[OrderOut])
def list_orders(dealer_id: int, db: Session = Depends(get_db), _=Depends(require_dealer_access)):
    return db.query(m.FuelOrder).filter(m.FuelOrder.dealer_id == dealer_id).order_by(m.FuelOrder.created_at.desc()).all()


@router.post("/{order_id}/recommend", response_model=OrderRecommendationOut)
def recommend_order(order_id: int, fuel_type: str, db: Session = Depends(get_db), current_user: m.User = Depends(get_current_user)):
    agent = OrderRecommendationAgent(db)
    try:
        return agent.recommend(current_user.dealer_id, fuel_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/approve", response_model=OrderOut)
def approve_order(order_id: int, db: Session = Depends(get_db), current_user: m.User = Depends(get_current_user)):
    order = db.query(m.FuelOrder).filter(m.FuelOrder.id == order_id, m.FuelOrder.dealer_id == current_user.dealer_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = "APPROVED"
    order.approved_at = utc_now()
    db.commit()
    db.refresh(order)
    return order


@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel_order(order_id: int, db: Session = Depends(get_db), current_user: m.User = Depends(get_current_user)):
    order = db.query(m.FuelOrder).filter(m.FuelOrder.id == order_id, m.FuelOrder.dealer_id == current_user.dealer_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status in ("FULFILLED", "CANCELLED"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel order in status {order.status}")
    order.status = "CANCELLED"
    db.commit()
    db.refresh(order)
    return order
