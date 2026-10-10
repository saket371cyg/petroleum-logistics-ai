"""
Trains the Demand Forecast Agent's model: one RandomForestRegressor per
(dealer, fuel_type), using lag/calendar features on daily_sales history.

Why RandomForest and not LSTM: the spec calls for a simple, reliable
baseline. With ~400 days of daily data per dealer/fuel, a tree ensemble on
lag + calendar features is far more robust than a deep sequence model and
is trivial to explain to a B.Tech evaluation panel.

Run: python -m app.ml.train_demand_model
Writes one .joblib model per dealer/fuel_type into app/ml/model_store/,
plus metrics.json with MAE/RMSE/MAPE per model.
"""
import os
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

from app.core.db import SessionLocal
from app import models as m

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_store")
os.makedirs(MODEL_DIR, exist_ok=True)

LAGS = [1, 2, 3, 7, 14]
ROLLING_WINDOWS = [7, 14]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("sale_date").reset_index(drop=True)
    df["sale_date"] = pd.to_datetime(df["sale_date"])
    df["day_of_week"] = df["sale_date"].dt.dayofweek
    df["month"] = df["sale_date"].dt.month
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

    for lag in LAGS:
        df[f"lag_{lag}"] = df["quantity_l"].shift(lag)
    for w in ROLLING_WINDOWS:
        df[f"rolling_mean_{w}"] = df["quantity_l"].shift(1).rolling(w).mean()
        df[f"rolling_std_{w}"] = df["quantity_l"].shift(1).rolling(w).std()

    df = df.dropna().reset_index(drop=True)
    return df


FEATURE_COLS = (
    ["day_of_week", "month", "is_weekend"]
    + [f"lag_{l}" for l in LAGS]
    + [f"rolling_mean_{w}" for w in ROLLING_WINDOWS]
    + [f"rolling_std_{w}" for w in ROLLING_WINDOWS]
)


def train_one(dealer_id: int, fuel_type: str, raw: pd.DataFrame) -> dict:
    feat = build_features(raw)
    if len(feat) < 30:
        raise ValueError(f"Not enough history for dealer {dealer_id} / {fuel_type}")

    split = int(len(feat) * 0.85)
    train, test = feat.iloc[:split], feat.iloc[split:]

    X_train, y_train = train[FEATURE_COLS], train["quantity_l"]
    X_test, y_test = test[FEATURE_COLS], test["quantity_l"]

    model = RandomForestRegressor(n_estimators=300, max_depth=10, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    mae = float(mean_absolute_error(y_test, preds))
    rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
    mape = float(np.mean(np.abs((y_test.values - preds) / np.clip(y_test.values, 1, None))) * 100)

    fname = f"dealer{dealer_id}_{fuel_type.lower()}.joblib"
    joblib.dump({"model": model, "feature_cols": FEATURE_COLS, "lags": LAGS, "rolling": ROLLING_WINDOWS}, os.path.join(MODEL_DIR, fname))

    return {"dealer_id": dealer_id, "fuel_type": fuel_type, "mae": mae, "rmse": rmse, "mape": mape, "n_train": len(train), "n_test": len(test)}


def main():
    db = SessionLocal()
    metrics = []
    try:
        fuel_pairs = db.query(m.DailySales.dealer_id, m.DailySales.fuel_type).distinct().all()
        for dealer_id, fuel_type in fuel_pairs:
            rows = db.query(m.DailySales).filter(
                m.DailySales.dealer_id == dealer_id, m.DailySales.fuel_type == fuel_type
            ).all()
            raw = pd.DataFrame([{"sale_date": r.sale_date, "quantity_l": r.quantity_l} for r in rows])
            if raw.empty:
                continue
            try:
                result = train_one(dealer_id, fuel_type, raw)
            except ValueError as error:
                print(f"Skipped dealer={dealer_id} fuel={fuel_type}: {error}")
                continue
            metrics.append(result)
            print(f"Trained dealer={dealer_id} fuel={fuel_type}: MAE={result['mae']:.1f}L "
                  f"RMSE={result['rmse']:.1f}L MAPE={result['mape']:.2f}%")
    finally:
        db.close()

    with open(os.path.join(MODEL_DIR, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"\nSaved {len(metrics)} models to {MODEL_DIR}")


if __name__ == "__main__":
    main()
