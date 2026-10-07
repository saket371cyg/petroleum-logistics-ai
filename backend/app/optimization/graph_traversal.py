"""
BFS and DFS utilities.

Per the project spec these are NOT used for dispatch optimization (that's
Hill Climbing, see hill_climbing.py). They serve two different purposes:

  BFS -> explore system/entity relationships level-by-level. Used here to
         answer "what does this dispatch depend on / relate to, at each
         distance" (e.g. dispatch -> order/tanker/driver -> dealer/refinery).

  DFS -> trace a single deep dependency/workflow path end-to-end, e.g.
         "walk the full chain from a fuel order to its eventual delivery."
"""
from collections import deque
from typing import Callable, Dict, List, Set


def build_relationship_graph(dispatch, db, models) -> Dict[str, List[str]]:
    """
    Builds an adjacency list describing how a dispatch relates to other
    entities, for BFS/DFS demonstration and for the Executive Agent's
    "show related records" feature.
    """
    graph: Dict[str, List[str]] = {}

    dispatch_node = f"dispatch:{dispatch.id}"
    order_node = f"order:{dispatch.order_id}"
    graph.setdefault(dispatch_node, []).append(order_node)

    dealer_node = f"dealer:{dispatch.dealer_id}"
    graph.setdefault(order_node, []).append(dealer_node)

    if dispatch.tanker_id:
        tanker_node = f"tanker:{dispatch.tanker_id}"
        graph.setdefault(dispatch_node, []).append(tanker_node)
        graph.setdefault(tanker_node, []).append(dealer_node)

    if dispatch.driver_id:
        driver_node = f"driver:{dispatch.driver_id}"
        graph.setdefault(dispatch_node, []).append(driver_node)
        graph.setdefault(driver_node, []).append(dealer_node)

    if dispatch.loading_slot_id:
        slot = db.query(models.LoadingSlot).filter(models.LoadingSlot.id == dispatch.loading_slot_id).first()
        if slot:
            slot_node = f"slot:{slot.id}"
            refinery_node = f"refinery:{slot.refinery_id}"
            graph.setdefault(dispatch_node, []).append(slot_node)
            graph.setdefault(slot_node, []).append(refinery_node)

    return graph


def bfs_levels(graph: Dict[str, List[str]], start: str) -> List[List[str]]:
    """Returns nodes grouped by distance (level) from `start`."""
    visited: Set[str] = {start}
    queue = deque([start])
    levels: List[List[str]] = []

    while queue:
        level_size = len(queue)
        level_nodes = []
        for _ in range(level_size):
            node = queue.popleft()
            level_nodes.append(node)
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        levels.append(level_nodes)
    return levels


def dfs_path(graph: Dict[str, List[str]], start: str) -> List[str]:
    """Returns one deep path from `start`, following the first unvisited neighbor each time."""
    visited: Set[str] = set()
    path: List[str] = []

    def _visit(node: str):
        if node in visited:
            return
        visited.add(node)
        path.append(node)
        for neighbor in graph.get(node, []):
            _visit(neighbor)

    _visit(start)
    return path
