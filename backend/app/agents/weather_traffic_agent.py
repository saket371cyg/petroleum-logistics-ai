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

    def _fetch_conditions(
        self,
        distance_km: float,
        departure_time: datetime,
        dealer_location: str = "inland",
        route_profile: str = "default",
    ) -> tuple:
        """Synthetic stand-in for a real traffic/weather API call."""
        location_bias = {
            "coastal": {"RAIN": 1.8, "FOG": 1.2, "STORM": 1.6, "traffic": 1.1},
            "inland": {"RAIN": 1.0, "FOG": 1.0, "STORM": 1.0, "traffic": 1.0},
            "hilly": {"RAIN": 1.5, "FOG": 1.8, "STORM": 1.9, "traffic": 1.15},
        }.get(dealer_location.lower(), {"RAIN": 1.0, "FOG": 1.0, "STORM": 1.0, "traffic": 1.0})

        route_bias = {
            "default": (0.0, 0.0),
            "port_corridor": (0.10, 0.08),
            "mountain_pass": (0.15, 0.12),
            "highway_arc": (-0.05, -0.04),
        }.get(route_profile.lower(), (0.0, 0.0))

        seed = int(distance_km * 100) + departure_time.hour + int((departure_time.minute / 60) * 10)
        rng = random.Random(seed)

        traffic_weights = [0.5, 0.35, 0.15]
        traffic_weights[0] = max(0.1, traffic_weights[0] + route_bias[1])
        traffic_weights[1] = max(0.1, traffic_weights[1] + route_bias[1] * 0.5)
        traffic_weights[2] = min(0.7, traffic_weights[2] + route_bias[0])

        traffic_level = rng.choices(["LOW", "MODERATE", "HEAVY"], weights=traffic_weights)[0]
        weather_map = {"CLEAR": 0.65, "RAIN": 0.2, "FOG": 0.1, "STORM": 0.05}
        weather_map["RAIN"] *= location_bias["RAIN"]
        weather_map["FOG"] *= location_bias["FOG"]
        weather_map["STORM"] *= location_bias["STORM"]
        weather = rng.choices(["CLEAR", "RAIN", "FOG", "STORM"], weights=list(weather_map.values()))[0]
        return traffic_level, weather

    def assess(
        self,
        distance_km: float,
        departure_time: datetime,
        dealer_location: str = "inland",
        route_profile: str = "default",
    ) -> RouteRiskAssessment:
        traffic_level, weather = self._fetch_conditions(distance_km, departure_time, dealer_location, route_profile)
        base_hours = distance_km / self.AVG_SPEED_KMPH

        traffic_delay_factor = {"LOW": 0.0, "MODERATE": 0.20, "HEAVY": 0.45}[traffic_level]
        weather_delay_factor = {"CLEAR": 0.0, "RAIN": 0.15, "FOG": 0.25, "STORM": 0.40}[weather]

        if dealer_location.lower() == "coastal" and weather == "RAIN":
            weather_delay_factor += 0.05
        if route_profile.lower() == "port_corridor" and traffic_level == "HEAVY":
            traffic_delay_factor += 0.05

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
