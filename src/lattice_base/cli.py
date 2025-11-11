from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

import yaml
import subprocess

from .model import Lattice, ProjectMeta, Task
from .io import load_lattice, save_lattice
from .graph import compute_ready_tasks, topological_sort, iter_edges


DEFAULT_FILENAME = "project.yaml"


def _find_repo_root(start: Path) -> Path:
    """
    Very simple heuristic: walk up until we find a project.yaml, pyproject.toml, or .git.
    """
    p = start.resolve()
    for parent in [p] + list(p.parents):
        if (parent / DEFAULT_FILENAME).exists() or (parent / "pyproject.toml").exists() or (parent / ".git").exists():
            return parent
    return start


# ---------------------- init ----------------------


def main_init(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Initialize a project.yaml lattice.")
    parser.add_argument("--repo", type=str, default=".", help="Path to repo root (default: .)")
    parser.add_argument("--id", type=str, default=None, help="Project id (default: repo directory name)")
    parser.add_argument("--name", type=str, default=None, help="Project name (default: id)")
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    repo.mkdir(parents=True, exist_ok=True)
    pid = args.id or repo.name
    name = args.name or pid

    project = ProjectMeta(
        id=pid,
        name=name,
        owner=None,
        description=None,
        statuses=["suggested", "design", "planned", "in-progress", "done", "blocked"],
    )

    lattice = Lattice(project=project, tasks=[])

    out_path = repo / DEFAULT_FILENAME
    if out_path.exists():
        print(f"{out_path} already exists; refusing to overwrite.", file=sys.stderr)
        return 1

    save_lattice(lattice, out_path)
    print(f"Initialized lattice at {out_path}")
    return 0


# ---------------------- next ----------------------


def main_next(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="List tasks that are ready to start (all dependencies done, not blocked)."
    )
    parser.add_argument("--repo", type=str, default=".", help="Path to repo root (default: .)")
    parser.add_argument("--filename", type=str, default=DEFAULT_FILENAME, help="Lattice filename (default: project.yaml)")
    args = parser.parse_args(argv)

    repo = _find_repo_root(Path(args.repo))
    path = repo / args.filename
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        return 1

    lat = load_lattice(path)
    ready = compute_ready_tasks(lat)

    if not ready:
        print(f"No ready tasks found in {args.filename} (repo: {repo})")
        return 0

    print(f"Ready tasks in {args.filename} (repo: {repo}):\n")
    for t in sorted(ready, key=lambda t: (t.priority or "medium", t.id)):
        status = t.status or "suggested"
        deps = ", ".join(t.depends_on) if t.depends_on else "none"
        print(f"- {t.id}: {t.name}  (status: {status}, depends_on: {deps})")
    return 0


# ---------------------- validate ----------------------


def main_validate(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a lattice project.yaml.")
    parser.add_argument("--repo", type=str, default=".", help="Path to repo root (default: .)")
    parser.add_argument("--filename", type=str, default=DEFAULT_FILENAME, help="Lattice filename (default: project.yaml)")
    args = parser.parse_args(argv)

    repo = _find_repo_root(Path(args.repo))
    path = repo / args.filename
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        return 1

    lat = load_lattice(path)
    idx = lat.task_index()
    errors: list[str] = []

    # Check for duplicate task IDs
    id_counts: dict[str, int] = {}
    for t in lat.tasks:
        id_counts[t.id] = id_counts.get(t.id, 0) + 1
    for tid, count in id_counts.items():
        if count > 1:
            errors.append(f"Duplicate task id {tid!r} found.")

    # Check depends_on references
    for t in lat.tasks:
        for dep in t.depends_on:
            if dep not in idx:
                errors.append(f"Task {t.id!r} depends_on unknown id {dep!r}")

    # Check for cycles
    try:
        _ = topological_sort(lat)
    except ValueError as e:
        errors.append(f"Cycle detected: {e}")

    # Check test requirements for tasks/completions
    for t in lat.tasks:
        if t.kind in ("task", "completion"):
            status = t.status or "suggested"
            if status in ("design", "planned", "in-progress", "done", "blocked") and not t.test:
                errors.append(
                    f"Task {t.id!r} (kind={t.kind}, status={status}) must define a test command."
                )

    if errors:
        print("Validation failed:", file=sys.stderr)
        for e in errors:
            print(" -", e, file=sys.stderr)
        return 1

    print(f"{args.filename} is valid.")
    return 0


# ---------------------- mermaid ----------------------


def main_mermaid(argv: Optional[list[str]] = None) -> int:
    """
    Emit a Mermaid graph for the lattice on stdout.

    Usage:
        lattice-base-mermaid --repo . > lattice.mmd
    """
    parser = argparse.ArgumentParser(description="Generate Mermaid diagram for a lattice.")
    parser.add_argument("--repo", type=str, default=".", help="Path to repo root (default: .)")
    parser.add_argument("--filename", type=str, default=DEFAULT_FILENAME, help="Lattice filename (default: project.yaml)")
    parser.add_argument(
        "--direction",
        type=str,
        default="TD",
        choices=["TD", "LR", "BT"],
        help="Mermaid graph direction (TD, LR, BT). Default TD.",
    )
    args = parser.parse_args(argv)

    repo = _find_repo_root(Path(args.repo))
    path = repo / args.filename
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        return 1

    lat = load_lattice(path)
    idx = lat.task_index()

    # start mermaid
    print(f"graph {args.direction}")

    # nodes
    for t in lat.tasks:
        label = t.name or t.id
        # simple shape hint by kind
        shape_open = "("
        shape_close = ")"
        if t.kind == "epic":
            shape_open, shape_close = "[", "]"
        elif t.kind == "subproject":
            shape_open, shape_close = "[[", "]]"
        elif t.kind == "completion":
            shape_open, shape_close = "(((", ")))"

        print(f'  {t.id}{shape_open}"{label}"{shape_close}')

    # edges
    for src, dst in iter_edges(lat):
        print(f"  {src} --> {dst}")

    # optional styling by status (not required, but handy)
    print()
    print("%% status-based styling (optional, adjust in your docs if desired)")
    print("classDef done fill:#bbf,stroke:#000;")
    print("classDef inprogress fill:#ffd,stroke:#000;")
    print("classDef planned fill:#dfd,stroke:#000;")
    print("classDef blocked fill:#fbb,stroke:#000;")

    # assign classes
    for t in lat.tasks:
        if t.kind not in ("task", "completion"):
            continue
        status = t.status or "suggested"
        if status == "done":
            print(f"class {t.id} done;")
        elif status == "in-progress":
            print(f"class {t.id} inprogress;")
        elif status == "planned":
            print(f"class {t.id} planned;")
        elif status == "blocked":
            print(f"class {t.id} blocked;")

    return 0
# ---------------------- test (run task tests and optionally mark done) ----------------------



# ---------------------- test (run tests and optionally update statuses) ----------------------


def main_test(argv: Optional[list[str]] = None) -> int:
    """
    Run tests for lattice tasks.

    Modes:
      - Single task:
          lattice-base-test --task TASK_ID [--mark-done]
      - Complete mode (project-wide):
          lattice-base-test --complete

    In --task mode, runs the given task's test and optionally marks it done
    on success.

    In --complete mode, walks all testable tasks/completions in topological
    order, runs their tests when dependencies are done, marks successes as
    done, and demotes broken nodes when dependencies break or tests fail.
    """
    parser = argparse.ArgumentParser(description="Run tests for lattice tasks.")
    parser.add_argument("--repo", type=str, default=".", help="Path to repo root (default: .)")
    parser.add_argument(
        "--filename",
        type=str,
        default=DEFAULT_FILENAME,
        help="Lattice filename (default: project.yaml)",
    )
    parser.add_argument("--task", help="Task id whose test command should be run.")
    parser.add_argument(
        "--mark-done",
        action="store_true",
        help="(Single-task mode) Mark the task as 'done' when the test command succeeds.",
    )
    parser.add_argument(
        "--complete",
        action="store_true",
        help="Run tests for all testable tasks/completions and update statuses.",
    )
    args = parser.parse_args(argv)

    repo = _find_repo_root(Path(args.repo))
    path = repo / args.filename
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        return 1

    # Mode selection sanity
    if args.complete and args.task:
        print("ERROR: --task and --complete are mutually exclusive.", file=sys.stderr)
        return 1
    if not args.complete and not args.task:
        print("ERROR: must supply either --task or --complete.", file=sys.stderr)
        return 1

    # Load lattice once
    lat = load_lattice(path)

    if args.complete:
        return _main_test_complete(lat, path)
    else:
        return _main_test_single(lat, path, args.task, args.mark_done)


def _main_test_single(lat: Lattice, path: Path, task_id: str, mark_done: bool) -> int:
    t = lat.task_by_id(task_id)
    if t is None:
        print(f"ERROR: task {task_id!r} not found in {path.name}", file=sys.stderr)
        return 1

    if t.kind not in ("task", "completion"):
        print(f"ERROR: task {task_id!r} has kind={t.kind!r}, expected 'task' or 'completion'.", file=sys.stderr)
        return 1

    if not t.test:
        print(
            f"ERROR: task {task_id!r} (kind={t.kind}) has no test command defined.",
            file=sys.stderr,
        )
        return 1

    # Check that dependencies are done (if any)
    idx = lat.task_index()
    deps_not_done = [d for d in t.depends_on if (d in idx and idx[d].status != "done")]
    if deps_not_done:
        print(
            f"ERROR: task {task_id!r} has dependencies not done: {', '.join(deps_not_done)}",
            file=sys.stderr,
        )
        return 1

    print(f"Running test for {t.id!r}: {t.test}")
    result = subprocess.run(t.test, shell=True)
    exit_code = result.returncode

    if exit_code == 0:
        print(f"Test for {t.id!r} succeeded (exit code 0).")
        if mark_done:
            old_status = t.status or "suggested"
            t.status = "done"
            save_lattice(lat, path)
            print(f"Updated status for {t.id!r}: {old_status} -> done")
    else:
        print(f"Test for {t.id!r} FAILED with exit code {exit_code}.", file=sys.stderr)

    return exit_code


def _main_test_complete(lat: Lattice, path: Path) -> int:
    idx = lat.task_index()
    try:
        order = topological_sort(lat)
    except ValueError as e:
        print(f"ERROR: cannot run --complete; cycle detected: {e}", file=sys.stderr)
        return 1

    any_fail = False
    changed = False

    # Snapshot initial statuses before we touch anything
    initial_status: dict[str, str | None] = {tid: t.status for tid, t in idx.items()}

    def deps_done_snapshot(t) -> bool:
        for d in t.depends_on:
            dep = idx.get(d)
            if dep is None:
                return False
            if initial_status.get(d) != "done":
                return False
        return True

    # First pass: demote tasks that *claim* to be done but whose
    # dependencies were not done in the initial snapshot.
    demoted_due_to_deps: set[str] = set()
    for tid, t in idx.items():
        if t.kind not in ("task", "completion"):
            continue
        if initial_status.get(tid) == "done" and not deps_done_snapshot(t):
            print(
                f"Demoting {t.id!r} from done -> planned "
                f"(dependencies not done in initial snapshot)."
            )
            t.status = "planned"
            demoted_due_to_deps.add(tid)
            changed = True

    def deps_done_current(t) -> bool:
        for d in t.depends_on:
            dep = idx.get(d)
            if dep is None:
                return False
            if dep.status != "done":
                return False
        return True

    # Second pass: walk in topological order, run tests where allowed.
    for tid in order:
        t = idx[tid]

        if t.kind not in ("task", "completion"):
            continue
        if not t.test:
            continue

        # If we already demoted this task because of unmet deps in the snapshot,
        # we skip it entirely this pass (no test run).
        if tid in demoted_due_to_deps:
            print(
                f"Skipping {t.id!r} test because it was demoted due to unmet dependencies."
            )
            continue

        # If dependencies are not done *now*, we may demote dynamically in case
        # an upstream test failed during this run.
        if not deps_done_current(t):
            if t.status == "done":
                print(
                    f"Demoting {t.id!r} from done -> planned "
                    f"(dependencies not done in current lattice)."
                )
                t.status = "planned"
                changed = True
            continue

        print(f"Running test for {t.id!r}: {t.test}")
        result = subprocess.run(t.test, shell=True)
        exit_code = result.returncode

        if exit_code == 0:
            old_status = t.status or "suggested"
            if t.status != "done":
                t.status = "done"
                changed = True
                print(f"Updated status for {t.id!r}: {old_status} -> done")
            else:
                print(f"Test for {t.id!r} succeeded; status already 'done'.")
        else:
            any_fail = True
            print(
                f"Test for {t.id!r} FAILED with exit code {exit_code}.",
                file=sys.stderr,
            )
            if t.status == "done":
                t.status = "in-progress"
                changed = True
                print(
                    f"Demoting {t.id!r} from done -> in-progress due to failing test."
                )

    if changed:
        save_lattice(lat, path)
        print(f"Saved updated lattice to {path}")

    return 1 if any_fail else 0

