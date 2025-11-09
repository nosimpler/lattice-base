from __future__ import annotations

from typing import List

import param

from lattice_base.lattice.model import Lattice, Task, ProjectInfo


class TaskState(param.Parameterized):
    """
    UI-level representation of a Task.
    This is what Panel/param will manipulate directly.
    """

    id = param.String(doc="Task identifier")
    name = param.String(doc="Human-readable task name")

    kind = param.ObjectSelector(
        default="task",
        objects=["subproject", "epic", "task", "spike", "milestone"],
        doc="Task type/category",
    )

    status = param.ObjectSelector(
        default="todo",
        objects=["todo", "in-progress", "blocked", "done", "planned"],
        doc="Task status/state",
    )

    # NOTE: use item_type= instead of class_= to avoid ParamFutureWarning
    depends_on = param.List(item_type=str, default=[], doc="List of task IDs this depends on")
    tags = param.List(item_type=str, default=[], doc="Free-form tags")
    description = param.String(default="", doc="Optional longer description")


class LatticeState(param.Parameterized):
    """
    UI-level state for an entire lattice.
    """

    project_id = param.String(default="example", doc="Project id")
    project_name = param.String(default="Example Project", doc="Project name")
    project_owner = param.String(default="", doc="Owner")
    project_description = param.String(default="", doc="Description")

    # list of TaskState objects
    tasks = param.List(item_type=TaskState, default=[], doc="List of TaskState objects")


# ────────────── converters ──────────────

def lattice_to_state(lat: Lattice) -> LatticeState:
    state = LatticeState(
        project_id=lat.project.id,
        project_name=lat.project.name,
        project_owner=lat.project.owner or "",
        project_description=lat.project.description or "",
    )

    state.tasks = [
        TaskState(
            id=t.id,
            name=t.name,
            kind=t.kind,
            status=t.status,
            depends_on=list(t.depends_on),
            tags=list(t.tags),
            description=t.description or "",
        )
        for t in lat.tasks
    ]
    return state


def state_to_lattice(state: LatticeState) -> Lattice:
    project = ProjectInfo(
        id=state.project_id,
        name=state.project_name,
        owner=state.project_owner or None,
        description=state.project_description or None,
    )

    tasks: List[Task] = []
    for ts in state.tasks:
        tasks.append(
            Task(
                id=ts.id,
                name=ts.name,
                kind=ts.kind,
                status=ts.status,
                depends_on=list(ts.depends_on),
                tags=list(ts.tags),
                description=ts.description or None,
            )
        )

    return Lattice(version=0.1, project=project, tasks=tasks)
