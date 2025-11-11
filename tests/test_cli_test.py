# tests/test_cli_test.py

from pathlib import Path

import yaml

from lattice_base import cli


def test_complete_marks_successful_tasks_done(tmp_path, capsys):
    repo = tmp_path
    project_yaml = repo / "project.yaml"

    # A -> B chain, both have trivial passing tests
    data = {
        "version": 0.1,
        "project": {"id": "demo", "name": "Demo Project"},
        "tasks": [
            {
                "id": "a",
                "name": "Task A",
                "kind": "task",
                "status": "planned",
                "depends_on": [],
                "test": "echo A",
            },
            {
                "id": "b",
                "name": "Task B",
                "kind": "task",
                "status": "planned",
                "depends_on": ["a"],
                "test": "echo B",
            },
        ],
    }
    project_yaml.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    exit_code = cli.main_test(["--repo", str(repo), "--complete"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Updated status for 'a': planned -> done" in captured.out
    assert "Updated status for 'b': planned -> done" in captured.out

    updated = yaml.safe_load(project_yaml.read_text(encoding="utf-8"))
    tasks = {t["id"]: t for t in updated["tasks"]}

    assert tasks["a"]["status"] == "done"
    assert tasks["b"]["status"] == "done"


def test_complete_demotes_done_task_on_failed_test(tmp_path, capsys):
    repo = tmp_path
    project_yaml = repo / "project.yaml"

    # Single task t1 is marked done but its test will fail
    data = {
        "version": 0.1,
        "project": {"id": "demo", "name": "Demo Project"},
        "tasks": [
            {
                "id": "t1",
                "name": "Task with failing test",
                "kind": "task",
                "status": "done",
                "depends_on": [],
                # Use a Python command that exits with code 1
                "test": 'python -c "import sys; sys.exit(1)"',
            }
        ],
    }
    project_yaml.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    exit_code = cli.main_test(["--repo", str(repo), "--complete"])
    captured = capsys.readouterr()

    assert exit_code != 0
    assert "FAILED with exit code" in captured.err
    assert "Demoting 't1' from done -> in-progress" in captured.out

    updated = yaml.safe_load(project_yaml.read_text(encoding="utf-8"))
    [task] = updated["tasks"]
    assert task["status"] == "in-progress"


def test_complete_demotes_done_when_deps_not_done(tmp_path, capsys):
    repo = tmp_path
    project_yaml = repo / "project.yaml"

    # A is planned (not done), B is done but depends on A.
    # In --complete mode, B should be demoted to planned and its test skipped.
    data = {
        "version": 0.1,
        "project": {"id": "demo", "name": "Demo Project"},
        "tasks": [
            {
                "id": "a",
                "name": "Upstream task A",
                "kind": "task",
                "status": "planned",
                "depends_on": [],
                "test": "echo A",
            },
            {
                "id": "b",
                "name": "Downstream task B",
                "kind": "task",
                "status": "done",
                "depends_on": ["a"],
                "test": "echo B",
            },
        ],
    }
    project_yaml.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    exit_code = cli.main_test(["--repo", str(repo), "--complete"])
    captured = capsys.readouterr()

    # Tests for A/B may run; crucial is that B is demoted since A is not done on first pass
    assert exit_code == 0 or exit_code == 0  # we don't care about exact code here if both tests succeed

    updated = yaml.safe_load(project_yaml.read_text(encoding="utf-8"))
    tasks = {t["id"]: t for t in updated["tasks"]}

    # After first pass, A should become done (test passes)
    assert tasks["a"]["status"] == "done"
    # B should have been demoted from done -> planned because at the time it was processed, A wasn't done yet
    assert tasks["b"]["status"] == "planned"
def test_main_test_marks_done_on_success(tmp_path, capsys):
    """
    lattice-base-test --task ... --mark-done should run the test command,
    exit with code 0, and update the task status to 'done' on success.
    """
    repo = tmp_path
    project_yaml = repo / "project.yaml"

    data = {
        "version": 0.1,
        "project": {"id": "demo", "name": "Demo Project"},
        "tasks": [
            {
                "id": "t1",
                "name": "Task with echo test",
                "kind": "task",
                "status": "planned",
                "depends_on": [],
                "test": "echo ok",
            }
        ],
    }
    project_yaml.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    # Run lattice-base-test in single-task mode
    exit_code = cli.main_test(["--repo", str(repo), "--task", "t1", "--mark-done"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Test for 't1' succeeded" in captured.out
    assert "Updated status for 't1': planned -> done" in captured.out

    # Reload lattice and check status
    updated = yaml.safe_load(project_yaml.read_text(encoding="utf-8"))
    [task] = updated["tasks"]
    assert task["status"] == "done"


def test_main_test_errors_on_missing_test(tmp_path, capsys):
    """
    lattice-base-test --task ... should fail if the task has no test command.
    """
    repo = tmp_path
    project_yaml = repo / "project.yaml"

    data = {
        "version": 0.1,
        "project": {"id": "demo", "name": "Demo Project"},
        "tasks": [
            {
                "id": "t1",
                "name": "Task without test",
                "kind": "task",
                "status": "planned",
                "depends_on": [],
                # no 'test' field
            }
        ],
    }
    project_yaml.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    exit_code = cli.main_test(["--repo", str(repo), "--task", "t1"])
    captured = capsys.readouterr()

    assert exit_code != 0
    assert "has no test command defined" in captured.err