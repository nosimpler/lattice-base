# tests/test_cli_mermaid.py

from pathlib import Path

import yaml

from lattice_base import cli


def test_mermaid_output_non_empty(tmp_path, capsys):
    """
    lattice-base-mermaid should emit a Mermaid graph that includes:
      - a 'graph TD' (default direction)
      - at least the node ids
      - edges between dependent tasks
    """
    repo = tmp_path
    project_yaml = repo / "project.yaml"

    data = {
        "version": 0.1,
        "project": {"id": "demo", "name": "Demo Mermaid Project"},
        "tasks": [
            {
                "id": "a",
                "name": "Task A",
                "kind": "task",
                "status": "done",
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
            {
                "id": "ep1",
                "name": "Epic 1",
                "kind": "epic",
                "depends_on": [],
                "tags": ["epic"],
                "description": "An epic node for grouping",
            },
        ],
    }
    project_yaml.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    # Run lattice-base-mermaid
    exit_code = cli.main_mermaid(["--repo", str(repo)])
    captured = capsys.readouterr()

    assert exit_code == 0

    out = captured.out.strip()
    assert out, "Mermaid output should not be empty"

    # Basic structural checks
    assert out.startswith("graph TD"), "Default graph direction should be TD"

    # Node definitions
    assert "a(" in out or 'a("' in out  # allow for shape variations
    assert "b(" in out or 'b("' in out

    # Edge definition a --> b
    assert "a --> b" in out
