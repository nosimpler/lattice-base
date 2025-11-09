from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Set

import yaml

from .model import Lattice


def load_lattice(path: str | Path) -> Lattice:
    path = Path(path)
    with path.open("r") as f:
        data = yaml.safe_load(f) or {}
    return Lattice(**data)


def dump_lattice(lat: Lattice, path: str | Path) -> None:
    path = Path(path)
    with path.open("w") as f:
        yaml.safe_dump(lat.dict(), f, sort_keys=False)


def detect_cycles(lat: Lattice) -> List[List[str]]:
    tasks = lat.tasks
    graph: Dict[str, List[str]] = {t.id: list(t.depends_on) for t in tasks}
    temp: Set[str] = set()
    perm: Set[str] = set()
    stack: List[str] = []
    cycles: List[List[str]] = []

    def visit(node: str):
        if node in perm:
            return
        if node in temp:
            if node in stack:
                idx = stack.index(node)
                cycles.append(stack[idx:] + [node])
            return
        temp.add(node)
        stack.append(node)
        for dep in graph.get(node, []):
            visit(dep)
        stack.pop()
        temp.remove(node)
        perm.add(node)

    for n in graph:
        if n not in perm:
            visit(n)
    return cycles


def topo_sort(lat: Lattice) -> List[str]:
    tasks = lat.tasks
    deps: Dict[str, Set[str]] = {t.id: set(t.depends_on) for t in tasks}
    rev: Dict[str, Set[str]] = {t.id: set() for t in tasks}
    for t in tasks:
        for d in t.depends_on:
            rev.setdefault(d, set()).add(t.id)

    result: List[str] = []
    ready: List[str] = sorted([tid for tid, d in deps.items() if not d])

    while ready:
        n = ready.pop(0)
        result.append(n)
        for m in list(rev.get(n, [])):
            deps[m].discard(n)
            if not deps[m]:
                ready.append(m)
                ready.sort()

    if len(result) != len(tasks):
        raise ValueError("Graph has cycles; cannot topologically sort")
    return result
