from __future__ import annotations

from pathlib import Path
from typing import Optional, List

import argparse
import sys
import yaml

from lattice_base.lattice.model import Lattice, ProjectInfo, Task
from lattice_base.lattice.io import load_lattice


PROJECT_FILENAMES = ("project.yaml", "lattice.yaml")


def find_project_root(start: Optional[Path] = None) -> Path:
    """
    Walk upward from `start` (or cwd) to find a directory that looks like a project root.
    Heuristics:
      - Contains project.yaml or lattice.yaml
      - OR contains pyproject.toml
      - OR contains .git
    Returns the found directory or raises FileNotFoundError.
    """
    cur = Path(start or Path.cwd()).resolve()

    for parent in [cur] + list(cur.parents):
        has_project_file = any((parent / name).exists() for name in PROJECT_FILENAMES)
        if has_project_file or (parent / "pyproject.toml").exists() or (parent / ".git").exists():
            return parent

    raise FileNotFoundError("Could not find project root (no project.yaml, pyproject.toml, or .git upwards).")


def load_project_lattice(path: Optional[Path] = None, filename: str = "project.yaml") -> Lattice:
    """
    Load the lattice for the current project:
      - If `path` is provided, use that directory.
      - Otherwise, call find_project_root() and look for `filename`.
    """
    root = path or find_project_root()
    lattice_path = root / filename
    if not lattice_path.exists():
        raise FileNotFoundError(f"No {filename!r} found at project root {root}")
    return load_lattice(lattice_path)


def init_project_lattice(
    repo: Path,
    project_id: str,
    name: str,
    owner: Optional[str] = None,
    description: Optional[str] = None,
    filename: str = "project.yaml",
    overwrite: bool = False,
    with_example_tasks: bool = True,
) -> Path:
    """
    Initialize a minimal project lattice in `repo/filename`.

    - If the file already exists and overwrite=False, raises FileExistsError.
    - Optionally adds a couple of example tasks to get started.
    """
    repo = repo.resolve()
    if not repo.exists():
        raise FileNotFoundError(f"Repo directory does not exist: {repo}")

    path = repo / filename
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} already exists (use overwrite=True to replace).")

    project = ProjectInfo(
        id=project_id,
        name=name,
        owner=owner or None,
        description=description or None,
    )

    tasks = []
    if with_example_tasks:
        tasks = [
            {
                "id": "core",
                "name": "Core project setup",
                "kind": "epic",
                "status": "in-progress",
                "depends_on": [],
                "tags": ["infra", "bootstrap"],
                "description": "Initial project scaffolding and shared infrastructure.",
            },
            {
                "id": "docs",
                "name": "Documentation & quickstart",
                "kind": "task",
                "status": "todo",
                "depends_on": ["core"],
                "tags": ["docs"],
                "description": "Create a quickstart guide and basic README for the project.",
            },
        ]

    lattice = Lattice(version=0.1, project=project, tasks=tasks)  # type: ignore[arg-type]

    path.write_text(yaml.safe_dump(lattice.dict(), sort_keys=False), encoding="utf-8")
    return path


# ─────────────────────────── CLI ───────────────────────────

def cli_main(argv: Optional[list[str]] = None) -> int:
    """
    CLI entrypoint for `lattice-base-init`:

        lattice-base-init --repo . --id neurd2 --name "Neurd2 Project"
    """
    parser = argparse.ArgumentParser(description="Initialize a lattice-base project.yaml in a repo.")
    parser.add_argument(
        "--repo",
        type=str,
        default=".",
        help="Path to the repo root (default: current directory).",
    )
    parser.add_argument("--id", type=str, help="Project id (default: repo directory name).")
    parser.add_argument("--name", type=str, help="Project name (default: derived from id).")
    parser.add_argument("--owner", type=str, help="Project owner (optional).")
    parser.add_argument("--description", type=str, help="Project description (optional).")
    parser.add_argument(
        "--filename",
        type=str,
        default="project.yaml",
        help="Project lattice filename to create (default: project.yaml).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing project.yaml if present.",
    )
    parser.add_argument(
        "--no-example-tasks",
        action="store_true",
        help="Do not add example tasks; start with an empty task list.",
    )

    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()

    # Derive defaults and prompt if needed
    default_id = repo.name
    project_id = args.id or input(f"Project id [{default_id}]: ").strip() or default_id

    default_name = args.name or project_id.replace("-", " ").title()
    name = args.name or input(f"Project name [{default_name}]: ").strip() or default_name

    owner = args.owner or input("Owner (optional): ").strip() or None
    description = args.description or input("Description (optional): ").strip() or None

    with_example = not args.no_example_tasks

    try:
        path = init_project_lattice(
            repo=repo,
            project_id=project_id,
            name=name,
            owner=owner,
            description=description,
            filename=args.filename,
            overwrite=args.force,
            with_example_tasks=with_example,
        )
    except FileExistsError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(f"✅ Created lattice project file at: {path}")
    return 0
def _task_priority_value(task: Task) -> int:
    """
    Map a task's optional 'priority' attribute to a sort key:
      high -> 0, medium -> 1, low -> 2, unknown -> 3
    """
    pr = getattr(task, "priority", None)
    if not pr:
        return 3
    pr = str(pr).lower()
    if pr == "high":
        return 0
    if pr == "medium":
        return 1
    if pr == "low":
        return 2
    return 3


def cli_next_main(argv: Optional[list[str]] = None) -> int:
    """
    CLI entrypoint for `lattice-base-next`:

        lattice-base-next
        lattice-base-next --repo path/to/repo --filename project.yaml
    """
    parser = argparse.ArgumentParser(
        description="List incomplete tasks that are ready to start, "
                    "given currently completed tasks in the lattice."
    )
    parser.add_argument(
        "--repo",
        type=str,
        default=".",
        help="Path to the repo root (default: current directory).",
    )
    parser.add_argument(
        "--filename",
        type=str,
        default="project.yaml",
        help="Lattice filename to load (default: project.yaml).",
    )

    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    try:
        # load_project_lattice already uses find_project_root when path is given,
        # but here we want repo to be explicit.
        lat = load_project_lattice(path=repo, filename=args.filename)  # type: ignore[arg-type]
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    ready = compute_possible_tasks(lat)

    if not ready:
        print("No ready-to-start tasks found.")
        return 0

    # Sort by priority, then by id
    ready_sorted = sorted(ready, key=lambda t: (_task_priority_value(t), t.id))

    print(f"Ready-to-start tasks in {args.filename} (repo: {repo}):\n")
    for t in ready_sorted:
        status = getattr(t, "status", "todo")
        priority = getattr(t, "priority", None)
        deps = getattr(t, "depends_on", []) or []
        pr_str = f"[{priority}]" if priority else ""
        deps_str = ", ".join(deps) if deps else "none"
        print(f"- {pr_str} {t.id}: {t.name}  (status: {status}, depends_on: {deps_str})")

    return 0


def compute_possible_tasks(lat: Lattice) -> List[Task]:
    """
    Given a Lattice, return the list of tasks that are "ready to start":

      - status != "done"
      - status != "blocked" (for now)
      - all depends_on tasks have status == "done"

    This is intentionally simple; you can refine the semantics later.
    """
    # Index tasks by id for quick lookup
    by_id = {t.id: t for t in lat.tasks}

    def is_done(tid: str) -> bool:
        t = by_id.get(tid)
        return bool(t and getattr(t, "status", "") == "done")

    ready: List[Task] = []
    for t in lat.tasks:
        status = getattr(t, "status", "") or ""
        if status == "done":
            continue
        if status == "blocked":
            continue

        deps = getattr(t, "depends_on", []) or []
        if all(is_done(dep) for dep in deps):
            ready.append(t)

    return ready


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(cli_main())
