"""
Pydantic schemas for request/response validation.
"""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class AppBaseModel(BaseModel):
    model_config = ConfigDict(protected_namespaces=())


# ---------- Auth ----------
class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    dealer_id: int
    user_id: int
    email: str


# ---------- Inventory ----------
class InventoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    fuel_type: str
    current_level_l: float
    tank_capacity_l: float
    safety_stock_l: float
    reorder_point_l: float
    updated_at: datetime


class InventoryRiskOut(BaseModel):
    fuel_type: str
    current_level_l: float
    predicted_daily_demand_l: float
    days_of_stock: float
    status: str  # NORMAL / WARNING / CRITICAL
    reorder_point_l: float


# ---------- Forecast ----------
class ForecastPoint(BaseModel):
    date: date
    predicted_qty_l: float


class ForecastOut(AppBaseModel):
    fuel_type: str
    horizon_days: int
    confidence: float
    model_version: str
    points: List[ForecastPoint]
    mae: Optional[float] = None
    rmse: Optional[float] = None
    mape: Optional[float] = None


# ---------- Orders ----------
class OrderCreate(BaseModel):
    fuel_type: str
    quantity_l: float


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    fuel_type: str
    quantity_l: float
    status: str
    recommended_by_agent: bool
    explanation: Optional[str] = None
    created_at: datetime


class OrderRecommendationOut(BaseModel):
    fuel_type: str
    should_order: bool
    recommended_quantity_l: float
    target_inventory_l: float
    current_inventory_l: float
    explanation: str


# ---------- Fleet ----------
class TankerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    capacity_l: float
    status: str
    current_location: Optional[str] = None
    mileage_km: float
    age_years: float


class DriverOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    license_number: str
    license_expiry: date
    status: str


# ---------- Refinery ----------
class LoadingSlotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    refinery_id: int
    slot_start: datetime
    slot_end: datetime
    status: str


# ---------- Dispatch ----------
class DispatchOptimizeRequest(BaseModel):
    order_id: int
    deadline_hours: float = 6.0


class DispatchOptimizeResponse(BaseModel):
    dispatch_id: int
    recommended_tanker: str
    recommended_driver: str
    loading_slot_start: datetime
    departure_time: datetime
    eta: datetime
    estimated_cost: float
    risk_level: str
    optimization_score: float
    iterations_run: int
    explanation: str


class DispatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    order_id: int
    tanker_id: Optional[int]
    driver_id: Optional[int]
    status: str
    distance_km: Optional[float]
    departure_time: Optional[datetime]
    eta: Optional[datetime]
    risk_level: Optional[str]
    estimated_cost: Optional[float]


# ---------- Compliance / Maintenance ----------
class ComplianceAlertOut(BaseModel):
    entity_type: str
    entity_id: int
    entity_label: str
    doc_type: str
    expiry_date: date
    status: str
    days_to_expiry: int


class MaintenanceAlertOut(BaseModel):
    tanker_id: int
    tanker_code: str
    risk_score: float
    risk_level: str
    recommended_service_date: date
    reason: str


# ---------- Analytics / Executive ----------
class AnalyticsOut(BaseModel):
    dealer_id: int
    generated_at: datetime
    petrol_stock_l: float
    diesel_stock_l: float
    pending_orders: int
    available_tankers: int
    active_dispatches: int
    critical_alerts: int
    avg_delivery_hours: Optional[float]
    fleet_utilization_pct: float
    summary_text: str


class AIQueryRequest(BaseModel):
    question: str


class AIQueryResponse(BaseModel):
    answer: str
    data_sources: List[str] = []
    sources: List[str] = []
    tool_trace: List[str] = []
    mode: str = "fallback"
    decision: Optional[dict] = None
