from __future__ import annotations

"""
Aggregate Panel hub for lattice-base.

- Always includes a "Lattice Editor" tab (LatticeEditor from lattice_base.lattice.panel_app)
- Discovers additional apps via the `lattice_base.apps` entry point group
"""

from importlib.metadata import entry_points
from typing import List

import panel as pn

from .base import LatticeAppPlugin
from lattice_base.lattice.panel_app import LatticeEditor


def builtin_apps() -> List[LatticeAppPlugin]:
    """
    Built-in apps that always appear in the aggregate hub.
    Currently just the Lattice Editor.
    """

    class LatticeEditorWrapper:
        name = "Lattice Editor"
        slug = "lattice-editor"

        def panel(self):
            editor = LatticeEditor()
            return editor.panel()

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
    pn.extension("tabulator")
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
