from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .io import load_lattice, detect_cycles, topo_sort


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a lattice-base YAML lattice file."
    )
    parser.add_argument("path", help="Path to lattice YAML (e.g. examples/example-lattice.yaml)")
    args = parser.parse_args()

    path = Path(args.path)
    try:
        lat = load_lattice(path)
        cycles = detect_cycles(lat)
        order = topo_sort(lat)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)

    if cycles:
        print("⚠️ Graph has cycles:")
        for c in cycles:
            print("  - " + " -> ".join(c))
        sys.exit(1)

    print(f"✅ Lattice {path} is valid.")
    print("Topological order:")
    for tid in order:
        print(f"  {tid}")

    sys.exit(0)
