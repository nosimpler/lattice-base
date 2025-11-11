# tests/test_cli_init.py

from pathlib import Path

import yaml

from lattice_base import cli


def test_init_creates_project_yaml(tmp_path):
    repo = tmp_path

    # Run the CLI entry point directly
    exit_code = cli.main_init(
        ["--repo", str(repo), "--id", "testproj", "--name", "Test Project"]
    )
    assert exit_code == 0

    project_yaml = repo / "project.yaml"
    assert project_yaml.exists(), "project.yaml should be created by lattice-base-init"

    data = yaml.safe_load(project_yaml.read_text(encoding="utf-8"))
    assert "project" in data
    proj = data["project"]

    assert proj["id"] == "testproj"
    assert proj["name"] == "Test Project"

    # Make sure the default statuses were written
    assert "statuses" in proj
    assert set(proj["statuses"]) == {
        "suggested",
        "design",
        "planned",
        "in-progress",
        "done",
        "blocked",
    }

    # Calling init again on same repo should fail (no overwrite)
    exit_code2 = cli.main_init(["--repo", str(repo), "--id", "testproj2"])
    assert exit_code2 != 0
