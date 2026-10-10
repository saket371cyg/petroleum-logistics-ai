"""
Creates all tables and loads the synthetic CSVs into the database.

Run: python seed_db.py
"""
import os
import pandas as pd
from datetime import datetime

from app.core.db import Base, engine, SessionLocal
from app.core.security import hash_password
from app import models as m

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "synthetic")


def load_csv(name):
    return pd.read_csv(os.path.join(DATA_DIR, f"{name}.csv"))


def main():
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"), exist_ok=True)

    print("Creating tables if needed...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if db.query(m.Dealer).first() is not None:
            print("Database already contains dealers; preserving existing data.")
            return

        dealers = load_csv("dealers")
        for _, r in dealers.iterrows():
            db.add(m.Dealer(id=int(r["id"]), name=r["name"], location=r["location"]))
        db.commit()

        users = load_csv("users")
        for _, r in users.iterrows():
            db.add(m.User(dealer_id=int(r["dealer_id"]), email=r["email"],
                           password_hash=hash_password(str(r["password_plain"])), role=r["role"]))
        db.commit()
        print(f"  Seeded {len(users)} users. Demo login: dealer1@example.com / password123")

        sales = load_csv("daily_sales")
        for _, r in sales.iterrows():
            db.add(m.DailySales(dealer_id=int(r["dealer_id"]), fuel_type=r["fuel_type"],
                                 sale_date=pd.to_datetime(r["sale_date"]).date(), quantity_l=float(r["quantity_l"])))
        db.commit()
        print(f"  Seeded {len(sales)} daily sales rows.")

        inv = load_csv("fuel_inventory")
        for _, r in inv.iterrows():
            db.add(m.FuelInventory(dealer_id=int(r["dealer_id"]), fuel_type=r["fuel_type"],
                                    current_level_l=float(r["current_level_l"]), tank_capacity_l=float(r["tank_capacity_l"]),
                                    safety_stock_l=float(r["safety_stock_l"]), reorder_point_l=float(r["reorder_point_l"])))
        db.commit()

        tankers = load_csv("tankers")
        for _, r in tankers.iterrows():
            db.add(m.Tanker(id=int(r["id"]), dealer_id=int(r["dealer_id"]), code=r["code"],
                             capacity_l=float(r["capacity_l"]), status=r["status"], current_location=r["current_location"],
                             mileage_km=float(r["mileage_km"]), age_years=float(r["age_years"]),
                             last_service_date=pd.to_datetime(r["last_service_date"]).date()))
        db.commit()

        drivers = load_csv("drivers")
        for _, r in drivers.iterrows():
            db.add(m.Driver(id=int(r["id"]), dealer_id=int(r["dealer_id"]), name=r["name"],
                             license_number=r["license_number"], license_expiry=pd.to_datetime(r["license_expiry"]).date(),
                             status=r["status"]))
        db.commit()

        refineries = load_csv("refineries")
        for _, r in refineries.iterrows():
            db.add(m.Refinery(id=int(r["id"]), name=r["name"], location=r["location"],
                               distance_km_default=float(r["distance_km_default"])))
        db.commit()

        slots = load_csv("loading_slots")
        for _, r in slots.iterrows():
            db.add(m.LoadingSlot(id=int(r["id"]), refinery_id=int(r["refinery_id"]),
                                  slot_start=pd.to_datetime(r["slot_start"]), slot_end=pd.to_datetime(r["slot_end"]),
                                  status=r["status"]))
        db.commit()

        maint = load_csv("maintenance_records")
        for _, r in maint.iterrows():
            db.add(m.MaintenanceRecord(id=int(r["id"]), tanker_id=int(r["tanker_id"]),
                                        service_date=pd.to_datetime(r["service_date"]).date(),
                                        mileage_at_service=float(r["mileage_at_service"]), issue_notes=r["issue_notes"],
                                        next_due_date=pd.to_datetime(r["next_due_date"]).date()))
        db.commit()

        comp = load_csv("compliance_records")
        for _, r in comp.iterrows():
            db.add(m.ComplianceRecord(id=int(r["id"]), entity_type=r["entity_type"], entity_id=int(r["entity_id"]),
                                       doc_type=r["doc_type"], expiry_date=pd.to_datetime(r["expiry_date"]).date(),
                                       status=r["status"]))
        db.commit()

        print("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
