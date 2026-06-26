import json
from typing import List, Dict, Any, Optional
from ..client import TuleapClient

_SLIM_FIELDS = {"status", "assigned_to", "assignees", "last_modified_date", "estimated_delivery"}


def _slim_artifact(artifact: Dict[str, Any]) -> Dict[str, Any]:
    slim = {"id": artifact.get("id"), "title": artifact.get("title")}
    for f in artifact.get("values") or []:
        name = (f.get("label") or "").lower().replace(" ", "_")
        if name in _SLIM_FIELDS:
            slim[name] = f.get("value") or f.get("values")
    return slim


async def get_artifact_details(
    client: TuleapClient, artifact_id: int
) -> Dict[str, Any]:
    data = await client.get(f"artifacts/{artifact_id}")
    return _slim_artifact(data)


async def search_artifacts(
    client: TuleapClient, tracker_id: int, filters: Optional[Dict] = None
) -> List[Dict[str, Any]]:
    params = {}
    if filters:
        params["query"] = json.dumps(filters)
    results = await client.get_paginated(f"trackers/{tracker_id}/artifacts", params=params)
    return [_slim_artifact(a) for a in results]


async def create_artifact(
    client: TuleapClient, tracker_id: int, values: List[Dict[str, Any]]
) -> Dict[str, Any]:
    payload = {"tracker": {"id": tracker_id}, "values": values}
    return await client.post("artifacts", json=payload)


async def get_project_trackers(
    client: TuleapClient, project_id: int
) -> List[Dict[str, Any]]:
    return await client.get(f"projects/{project_id}/trackers")


async def get_tracker_fields(
    client: TuleapClient, tracker_id: int
) -> List[Dict[str, Any]]:
    """Return fields for a tracker with their IDs, types, and allowed values."""
    data = await client.get(f"trackers/{tracker_id}")
    fields = []
    for f in data.get("fields") or []:
        field = {
            "field_id": f.get("field_id"),
            "label": f.get("label"),
            "type": f.get("type"),
            "required": f.get("required", False),
        }
        if f.get("values"):
            field["values"] = [
                {"id": v.get("id"), "label": v.get("label")}
                for v in f["values"]
            ]
        fields.append(field)
    return fields


async def get_artifact_comments(
    client: TuleapClient, artifact_id: int
) -> List[Dict[str, Any]]:
    """Return comments (changesets with non-empty body) for an artifact."""
    changesets = await client.get_paginated(
        f"artifacts/{artifact_id}/changesets", params={"fields": "comments"}
    )
    comments = []
    for cs in changesets:
        body = (cs.get("last_comment") or {}).get("body", "").strip()
        if body:
            comments.append({
                "submitted_by": cs.get("submitted_by_details", {}).get("display_name"),
                "submitted_on": cs.get("submitted_on"),
                "body": body,
            })
    return comments


async def get_my_artifacts(
    client: TuleapClient, user_id: int, tracker_id: int
) -> List[Dict[str, Any]]:
    """Return slim artifacts assigned to a specific user in a tracker."""
    results = await client.get_paginated(
        f"trackers/{tracker_id}/artifacts",
        params={"query": json.dumps({"assigned_to": {"id": user_id}})},
    )
    return [_slim_artifact(a) for a in results]


async def update_artifact(
    client: TuleapClient,
    artifact_id: int,
    values: List[Dict[str, Any]],
    comment: Optional[str] = None,
) -> Dict[str, Any]:
    payload = {"values": values}
    if comment:
        payload["comment"] = {"body": comment, "format": "html"}
    return await client.put(f"artifacts/{artifact_id}", json=payload)
