from __future__ import annotations

from pathlib import Path
from typing import Union

import yaml

from .model import Lattice


PathLike = Union[str, Path]


def load_lattice(path: PathLike) -> Lattice:
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return Lattice(**data)


def save_lattice(lattice: Lattice, path: PathLike) -> None:
    path = Path(path)
    data = lattice.model_dump(mode="python")
    text = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    path.write_text(text, encoding="utf-8")
