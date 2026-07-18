import os
import sys
from mcp.server.fastmcp import FastMCP
from .client import TuleapClient
from .tools import users, trackers, agile, files


def get_client() -> TuleapClient:
    tuleap_url = os.getenv("TULEAP_URL")
    tuleap_api_key = os.getenv("TULEAP_API_KEY")

    if not tuleap_url or not tuleap_api_key:
        print(
            "Error: TULEAP_URL and TULEAP_API_KEY environment variables must be set.",
            file=sys.stderr,
        )
        sys.exit(1)

    return TuleapClient(tuleap_url, tuleap_api_key)


mcp = FastMCP("Tuleap MCP Server")


# ── Projects ──────────────────────────────────────────────────────────────────

@mcp.tool()
async def search_projects(query: str = None) -> str:
    """List projects you are a member of. Pass an optional query to filter by shortname."""
    client = get_client()
    return str(await agile.search_projects(client, query))


# ── Trackers ──────────────────────────────────────────────────────────────────

@mcp.tool()
async def get_project_trackers(project_id: int, full: bool = False) -> str:
    """List all trackers (e.g. Tasks, Bugs, Stories) for a project. Returns slim entries:
    id, label, item_name, description, has_change_request_field (bool), and
    change_request_budget_field (the tracker's approved-budget hours field label, or None).
    Use this to find which trackers support Change Requests. Pass full=True for the raw
    Tuleap payload with complete field definitions (very large)."""
    client = get_client()
    return str(await trackers.get_project_trackers(client, project_id, full))


@mcp.tool()
async def get_tracker_fields(tracker_id: int) -> str:
    """List all fields for a tracker, including field_id, label, type, required flag, and allowed values.
    Call this before create_artifact or update_artifact to know the correct field_ids and value ids."""
    client = get_client()
    return str(await trackers.get_tracker_fields(client, tracker_id))


# ── Artifacts ─────────────────────────────────────────────────────────────────

@mcp.tool()
async def search_artifacts(tracker_id: int, filters: dict = None) -> str:
    """Search artifacts in a tracker. Optional filters dict narrows results, e.g.
    {"assigned_to": {"id": 5}} or {"status": "Open"}. Returns slim payloads (id, title, status,
    assignees, priority, submitted_on, last_modified_date — the last three allow sorting by
    urgency or recency).
    If the tracker has a 'Change Request' field, results also include change_request (bool) and
    change_request_status; use search_change_requests to filter on these directly.
    If the tracker has an approved-budget field (e.g. "Approved Hours"), results include
    approved_budget (hours, may be null) and approved_budget_field.
    If the tracker has a 'Technical Details' field, results also include technical_details
    (text, may be null) — use update_technical_details to set it."""
    client = get_client()
    return str(await trackers.search_artifacts(client, tracker_id, filters))


@mcp.tool()
async def get_artifact(artifact_id: int) -> str:
    """Get slim details of a specific artifact: id, title, status, assigned_to, priority,
    submitted_on, last_modified_date, estimated_delivery.
    If the artifact's tracker has a 'Change Request' field, also includes change_request (bool) and,
    when set, change_request_status — useful for deciding how to code Replicon timesheet entries.
    If the tracker has an approved-budget field (e.g. "Approved Hours", "CR hours approved"),
    also includes approved_budget (hours, may be null) and approved_budget_field.
    If the tracker has a 'Technical Details' field, also includes technical_details
    (text, may be null) — use update_technical_details to set it."""
    client = get_client()
    return str(await trackers.get_artifact_details(client, artifact_id))


@mcp.tool()
async def search_change_requests(tracker_id: int, status: list = None) -> str:
    """List artifacts in a tracker flagged as Change Request (via the tracker's
    'Change Request' checkbox field). Optional status filters by Change Request
    Status label(s), e.g. ["Accepted"] for approved change requests.
    Returns {"supported": false, "results": []} if the tracker has no Change
    Request field at all — distinct from {"supported": true, "results": []}
    which means the field exists but nothing currently matches.
    The response's budget_field names the tracker's approved-budget hours field
    when one exists (labels vary: "Approved Hours", "Accepted effort (h)",
    "CR hours approved"); each result then carries approved_budget (hours, may
    be null when not yet filled in).
    Results also include priority, submitted_on, and last_modified_date for sorting.
    Use for building Replicon timesheet project/task codes from approved change requests."""
    client = get_client()
    return str(await trackers.search_change_requests(client, tracker_id, status))


@mcp.tool()
async def get_artifact_comments(artifact_id: int) -> str:
    """Get all comments posted on an artifact, with author and timestamp."""
    client = get_client()
    return str(await trackers.get_artifact_comments(client, artifact_id))


@mcp.tool()
async def get_artifact_attachments(
    artifact_id: int,
    last_n_changesets: int = None,
    last_n_files: int = None,
) -> str:
    """List files attached to an artifact.
    last_n_changesets=2 → files from the 2 most recent upload events (one event may include multiple files).
    last_n_files=2      → the 2 most recently uploaded individual files by timestamp.
    Both can be combined: last_n_changesets scopes first, then last_n_files trims the result."""
    client = get_client()
    return str(await trackers.get_artifact_attachments(client, artifact_id, last_n_changesets, last_n_files))


@mcp.tool()
async def download_artifact_attachment(file_id: int, save_path: str = None, html_url: str = None) -> str:
    """Download an attachment by file_id to disk. Pass html_url from get_artifact_attachments
    for direct binary download (avoids base64 overhead). Returns the local path where the file was saved."""
    client = get_client()
    return str(await trackers.download_artifact_attachment(client, file_id, save_path, html_url))


@mcp.tool()
async def upload_artifact_attachment(file_path: str, description: str = "") -> str:
    """Upload a local file as a temporary attachment. Returns file_id to reference in create_artifact
    or update_artifact values: {"field_id": <file_field_id>, "value": {"id": <file_id>}}.
    The file is read from disk in Python — the LLM never handles raw bytes."""
    client = get_client()
    return str(await trackers.upload_artifact_attachment(client, file_path, description))


@mcp.tool()
async def create_artifact(tracker_id: int, values: list) -> str:
    """Create a new artifact in a tracker. Call get_tracker_fields first to get field_ids and allowed values.
    values example: [{"field_id": 123, "value": "Title"}, {"field_id": 456, "bind_value_ids": [789]}]"""
    client = get_client()
    return str(await trackers.create_artifact(client, tracker_id, values))


@mcp.tool()
async def assign_artifact(artifact_id: int, user_id: int) -> str:
    """Assign an artifact to a user. Automatically resolves the correct User Group
    to satisfy Tuleap's workflow constraint (Assigned To and User Group must match).
    Use search_users to find user_id."""
    client = get_client()
    return str(await trackers.assign_artifact(client, artifact_id, user_id))


@mcp.tool()
async def update_artifact(
    artifact_id: int, values: list = None, comment: str = None, comment_format: str = "html"
) -> str:
    """Update an artifact's fields or add a comment. At least one of values or comment is required.
    comment_format: 'html' (default), 'text', or 'commonmark' (Markdown).
    Call get_tracker_fields first to know valid field_ids and bind_value_ids."""
    client = get_client()
    if not values and not comment:
        return "Error: Must provide either values or comment to update."
    if values is None:
        values = []
    return str(await trackers.update_artifact(client, artifact_id, values, comment, comment_format))


@mcp.tool()
async def update_technical_details(artifact_id: int, text: str, text_format: str = "commonmark") -> str:
    """Write text into an artifact's 'Technical Details' field, if its tracker has one.
    text_format: 'commonmark' (default, Markdown), 'html', or 'text'.
    This field is often restricted by Tuleap tracker permissions to a specific user
    group (e.g. SwE) — callers outside that group will get an error. Call
    get_tracker_fields first to confirm the tracker has a 'Technical Details' field."""
    client = get_client()
    return str(await trackers.update_technical_details(client, artifact_id, text, text_format))


@mcp.tool()
async def get_my_artifacts(user_id: int, tracker_id: int, status: list = None) -> str:
    """Get artifacts assigned to a specific user in a tracker. Returns slim payloads
    including priority, submitted_on, last_modified_date, and technical_details (when the
    tracker has that field) so the list can be sorted by urgency or recency.
    Optional status list filters by label name(s) server-side, e.g.
    ["To be analysed", "To be solved", "To be tested"] for active tasks.
    Labels are matched case-insensitively; IDs are resolved automatically.
    Use search_users to find user_id, get_project_trackers to find tracker_id."""
    client = get_client()
    return str(await trackers.get_my_artifacts(client, user_id, tracker_id, status))


# ── Users ─────────────────────────────────────────────────────────────────────

@mcp.tool()
async def search_users(query: str = None) -> str:
    """Search for Tuleap users by name, username, or email. Returns id, display_name, email."""
    client = get_client()
    return str(await users.get_users(client, query))


# ── Agile ─────────────────────────────────────────────────────────────────────

@mcp.tool()
async def get_project_epics(project_id: int) -> str:
    """List all epics for a project. Returns id and title. Use get_artifact for full details."""
    client = get_client()
    return str(await agile.get_epics(client, project_id))


@mcp.tool()
async def create_epic(project_id: int, values: list) -> str:
    """Create a new epic in a project. Call get_tracker_fields on the project's Epic tracker first."""
    client = get_client()
    return str(await agile.create_epic(client, project_id, values))


@mcp.tool()
async def get_project_user_stories(project_id: int, epic_id: int = None) -> str:
    """List user stories for a project, optionally filtered by parent epic_id."""
    client = get_client()
    return str(await agile.get_user_stories(client, project_id, epic_id))


@mcp.tool()
async def create_user_story(project_id: int, values: list) -> str:
    """Create a new user story in a project. Call get_tracker_fields on the User Story tracker first."""
    client = get_client()
    return str(await agile.create_user_story(client, project_id, values))


@mcp.tool()
async def link_to_epic(epic_id: int, child_artifact_id: int) -> str:
    """Link a child artifact (e.g. a User Story) to a parent epic using the _is_child link type."""
    client = get_client()
    return str(await agile.link_to_epic(client, epic_id, child_artifact_id))


@mcp.tool()
async def get_epic_progress(epic_id: int) -> str:
    """Get summarized progress for an epic: Status, Progress, Remaining Effort, Total Effort."""
    client = get_client()
    return str(await agile.get_epic_progress(client, epic_id))


@mcp.tool()
async def get_project_milestones(project_id: int, status: str = None) -> str:
    """List milestones (releases/sprints) for a project. Optional status filter: 'open' or 'closed'.
    Returns id, label, status, start_date, end_date, capacity, remaining_effort."""
    client = get_client()
    return str(await agile.get_project_milestones(client, project_id, status))


# ── Git ───────────────────────────────────────────────────────────────────────

@mcp.tool()
async def get_git_repos(project_id: int) -> str:
    """List git repositories linked to a project."""
    client = get_client()
    return str(await files.get_git_repositories(client, project_id))


def main():
    mcp.run()


if __name__ == "__main__":
    main()
