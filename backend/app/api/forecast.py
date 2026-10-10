from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import require_dealer_access
from app.schemas import ForecastOut
from app.agents.demand_forecast_agent import DemandForecastAgent

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get("/{dealer_id}", response_model=ForecastOut)
def get_forecast(
    dealer_id: int,
    fuel_type: str = Query("DIESEL"),
    horizon_days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    _=Depends(require_dealer_access),
):
    agent = DemandForecastAgent(db)
    try:
        return agent.predict(dealer_id, fuel_type, horizon_days)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
