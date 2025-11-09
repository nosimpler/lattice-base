from __future__ import annotations

from importlib.metadata import entry_points

import panel as pn

from .base import LatticeAppPlugin
from ..lattice import panel_app as lattice_panel_app


def builtin_apps() -> list[LatticeAppPlugin]:
    class LatticeWrapper:
        name = "Lattice Editor"
        slug = "lattice-editor"

        def panel(self):
            app = lattice_panel_app.LatticeApp()
            return app.panel()

    return [LatticeWrapper()]


def discover_plugins() -> list[LatticeAppPlugin]:
    apps: list[LatticeAppPlugin] = []
    for ep in entry_points(group="lattice_base.apps"):
        try:
            factory = ep.load()
            app = factory()
            apps.append(app)
        except Exception as e:
            print(f"Failed to load lattice_base app {ep.name}: {e}")
    return apps


def make_aggregate_panel() -> pn.viewable.Viewable:
    pn.extension("tabulator")
    pn.config.sizing_mode = "stretch_both"

    core = builtin_apps()
    plugins = discover_plugins()
    all_apps = core + plugins

    if not all_apps:
        return pn.pane.Markdown("No apps registered.")

    tabs = [(app.name, app.panel()) for app in all_apps]

    tmpl = pn.template.MaterialTemplate(
        title="Lattice Base Aggregate",
        main=[pn.Tabs(*tabs)],
        sidebar=[pn.pane.Markdown(
            "## Apps\n" + "\n".join(f"- {a.name}" for a in all_apps)
        )],
    )
    return tmpl


def main():
    app = make_aggregate_panel()
    app.servable("Lattice Hub")
