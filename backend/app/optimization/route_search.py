"""
A* / Dijkstra route search.

Real turn-by-turn routing needs a mapping API and is out of scope for this
academic project. Instead, we model the dealer->refinery corridor as a
small synthetic waypoint graph (a handful of alternative road segments with
distance + heuristic straight-line estimates) so the optimizer has a real
shortest-path problem to solve, with a clean seam to swap in a real
road-graph/Maps API later.
"""
import heapq
from typing import Dict, List, Tuple


def build_corridor_graph(distance_km: float) -> Tuple[Dict[str, List[Tuple[str, float]]], Dict[str, float]]:
    """
    Builds a small synthetic graph with 2-3 alternative routes between
    'DEALER' and 'REFINERY', each with a different distance (representing
    highway vs local road choices), plus straight-line heuristic distances
    for A*.
    """
    highway = round(distance_km * 1.05, 1)     # slightly longer, but faster in practice
    local_road = round(distance_km * 1.25, 1)  # shorter detour avoided, more turns
    direct = round(distance_km * 1.0, 1)

    graph = {
        "DEALER": [("VIA_HIGHWAY", highway / 2), ("VIA_LOCAL", local_road / 2), ("VIA_DIRECT", direct / 2)],
        "VIA_HIGHWAY": [("REFINERY", highway / 2)],
        "VIA_LOCAL": [("REFINERY", local_road / 2)],
        "VIA_DIRECT": [("REFINERY", direct / 2)],
        "REFINERY": [],
    }
    heuristic = {
        "DEALER": distance_km,
        "VIA_HIGHWAY": distance_km / 2,
        "VIA_LOCAL": distance_km / 2,
        "VIA_DIRECT": distance_km / 2,
        "REFINERY": 0.0,
    }
    return graph, heuristic


def dijkstra(graph: Dict[str, List[Tuple[str, float]]], start: str, goal: str):
    dist = {node: float("inf") for node in graph}
    dist[start] = 0.0
    prev = {}
    pq = [(0.0, start)]
    visited = set()

    while pq:
        d, node = heapq.heappop(pq)
        if node in visited:
            continue
        visited.add(node)
        if node == goal:
            break
        for neighbor, weight in graph.get(node, []):
            nd = d + weight
            if nd < dist[neighbor]:
                dist[neighbor] = nd
                prev[neighbor] = node
                heapq.heappush(pq, (nd, neighbor))

    path = _reconstruct(prev, start, goal)
    return path, dist.get(goal, float("inf"))


def a_star(graph: Dict[str, List[Tuple[str, float]]], heuristic: Dict[str, float], start: str, goal: str):
    dist = {node: float("inf") for node in graph}
    dist[start] = 0.0
    prev = {}
    pq = [(heuristic.get(start, 0), start)]
    visited = set()

    while pq:
        _, node = heapq.heappop(pq)
        if node in visited:
            continue
        visited.add(node)
        if node == goal:
            break
        for neighbor, weight in graph.get(node, []):
            nd = dist[node] + weight
            if nd < dist[neighbor]:
                dist[neighbor] = nd
                prev[neighbor] = node
                heapq.heappush(pq, (nd + heuristic.get(neighbor, 0), neighbor))

    path = _reconstruct(prev, start, goal)
    return path, dist.get(goal, float("inf"))


def _reconstruct(prev, start, goal):
    if goal not in prev and goal != start:
        return []
    path = [goal]
    while path[-1] != start:
        path.append(prev[path[-1]])
    return list(reversed(path))


def best_route(distance_km: float) -> dict:
    """Convenience wrapper: runs both algorithms and returns the best result found."""
    graph, heuristic = build_corridor_graph(distance_km)
    dij_path, dij_dist = dijkstra(graph, "DEALER", "REFINERY")
    astar_path, astar_dist = a_star(graph, heuristic, "DEALER", "REFINERY")

    best_path, best_dist, algo = (dij_path, dij_dist, "dijkstra") if dij_dist <= astar_dist else (astar_path, astar_dist, "a_star")
    return {"path": best_path, "distance_km": round(best_dist, 1), "algorithm": algo}
