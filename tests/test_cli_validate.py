# tests/test_cli_validate.py

from pathlib import Path

import yaml

from lattice_base import cli


def test_reports_validation_errors(tmp_path, capsys):
    repo = tmp_path
    project_yaml = repo / "project.yaml"

    # Lattice with two validation problems:
    # 1) Task t1 depends_on unknown id "missing"
    # 2) Task t1 has status planned but no test command
    data = {
        "version": 0.1,
        "project": {
            "id": "demo",
            "name": "Demo Project",
        },
        "tasks": [
            {
                "id": "t1",
                "name": "Broken task",
                "kind": "task",
                "status": "planned",
                "depends_on": ["missing"],
                # no test field -> should trigger validation error
            }
        ],
    }
    project_yaml.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    exit_code = cli.main_validate(["--repo", str(repo)])
    captured = capsys.readouterr()

    assert exit_code != 0, "Validation should fail for an invalid lattice"

    err = captured.err
    # Check that both kinds of error are mentioned
    assert "depends_on unknown id" in err
    assert "must define a test command" in err
