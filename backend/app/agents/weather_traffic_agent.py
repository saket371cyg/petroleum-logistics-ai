"""
Weather & Traffic Agent.

Clean abstraction so a real traffic/weather API can be plugged in later
(swap `_fetch_conditions` for a real HTTP call). For development, conditions
are synthetically generated but deterministic per (distance, hour) so the
same route always returns the same simulated risk within a run.
"""
import random
from dataclasses import dataclass
from datetime import datetime


@dataclass
class RouteRiskAssessment:
    traffic_level: str      # LOW / MODERATE / HEAVY
    weather_condition: str  # CLEAR / RAIN / FOG / STORM
    base_travel_hours: float
    eta_adjustment_hours: float
    risk_score: float       # 0-100
    risk_level: str         # LOW / MEDIUM / HIGH


class WeatherTrafficAgent:

    AVG_SPEED_KMPH = 40.0

    def _fetch_conditions(self, distance_km: float, departure_time: datetime) -> tuple:
        """Synthetic stand-in for a real traffic/weather API call."""
        seed = int(distance_km * 100) + departure_time.hour
        rng = random.Random(seed)
        traffic_level = rng.choices(["LOW", "MODERATE", "HEAVY"], weights=[0.5, 0.35, 0.15])[0]
        weather = rng.choices(["CLEAR", "RAIN", "FOG", "STORM"], weights=[0.65, 0.2, 0.1, 0.05])[0]
        return traffic_level, weather

    def assess(self, distance_km: float, departure_time: datetime) -> RouteRiskAssessment:
        traffic_level, weather = self._fetch_conditions(distance_km, departure_time)
        base_hours = distance_km / self.AVG_SPEED_KMPH

        traffic_delay_factor = {"LOW": 0.0, "MODERATE": 0.20, "HEAVY": 0.45}[traffic_level]
        weather_delay_factor = {"CLEAR": 0.0, "RAIN": 0.15, "FOG": 0.25, "STORM": 0.40}[weather]

        eta_adjustment = base_hours * (traffic_delay_factor + weather_delay_factor)

        risk_score = min(100, (traffic_delay_factor + weather_delay_factor) * 100)
        risk_level = "HIGH" if risk_score >= 45 else ("MEDIUM" if risk_score >= 20 else "LOW")

        return RouteRiskAssessment(
            traffic_level=traffic_level,
            weather_condition=weather,
            base_travel_hours=round(base_hours, 2),
            eta_adjustment_hours=round(eta_adjustment, 2),
            risk_score=round(risk_score, 1),
            risk_level=risk_level,
        )
