from datetime import datetime

from app.agents.weather_traffic_agent import WeatherTrafficAgent
from app.optimization.route_search import best_route


def test_weather_agent_accepts_dealer_profile_for_route_risk():
    agent = WeatherTrafficAgent()
    assessment = agent.assess(
        distance_km=120,
        departure_time=datetime(2026, 6, 15, 17, 30),
        dealer_location="coastal",
        route_profile="port_corridor",
    )

    assert assessment.risk_level in {"LOW", "MEDIUM", "HIGH"}
    assert assessment.weather_condition in {"CLEAR", "RAIN", "FOG", "STORM"}
    assert assessment.base_travel_hours > 0
    assert assessment.eta_adjustment_hours >= 0


def test_best_route_uses_dealer_specific_profile():
    route = best_route(
        distance_km=120,
        dealer_location="coastal",
        route_profile="port_corridor",
    )

    assert route["distance_km"] > 0
    assert route["algorithm"] in {"dijkstra", "a_star"}
    assert route["path"][0] == "DEALER"
    assert route["path"][-1] == "REFINERY"
