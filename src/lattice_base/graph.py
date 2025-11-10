from __future__ import annotations

from typing import List, Dict, Set, Iterable

from .model import Lattice, Task, Status


def build_dependency_graph(lat: Lattice) -> Dict[str, List[str]]:
    idx = lat.task_index()
    graph: Dict[str, List[str]] = {k: [] for k in idx.keys()}
    for t in lat.tasks:
        for dep in t.depends_on:
            if dep in graph:
                graph[dep].append(t.id)
    return graph


def compute_ready_tasks(lat: Lattice) -> List[Task]:
    idx = lat.task_index()

    def is_done(tid: str) -> bool:
        t = idx.get(tid)
        return bool(t and t.status == "done")

    ready: List[Task] = []
    for t in lat.tasks:
        if t.kind != "task":
            continue
        status: Status | None = t.status or "suggested"  # type: ignore
        if status in ("done", "blocked"):
            continue

        if all(is_done(d) for d in t.depends_on):
            ready.append(t)
    return ready


def topological_sort(lat: Lattice) -> List[str]:
    """
    Simple Kahn's algorithm. Raises ValueError on cycles.
    """
    idx = lat.task_index()
    incoming: Dict[str, int] = {k: 0 for k in idx.keys()}

    for t in lat.tasks:
        for dep in t.depends_on:
            if dep in incoming:
                incoming[t.id] += 1

    # nodes with no incoming
    queue: List[str] = [tid for tid, deg in incoming.items() if deg == 0]
    result: List[str] = []

    while queue:
        n = queue.pop()
        result.append(n)
        for t in lat.tasks:
            if n in t.depends_on:
                incoming[t.id] -= 1
                if incoming[t.id] == 0:
                    queue.append(t.id)

    if len(result) != len(idx):
        raise ValueError("Cycle detected in dependency graph")
    return result


def iter_edges(lat: Lattice) -> Iterable[tuple[str, str]]:
    """
    Yield (from_id, to_id) for each dependency edge dep -> task.
    """
    idx = lat.task_index()
    for t in lat.tasks:
        for dep in t.depends_on:
            if dep in idx:
                yield dep, t.id
