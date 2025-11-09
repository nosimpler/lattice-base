from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, validator


class ProjectInfo(BaseModel):
    id: str
    name: str
    owner: Optional[str] = None
    description: Optional[str] = None


class Task(BaseModel):
    id: str
    name: str
    kind: str = Field(..., regex="^(subproject|epic|task|spike|milestone)$")
    status: str = Field(..., regex="^(todo|in-progress|blocked|done|planned)$")
    depends_on: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

    @validator("id")
    def nonempty_id(cls, v: str) -> str:
        if not v:
            raise ValueError("Task id must not be empty")
        return v


class Lattice(BaseModel):
    version: float = 0.1
    project: ProjectInfo
    tasks: List[Task]

    @validator("tasks")
    def unique_ids(cls, tasks: List[Task]) -> List[Task]:
        ids = set()
        for t in tasks:
            if t.id in ids:
                raise ValueError(f"Duplicate task id: {t.id}")
            ids.add(t.id)
        return tasks
