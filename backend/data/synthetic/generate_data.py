"""
Generates a realistic SYNTHETIC dataset for the petroleum dealer platform.

IMPORTANT: All data produced here is synthetic / fabricated for development
and ML testing. It is NOT real Reliance/IOCL/BPCL/HPCL operational data.

Run: python data/synthetic/generate_data.py
Writes CSVs into data/synthetic/*.csv
"""
import os
import random
import numpy as np
import pandas as pd
from datetime import date, datetime, timedelta

random.seed(42)
np.random.seed(42)

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

DEALERS = [
    {"id": 1, "name": "Shree Balaji Fuel Station", "location": "Indore, MP"},
    {"id": 2, "name": "Highway Petro Point", "location": "Bhopal, MP"},
    {"id": 3, "name": "National Fuel Junction", "location": "Nagpur, MH"},
]

FUEL_TYPES = ["PETROL", "DIESEL"]
HISTORY_DAYS = 400


def gen_dealers():
    return pd.DataFrame(DEALERS).assign(created_at=datetime.utcnow().isoformat())


def gen_users():
    rows = []
    for d in DEALERS:
        rows.append({
            "dealer_id": d["id"],
            "email": f"dealer{d['id']}@example.com",
            # plaintext here only for seeding convenience; seed_db.py hashes it before insert
            "password_plain": "password123",
            "role": "DEALER_ADMIN",
        })
    return pd.DataFrame(rows)


def gen_daily_sales():
    rows = []
    start = date.today() - timedelta(days=HISTORY_DAYS)
    for d in DEALERS:
        base = {"PETROL": 8000, "DIESEL": 11000}[FUEL_TYPES[0]] if False else None
        base_petrol = np.random.uniform(6000, 9000)
        base_diesel = np.random.uniform(9000, 13000)
        for i in range(HISTORY_DAYS):
            day = start + timedelta(days=i)
            dow = day.weekday()  # 0=Mon
            month = day.month

            # weekly pattern: weekends slightly higher for petrol (travel), diesel slightly lower (less freight)
            weekly_petrol = 1.15 if dow >= 5 else 1.0
            weekly_diesel = 0.9 if dow >= 5 else 1.05

            # seasonal pattern: summer months (Apr-Jun) higher travel; monsoon (Jul-Sep) lower diesel freight
            seasonal_petrol = 1.1 if month in (4, 5, 6) else 1.0
            seasonal_diesel = 0.85 if month in (7, 8, 9) else 1.0

            noise_petrol = np.random.normal(0, 400)
            noise_diesel = np.random.normal(0, 600)

            petrol_qty = max(500, base_petrol * weekly_petrol * seasonal_petrol + noise_petrol)
            diesel_qty = max(500, base_diesel * weekly_diesel * seasonal_diesel + noise_diesel)

            rows.append({"dealer_id": d["id"], "fuel_type": "PETROL", "sale_date": day.isoformat(), "quantity_l": round(petrol_qty, 1)})
            rows.append({"dealer_id": d["id"], "fuel_type": "DIESEL", "sale_date": day.isoformat(), "quantity_l": round(diesel_qty, 1)})
    return pd.DataFrame(rows)


def gen_inventory(sales_df):
    rows = []
    for d in DEALERS:
        for ft in FUEL_TYPES:
            recent_avg = sales_df[(sales_df.dealer_id == d["id"]) & (sales_df.fuel_type == ft)]["quantity_l"].tail(14).mean()
            capacity = round(recent_avg * 6, -2)
            # Deliberately make dealer 1's diesel tight (stock-risk demo scenario)
            if d["id"] == 1 and ft == "DIESEL":
                current = round(recent_avg * 1.4, -2)
            else:
                current = round(np.random.uniform(2.5, 4.5) * recent_avg, -2)
            rows.append({
                "dealer_id": d["id"],
                "fuel_type": ft,
                "current_level_l": current,
                "tank_capacity_l": capacity,
                "safety_stock_l": round(recent_avg * 2, -2),
                "reorder_point_l": round(recent_avg * 3, -2),
            })
    return pd.DataFrame(rows)


def gen_tankers():
    rows = []
    tid = 1
    statuses = ["AVAILABLE", "AVAILABLE", "AVAILABLE", "IN_TRANSIT", "MAINTENANCE"]
    for d in DEALERS:
        n = random.randint(4, 6)
        for i in range(n):
            rows.append({
                "id": tid,
                "dealer_id": d["id"],
                "code": f"T-{100 + tid}",
                "capacity_l": random.choice([8000, 12000, 16000, 20000]),
                "status": random.choice(statuses),
                "current_location": d["location"],
                "mileage_km": round(np.random.uniform(20000, 220000), 0),
                "age_years": round(np.random.uniform(0.5, 9), 1),
                "last_service_date": (date.today() - timedelta(days=random.randint(10, 200))).isoformat(),
            })
            tid += 1
    return pd.DataFrame(rows)


def gen_drivers():
    rows = []
    did = 1
    names = ["Ramesh Kumar", "Suresh Yadav", "Anil Sharma", "Vikram Singh", "Deepak Patil",
             "Manoj Verma", "Sanjay Rao", "Ashok Mehta", "Rakesh Joshi", "Vinod Chauhan",
             "Prakash Gupta", "Sunil Deshmukh"]
    for d in DEALERS:
        n = random.randint(4, 6)
        for i in range(n):
            expiry_offset = random.choice([random.randint(-30, 15), random.randint(60, 500)])
            rows.append({
                "id": did,
                "dealer_id": d["id"],
                "name": random.choice(names),
                "license_number": f"MP{random.randint(10,99)}-{random.randint(100000,999999)}",
                "license_expiry": (date.today() + timedelta(days=expiry_offset)).isoformat(),
                "status": random.choice(["AVAILABLE", "AVAILABLE", "ON_DUTY", "OFF"]),
            })
            did += 1
    return pd.DataFrame(rows)


def gen_refineries():
    return pd.DataFrame([
        {"id": 1, "name": "Central Refinery Depot", "location": "Indore, MP", "distance_km_default": 35},
        {"id": 2, "name": "Regional Refinery Hub", "location": "Bhopal, MP", "distance_km_default": 60},
    ])


def gen_loading_slots():
    rows = []
    sid = 1
    for ref_id in [1, 2]:
        for day_offset in range(5):
            day = datetime.utcnow() + timedelta(days=day_offset)
            for hour in [7, 9, 11, 13, 15, 17]:
                slot_start = day.replace(hour=hour, minute=0, second=0, microsecond=0)
                rows.append({
                    "id": sid,
                    "refinery_id": ref_id,
                    "slot_start": slot_start.isoformat(),
                    "slot_end": (slot_start + timedelta(hours=1)).isoformat(),
                    "status": random.choice(["OPEN", "OPEN", "OPEN", "BOOKED"]),
                })
                sid += 1
    return pd.DataFrame(rows)


def gen_maintenance_records(tankers_df):
    rows = []
    rid = 1
    for _, t in tankers_df.iterrows():
        for _ in range(random.randint(1, 3)):
            svc_date = date.today() - timedelta(days=random.randint(30, 400))
            rows.append({
                "id": rid,
                "tanker_id": int(t["id"]),
                "service_date": svc_date.isoformat(),
                "mileage_at_service": round(t["mileage_km"] - random.uniform(1000, 20000), 0),
                "issue_notes": random.choice(["Routine service", "Brake inspection", "Tyre replacement", "Oil change", "Engine check"]),
                "next_due_date": (svc_date + timedelta(days=180)).isoformat(),
            })
            rid += 1
    return pd.DataFrame(rows)


def gen_compliance_records(tankers_df, drivers_df):
    rows = []
    cid = 1
    for _, t in tankers_df.iterrows():
        for doc in ["PERMIT", "INSURANCE", "SAFETY_CERT"]:
            expiry = date.today() + timedelta(days=random.choice([random.randint(-20, 20), random.randint(60, 400)]))
            status = "EXPIRED" if expiry < date.today() else ("EXPIRING_SOON" if (expiry - date.today()).days <= 30 else "VALID")
            rows.append({"id": cid, "entity_type": "TANKER", "entity_id": int(t["id"]), "doc_type": doc,
                         "expiry_date": expiry.isoformat(), "status": status})
            cid += 1
    for _, dr in drivers_df.iterrows():
        expiry = pd.to_datetime(dr["license_expiry"]).date()
        status = "EXPIRED" if expiry < date.today() else ("EXPIRING_SOON" if (expiry - date.today()).days <= 30 else "VALID")
        rows.append({"id": cid, "entity_type": "DRIVER", "entity_id": int(dr["id"]), "doc_type": "LICENSE",
                     "expiry_date": expiry.isoformat(), "status": status})
        cid += 1
    return pd.DataFrame(rows)


def main():
    dealers = gen_dealers()
    users = gen_users()
    sales = gen_daily_sales()
    inventory = gen_inventory(sales)
    tankers = gen_tankers()
    drivers = gen_drivers()
    refineries = gen_refineries()
    slots = gen_loading_slots()
    maintenance = gen_maintenance_records(tankers)
    compliance = gen_compliance_records(tankers, drivers)

    dealers.to_csv(os.path.join(OUT_DIR, "dealers.csv"), index=False)
    users.to_csv(os.path.join(OUT_DIR, "users.csv"), index=False)
    sales.to_csv(os.path.join(OUT_DIR, "daily_sales.csv"), index=False)
    inventory.to_csv(os.path.join(OUT_DIR, "fuel_inventory.csv"), index=False)
    tankers.to_csv(os.path.join(OUT_DIR, "tankers.csv"), index=False)
    drivers.to_csv(os.path.join(OUT_DIR, "drivers.csv"), index=False)
    refineries.to_csv(os.path.join(OUT_DIR, "refineries.csv"), index=False)
    slots.to_csv(os.path.join(OUT_DIR, "loading_slots.csv"), index=False)
    maintenance.to_csv(os.path.join(OUT_DIR, "maintenance_records.csv"), index=False)
    compliance.to_csv(os.path.join(OUT_DIR, "compliance_records.csv"), index=False)

    print("Synthetic dataset generated (NOT real operational data):")
    for name, df in [("dealers", dealers), ("users", users), ("daily_sales", sales),
                      ("fuel_inventory", inventory), ("tankers", tankers), ("drivers", drivers),
                      ("refineries", refineries), ("loading_slots", slots),
                      ("maintenance_records", maintenance), ("compliance_records", compliance)]:
        print(f"  {name}: {len(df)} rows")


if __name__ == "__main__":
    main()
