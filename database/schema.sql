-- Reference PostgreSQL schema. The application itself creates these tables
-- automatically via SQLAlchemy (see backend/app/models and backend/seed_db.py);
-- this file is provided for documentation and for anyone who wants to
-- provision the schema by hand instead.

CREATE TABLE dealers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    location VARCHAR(200) NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    dealer_id INTEGER NOT NULL REFERENCES dealers(id),
    email VARCHAR(200) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(30) DEFAULT 'DEALER_ADMIN',
    created_at TIMESTAMP DEFAULT now()
);
CREATE INDEX idx_users_dealer ON users(dealer_id);

CREATE TABLE fuel_inventory (
    id SERIAL PRIMARY KEY,
    dealer_id INTEGER NOT NULL REFERENCES dealers(id),
    fuel_type VARCHAR(20) NOT NULL,
    current_level_l FLOAT NOT NULL,
    tank_capacity_l FLOAT NOT NULL,
    safety_stock_l FLOAT NOT NULL,
    reorder_point_l FLOAT NOT NULL,
    updated_at TIMESTAMP DEFAULT now(),
    UNIQUE(dealer_id, fuel_type)
);
CREATE INDEX idx_inventory_dealer ON fuel_inventory(dealer_id);

CREATE TABLE fuel_orders (
    id SERIAL PRIMARY KEY,
    dealer_id INTEGER NOT NULL REFERENCES dealers(id),
    fuel_type VARCHAR(20) NOT NULL,
    quantity_l FLOAT NOT NULL,
    status VARCHAR(20) DEFAULT 'PENDING',
    recommended_by_agent BOOLEAN DEFAULT FALSE,
    explanation TEXT,
    created_at TIMESTAMP DEFAULT now(),
    approved_at TIMESTAMP
);
CREATE INDEX idx_orders_dealer ON fuel_orders(dealer_id);
CREATE INDEX idx_orders_status ON fuel_orders(status);

CREATE TABLE tankers (
    id SERIAL PRIMARY KEY,
    dealer_id INTEGER NOT NULL REFERENCES dealers(id),
    code VARCHAR(30) NOT NULL,
    capacity_l FLOAT NOT NULL,
    status VARCHAR(20) DEFAULT 'AVAILABLE',
    current_location VARCHAR(150),
    mileage_km FLOAT DEFAULT 0,
    age_years FLOAT DEFAULT 1.0,
    last_service_date DATE
);
CREATE INDEX idx_tankers_dealer ON tankers(dealer_id);
CREATE INDEX idx_tankers_status ON tankers(status);

CREATE TABLE drivers (
    id SERIAL PRIMARY KEY,
    dealer_id INTEGER NOT NULL REFERENCES dealers(id),
    name VARCHAR(150) NOT NULL,
    license_number VARCHAR(50) NOT NULL,
    license_expiry DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'AVAILABLE'
);
CREATE INDEX idx_drivers_dealer ON drivers(dealer_id);
CREATE INDEX idx_drivers_status ON drivers(status);

CREATE TABLE refineries (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    location VARCHAR(200) NOT NULL,
    distance_km_default FLOAT DEFAULT 50.0
);

CREATE TABLE loading_slots (
    id SERIAL PRIMARY KEY,
    refinery_id INTEGER NOT NULL REFERENCES refineries(id),
    slot_start TIMESTAMP NOT NULL,
    slot_end TIMESTAMP NOT NULL,
    status VARCHAR(20) DEFAULT 'OPEN'
);
CREATE INDEX idx_slots_refinery ON loading_slots(refinery_id);
CREATE INDEX idx_slots_status ON loading_slots(status);

CREATE TABLE dispatches (
    id SERIAL PRIMARY KEY,
    dealer_id INTEGER NOT NULL REFERENCES dealers(id),
    order_id INTEGER NOT NULL REFERENCES fuel_orders(id),
    tanker_id INTEGER REFERENCES tankers(id),
    driver_id INTEGER REFERENCES drivers(id),
    loading_slot_id INTEGER REFERENCES loading_slots(id),
    status VARCHAR(20) DEFAULT 'PLANNED',
    distance_km FLOAT,
    departure_time TIMESTAMP,
    eta TIMESTAMP,
    actual_arrival TIMESTAMP,
    risk_level VARCHAR(10),
    estimated_cost FLOAT,
    optimization_score FLOAT,
    created_at TIMESTAMP DEFAULT now()
);
CREATE INDEX idx_dispatches_dealer ON dispatches(dealer_id);
CREATE INDEX idx_dispatches_status ON dispatches(status);

CREATE TABLE maintenance_records (
    id SERIAL PRIMARY KEY,
    tanker_id INTEGER NOT NULL REFERENCES tankers(id),
    service_date DATE NOT NULL,
    mileage_at_service FLOAT,
    issue_notes TEXT,
    next_due_date DATE
);
CREATE INDEX idx_maintenance_tanker ON maintenance_records(tanker_id);

CREATE TABLE compliance_records (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(20) NOT NULL,
    entity_id INTEGER NOT NULL,
    doc_type VARCHAR(50) NOT NULL,
    expiry_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'VALID'
);
CREATE INDEX idx_compliance_entity ON compliance_records(entity_type, entity_id);

CREATE TABLE demand_predictions (
    id SERIAL PRIMARY KEY,
    dealer_id INTEGER NOT NULL REFERENCES dealers(id),
    fuel_type VARCHAR(20) NOT NULL,
    prediction_date DATE NOT NULL,
    horizon_days INTEGER DEFAULT 7,
    predicted_qty_l FLOAT NOT NULL,
    confidence FLOAT,
    model_version VARCHAR(30) DEFAULT 'v1',
    created_at TIMESTAMP DEFAULT now()
);
CREATE INDEX idx_predictions_dealer ON demand_predictions(dealer_id);

CREATE TABLE traffic_data (
    id SERIAL PRIMARY KEY,
    dispatch_id INTEGER REFERENCES dispatches(id),
    route_segment VARCHAR(150),
    traffic_level VARCHAR(20) NOT NULL,
    recorded_at TIMESTAMP DEFAULT now()
);

CREATE TABLE weather_data (
    id SERIAL PRIMARY KEY,
    dispatch_id INTEGER REFERENCES dispatches(id),
    condition VARCHAR(30) NOT NULL,
    rain_mm FLOAT DEFAULT 0,
    recorded_at TIMESTAMP DEFAULT now()
);

CREATE TABLE ai_recommendations (
    id SERIAL PRIMARY KEY,
    dealer_id INTEGER NOT NULL REFERENCES dealers(id),
    recommendation_type VARCHAR(50) NOT NULL,
    reference_table VARCHAR(50),
    reference_id INTEGER,
    payload_json TEXT NOT NULL,
    explanation_text TEXT,
    status VARCHAR(20) DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT now()
);
CREATE INDEX idx_recommendations_dealer ON ai_recommendations(dealer_id);

CREATE TABLE daily_sales (
    id SERIAL PRIMARY KEY,
    dealer_id INTEGER NOT NULL REFERENCES dealers(id),
    fuel_type VARCHAR(20) NOT NULL,
    sale_date DATE NOT NULL,
    quantity_l FLOAT NOT NULL
);
CREATE INDEX idx_sales_dealer_fuel_date ON daily_sales(dealer_id, fuel_type, sale_date);
