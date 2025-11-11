# tests/test_graph.py

from lattice_base.model import Lattice, ProjectMeta, Task
from lattice_base.graph import (
    compute_ready_tasks,
    topological_sort,
    iter_edges,
    build_dependency_graph,
)


def _make_chain_lattice() -> Lattice:
    """
    Build a simple A -> B -> C lattice for graph tests.
    A is done, B and C are planned.
    """
    project = ProjectMeta(
        id="graph-demo",
        name="Graph Demo Project",
    )

    tasks = [
        Task(
            id="a",
            name="Task A",
            kind="task",
            status="done",
            depends_on=[],
            test="echo a",
        ),
        Task(
            id="b",
            name="Task B",
            kind="task",
            status="planned",
            depends_on=["a"],
            test="echo b",
        ),
        Task(
            id="c",
            name="Task C",
            kind="task",
            status="planned",
            depends_on=["b"],
            test="echo c",
        ),
    ]

    return Lattice(version=0.1, project=project, tasks=tasks)


def test_compute_ready_tasks():
    """
    Only B should be ready in the A -> B -> C chain:
      - A is done
      - B depends on A, not done yet -> ready
      - C depends on B, which is not done yet -> not ready
    """
    lat = _make_chain_lattice()
    ready = compute_ready_tasks(lat)

    ready_ids = {t.id for t in ready}
    assert ready_ids == {"b"}, f"Expected only 'b' to be ready, got {ready_ids}"


def test_topological_sort_and_cycle_detection():
    """
    topological_sort should produce an order with dependencies first,
    and should raise ValueError when a cycle is present.
    """
    # Acyclic case
    lat = _make_chain_lattice()
    order = topological_sort(lat)

    # The exact order can vary, but A must come before B, and B before C.
    pos = {tid: i for i, tid in enumerate(order)}
    assert pos["a"] < pos["b"] < pos["c"]

    # Cyclic case: x <-> y
    project = ProjectMeta(id="cycle-demo", name="Cycle Demo")
    tasks = [
        Task(
            id="x",
            name="Task X",
            kind="task",
            status="planned",
            depends_on=["y"],
            test="echo x",
        ),
        Task(
            id="y",
            name="Task Y",
            kind="task",
            status="planned",
            depends_on=["x"],
            test="echo y",
        ),
    ]
    lat_cycle = Lattice(version=0.1, project=project, tasks=tasks)

    import pytest

    with pytest.raises(ValueError):
        _ = topological_sort(lat_cycle)


def test_build_dependency_graph_and_iter_edges_consistency():
    """
    Ensure build_dependency_graph and iter_edges agree on edges.
    """
    lat = _make_chain_lattice()

    dep_graph = build_dependency_graph(lat)
    edges = set(iter_edges(lat))

    # In our chain A -> B -> C, we expect:
    # A -> B, B -> C
    expected_edges = {("a", "b"), ("b", "c")}
    assert edges == expected_edges

    # dep_graph maps from each node to its outgoing neighbors
    assert dep_graph["a"] == ["b"]
    assert dep_graph["b"] == ["c"]
    # C has no outgoing edges
    assert dep_graph["c"] == []
