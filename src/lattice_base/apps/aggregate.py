from __future__ import annotations

"""
Aggregate Panel hub for lattice-base.

- Always includes a "Lattice Editor" tab (LatticeEditor from lattice_base.lattice.panel_app)
- Discovers additional apps via the `lattice_base.apps` entry point group
- Automatically tries to load the nearest project.yaml and shows project info
"""

from importlib.metadata import entry_points
from pathlib import Path
from typing import List, Optional, Tuple

import panel as pn

from .base import LatticeAppPlugin
from lattice_base.lattice.panel_app import LatticeEditor
from lattice_base.project import find_project_root, load_project_lattice


def _detect_project() -> Tuple[Optional[Path], Optional[Path], Optional[str], Optional[str]]:
    """
    Try to detect the current project lattice:

    Returns (project_root, lattice_path, project_id, project_name) or (None, None, None, None)
    if nothing suitable is found.
    """
    try:
        root = find_project_root()
    except Exception:
        return None, None, None, None

    lattice_path = root / "project.yaml"
    if not lattice_path.exists():
        # fall back to lattice.yaml if present
        alt = root / "lattice.yaml"
        if not alt.exists():
            return root, None, None, None
        lattice_path = alt

    try:
        lattice = load_project_lattice(root, filename=lattice_path.name)  # type: ignore[arg-type]
        project_id = lattice.project.id
        project_name = lattice.project.name
        return root, lattice_path, project_id, project_name
    except Exception:
        # If parsing fails, still return the path so the user can see it
        return root, lattice_path, None, None


def builtin_apps() -> List[LatticeAppPlugin]:
    """
    Built-in apps that always appear in the aggregate hub.
    Currently just the Lattice Editor, wired to the nearest project.yaml if available.
    """

    class LatticeEditorWrapper:
        name = "Lattice Editor"
        slug = "lattice-editor"

        def __init__(self):
            (
                self.project_root,
                self.lattice_path,
                self.project_id,
                self.project_name,
            ) = _detect_project()

        def panel(self):
            # Build the core editor, pointing at the detected lattice file if any
            if self.lattice_path is not None:
                editor = LatticeEditor(path=self.lattice_path)
            else:
                editor = LatticeEditor()

            editor_layout = editor.panel()

            # Build a small header with project information, if available
            header_lines = []

            if self.project_id or self.project_name:
                title = self.project_name or self.project_id or ""
                header_lines.append(f"### Project: `{title}`")
                if self.project_id and self.project_name and self.project_name != self.project_id:
                    header_lines.append(f"- **id**: `{self.project_id}`")
            else:
                header_lines.append("### Project: (no project.yaml found)")

            if self.lattice_path is not None:
                rel_path = (
                    str(self.lattice_path.relative_to(self.project_root))
                    if self.project_root and self.lattice_path.is_relative_to(self.project_root)
                    else str(self.lattice_path)
                )
                header_lines.append(f"- **lattice file**: `{rel_path}`")
            elif self.project_root is not None:
                header_lines.append(f"- Searched root: `{self.project_root}`")
                header_lines.append(
                    "- Hint: create `project.yaml` in this directory or run "
                    "`lattice-base-init --repo .` from there."
                )
            else:
                header_lines.append(
                    "- Hint: run this from inside a repo with `project.yaml`, "
                    "`lattice.yaml`, `pyproject.toml`, or `.git`."
                )

            header_md = "\n".join(header_lines)
            header = pn.pane.Markdown(header_md, sizing_mode="stretch_width")

            return pn.Column(header, editor_layout, sizing_mode="stretch_both")

    return [LatticeEditorWrapper()]


def discover_plugins() -> List[LatticeAppPlugin]:
    """
    Discover additional apps registered under the `lattice_base.apps`
    entry point group.

    Each entry point must be a zero-arg callable returning an object
    implementing the LatticeAppPlugin protocol (name, slug, panel()).
    """
    apps: List[LatticeAppPlugin] = []

    for ep in entry_points(group="lattice_base.apps"):
        try:
            factory = ep.load()
            app = factory()
            apps.append(app)
        except Exception as e:  # pragma: no cover - defensive
            # Don't crash the hub if a plugin is broken; just log it.
            print(f"[lattice-base] Failed to load app {ep.name!r}: {e}")

    return apps


def make_aggregate_panel() -> pn.viewable.Viewable:
    """
    Build the aggregate Panel UI: tabs for each app (built-in + plugins),
    wrapped in a MaterialTemplate.
    """
    pn.extension()
    pn.config.sizing_mode = "stretch_both"

    core_apps = builtin_apps()
    plugin_apps = discover_plugins()
    all_apps = core_apps + plugin_apps

    if not all_apps:
        return pn.pane.Markdown("No lattice-base apps registered.")

    tabs = [(app.name, app.panel()) for app in all_apps]

    sidebar_md = "## Apps\n" + "\n".join(f"- {a.name}" for a in all_apps)

    template = pn.template.MaterialTemplate(
        title="Lattice Base Aggregate Hub",
        main=[pn.Tabs(*tabs)],
        sidebar=[pn.pane.Markdown(sidebar_md)],
    )
    return template


def main():
    """
    Entry point used by `lattice-base-aggregate-gui`.
    Starts an in-process Panel server and opens the browser.
    """
    app = make_aggregate_panel()
    pn.serve(app, title="Lattice Hub", show=True)
