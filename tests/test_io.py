# tests/test_io.py

from pathlib import Path

import yaml

from lattice_base.model import Lattice, ProjectMeta, Task
from lattice_base.io import load_lattice, save_lattice


def test_load_save_roundtrip(tmp_path: Path):
    """
    Verify that load_lattice and save_lattice can roundtrip a basic lattice
    through YAML on disk without losing key information.
    """
    # Construct a basic in-memory lattice
    project = ProjectMeta(
        id="demo-io",
        name="Demo IO Project",
        owner="tester",
        description="Project for testing IO roundtrip.",
    )

    tasks = [
        Task(
            id="a",
            name="Task A",
            kind="task",
            status="planned",
            depends_on=[],
            tags=["io"],
            test="echo a",
            description="Root task",
        ),
        Task(
            id="b",
            name="Task B",
            kind="task",
            status="planned",
            depends_on=["a"],
            tags=["io"],
            test="echo b",
            description="Depends on A",
        ),
    ]

    lattice_original = Lattice(version=0.1, project=project, tasks=tasks)

    path = tmp_path / "project.yaml"

    # Save to disk
    save_lattice(lattice_original, path)
    assert path.exists(), "project.yaml should be written by save_lattice"

    # Load back
    lattice_loaded = load_lattice(path)

    # Compare core fields
    assert lattice_loaded.project.id == lattice_original.project.id
    assert lattice_loaded.project.name == lattice_original.project.name
    assert len(lattice_loaded.tasks) == len(lattice_original.tasks)

    by_id_original = {t.id: t for t in lattice_original.tasks}
    by_id_loaded = {t.id: t for t in lattice_loaded.tasks}

    assert set(by_id_original.keys()) == set(by_id_loaded.keys())

    for tid, t_orig in by_id_original.items():
        t_loaded = by_id_loaded[tid]
        assert t_loaded.name == t_orig.name
        assert t_loaded.kind == t_orig.kind
        assert t_loaded.status == t_orig.status
        assert t_loaded.depends_on == t_orig.depends_on
        assert t_loaded.test == t_orig.test

    # Also check that the YAML structure is sensible
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    assert "project" in data
    assert "tasks" in data
    assert data["project"]["id"] == "demo-io"
