"""
Demand Forecast Agent.

Loads the trained per-dealer/fuel-type RandomForest model (see
app/ml/train_demand_model.py) and produces a multi-day-ahead forecast by
iterating one day at a time, feeding each prediction back in as a lag
feature for the next day (standard recursive forecasting).
"""
import os
import json
from datetime import date, timedelta
from typing import List

import joblib
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app import models as m
from app.schemas import ForecastOut, ForecastPoint
from app.ml.train_demand_model import LAGS, ROLLING_WINDOWS, FEATURE_COLS

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml", "model_store")


class DemandForecastAgent:

    def __init__(self, db: Session):
        self.db = db
        self._metrics = self._load_metrics()

    def _load_metrics(self):
        path = os.path.join(MODEL_DIR, "metrics.json")
        if os.path.exists(path):
            with open(path) as f:
                return {(r["dealer_id"], r["fuel_type"]): r for r in json.load(f)}
        return {}

    def _load_model(self, dealer_id: int, fuel_type: str):
        fname = f"dealer{dealer_id}_{fuel_type.lower()}.joblib"
        path = os.path.join(MODEL_DIR, fname)
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"No trained model for dealer={dealer_id} fuel={fuel_type}. "
                f"Run `python -m app.ml.train_demand_model` first."
            )
        return joblib.load(path)

    def _recent_history(self, dealer_id: int, fuel_type: str, min_days: int = 30) -> pd.DataFrame:
        rows = (
            self.db.query(m.DailySales)
            .filter(m.DailySales.dealer_id == dealer_id, m.DailySales.fuel_type == fuel_type)
            .order_by(m.DailySales.sale_date.desc())
            .limit(60)
            .all()
        )
        if not rows:
            raise ValueError("No sales history available for this dealer and fuel type.")
        if len(rows) < min_days:
            min_days = len(rows)
        df = pd.DataFrame([{"sale_date": r.sale_date, "quantity_l": r.quantity_l} for r in rows])
        return df.sort_values("sale_date").reset_index(drop=True)

    def _fallback_predict(self, dealer_id: int, fuel_type: str, horizon_days: int = 7) -> ForecastOut:
        """Generates a deterministic offline baseline when the trained model is unavailable."""
        history = self._recent_history(dealer_id, fuel_type, min_days=14)
        values = history["quantity_l"].astype(float).tolist()
        recent_window = values[-7:]
        recent_mean = float(np.mean(recent_window)) if recent_window else 0.0
        trend = float(np.mean(np.diff(recent_window))) if len(recent_window) > 1 else 0.0

        points: List[ForecastPoint] = []
        last_date = pd.to_datetime(history["sale_date"].iloc[-1])
        for step in range(horizon_days):
            next_date = last_date + timedelta(days=step + 1)
            seasonal_adjustment = max(0.0, 0.12 * np.sin((next_date.dayofweek + 1) / 7 * 2 * np.pi))
            bias = step * 0.35 * max(0.0, trend)
            prediction = max(0.0, recent_mean + bias + seasonal_adjustment)
            points.append(ForecastPoint(date=next_date.date(), predicted_qty_l=round(prediction, 1)))

        return ForecastOut(
            fuel_type=fuel_type,
            horizon_days=horizon_days,
            confidence=0.62,
            model_version="baseline_v1",
            points=points,
            mae=None,
            rmse=None,
            mape=None,
        )

    def predict(self, dealer_id: int, fuel_type: str, horizon_days: int = 7) -> ForecastOut:
        try:
            bundle = self._load_model(dealer_id, fuel_type)
        except FileNotFoundError:
            return self._fallback_predict(dealer_id, fuel_type, horizon_days)

        model = bundle["model"]
        history = self._recent_history(dealer_id, fuel_type)

        try:
            series = history[["sale_date", "quantity_l"]].copy()
            series["sale_date"] = pd.to_datetime(series["sale_date"])

            points: List[ForecastPoint] = []
            cursor = series.copy()

            for step in range(horizon_days):
                next_date = cursor["sale_date"].iloc[-1] + timedelta(days=1)
                row = {"sale_date": next_date}
                row["day_of_week"] = next_date.dayofweek
                row["month"] = next_date.month
                row["is_weekend"] = int(next_date.dayofweek >= 5)

                vals = cursor["quantity_l"].values
                for lag in LAGS:
                    if len(vals) >= lag:
                        row[f"lag_{lag}"] = vals[-lag]
                    else:
                        row[f"lag_{lag}"] = float(vals[0]) if len(vals) else 0.0
                for w in ROLLING_WINDOWS:
                    window_values = vals[-w:] if len(vals) >= w else vals
                    row[f"rolling_mean_{w}"] = np.mean(window_values) if len(window_values) else 0.0
                    row[f"rolling_std_{w}"] = np.std(window_values) if len(window_values) else 0.0

                X = pd.DataFrame([row])[FEATURE_COLS]
                pred = float(model.predict(X)[0])
                pred = max(0.0, pred)

                points.append(ForecastPoint(date=next_date.date(), predicted_qty_l=round(pred, 1)))
                cursor = pd.concat([cursor, pd.DataFrame([{"sale_date": next_date, "quantity_l": pred}])], ignore_index=True)

            metrics = self._metrics.get((dealer_id, fuel_type), {})
            mape = metrics.get("mape", None)
            confidence = max(0.5, 1 - (mape / 100)) if mape is not None else 0.75

            return ForecastOut(
                fuel_type=fuel_type,
                horizon_days=horizon_days,
                confidence=round(confidence, 2),
                model_version="rf_v1",
                points=points,
                mae=metrics.get("mae"),
                rmse=metrics.get("rmse"),
                mape=metrics.get("mape"),
            )
        except (IndexError, ValueError, TypeError):
            return self._fallback_predict(dealer_id, fuel_type, horizon_days)

    def predicted_daily_demand(self, dealer_id: int, fuel_type: str) -> float:
        """Convenience: average of the next-day and 3-day forecast, used by other agents."""
        forecast = self.predict(dealer_id, fuel_type, horizon_days=3)
        return sum(p.predicted_qty_l for p in forecast.points) / len(forecast.points)
