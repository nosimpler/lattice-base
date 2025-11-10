from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

import yaml

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
