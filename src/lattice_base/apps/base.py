from __future__ import annotations

from typing import Protocol
import panel as pn


class LatticeAppPlugin(Protocol):
    """
    Protocol for sub-apps that can be added to the aggregate hub.
    """

    name: str
    slug: str

    def panel(self) -> pn.viewable.Viewable:
        ...
