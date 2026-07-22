import base64
import json
import mimetypes
import os
import re
from typing import List, Dict, Any, Optional
from ..client import TuleapClient

_SLIM_FIELDS = {
    "status",
    "assigned_to",
    "assignees",
    "priority",
    "importance",
    "estimated_delivery",
    "change_request",
    "change_request_status",
    "description",
    "progress",
    "remaining_effort",
    "total_effort",
}

# Budget fields are labelled differently per tracker ("Approved Hours",
# "Accepted effort (h)", "CR hours approved"), so match by pattern instead.
_BUDGET_LABEL_RE = re.compile(
    r"(approved|accepted).*(hours?|effort)|(hours?|effort).*(approved|accepted)|budget",
    re.I,
)
_BUDGET_FIELD_TYPES = {"float", "int", "computed"}
_LAYOUT_FIELD_TYPES = {"fieldset", "column"}


def _find_change_request_field(fields: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    return next(
        (
            f for f in fields
            if (f.get("label") or "").lower() == "change request"
            and f.get("type") not in _LAYOUT_FIELD_TYPES
        ),
        None,
    )


def _find_technical_details_field(fields: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    return next(
        (
            f for f in fields
            if (f.get("label") or "").lower() == "technical details"
            and f.get("type") not in _LAYOUT_FIELD_TYPES
        ),
        None,
    )


def _find_budget_field(fields: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    return next(
        (
            f for f in fields
            if f.get("type") in _BUDGET_FIELD_TYPES
            and _BUDGET_LABEL_RE.search(f.get("label") or "")
        ),
        None,
    )


def _slim_artifact(artifact: Dict[str, Any]) -> Dict[str, Any]:
    slim = {"id": artifact.get("id"), "title": artifact.get("title")}
    for f in artifact.get("values") or []:
        label = f.get("label") or ""
        if f.get("type") in _BUDGET_FIELD_TYPES and _BUDGET_LABEL_RE.search(label):
            slim["approved_budget"] = f.get("value")
            slim["approved_budget_field"] = label
            continue
        name = label.lower().replace(" ", "_")
        if name not in _SLIM_FIELDS:
            continue
        raw = f.get("value") or f.get("values")
        if f.get("type") == "cb":
            slim[name] = bool(raw)
        elif f.get("type") == "sb" and isinstance(raw, list):
            slim[name] = raw[0].get("label") if raw else None
        elif f.get("type") == "sb" and isinstance(raw, dict):
            slim[name] = raw.get("label")
        else:
            slim[name] = raw
    # submission/modification timestamps live on the artifact itself, not in
    # its values; both endpoints return them as ISO-8601 strings which sort
    # lexicographically.
    for key in ("submitted_on", "last_modified_date"):
        if artifact.get(key):
            slim[key] = artifact[key]
    return slim


async def get_artifact_details(
    client: TuleapClient, artifact_id: int
) -> Dict[str, Any]:
    data = await client.get(f"artifacts/{artifact_id}")
    return _slim_artifact(data)


async def search_artifacts(
    client: TuleapClient, tracker_id: int, filters: Optional[Dict] = None
) -> List[Dict[str, Any]]:
    # values=all makes the listing endpoint return field values, so slim
    # payloads (status, assignees, approved_budget, ...) can be built without
    # fetching each artifact individually.
    params: Dict[str, Any] = {"values": "all"}
    if filters:
        params["query"] = json.dumps(filters)
    results = await client.get_paginated(f"trackers/{tracker_id}/artifacts", params=params)
    return [_slim_artifact(a) for a in results]


async def search_change_requests(
    client: TuleapClient,
    tracker_id: int,
    status: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Return artifacts flagged as Change Request, optionally filtered by
    Change Request Status label(s). `supported` is False when the tracker has
    no 'Change Request' field at all (as opposed to zero matches).

    Filters server-side via the tracker's field names/bind-value ids (Tuleap's
    artifact listing endpoint accepts `{field_name: [value_id, ...]}` in its
    `query` param, ORing multiple ids) and requests `values=all` so each
    result carries its Change Request Status and approved budget directly —
    no per-artifact fetches. If status label(s) are given but none match the
    tracker's known Change Request Status values (or it has no such field),
    returns no results rather than silently ignoring the filter.

    `budget_field` names the tracker's approved-budget (hours) field when one
    exists (labels vary per tracker, e.g. "Approved Hours", "Accepted effort
    (h)", "CR hours approved"); each result then carries `approved_budget`."""
    tracker = await client.get(f"trackers/{tracker_id}")
    fields = tracker.get("fields") or []
    cr_field = _find_change_request_field(fields)
    if not cr_field:
        return {"supported": False, "budget_field": None, "results": []}

    budget_field = _find_budget_field(fields)
    budget_label = budget_field["label"] if budget_field else None

    cr_value_ids = [str(v["id"]) for v in (cr_field.get("values") or [])]
    if not cr_value_ids:
        return {"supported": True, "budget_field": budget_label, "results": []}

    status_field = next(
        (f for f in fields if (f.get("label") or "").lower() == "change request status"), None
    )
    if status and not status_field:
        return {"supported": True, "budget_field": budget_label, "results": []}

    filters = {cr_field["name"]: cr_value_ids}
    if status_field and status:
        available = {v["label"].lower(): v for v in (status_field.get("values") or [])}
        targets = [available[s.lower()] for s in status if s.lower() in available]
        if not targets:
            return {"supported": True, "budget_field": budget_label, "results": []}
        filters[status_field["name"]] = [str(t["id"]) for t in targets]

    results = await search_artifacts(client, tracker_id, filters=filters)
    for r in results:
        r["change_request"] = True
        if status_field:
            r.setdefault("change_request_status", None)
        if budget_field:
            r.setdefault("approved_budget", None)
            r.setdefault("approved_budget_field", budget_label)

    results.sort(key=lambda a: a["id"])
    return {"supported": True, "budget_field": budget_label, "results": results}


async def create_artifact(
    client: TuleapClient, tracker_id: int, values: List[Dict[str, Any]]
) -> Dict[str, Any]:
    payload = {"tracker": {"id": tracker_id}, "values": values}
    return await client.post("artifacts", json=payload)


async def get_project_trackers(
    client: TuleapClient, project_id: int, full: bool = False
) -> List[Dict[str, Any]]:
    """List a project's trackers. Slim by default (the raw payload includes
    every field definition and easily exceeds 100k characters per project);
    pass full=True for the untouched REST response."""
    data = await client.get(f"projects/{project_id}/trackers")
    if full:
        return data
    slim = []
    for t in data:
        fields = t.get("fields") or []
        budget_field = _find_budget_field(fields)
        slim.append({
            "id": t.get("id"),
            "label": t.get("label"),
            "item_name": t.get("item_name"),
            "description": t.get("description"),
            "has_change_request_field": _find_change_request_field(fields) is not None,
            "change_request_budget_field": budget_field["label"] if budget_field else None,
        })
    return slim


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
        params={"values": "all", "query": json.dumps(query)},
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


async def get_technical_details(
    client: TuleapClient, artifact_id: int
) -> Dict[str, Any]:
    """Return an artifact's 'Technical Details' field on its own — kept out of
    get_artifact/search_artifacts/get_my_artifacts since those are meant for
    high-level summaries and the field's content can be long."""
    data = await client.get(f"artifacts/{artifact_id}")
    for f in data.get("values") or []:
        if (f.get("label") or "").lower() == "technical details":
            return {"id": data.get("id"), "technical_details": f.get("value") or f.get("values")}
    return {"id": data.get("id"), "technical_details": None}


async def update_technical_details(
    client: TuleapClient,
    artifact_id: int,
    text: str,
    text_format: str = "commonmark",
) -> Dict[str, Any]:
    """Write text into an artifact's 'Technical Details' field. It's a rich-text
    field (Tuleap's default for it is 'commonmark', i.e. Markdown) — passing a
    bare string instead of a {format, content} value would make Tuleap treat it
    as HTML, so text_format must always be sent explicitly.
    Tuleap may restrict this field to a specific user group (e.g. SwE) via
    tracker permissions; callers outside that group will get a Tuleap API
    error on the PUT, or the field simply won't exist for them."""
    artifact = await client.get(f"artifacts/{artifact_id}")
    tracker_id = artifact["tracker"]["id"]
    tracker = await client.get(f"trackers/{tracker_id}")
    field = _find_technical_details_field(tracker.get("fields") or [])
    if not field:
        raise ValueError(f"Tracker {tracker_id} has no 'Technical Details' field")
    return await client.put(
        f"artifacts/{artifact_id}",
        json={
            "values": [
                {
                    "field_id": field["field_id"],
                    "value": {"format": text_format, "content": text},
                }
            ]
        },
    )


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
