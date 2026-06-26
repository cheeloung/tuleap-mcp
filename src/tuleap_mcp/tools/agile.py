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


async def _get_tracker_id_by_name(
    client: TuleapClient, project_id: int, tracker_name: str
) -> Optional[int]:
    """Helper to find a tracker ID by its name within a project."""
    trackers = await client.get(f"projects/{project_id}/trackers")
    for t in trackers:
        if (
            tracker_name.lower() in t.get("item_name", "").lower()
            or tracker_name.lower() in t.get("name", "").lower()
            or t.get("shortname", "").lower() == tracker_name.lower()
        ):
            return t.get("id")
    return None


async def _get_epic_tracker_id(client: TuleapClient, project_id: int) -> int:
    tracker_id = await _get_tracker_id_by_name(client, project_id, "epic")
    if not tracker_id:
        raise Exception(f"Could not find an 'Epic' tracker in project {project_id}")
    return tracker_id


async def _get_user_story_tracker_id(client: TuleapClient, project_id: int) -> int:
    tracker_id = await _get_tracker_id_by_name(client, project_id, "user stor")
    if not tracker_id:
        tracker_id = await _get_tracker_id_by_name(client, project_id, "story")
    if not tracker_id:
        raise Exception(
            f"Could not find a 'User Story' tracker in project {project_id}"
        )
    return tracker_id


async def get_epics(client: TuleapClient, project_id: int) -> List[Dict[str, Any]]:
    tracker_id = await _get_epic_tracker_id(client, project_id)
    results = await client.get_paginated(f"trackers/{tracker_id}/artifacts")
    return [{"id": a.get("id"), "title": a.get("title")} for a in results]


async def create_epic(
    client: TuleapClient, project_id: int, values: List[Dict[str, Any]]
) -> Dict[str, Any]:
    tracker_id = await _get_epic_tracker_id(client, project_id)
    return await client.post("artifacts", json={"tracker": {"id": tracker_id}, "values": values})


async def get_user_stories(
    client: TuleapClient, project_id: int, epic_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    tracker_id = await _get_user_story_tracker_id(client, project_id)
    params = {}
    if epic_id:
        params["query"] = f"parent_id={epic_id}"
    results = await client.get_paginated(f"trackers/{tracker_id}/artifacts", params=params)
    return [{"id": a.get("id"), "title": a.get("title")} for a in results]


async def create_user_story(
    client: TuleapClient, project_id: int, values: List[Dict[str, Any]]
) -> Dict[str, Any]:
    tracker_id = await _get_user_story_tracker_id(client, project_id)
    return await client.post("artifacts", json={"tracker": {"id": tracker_id}, "values": values})


async def link_to_epic(
    client: TuleapClient, epic_id: int, child_artifact_id: int
) -> Any:
    """Link a child artifact to a parent epic via the artifact links endpoint."""
    payload = {
        "all_links": [{"id": epic_id, "type": "_is_child"}]
    }
    return await client.put(f"artifacts/{child_artifact_id}/links", json=payload)


async def get_epic_progress(client: TuleapClient, epic_id: int) -> Dict[str, Any]:
    artifact = await client.get(f"artifacts/{epic_id}")
    summary = {"id": artifact.get("id")}
    for v in artifact.get("values") or []:
        label = v.get("label")
        if label in ["Status", "Progress", "Remaining Effort", "Total Effort"]:
            summary[label] = v.get("value")
    return summary


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
