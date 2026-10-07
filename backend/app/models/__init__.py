"""
SQLAlchemy ORM models. Mirrors database/schema.sql.
"""
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship

from app.core.db import Base


class Dealer(Base):
    __tablename__ = "dealers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    location = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="dealer")
    inventory = relationship("FuelInventory", back_populates="dealer")
    orders = relationship("FuelOrder", back_populates="dealer")
    tankers = relationship("Tanker", back_populates="dealer")
    drivers = relationship("Driver", back_populates="dealer")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    dealer_id = Column(Integer, ForeignKey("dealers.id"), nullable=False, index=True)
    email = Column(String(200), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(30), default="DEALER_ADMIN")
    created_at = Column(DateTime, default=datetime.utcnow)

    dealer = relationship("Dealer", back_populates="users")


class FuelInventory(Base):
    __tablename__ = "fuel_inventory"
    __table_args__ = (UniqueConstraint("dealer_id", "fuel_type", name="uq_dealer_fueltype"),)

    id = Column(Integer, primary_key=True, index=True)
    dealer_id = Column(Integer, ForeignKey("dealers.id"), nullable=False, index=True)
    fuel_type = Column(String(20), nullable=False)  # PETROL / DIESEL
    current_level_l = Column(Float, nullable=False)
    tank_capacity_l = Column(Float, nullable=False)
    safety_stock_l = Column(Float, nullable=False)
    reorder_point_l = Column(Float, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    dealer = relationship("Dealer", back_populates="inventory")


class FuelOrder(Base):
    __tablename__ = "fuel_orders"

    id = Column(Integer, primary_key=True, index=True)
    dealer_id = Column(Integer, ForeignKey("dealers.id"), nullable=False, index=True)
    fuel_type = Column(String(20), nullable=False)
    quantity_l = Column(Float, nullable=False)
    status = Column(String(20), default="PENDING", index=True)  # PENDING/APPROVED/FULFILLED/CANCELLED
    recommended_by_agent = Column(Boolean, default=False)
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)

    dealer = relationship("Dealer", back_populates="orders")
    dispatches = relationship("Dispatch", back_populates="order")


class Tanker(Base):
    __tablename__ = "tankers"

    id = Column(Integer, primary_key=True, index=True)
    dealer_id = Column(Integer, ForeignKey("dealers.id"), nullable=False, index=True)
    code = Column(String(30), nullable=False)
    capacity_l = Column(Float, nullable=False)
    status = Column(String(20), default="AVAILABLE", index=True)  # AVAILABLE/IN_TRANSIT/MAINTENANCE/OUT_OF_SERVICE
    current_location = Column(String(150), nullable=True)
    mileage_km = Column(Float, default=0)
    age_years = Column(Float, default=1.0)
    last_service_date = Column(Date, nullable=True)

    dealer = relationship("Dealer", back_populates="tankers")
    maintenance_records = relationship("MaintenanceRecord", back_populates="tanker")


class Driver(Base):
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True)
    dealer_id = Column(Integer, ForeignKey("dealers.id"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    license_number = Column(String(50), nullable=False)
    license_expiry = Column(Date, nullable=False)
    status = Column(String(20), default="AVAILABLE", index=True)  # AVAILABLE/ON_DUTY/OFF

    dealer = relationship("Dealer", back_populates="drivers")


class Refinery(Base):
    __tablename__ = "refineries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    location = Column(String(200), nullable=False)
    distance_km_default = Column(Float, default=50.0)

    loading_slots = relationship("LoadingSlot", back_populates="refinery")


class LoadingSlot(Base):
    __tablename__ = "loading_slots"

    id = Column(Integer, primary_key=True, index=True)
    refinery_id = Column(Integer, ForeignKey("refineries.id"), nullable=False, index=True)
    slot_start = Column(DateTime, nullable=False)
    slot_end = Column(DateTime, nullable=False)
    status = Column(String(20), default="OPEN", index=True)  # OPEN/BOOKED/CLOSED

    refinery = relationship("Refinery", back_populates="loading_slots")


class Dispatch(Base):
    __tablename__ = "dispatches"

    id = Column(Integer, primary_key=True, index=True)
    dealer_id = Column(Integer, ForeignKey("dealers.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("fuel_orders.id"), nullable=False, index=True)
    tanker_id = Column(Integer, ForeignKey("tankers.id"), nullable=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)
    loading_slot_id = Column(Integer, ForeignKey("loading_slots.id"), nullable=True)
    status = Column(String(20), default="PLANNED", index=True)  # PLANNED/APPROVED/ACTIVE/DELIVERED/CANCELLED
    distance_km = Column(Float, nullable=True)
    departure_time = Column(DateTime, nullable=True)
    eta = Column(DateTime, nullable=True)
    actual_arrival = Column(DateTime, nullable=True)
    risk_level = Column(String(10), nullable=True)  # LOW/MEDIUM/HIGH
    estimated_cost = Column(Float, nullable=True)
    optimization_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    order = relationship("FuelOrder", back_populates="dispatches")


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    id = Column(Integer, primary_key=True, index=True)
    tanker_id = Column(Integer, ForeignKey("tankers.id"), nullable=False, index=True)
    service_date = Column(Date, nullable=False)
    mileage_at_service = Column(Float, nullable=True)
    issue_notes = Column(Text, nullable=True)
    next_due_date = Column(Date, nullable=True)

    tanker = relationship("Tanker", back_populates="maintenance_records")


class ComplianceRecord(Base):
    __tablename__ = "compliance_records"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(20), nullable=False)  # DRIVER / TANKER
    entity_id = Column(Integer, nullable=False, index=True)
    doc_type = Column(String(50), nullable=False)  # LICENSE/PERMIT/INSURANCE/SAFETY_CERT
    expiry_date = Column(Date, nullable=False)
    status = Column(String(20), default="VALID")  # VALID/EXPIRING_SOON/EXPIRED


class DemandPrediction(Base):
    __tablename__ = "demand_predictions"

    id = Column(Integer, primary_key=True, index=True)
    dealer_id = Column(Integer, ForeignKey("dealers.id"), nullable=False, index=True)
    fuel_type = Column(String(20), nullable=False)
    prediction_date = Column(Date, nullable=False)
    horizon_days = Column(Integer, default=7)
    predicted_qty_l = Column(Float, nullable=False)
    confidence = Column(Float, nullable=True)
    model_version = Column(String(30), default="v1")
    created_at = Column(DateTime, default=datetime.utcnow)


class TrafficData(Base):
    __tablename__ = "traffic_data"

    id = Column(Integer, primary_key=True, index=True)
    dispatch_id = Column(Integer, ForeignKey("dispatches.id"), nullable=True)
    route_segment = Column(String(150), nullable=True)
    traffic_level = Column(String(20), nullable=False)  # LOW/MODERATE/HEAVY
    recorded_at = Column(DateTime, default=datetime.utcnow)


class WeatherData(Base):
    __tablename__ = "weather_data"

    id = Column(Integer, primary_key=True, index=True)
    dispatch_id = Column(Integer, ForeignKey("dispatches.id"), nullable=True)
    condition = Column(String(30), nullable=False)  # CLEAR/RAIN/FOG/STORM
    rain_mm = Column(Float, default=0)
    recorded_at = Column(DateTime, default=datetime.utcnow)


class AIRecommendation(Base):
    __tablename__ = "ai_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    dealer_id = Column(Integer, ForeignKey("dealers.id"), nullable=False, index=True)
    recommendation_type = Column(String(50), nullable=False)  # ORDER/DISPATCH/MAINTENANCE/...
    reference_table = Column(String(50), nullable=True)
    reference_id = Column(Integer, nullable=True)
    payload_json = Column(Text, nullable=False)
    explanation_text = Column(Text, nullable=True)
    status = Column(String(20), default="PENDING")  # PENDING/ACCEPTED/REJECTED
    created_at = Column(DateTime, default=datetime.utcnow)


class DailySales(Base):
    """Historical sales used to train/evaluate the demand forecast model."""
    __tablename__ = "daily_sales"

    id = Column(Integer, primary_key=True, index=True)
    dealer_id = Column(Integer, ForeignKey("dealers.id"), nullable=False, index=True)
    fuel_type = Column(String(20), nullable=False)
    sale_date = Column(Date, nullable=False)
    quantity_l = Column(Float, nullable=False)
