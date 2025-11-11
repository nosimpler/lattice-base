# tests/test_cli_next.py

from pathlib import Path

import yaml

from lattice_base import cli


def test_lists_ready_tasks(tmp_path, capsys):
    repo = tmp_path
    project_yaml = repo / "project.yaml"

    # Minimal lattice with three tasks:
    # - a: done
    # - b: planned, depends_on a      -> should be ready
    # - c: planned, depends_on b      -> not ready yet
    data = {
        "version": 0.1,
        "project": {
            "id": "demo",
            "name": "Demo Project",
        },
        "tasks": [
            {
                "id": "a",
                "name": "A done",
                "kind": "task",
                "status": "done",
                "depends_on": [],
                "test": "echo a",  # not used, but keeps semantics happy
            },
            {
                "id": "b",
                "name": "B depends on A",
                "kind": "task",
                "status": "planned",
                "depends_on": ["a"],
                "test": "echo b",
            },
            {
                "id": "e",
                "name": "epic depends on B",
                "kind": "epic",
                "depends_on": ["b"],
            },
            {
                "id": "c",
                "name": "C depends on E",
                "kind": "task",
                "status": "planned",
                "depends_on": ["e"],
                "test": "echo c",
            },
        ],
    }
    project_yaml.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    # Run lattice-base-next
    exit_code = cli.main_next(["--repo", str(repo)])
    captured = capsys.readouterr()

    assert exit_code == 0

    out = captured.out
    # Should mention that there are ready tasks
    assert "Ready tasks" in out

    # Task b should be listed as ready
    assert "b: B depends on A" in out

    # Task c should NOT appear, since b is not done yet
    assert "c: C depends on B" not in out
