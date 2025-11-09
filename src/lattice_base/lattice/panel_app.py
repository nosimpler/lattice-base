from __future__ import annotations

"""
Panel-based lattice editor for lattice-base.

- Uses Pydantic Lattice/Task/ProjectInfo as the canonical data model.
- Uses param-based LatticeState/TaskState as the interactive UI state.
- Converts between the two at IO boundaries.
"""

from pathlib import Path
from typing import List

import pandas as pd
import networkx as nx
import holoviews as hv
import panel as pn
import param
import yaml

from lattice_base.lattice.model import Lattice
from lattice_base.lattice.io import load_lattice, detect_cycles, topo_sort
from lattice_base.ui.state import (
    LatticeState,
    TaskState,
    lattice_to_state,
    state_to_lattice,
)

pn.extension("tabulator")
hv.extension("bokeh")

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = ROOT / "examples"
DEFAULT_LATTICE_PATH = EXAMPLES_DIR / "example-lattice.yaml"


# ─────────────────────────── helpers ───────────────────────────

def _load_initial_lattice(path: Path) -> Lattice:
    if path.exists():
        return load_lattice(path)
    # Minimal fallback if example is missing
    return Lattice(
        version=0.1,
        project={"id": "example", "name": "Example Project"},
        tasks=[],  # type: ignore[arg-type]
    )


def _tasks_to_df(state: LatticeState) -> pd.DataFrame:
    rows = []
    for ts in state.tasks:
        rows.append(
            {
                "id": ts.id,
                "name": ts.name,
                "kind": ts.kind,
                "status": ts.status,
                "depends_on": ", ".join(ts.depends_on),
                "tags": ", ".join(ts.tags),
                "description": ts.description.strip(),
            }
        )
    return pd.DataFrame(rows)


def _build_graph(state: LatticeState) -> hv.Graph:
    G = nx.DiGraph()
    for ts in state.tasks:
        G.add_node(ts.id, label=ts.name, kind=ts.kind, status=ts.status)
    for ts in state.tasks:
        for dep in ts.depends_on:
            G.add_edge(dep, ts.id)

    if not G.nodes:
        return hv.Graph([])

    pos = nx.spring_layout(G, seed=0)
    graph = hv.Graph.from_networkx(G, pos).opts(
        node_size=15,
        node_color="kind",
        cmap="Category10",
        edge_color="black",
        directed=True,
        arrowhead_length=0.02,
        width=700,
        height=500,
        tools=["hover", "tap", "box_zoom", "reset", "wheel_zoom"],
        inspection_policy="nodes",
    )
    return graph


# ───────────────────── param-based editor ─────────────────────

class LatticeEditor(param.Parameterized):
    """
    Param/Panel-based editor that wraps:

    - Pydantic Lattice for IO (files, APIs)
    - param LatticeState/TaskState for interactive UI
    """

    # Core parameters (Panel binds widgets to these)
    yaml_text = param.String(doc="Raw YAML of the lattice file")
    auto_refresh = param.Boolean(default=False, doc="Re-parse YAML as you type")
    lattice_state = param.ClassSelector(class_=LatticeState, default=None, allow_None=True)

    status_md = param.String(default="", doc="Markdown status / validation messages")

    # Internal, non-param state
    _path: Path
    _updating_yaml: bool

    # Panel widgets we keep around
    table: pn.widgets.Tabulator
    graph_pane: pn.pane.HoloViews

    sel_id: pn.widgets.TextInput
    sel_name: pn.widgets.TextInput
    kind_select: pn.widgets.Select
    status_select: pn.widgets.Select
    update_task_btn: pn.widgets.Button

    new_id: pn.widgets.TextInput
    new_name: pn.widgets.TextInput
    new_kind: pn.widgets.Select
    new_status: pn.widgets.Select
    new_depends_on: pn.widgets.MultiSelect
    add_task_btn: pn.widgets.Button

    def __init__(self, path: Path | None = None, **params):
        super().__init__(**params)

        self._path = path or DEFAULT_LATTICE_PATH
        self._updating_yaml = False

        # Load initial lattice from disk and build state
        lat = _load_initial_lattice(self._path)
        self.lattice_state = lattice_to_state(lat)
        self.yaml_text = yaml.safe_dump(lat.dict(), sort_keys=False)
        self.status_md = "⚠️ Edit YAML and press **Refresh** or enable auto-refresh."

        # Build initial widgets
        self.table = pn.widgets.Tabulator(
            _tasks_to_df(self.lattice_state) if self.lattice_state else pd.DataFrame(),
            selectable="row",
            height=300,
            sizing_mode="stretch_width",
        )
        self.graph_pane = pn.pane.HoloViews(
            _build_graph(self.lattice_state) if self.lattice_state else hv.Graph([]),
            sizing_mode="stretch_both",
        )

        # Edit widgets
        self.sel_id = pn.widgets.TextInput(name="Selected task id", disabled=True)
        self.sel_name = pn.widgets.TextInput(name="Task name", disabled=True)
        self.kind_select = pn.widgets.Select(
            name="kind",
            options=["subproject", "epic", "task", "spike", "milestone"],
        )
        self.status_select = pn.widgets.Select(
            name="status",
            options=["todo", "in-progress", "blocked", "done", "planned"],
        )
        self.update_task_btn = pn.widgets.Button(
            name="Update task", button_type="success"
        )

        # Add-task widgets
        self.new_id = pn.widgets.TextInput(name="New task id")
        self.new_name = pn.widgets.TextInput(name="New task name")
        self.new_kind = pn.widgets.Select(
            name="New kind",
            options=["subproject", "epic", "task", "spike", "milestone"],
            value="task",
        )
        self.new_status = pn.widgets.Select(
            name="New status",
            options=["todo", "in-progress", "blocked", "done", "planned"],
            value="todo",
        )
        self.new_depends_on = pn.widgets.MultiSelect(
            name="Depends on",
            options=self._current_task_ids(),
        )
        self.add_task_btn = pn.widgets.Button(
            name="Add task", button_type="primary"
        )

        # Wire param watchers
        self.param.watch(self._on_yaml_change, "yaml_text")

        # Wire widget callbacks
        self.table.param.watch(self._on_row_select, "selection")
        self.update_task_btn.on_click(self._on_update_task)
        self.add_task_btn.on_click(self._on_add_task)

        # Initial view refresh
        self._refresh_views_from_state()

    # ────────────── param-dependent views ──────────────

    @param.depends("status_md")
    def status_panel(self):
        return pn.pane.Markdown(self.status_md, sizing_mode="stretch_width")

    # ────────────── helpers ──────────────

    def _current_task_ids(self) -> List[str]:
        if self.lattice_state is None:
            return []
        return [ts.id for ts in self.lattice_state.tasks]

    def _refresh_views_from_state(self):
        """Refresh table, graph, and depends_on options from lattice_state."""
        if self.lattice_state is None:
            self.table.value = pd.DataFrame()
            self.graph_pane.object = hv.Graph([])
            self.new_depends_on.options = []
            return

        self.table.value = _tasks_to_df(self.lattice_state)
        self.graph_pane.object = _build_graph(self.lattice_state)
        self.new_depends_on.options = self._current_task_ids()

    def _set_status(self, msg: str):
        self.status_md = msg

    # ────────────── YAML ↔ state ──────────────

    def refresh_from_yaml(self):
        """Parse yaml_text into a Pydantic Lattice, validate, and update state."""
        try:
            data = yaml.safe_load(self.yaml_text) or {}
            lat = Lattice(**data)
            cycles = detect_cycles(lat)
            order = topo_sort(lat)

            # update state
            self.lattice_state = lattice_to_state(lat)
            self._refresh_views_from_state()

            msg = "✅ **Valid lattice**\n\n"
            if cycles:
                msg += "⚠️ Cycles detected:\n" + "\n".join(
                    ["- " + " → ".join(c) for c in cycles]
                )
            msg += "\n**Topological order:**\n" + ", ".join(order)
            self._set_status(msg)
        except Exception as e:
            self._set_status(
                f"❌ Error parsing/validating lattice:\n\n```text\n{e}\n```"
            )

    def _on_yaml_change(self, *_):
        if self._updating_yaml:
            return
        if self.auto_refresh:
            self.refresh_from_yaml()

    def _sync_yaml_from_state(self):
        """Dump lattice_state back to yaml_text using Pydantic Lattice."""
        if self.lattice_state is None:
            return
        lat = state_to_lattice(self.lattice_state)
        self._updating_yaml = True
        try:
            self.yaml_text = yaml.safe_dump(lat.dict(), sort_keys=False)
        finally:
            self._updating_yaml = False
        self._refresh_views_from_state()

    # ────────────── table callbacks ──────────────

    def _on_row_select(self, event):
        if not event.new or self.lattice_state is None:
            self.sel_id.value = ""
            self.sel_name.value = ""
            return

        idx = event.new[0]
        if idx >= len(self.lattice_state.tasks):
            return
        ts = self.lattice_state.tasks[idx]

        self.sel_id.value = ts.id
        self.sel_name.value = ts.name
        if ts.kind in self.kind_select.options:
            self.kind_select.value = ts.kind
        if ts.status in self.status_select.options:
            self.status_select.value = ts.status

    # ────────────── edit/update task ──────────────

    def _on_update_task(self, _event):
        if self.lattice_state is None:
            self._set_status("❌ No lattice loaded.")
            return
        tid = self.sel_id.value.strip()
        if not tid:
            self._set_status("❌ No task selected to update.")
            return

        updated = False
        for ts in self.lattice_state.tasks:
            if ts.id == tid:
                ts.kind = self.kind_select.value
                ts.status = self.status_select.value
                updated = True
                break

        if not updated:
            self._set_status(f"❌ Task `{tid}` not found.")
            return

        self._sync_yaml_from_state()
        self._set_status(f"✅ Updated task `{tid}`.")

    # ────────────── add task ──────────────

    def _on_add_task(self, _event):
        if self.lattice_state is None:
            # initialize an empty state if needed
            self.lattice_state = LatticeState()
        tid = self.new_id.value.strip()
        name = self.new_name.value.strip()
        if not tid or not name:
            self._set_status("❌ New task must have id and name.")
            return

        if any(ts.id == tid for ts in self.lattice_state.tasks):
            self._set_status(f"❌ Task id `{tid}` already exists.")
            return

        new_ts = TaskState(
            id=tid,
            name=name,
            kind=self.new_kind.value,
            status=self.new_status.value,
            depends_on=list(self.new_depends_on.value),
            tags=[],
            description="",
        )
        self.lattice_state.tasks.append(new_ts)
