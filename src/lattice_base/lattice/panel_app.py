from __future__ import annotations

"""
Panel-based lattice editor for lattice-base.

- Uses Pydantic Lattice/Task/ProjectInfo as the canonical data model.
- Uses param-based LatticeState/TaskState as the interactive UI state.
- Converts between the two at IO boundaries.

UI design:
- Tab 1: "Graph Editor"
  - Large graph on the left
  - Single-task editor on the right, with a dropdown to select a task by id
  - Buttons to create and delete tasks
- Tab 2: "YAML Editor"
  - Full YAML text area
  - Buttons:
      - Apply YAML → Graph
      - Sync Graph → YAML
"""

from pathlib import Path
from typing import List, Tuple

import holoviews as hv
import networkx as nx
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

pn.extension()
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
        node_size=18,
        node_color="kind",
        cmap="Category10",
        edge_color="black",
        directed=True,
        arrowhead_length=0.02,
        width=900,
        height=700,
        tools=["hover", "box_zoom", "reset", "wheel_zoom"],
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

    # Core parameters
    yaml_text = param.String(doc="Raw YAML of the lattice file")
    auto_refresh = param.Boolean(default=False, doc="Re-parse YAML as you type")
    lattice_state = param.ClassSelector(class_=LatticeState, default=None, allow_None=True)

    status_md = param.String(default="", doc="Markdown status / validation messages")
    selected_task_id = param.String(default="", doc="Currently selected task id")

    # Internal state
    _path: Path
    _updating_yaml: bool

    # Panel widgets
    graph_pane: pn.pane.HoloViews

    # task selection + editor widgets
    task_select: pn.widgets.Select
    sel_id: pn.widgets.TextInput
    sel_name: pn.widgets.TextInput
    sel_kind: pn.widgets.Select
    sel_status: pn.widgets.Select
    sel_depends_on: pn.widgets.MultiSelect
    update_task_btn: pn.widgets.Button
    delete_task_btn: pn.widgets.Button

    # new-task widgets
    new_id: pn.widgets.TextInput
    new_name: pn.widgets.TextInput
    new_kind: pn.widgets.Select
    new_status: pn.widgets.Select
    new_depends_on: pn.widgets.MultiSelect
    add_task_btn: pn.widgets.Button

    # YAML editor buttons
    yaml_apply_btn: pn.widgets.Button
    yaml_sync_btn: pn.widgets.Button

    def __init__(self, path: Path | None = None, **params):
        super().__init__(**params)

        self._path = path or DEFAULT_LATTICE_PATH
        self._updating_yaml = False

        # Load initial lattice from disk and build state
        lat = _load_initial_lattice(self._path)
        self.lattice_state = lattice_to_state(lat)
        self.yaml_text = yaml.safe_dump(lat.dict(), sort_keys=False)
        self.status_md = "⚠️ Edit YAML and press **Apply YAML → Graph** or enable auto-refresh."

        # Build initial graph
        self.graph_pane = pn.pane.HoloViews(
            _build_graph(self.lattice_state) if self.lattice_state else hv.Graph([]),
            sizing_mode="stretch_both",
        )

        # Task selection + editor widgets
        self.task_select = pn.widgets.Select(
            name="Task",
            options=self._task_select_options(),
        )
        self.sel_id = pn.widgets.TextInput(name="Selected task id", disabled=True)
        self.sel_name = pn.widgets.TextInput(name="Task name")
        self.sel_kind = pn.widgets.Select(
            name="kind",
            options=["subproject", "epic", "task", "spike", "milestone"],
            value="task",
        )
        self.sel_status = pn.widgets.Select(
            name="status",
            options=["todo", "in-progress", "blocked", "done", "planned"],
            value="todo",
        )
        self.sel_depends_on = pn.widgets.MultiSelect(
            name="Depends on", options=self._current_task_ids()
        )
        self.update_task_btn = pn.widgets.Button(
            name="Update task", button_type="success"
        )
        self.delete_task_btn = pn.widgets.Button(
            name="Delete task", button_type="danger"
        )

        # New-task widgets
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
            name="Depends on (new task)", options=self._current_task_ids()
        )
        self.add_task_btn = pn.widgets.Button(
            name="Add task", button_type="primary"
        )

        # YAML buttons
        self.yaml_apply_btn = pn.widgets.Button(
            name="Apply YAML → Graph", button_type="primary"
        )
        self.yaml_sync_btn = pn.widgets.Button(
            name="Sync Graph → YAML", button_type="success"
        )
        self.yaml_save_btn = pn.widgets.Button(
            name="Save to disk", button_type="primary"
        )


        # Wire param watchers
        self.param.watch(self._on_yaml_change, "yaml_text")

        # Wire widget callbacks
        self.task_select.param.watch(self._on_task_select, "value")
        self.update_task_btn.on_click(self._on_update_task)
        self.delete_task_btn.on_click(self._on_delete_task)
        self.add_task_btn.on_click(self._on_add_task)
        self.yaml_apply_btn.on_click(lambda _e: self.refresh_from_yaml())
        self.yaml_sync_btn.on_click(lambda _e: self._sync_yaml_from_state())
        self.yaml_save_btn.on_click(self._on_save_to_disk)

        # Initialize UI fields from first task (if any)
        self._select_first_task()
                # YAML buttons



    # ────────────── status view ──────────────

    @param.depends("status_md")
    def status_panel(self):
        return pn.pane.Markdown(self.status_md, sizing_mode="stretch_width")

    # ────────────── helpers ──────────────

    def _current_task_ids(self) -> List[str]:
        if self.lattice_state is None:
            return []
        return [ts.id for ts in self.lattice_state.tasks]

    def _task_select_options(self):
        """
        Returns a dict of label -> value for the task Select widget.
        Label is "id — name" if name != id, otherwise just id.
        """
        if self.lattice_state is None or not self.lattice_state.tasks:
            return {}

        opts = {}
        for ts in self.lattice_state.tasks:
            if ts.name and ts.name != ts.id:
                label = f"{ts.id} — {ts.name}"
            else:
                label = ts.id
            opts[label] = ts.id
        return opts


    def _refresh_graph_from_state(self):
        if self.lattice_state is None:
            self.graph_pane.object = hv.Graph([])
            return
        graph = _build_graph(self.lattice_state)
        self.graph_pane.object = graph

    def _refresh_depend_options(self):
        ids = self._current_task_ids()
        self.sel_depends_on.options = ids
        self.new_depends_on.options = ids
        self.task_select.options = self._task_select_options()

    def _set_status(self, msg: str):
        self.status_md = msg

    def _select_first_task(self):
        if self.lattice_state is None or not self.lattice_state.tasks:
            self.selected_task_id = ""
            self.sel_id.value = ""
            self.sel_name.value = ""
            self.task_select.options = self._task_select_options()
            self.task_select.value = None
            return

        first = self.lattice_state.tasks[0]
        self.selected_task_id = first.id
        self.task_select.options = self._task_select_options()
        self.task_select.value = first.id
        self._load_selected_task_into_widgets(first)

    def _load_selected_task_into_widgets(self, ts: TaskState):
        self.selected_task_id = ts.id
        self.sel_id.value = ts.id
        self.sel_name.value = ts.name
        if ts.kind in self.sel_kind.options:
            self.sel_kind.value = ts.kind
        if ts.status in self.sel_status.options:
            self.sel_status.value = ts.status
        self.sel_depends_on.value = list(ts.depends_on)

    # ────────────── task selection ──────────────

    def _on_task_select(self, event):
        tid = event.new
        if not tid or self.lattice_state is None:
            return
        for ts in self.lattice_state.tasks:
            if ts.id == tid:
                self._load_selected_task_into_widgets(ts)
                break

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
            self._refresh_graph_from_state()
            self._refresh_depend_options()
            self._select_first_task()

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

        self._refresh_graph_from_state()
        self._refresh_depend_options()
        self._set_status("✅ Synced Graph → YAML.")

    def _on_save_to_disk(self, _event):
        """
        Save the current lattice to the backing file on disk.

        - If the editor was created with a `path` (via LatticeEditor(path=...)),
          we write to that.
        - Otherwise, we write to self._path, which defaults to DEFAULT_LATTICE_PATH.
        - We validate via Pydantic Lattice before writing to keep things sane.
        """
        path = getattr(self, "_path", None)
        if path is None:
            self._set_status("❌ No backing file path is configured; cannot save.")
            return

        try:
            # Parse current YAML and validate as a Lattice
            data = yaml.safe_load(self.yaml_text) or {}
            lat = Lattice(**data)

            # Canonicalize and write
            path.write_text(yaml.safe_dump(lat.dict(), sort_keys=False), encoding="utf-8")
            self._set_status(f"✅ Saved lattice to `{path}`.")
        except Exception as e:
            self._set_status(
                f"❌ Error saving lattice to disk:\n\n```text\n{e}\n```"
            )

    # ────────────── task editing ──────────────

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
                ts.name = self.sel_name.value.strip() or ts.name
                ts.kind = self.sel_kind.value
                ts.status = self.sel_status.value
                ts.depends_on = list(self.sel_depends_on.value)
                updated = True
                break

        if not updated:
            self._set_status(f"❌ Task `{tid}` not found.")
            return

        self._sync_yaml_from_state()
        self._set_status(f"✅ Updated task `{tid}`.")

    def _on_delete_task(self, _event):
        if self.lattice_state is None:
            self._set_status("❌ No lattice loaded.")
            return
        tid = self.sel_id.value.strip()
        if not tid:
            self._set_status("❌ No task selected to delete.")
            return

        # Remove the task
        new_tasks = [ts for ts in self.lattice_state.tasks if ts.id != tid]
        if len(new_tasks) == len(self.lattice_state.tasks):
            self._set_status(f"❌ Task `{tid}` not found.")
            return
        self.lattice_state.tasks = new_tasks

        # Remove references in depends_on
        for ts in self.lattice_state.tasks:
            if tid in ts.depends_on:
                ts.depends_on = [d for d in ts.depends_on if d != tid]

        self._sync_yaml_from_state()
        self._refresh_depend_options()
        self._select_first_task()
        self._set_status(f"✅ Deleted task `{tid}` and cleaned dependencies.")

    def _on_add_task(self, _event):
        if self.lattice_state is None:
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

        self.new_id.value = ""
        self.new_name.value = ""

        self._sync_yaml_from_state()
        self._refresh_depend_options()
        self._set_status(f"✅ Added task `{tid}`.")

    # ────────────── Panel layout ──────────────

    def _graph_editor_tab(self):
        # Right-hand editor column
        selected_box = pn.Column(
            "#### Selected task",
            self.task_select,
            self.sel_id,
            self.sel_name,
            self.sel_kind,
            self.sel_status,
            self.sel_depends_on,
            pn.Row(self.update_task_btn, self.delete_task_btn),
        )

        new_box = pn.Column(
            "#### New task",
            self.new_id,
            self.new_name,
            self.new_kind,
            self.new_status,
            self.new_depends_on,
            self.add_task_btn,
        )

        editor_col = pn.Column(
            selected_box,
            pn.layout.HSpacer(height=20),
            new_box,
            sizing_mode="fixed",
            width=380,
        )

        graph_col = pn.Column(
            "### Lattice Graph",
            self.graph_pane,
            sizing_mode="stretch_both",
        )

        return pn.Row(graph_col, editor_col, sizing_mode="stretch_both")

    def _yaml_editor_tab(self):
        yaml_widget = pn.widgets.TextAreaInput.from_param(
            self.param.yaml_text, height=600, sizing_mode="stretch_both"
        )

        buttons = pn.Row(
            self.yaml_apply_btn,
            self.yaml_sync_btn,
            self.yaml_save_btn,
        )


        return pn.Column(
            "### Lattice YAML",
            yaml_widget,
            buttons,
            self.status_panel,
            sizing_mode="stretch_both",
        )

    def panel(self):
        """Return the top-level Panel layout for this editor."""
        graph_tab = self._graph_editor_tab()
        yaml_tab = self._yaml_editor_tab()

        tabs = pn.Tabs(
            ("Graph Editor", graph_tab),
            ("YAML Editor", yaml_tab),
            sizing_mode="stretch_both",
        )
        return tabs


# ─────────────────────────── entrypoint ───────────────────────────

def main():
    """
    Entry point used by `lattice-base-lattice-gui`.
    Starts an in-process Panel server and opens the browser.
    """
    editor = LatticeEditor()
    layout = editor.panel()
    pn.config.sizing_mode = "stretch_both"
    pn.serve(layout, title="Lattice Editor", show=True)
