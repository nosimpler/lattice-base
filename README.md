# lattice-base

`lattice-base` is a small library for representing projects as lattices (partially ordered sets),
with:

- A YAML-based lattice format
- Pydantic models and validation
- A Panel-based lattice editor (graph + table + YAML)
- An aggregate Panel hub that discovers pluggable sub-apps
- Optional Notion integration (skeleton)
- Generic testing helpers

Canonical import pattern:

```python
import lattice_base as lab

lat = lab.load_lattice("examples/example-lattice.yaml")
order = lab.topo_sort(lat)
```