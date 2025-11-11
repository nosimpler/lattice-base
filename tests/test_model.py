# tests/test_model.py

from pathlib import Path
import yaml

from lattice_base.model import Lattice, ProjectMeta, Task
from lattice_base.io import save_lattice, load_lattice


def make_sample_lattice() -> Lattice:
    """Helper that constructs a minimal lattice for roundtrip testing."""
    project = ProjectMeta(
        id="demo",
        name="Demo Project",
        owner="tester",
        description="A simple project for testing lattice roundtrips.",
    )

    tasks = [
        Task(
            id="a",
            name="Task A",
            kind="task",
            status="planned",
            depends_on=[],
            tags=["core"],
            test="echo a",
            description="First task in the lattice.",
        ),
        Task(
            id="b",
            name="Task B",
            kind="task",
            status="planned",
            depends_on=["a"],
            tags=["core"],
            test="echo b",
            description="Depends on A.",
        ),
    ]

    return Lattice(version=0.1, project=project, tasks=tasks)


def test_lattice_roundtrip(tmp_path: Path):
    """Ensure Lattice objects serialize/deserialize correctly via YAML."""
    lattice = make_sample_lattice()
    path = tmp_path / "project.yaml"

    # Save to disk
    save_lattice(lattice, path)
    assert path.exists(), "YAML file should be written to disk"

    # Load back
    loaded = load_lattice(path)

    # Basic project-level checks
    assert loaded.project.id == lattice.project.id
    assert loaded.project.name == lattice.project.name
    assert isinstance(loaded.tasks, list)
    assert len(loaded.tasks) == 2

    # Check field preservation for first task
    t0 = loaded.tasks[0]
    assert t0.id == "a"
    assert t0.kind == "task"
    assert t0.status == "planned"
    assert t0.test == "echo a"

    # Ensure dependencies preserved
    t1 = loaded.tasks[1]
    assert t1.depends_on == ["a"]

    # And YAML content matches expected structure
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    assert "project" in data and "tasks" in data
    assert data["project"]["id"] == "demo"
