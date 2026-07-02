import base64
import json
import mimetypes
import os
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
    client: TuleapClient,
    user_id: int,
    tracker_id: int,
    status: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Return slim artifacts assigned to a specific user, optionally filtered by status labels."""
    query: Dict[str, Any] = {"assigned_to": {"id": user_id}}
    if status:
        tracker = await client.get(f"trackers/{tracker_id}")
        status_field = next(
            (f for f in (tracker.get("fields") or []) if f.get("name") == "status"),
            None,
        )
        if status_field:
            label_map = {v["label"].lower(): v["id"] for v in (status_field.get("values") or [])}
            ids = [label_map[s.lower()] for s in status if s.lower() in label_map]
            if ids:
                query["status"] = ids
    results = await client.get_paginated(
        f"trackers/{tracker_id}/artifacts",
        params={"query": json.dumps(query)},
    )
    return [_slim_artifact(a) for a in results]


async def get_artifact_attachments(
    client: TuleapClient,
    artifact_id: int,
    last_n_changesets: Optional[int] = None,
    last_n_files: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """List files attached to an artifact, with optional scoping filters."""
    changesets = await client.get_paginated(f"artifacts/{artifact_id}/changesets")
    file_changesets = [
        cs for cs in changesets
        if any(v.get("type") == "file" for v in (cs.get("values") or []))
    ]
    if last_n_changesets is not None:
        file_changesets = file_changesets[-last_n_changesets:]

    seen = set()
    result = []
    for cs in file_changesets:
        for v in cs.get("values") or []:
            if v.get("type") != "file":
                continue
            for f in v.get("file_descriptions") or v.get("values") or []:
                fid = f.get("id")
                if fid in seen:
                    continue
                seen.add(fid)
                result.append({
                    "file_id": fid,
                    "name": f.get("name"),
                    "size_bytes": f.get("size"),
                    "mime_type": f.get("type"),
                    "description": f.get("description"),
                    "html_url": f.get("html_url"),
                    "uploaded_by": cs.get("submitted_by_details", {}).get("display_name"),
                    "uploaded_on": cs.get("submitted_on"),
                    "changeset_id": cs.get("id"),
                })

    result.sort(key=lambda x: x.get("uploaded_on") or "", reverse=True)
    if last_n_files is not None:
        result = result[:last_n_files]
    return result


async def download_artifact_attachment(
    client: TuleapClient,
    file_id: int,
    save_path: Optional[str] = None,
    html_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Download a file attachment to disk, returning the local path."""
    if html_url:
        raw = await client.download_binary(html_url)
        filename = html_url.rsplit("/", 1)[-1]
    else:
        response = await client.download(f"artifact_files/{file_id}")
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            raw = base64.b64decode(response.json()["data"])
        else:
            raw = response.content
        disposition = response.headers.get("content-disposition", "")
        filename = f"attachment_{file_id}"
        if 'filename="' in disposition:
            filename = disposition.split('filename="')[1].rstrip('"')

    path = save_path or os.path.join(os.getcwd(), filename)
    with open(path, "wb") as fh:
        fh.write(raw)
    return {"saved_to": os.path.abspath(path), "size_bytes": len(raw)}


async def upload_artifact_attachment(
    client: TuleapClient,
    file_path: str,
    description: str = "",
) -> Dict[str, Any]:
    """Upload a local file as a temporary attachment. Returns file_id for use in artifact values."""
    path = os.path.abspath(file_path)
    name = os.path.basename(path)
    mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
    with open(path, "rb") as fh:
        content_b64 = base64.b64encode(fh.read()).decode()
    result = await client.post("artifact_temporary_files", json={
        "name": name,
        "mimetype": mime,
        "content": content_b64,
        "offset": 1,
        "description": description,
    })
    return {"file_id": result["id"], "name": result["name"], "size_bytes": result["size"]}


async def assign_artifact(
    client: TuleapClient,
    artifact_id: int,
    user_id: int,
) -> Dict[str, Any]:
    """Assign an artifact to a user, automatically setting the matching User Group."""
    artifact = await client.get(f"artifacts/{artifact_id}")
    tracker_id = artifact["tracker"]["id"]

    tracker = await client.get(f"trackers/{tracker_id}")
    fields = tracker.get("fields") or []
    assigned_to_field = next((f for f in fields if f.get("name") == "assigned_to"), None)
    user_group_field = next((f for f in fields if "user_group" in f.get("name", "")), None)

    values = []
    if assigned_to_field:
        values.append({"field_id": assigned_to_field["field_id"], "bind_value_ids": [user_id]})

    if user_group_field:
        matched_ref_id = None
        for gv in (user_group_field.get("values") or []):
            ref_id = (gv.get("ugroup_reference") or {}).get("id")
            if not ref_id:
                continue
            members = await client.get_paginated(f"user_groups/{ref_id}/users")
            if any(m.get("id") == user_id for m in members):
                matched_ref_id = ref_id
                break
        if matched_ref_id:
            values.append({"field_id": user_group_field["field_id"], "bind_value_ids": [matched_ref_id]})

    return await client.put(f"artifacts/{artifact_id}", json={"values": values})


async def update_artifact(
    client: TuleapClient,
    artifact_id: int,
    values: List[Dict[str, Any]],
    comment: Optional[str] = None,
    comment_format: str = "html",
) -> Dict[str, Any]:
    payload = {"values": values}
    if comment:
        payload["comment"] = {"body": comment, "format": comment_format}
    return await client.put(f"artifacts/{artifact_id}", json=payload)
