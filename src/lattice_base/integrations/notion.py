from __future__ import annotations

import os
import argparse
from pathlib import Path
from typing import Dict

from notion_client import Client  # optional extra

from ..lattice.io import load_lattice
from ..lattice.model import Lattice, Task


def _get_client() -> Client:
    token = os.environ.get("NOTION_API_TOKEN")
    if not token:
        raise RuntimeError("NOTION_API_TOKEN env var must be set")
    return Client(auth=token)


def _task_to_properties(task: Task) -> Dict:
    # Assumes a Notion DB schema roughly like:
    # - "Task ID" (rich text)
    # - "Name" (title)
    # - "Kind" (select)
    # - "Status" (select)
    # - "Tags" (multi-select)
    # - "Description" (rich text)
    return {
        "Task ID": {"rich_text": [{"text": {"content": task.id}}]},
        "Name": {"title": [{"text": {"content": task.name}}]},
        "Kind": {"select": {"name": task.kind}},
        "Status": {"select": {"name": task.status}},
        "Tags": {"multi_select": [{"name": t} for t in task.tags]},
        "Description": {
            "rich_text": [{"text": {"content": task.description or ""}}],
        },
    }


def push_lattice_to_notion(lattice_path: str | Path, database_id: str) -> None:
    """
    One-way sync: create (or extend) pages in a Notion database for each task.
    This is intentionally minimal and does not manage deletions or relations.
    """
    client = _get_client()
    lat: Lattice = load_lattice(lattice_path)

    for task in lat.tasks:
        props = _task_to_properties(task)
        client.pages.create(parent={"database_id": database_id}, properties=props)


def pull_lattice_from_notion(database_id: str) -> Lattice:
    """
    Skeleton for reading from Notion and building a Lattice.
    Relations/depends_on are not wired here.
    """
    client = _get_client()

    results = []
    cursor = None
    while True:
        kwargs = {"database_id": database_id}
        if cursor:
            kwargs["start_cursor"] = cursor
        resp = client.databases.query(**kwargs)
        results.extend(resp["results"])
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")

    tasks: list[Task] = []
    for page in results:
        props = page["properties"]
        tid = props["Task ID"]["rich_text"][0]["plain_text"] if props["Task ID"]["rich_text"] else ""
        name = props["Name"]["title"][0]["plain_text"] if props["Name"]["title"] else ""
        kind = props["Kind"]["select"]["name"] if props["Kind"]["select"] else "task"
        status = props["Status"]["select"]["name"] if props["Status"]["select"] else "todo"
        tags = [t["name"] for t in props["Tags"]["multi_select"]]
        desc = "".join(rt["plain_text"] for rt in props["Description"]["rich_text"])

        tasks.append(
            Task(
                id=tid,
                name=name,
                kind=kind,
                status=status,
                tags=tags,
                description=desc,
                depends_on=[],
            )
        )

    project = {"id": "from-notion", "name": "From Notion"}
    return Lattice(version=0.1, project=project, tasks=tasks)  # type: ignore[arg-type]


def cli_push():
    parser = argparse.ArgumentParser(
        description="Push a lattice YAML into a Notion database (create-only skeleton)."
    )
    parser.add_argument("lattice_path")
    parser.add_argument("--database-id", required=True)
    args = parser.parse_args()
    push_lattice_to_notion(args.lattice_path, args.database_id)


def cli_pull():
    parser = argparse.ArgumentParser(
        description="Pull a Notion database into a lattice YAML (skeleton)."
    )
    parser.add_argument("--database-id", required=True)
    parser.add_argument("--out", required=True, help="Output YAML path")
    args = parser.parse_args()

    lat = pull_lattice_from_notion(args.database_id)
    out = Path(args.out)
    with out.open("w") as f:
        import yaml

        yaml.safe_dump(lat.dict(), f, sort_keys=False)
