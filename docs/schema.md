# lattice-base Schema Reference

This document defines the **field-level structure** of `project.yaml` for use with the `lattice-base` toolkit.

| Section | Description |
|----------|--------------|
| `version` | Numeric schema version. Currently `0.1`. |
| `project` | Metadata block for the project (id, name, owner, description). |
| `tasks` | List of task, epic, subproject, and completion nodes. |

---

## Project

| Field | Type | Required | Description |
|--------|------|-----------|-------------|
| id | string | ✓ | Unique project identifier. |
| name | string | ✓ | Human-readable name of the project. |
| owner | string |  | Owner or primary lab/team. |
| description | string |  | Freeform description of the project. |

---

## Task

| Field | Type | Required | Description |
|--------|------|-----------|-------------|
| id | string | ✓ | Unique task identifier within the project. |
| name | string | ✓ | Human-readable task name. |
| kind | enum(`task`, `epic`, `completion`, `subproject`) | ✓ | Defines the node type. |
| status | enum(`suggested`, `design`, `planned`, `in-progress`, `done`, `blocked`) |  | Lifecycle state. |
| depends_on | list[string] |  | IDs of prerequisite nodes. |
| tags | list[string] |  | Optional metadata tags. |
| description | string |  | Freeform documentation of the node. |
| test | string |  | Shell command or expression used for validation. |
| scope | enum(`project`, `epic`, `subproject`) | (planned) | For completions only. |
| scope_of | string | (planned) | ID of the node this completion closes. |

---

## Relationships

- `depends_on` defines directed edges in the project DAG.  
- Cycles are disallowed.  
- Cross-epic dependencies are allowed but discouraged.  
- Subprojects may define their own lattices, linked via `kind: subproject` nodes in the parent.

---

## Example

```yaml
version: 0.1
project:
  id: example
  name: Example Project
  owner: nosimpler
  description: Demo of lattice-base schema
tasks:
  - id: t1
    name: Initialize
    kind: task
    status: done
    test: echo init
  - id: t2
    name: Validate
    kind: task
    status: planned
    depends_on: [t1]
    test: pytest
  - id: completion
    name: Project Completion
    kind: completion
    scope: project
    depends_on: [t2]
    test: lattice-base-test --complete
```

---

### Future Additions

- `version_lock`: optional field for locking schema version across subprojects.
- `origin`: metadata field linking tasks to external repos or files.
- `priority`: numeric ordering hint for scheduling or visualization.

---

_LGPL-3.0 © 2025 Robert Law <nosimpler@gmail.com>_
