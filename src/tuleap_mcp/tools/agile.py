from typing import List, Dict, Any, Optional
from ..client import TuleapClient


async def search_projects(
    client: TuleapClient, query: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Search for projects in Tuleap."""
    params = {"query": '{"is_member_of": true}'}
    if query:
        params["query"] = f'{{"is_member_of": true, "shortname": "{query}"}}'
    return await client.get("projects", params=params)


async def link_to_epic(
    client: TuleapClient, epic_id: int, child_artifact_id: int
) -> Any:
    """Link a child artifact to a parent epic via the artifact links endpoint."""
    payload = {
        "all_links": [{"id": epic_id, "type": "_is_child"}]
    }
    return await client.put(f"artifacts/{child_artifact_id}/links", json=payload)


async def get_project_milestones(
    client: TuleapClient, project_id: int, status: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get milestones (releases/sprints) for a project."""
    params = {}
    if status:
        params["query"] = f'{{"status": "{status}"}}'
    results = await client.get_paginated(f"projects/{project_id}/milestones", params=params)
    return [
        {
            "id": m.get("id"),
            "label": m.get("label"),
            "status": m.get("status_value"),
            "semantic_status": m.get("semantic_status"),
            "start_date": m.get("start_date"),
            "end_date": m.get("end_date"),
            "capacity": m.get("capacity"),
            "remaining_effort": m.get("remaining_effort"),
        }
        for m in results
    ]
