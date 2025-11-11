from __future__ import annotations

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, field_validator


Status = Literal["suggested", "design", "planned", "in-progress", "done", "blocked"]
Kind = Literal["task", "epic", "subproject", "completion"]


class ProjectMeta(BaseModel):
    id: str
    name: str
    owner: Optional[str] = None
    description: Optional[str] = None
    statuses: Optional[List[str]] = None
    # Optional internal/project version fields if you want
    lattice_version: Optional[str] = None
    package_version: Optional[str] = None
    # Optional global healthcheck
    test: Optional[str] = None


class Task(BaseModel):
    id: str
    name: str
    kind: Kind = "task"

    # Only meaningful for kind=task/completion
    status: Optional[Status] = None
    priority: Optional[Literal["low", "medium", "high"]] = None

    depends_on: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

    # Optional test command
    test: Optional[str] = None

    # Arbitrary extra fields are allowed and preserved
    extra: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("test")
    @classmethod
    def normalize_test(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v or None


class Lattice(BaseModel):
    version: Optional[float] = 0.1
    project: ProjectMeta
    tasks: List[Task] = Field(default_factory=list)

    def task_by_id(self, task_id: str) -> Optional[Task]:
        for t in self.tasks:
            if t.id == task_id:
                return t
        return None

    def task_index(self) -> Dict[str, Task]:
        return {t.id: t for t in self.tasks}
