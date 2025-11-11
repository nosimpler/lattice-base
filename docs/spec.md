# lattice-base Project Specification

## Versioning of this spec

This document describes the **intended data model and semantics** for `project.yaml` files used by `lattice-base`.

- **Spec version:** 0.1 (current)
- **Implementation status:** some fields and rules marked as _planned_ are not yet fully enforced by the CLI tools. They are included to guide future design and to keep lattices forward-compatible.

Whenever there is a difference between the current implementation and the spec, it will be called out explicitly as **(planned, not yet enforced)**.

---

## Overview

Each `project.yaml` defines a **project lattice** — a directed acyclic graph (DAG) of tasks, epics, completions, and subprojects.  
Each node corresponds to a unit of work with a lifecycle and (optionally) a test command.

The lattice specification allows both human-readable planning and machine-validated execution through `lattice-base` CLI tools.

---

## Completion Semantics (with scope)

> **Note:** Scope fields are part of the *design* of this spec and may not yet be fully enforced by the current CLI.

### Fields

```yaml
- id: completion-project
  kind: completion
  scope: project        # one of: project, epic, subproject
  scope_of: null        # for non-project scopes, this must be set
```

### Intended rules (planned, not yet fully enforced)

1. **Every completion has a scope.**
   - `scope: project` → completion for the entire lattice.  
   - `scope: epic` → completion for a specific epic.  
   - `scope: subproject` → completion for a specific subproject.

2. **At most one completion per target.**
   - One `scope: project` completion per `project.yaml`.  
   - One completion per epic or subproject target.

3. **Dependencies should lie within the scope.**
   - For `scope: epic`, depends_on should reference nodes within that epic’s sublattice.  
   - For `scope: subproject`, depends_on should reference nodes within that subproject.  
   - For `scope: project`, depends_on may reference any node.

4. **Project completion.**
   - A project is fully complete when its `scope: project` completion is `done`.  
   - In the absence of an explicit scoped completion, project completion is undefined.

### Current implementation

Currently, `kind: completion` behaves like a `task` with special intent.  
`scope` and `scope_of` are documented but **not yet enforced** by `lattice-base-validate`.

---

## Validation Rules

### Enforced today

1. All `id` values must be unique.  
2. All `depends_on` references must exist.  
3. The lattice must be acyclic.  
4. `task` and `completion` nodes with defined statuses must include a `test`.  
5. `lattice-base-test --complete` demotes inconsistent `done` states automatically.

### Planned future checks

1. Each project, epic, or subproject has **at most one** associated completion node.  
2. `scope` and `scope_of` are required and consistent for all completions.  
3. Scoped completions only depend on nodes within their respective sublattices.

---

## Versioning Policy

- Minor version increments (e.g., 0.1 → 0.2) add non-breaking fields or semantics.
- Major version increments (1.x → 2.x) may break compatibility.
- A future `schema_version` field in `project.yaml` will allow cross-version validation.

---

_LGPL-3.0 © 2025 Robert Law <nosimpler@gmail.com>_