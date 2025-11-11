# tests/test_validate.py

from pathlib import Path
import yaml

from lattice_base import cli


def _write_yaml(path: Path, data: dict):
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def test_basic_validation_rules(tmp_path, capsys):
    """Ensure lattice-base-validate correctly flags bad dependency and duplicate IDs."""
    repo = tmp_path
    project_yaml = repo / "project.yaml"

    # --- 1️⃣  Valid project ---
    good = {
        "version": 0.1,
        "project": {"id": "demo", "name": "Validation Demo"},
        "tasks": [
            {
                "id": "a",
                "name": "Task A",
                "kind": "task",
                "status": "planned",
                "depends_on": [],
                "test": "echo a",
            },
            {
                "id": "b",
                "name": "Task B",
                "kind": "task",
                "status": "planned",
                "depends_on": ["a"],
                "test": "echo b",
            },
        ],
    }
    _write_yaml(project_yaml, good)

    exit_code = cli.main_validate(["--repo", str(repo)])
    captured = capsys.readouterr()
    assert exit_code == 0, f"Expected success, got {exit_code}"
    assert "project.yaml is valid" in captured.out or "is valid." in captured.out

    # --- 2️⃣  Invalid dependency (unknown depends_on id) ---
    bad_dep = {
        "version": 0.1,
        "project": {"id": "demo", "name": "Validation Demo"},
        "tasks": [
            {
                "id": "a",
                "name": "Task A",
                "kind": "task",
                "status": "planned",
                "depends_on": [],
                "test": "echo a",
            },
            {
                "id": "b",
                "name": "Task B",
                "kind": "task",
                "status": "planned",
                "depends_on": ["missing"],
                "test": "echo b",
            },
        ],
    }
    _write_yaml(project_yaml, bad_dep)

    exit_code = cli.main_validate(["--repo", str(repo)])
    captured = capsys.readouterr()
    assert exit_code != 0
    err = captured.err.lower()
    assert "depends_on unknown id" in err

    # --- 3️⃣  Duplicate IDs ---
    dup = {
        "version": 0.1,
        "project": {"id": "demo", "name": "Validation Demo"},
        "tasks": [
            {
                "id": "a",
                "name": "Task A",
                "kind": "task",
                "status": "planned",
                "depends_on": [],
                "test": "echo a",
            },
            {
                "id": "a",
                "name": "Task A again",
                "kind": "task",
                "status": "planned",
                "depends_on": [],
                "test": "echo a-again",
            },
        ],
    }
    _write_yaml(project_yaml, dup)

    exit_code = cli.main_validate(["--repo", str(repo)])
    captured = capsys.readouterr()
    assert exit_code != 0
    err = captured.err.lower()
    assert "duplicate task id" in err
