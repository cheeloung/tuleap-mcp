import json
import pytest
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from tuleap_mcp.tools.trackers import (
    _find_budget_field,
    _find_change_request_field,
    _find_technical_details_field,
    get_artifact_details,
    search_artifacts,
    search_change_requests,
    update_artifact,
    update_technical_details,
    create_artifact,
    assign_artifact,
    get_project_trackers,
    get_tracker_fields,
    get_artifact_comments,
    get_technical_details,
    get_my_artifacts,
    get_artifact_attachments,
    download_artifact_attachment,
    upload_artifact_attachment,
)
from tuleap_mcp.client import TuleapClient


@pytest.mark.asyncio
async def test_get_artifact_details():
    mock_client = AsyncMock()
    mock_client.get.return_value = {
        "id": 100,
        "title": "Bug",
        "values": [{"label": "Status", "value": "Open"}],
    }

    result = await get_artifact_details(mock_client, artifact_id=100)

    mock_client.get.assert_called_once_with("artifacts/100")
    assert result == {"id": 100, "title": "Bug", "status": "Open"}


@pytest.mark.asyncio
async def test_get_artifact_details_change_request_checked():
    mock_client = AsyncMock()
    mock_client.get.return_value = {
        "id": 100,
        "title": "Task",
        "values": [
            {"label": "Status", "value": "Open"},
            {"label": "Change Request", "type": "cb", "values": [{"id": 1002, "label": "Change Request"}]},
            {"label": "Change Request Status", "type": "sb", "value": "Accepted"},
        ],
    }

    result = await get_artifact_details(mock_client, artifact_id=100)

    assert result["change_request"] is True
    assert result["change_request_status"] == "Accepted"


@pytest.mark.asyncio
async def test_get_artifact_details_change_request_unchecked():
    mock_client = AsyncMock()
    mock_client.get.return_value = {
        "id": 100,
        "title": "Task",
        "values": [
            {"label": "Status", "value": "Open"},
            {"label": "Change Request", "type": "cb", "values": []},
        ],
    }

    result = await get_artifact_details(mock_client, artifact_id=100)

    assert result["change_request"] is False


@pytest.mark.asyncio
async def test_get_artifact_details_change_request_field_absent():
    mock_client = AsyncMock()
    mock_client.get.return_value = {
        "id": 100,
        "title": "Task",
        "values": [{"label": "Status", "value": "Open"}],
    }

    result = await get_artifact_details(mock_client, artifact_id=100)

    assert "change_request" not in result
    assert "change_request_status" not in result


@pytest.mark.asyncio
async def test_get_artifact_details_priority_and_dates():
    mock_client = AsyncMock()
    mock_client.get.return_value = {
        "id": 2112,
        "title": "Modeling of Subcontractors",
        "submitted_on": "2025-11-04T09:05:56+01:00",
        "last_modified_date": "2026-03-17T18:17:30+01:00",
        "values": [
            {"label": "Priority", "type": "sb", "values": [{"id": 667, "label": "High"}]},
        ],
    }

    result = await get_artifact_details(mock_client, artifact_id=2112)

    assert result["priority"] == "High"
    assert result["submitted_on"] == "2025-11-04T09:05:56+01:00"
    assert result["last_modified_date"] == "2026-03-17T18:17:30+01:00"


@pytest.mark.asyncio
async def test_get_artifact_details_dates_omitted_when_absent():
    mock_client = AsyncMock()
    mock_client.get.return_value = {
        "id": 100,
        "title": "Task",
        "values": [{"label": "Status", "value": "Open"}],
    }

    result = await get_artifact_details(mock_client, artifact_id=100)

    assert "submitted_on" not in result
    assert "last_modified_date" not in result
    assert "priority" not in result


@pytest.mark.asyncio
async def test_search_artifacts_includes_dates_from_listing():
    mock_client = AsyncMock()
    mock_client.get_paginated.return_value = [
        {
            "id": 50,
            "title": "Task",
            "submitted_on": "2026-01-01T08:00:00+01:00",
            "last_modified_date": "2026-02-01T08:00:00+01:00",
            "values": [
                {"label": "Importance", "type": "sb", "values": [{"id": 1372, "label": "High"}]},
            ],
        },
    ]

    result = await search_artifacts(mock_client, tracker_id=19)

    assert result == [{
        "id": 50,
        "title": "Task",
        "importance": "High",
        "submitted_on": "2026-01-01T08:00:00+01:00",
        "last_modified_date": "2026-02-01T08:00:00+01:00",
    }]


@pytest.mark.asyncio
async def test_get_artifact_details_excludes_technical_details_field():
    mock_client = AsyncMock()
    mock_client.get.return_value = {
        "id": 2112,
        "title": "Modeling of Subcontractors",
        "values": [
            {"label": "Status", "value": "Open"},
            {"label": "Technical Details", "type": "text", "value": "Uses the batch furnace API"},
        ],
    }

    result = await get_artifact_details(mock_client, artifact_id=2112)

    assert "technical_details" not in result


@pytest.mark.asyncio
async def test_search_artifacts_excludes_technical_details():
    mock_client = AsyncMock()
    mock_client.get_paginated.return_value = [
        {
            "id": 50,
            "title": "Task",
            "values": [
                {"label": "Technical Details", "type": "text", "value": "See design doc"},
            ],
        },
    ]

    result = await search_artifacts(mock_client, tracker_id=67)

    assert result == [{"id": 50, "title": "Task"}]


@pytest.mark.asyncio
async def test_get_artifact_details_includes_description():
    mock_client = AsyncMock()
    mock_client.get.return_value = {
        "id": 2567,
        "title": 'New Field "Erfasser"',
        "values": [
            {"label": "Status", "value": "Open"},
            {"label": "Description", "type": "text", "value": "Hi Chee Loung, there is a new field..."},
        ],
    }

    result = await get_artifact_details(mock_client, artifact_id=2567)

    assert result["description"] == "Hi Chee Loung, there is a new field..."


@pytest.mark.asyncio
async def test_get_artifact_details_epic_progress_fields():
    mock_client = AsyncMock()
    mock_client.get.return_value = {
        "id": 101,
        "title": "Big Feature",
        "values": [
            {"label": "Status", "value": "Open"},
            {"label": "Progress", "value": 45},
            {"label": "Remaining Effort", "value": 10},
            {"label": "Total Effort", "value": 22},
        ],
    }

    result = await get_artifact_details(mock_client, artifact_id=101)

    assert result["status"] == "Open"
    assert result["progress"] == 45
    assert result["remaining_effort"] == 10
    assert result["total_effort"] == 22


@pytest.mark.asyncio
async def test_get_technical_details_field_present():
    mock_client = AsyncMock(spec=TuleapClient)
    mock_client.get.return_value = {
        "id": 2112,
        "values": [
            {"label": "Status", "value": "Open"},
            {"label": "Technical Details", "type": "text", "value": "Uses the batch furnace API"},
        ],
    }

    result = await get_technical_details(mock_client, artifact_id=2112)

    mock_client.get.assert_called_once_with("artifacts/2112")
    assert result == {"id": 2112, "technical_details": "Uses the batch furnace API"}


@pytest.mark.asyncio
async def test_get_technical_details_field_absent():
    mock_client = AsyncMock(spec=TuleapClient)
    mock_client.get.return_value = {
        "id": 100,
        "values": [{"label": "Status", "value": "Open"}],
    }

    result = await get_technical_details(mock_client, artifact_id=100)

    assert result == {"id": 100, "technical_details": None}


@pytest.mark.asyncio
async def test_get_artifact_details_approved_budget():
    mock_client = AsyncMock()
    mock_client.get.return_value = {
        "id": 2112,
        "title": "Modeling of Subcontractors",
        "values": [
            {"label": "Status", "value": "Accepted"},
            {"label": "Approved Hours", "type": "float", "value": 8},
        ],
    }

    result = await get_artifact_details(mock_client, artifact_id=2112)

    assert result["approved_budget"] == 8
    assert result["approved_budget_field"] == "Approved Hours"


@pytest.mark.asyncio
async def test_get_artifact_details_no_budget_field():
    mock_client = AsyncMock()
    mock_client.get.return_value = {
        "id": 100,
        "title": "Task",
        "values": [{"label": "Status", "value": "Open"}],
    }

    result = await get_artifact_details(mock_client, artifact_id=100)

    assert "approved_budget" not in result
    assert "approved_budget_field" not in result


@pytest.mark.asyncio
async def test_search_artifacts_with_filters():
    mock_client = AsyncMock()
    mock_client.get_paginated.return_value = [
        {"id": 100, "title": "Task A", "values": [{"label": "Status", "value": "Open"}]},
    ]
    filters = {"assigned_to": {"id": 5}}

    result = await search_artifacts(mock_client, tracker_id=5, filters=filters)

    mock_client.get_paginated.assert_called_once_with(
        "trackers/5/artifacts", params={"values": "all", "query": json.dumps(filters)}
    )
    assert result == [{"id": 100, "title": "Task A", "status": "Open"}]


@pytest.mark.asyncio
async def test_search_artifacts_no_filters():
    mock_client = AsyncMock()
    mock_client.get_paginated.return_value = []

    await search_artifacts(mock_client, tracker_id=5)

    mock_client.get_paginated.assert_called_once_with(
        "trackers/5/artifacts", params={"values": "all"}
    )


def _tracker_with_change_request_and_status_field():
    """Mirrors the real Tuleap tracker field shape: bound fields carry a
    'name' (shortname, used as the query filter key) alongside 'label'."""
    return {
        "fields": [
            {"field_id": 1, "label": "Title", "type": "string", "name": "title"},
            {
                "field_id": 3101, "label": "Change Request", "type": "cb", "name": "change_request",
                "values": [{"id": 1002, "label": "Change Request"}],
            },
            {
                "field_id": 3624, "label": "Change Request Status", "type": "sb", "name": "change_request_status",
                "values": [
                    {"id": 1180, "label": "Open"},
                    {"id": 1182, "label": "Accepted"},
                    {"id": 1181, "label": "Rejected"},
                ],
            },
        ]
    }


def _tracker_with_budget_field():
    tracker = _tracker_with_change_request_and_status_field()
    tracker["fields"].append(
        {"field_id": 4116, "label": "Approved Hours", "type": "float", "name": "approved_hours"}
    )
    return tracker


def _cr_value(status_id=None, status_label=None, approved_hours=...):
    values = [
        {"label": "Change Request", "type": "cb", "values": [{"id": 1002, "label": "Change Request"}]},
        {
            "label": "Change Request Status", "type": "sb",
            "values": [{"id": status_id, "label": status_label}] if status_id else [],
        },
    ]
    if approved_hours is not ...:
        values.append({"label": "Approved Hours", "type": "float", "value": approved_hours})
    return values


@pytest.mark.asyncio
async def test_search_change_requests_full_breakdown():
    mock_client = AsyncMock(spec=TuleapClient)
    mock_client.get.return_value = _tracker_with_change_request_and_status_field()

    async def fake_get_paginated(endpoint, params=None):
        assert params["values"] == "all"
        assert json.loads(params["query"]) == {"change_request": ["1002"]}
        return [
            {"id": 1, "title": "CR A", "values": _cr_value(1180, "Open")},
            {"id": 2, "title": "CR B", "values": _cr_value(1182, "Accepted")},
            {"id": 3, "title": "CR C", "values": _cr_value()},  # flagged, no status set
        ]

    mock_client.get_paginated.side_effect = fake_get_paginated

    result = await search_change_requests(mock_client, tracker_id=67)

    assert result["supported"] is True
    assert result["budget_field"] is None
    by_id = {r["id"]: r for r in result["results"]}
    assert set(by_id) == {1, 2, 3}
    assert by_id[1]["change_request_status"] == "Open"
    assert by_id[2]["change_request_status"] == "Accepted"
    assert by_id[3]["change_request_status"] is None
    assert all(r["change_request"] is True for r in result["results"])
    mock_client.get_paginated.assert_called_once()


@pytest.mark.asyncio
async def test_search_change_requests_filters_by_status():
    mock_client = AsyncMock(spec=TuleapClient)
    mock_client.get.return_value = _tracker_with_change_request_and_status_field()

    async def fake_get_paginated(endpoint, params=None):
        query = json.loads(params["query"])
        assert query == {"change_request": ["1002"], "change_request_status": ["1182"]}
        return [{"id": 2, "title": "CR B", "values": _cr_value(1182, "Accepted")}]

    mock_client.get_paginated.side_effect = fake_get_paginated

    result = await search_change_requests(mock_client, tracker_id=67, status=["accepted"])

    assert [r["id"] for r in result["results"]] == [2]
    assert result["results"][0]["change_request_status"] == "Accepted"
    mock_client.get_paginated.assert_called_once()


@pytest.mark.asyncio
async def test_search_change_requests_multiple_statuses_in_one_query():
    mock_client = AsyncMock(spec=TuleapClient)
    mock_client.get.return_value = _tracker_with_change_request_and_status_field()

    async def fake_get_paginated(endpoint, params=None):
        query = json.loads(params["query"])
        # multiple bind-value ids are ORed by Tuleap, so one query suffices
        assert query == {"change_request": ["1002"], "change_request_status": ["1180", "1182"]}
        return [
            {"id": 1, "title": "CR A", "values": _cr_value(1180, "Open")},
            {"id": 2, "title": "CR B", "values": _cr_value(1182, "Accepted")},
        ]

    mock_client.get_paginated.side_effect = fake_get_paginated

    result = await search_change_requests(mock_client, tracker_id=67, status=["Open", "Accepted"])

    assert [r["id"] for r in result["results"]] == [1, 2]
    mock_client.get_paginated.assert_called_once()


@pytest.mark.asyncio
async def test_search_change_requests_includes_approved_budget():
    mock_client = AsyncMock(spec=TuleapClient)
    mock_client.get.return_value = _tracker_with_budget_field()
    mock_client.get_paginated.return_value = [
        {"id": 7, "title": "CR budgeted", "values": _cr_value(1182, "Accepted", approved_hours=8)},
        {"id": 8, "title": "CR unbudgeted", "values": _cr_value(1182, "Accepted", approved_hours=None)},
        {"id": 9, "title": "CR missing field", "values": _cr_value(1182, "Accepted")},
    ]

    result = await search_change_requests(mock_client, tracker_id=67, status=["Accepted"])

    assert result["budget_field"] == "Approved Hours"
    by_id = {r["id"]: r for r in result["results"]}
    assert by_id[7]["approved_budget"] == 8
    assert by_id[8]["approved_budget"] is None
    assert by_id[9]["approved_budget"] is None  # backfilled when value absent
    assert all(r["approved_budget_field"] == "Approved Hours" for r in result["results"])


@pytest.mark.asyncio
async def test_search_change_requests_status_no_match():
    mock_client = AsyncMock(spec=TuleapClient)
    mock_client.get.return_value = _tracker_with_change_request_and_status_field()

    result = await search_change_requests(mock_client, tracker_id=67, status=["Nonexistent"])

    assert result == {"supported": True, "budget_field": None, "results": []}
    mock_client.get_paginated.assert_not_called()


@pytest.mark.asyncio
async def test_search_change_requests_no_status_field_on_tracker():
    mock_client = AsyncMock(spec=TuleapClient)
    mock_client.get.return_value = {
        "fields": [
            {
                "field_id": 3101, "label": "Change Request", "type": "cb", "name": "change_request",
                "values": [{"id": 1002, "label": "Change Request"}],
            },
        ]
    }
    mock_client.get_paginated.return_value = [{"id": 5, "title": "CR Only"}]

    result = await search_change_requests(mock_client, tracker_id=67)

    assert result == {
        "supported": True,
        "budget_field": None,
        "results": [{"id": 5, "title": "CR Only", "change_request": True}],
    }


@pytest.mark.asyncio
async def test_search_change_requests_status_requested_but_tracker_has_no_status_field():
    mock_client = AsyncMock(spec=TuleapClient)
    mock_client.get.return_value = {
        "fields": [
            {
                "field_id": 3101, "label": "Change Request", "type": "cb", "name": "change_request",
                "values": [{"id": 1002, "label": "Change Request"}],
            },
        ]
    }

    result = await search_change_requests(mock_client, tracker_id=67, status=["Accepted"])

    assert result == {"supported": True, "budget_field": None, "results": []}
    mock_client.get_paginated.assert_not_called()


@pytest.mark.asyncio
async def test_search_change_requests_field_has_no_values():
    mock_client = AsyncMock(spec=TuleapClient)
    mock_client.get.return_value = {
        "fields": [
            {"field_id": 3101, "label": "Change Request", "type": "cb", "name": "change_request", "values": []},
        ]
    }

    result = await search_change_requests(mock_client, tracker_id=67)

    assert result == {"supported": True, "budget_field": None, "results": []}
    mock_client.get_paginated.assert_not_called()


@pytest.mark.asyncio
async def test_search_change_requests_field_not_supported():
    mock_client = AsyncMock(spec=TuleapClient)
    mock_client.get.return_value = {
        "fields": [
            {"field_id": 1, "label": "Title", "type": "string"},
            {"field_id": 2, "label": "Status", "type": "sb"},
        ]
    }

    result = await search_change_requests(mock_client, tracker_id=4)

    assert result == {"supported": False, "budget_field": None, "results": []}
    mock_client.get_paginated.assert_not_called()


def test_find_budget_field_label_variants():
    # the three labels observed in production trackers 67, 62, 85 — plus a generic one
    for label in ("Approved Hours", "Accepted effort (h)", "CR hours approved", "Remaining budget"):
        field = _find_budget_field([{"label": label, "type": "float"}])
        assert field and field["label"] == label


def test_find_budget_field_requires_numeric_type():
    assert _find_budget_field([
        {"label": "Approved Hours", "type": "column"},   # layout artifact of the form designer
        {"label": "Approved Hours", "type": "string"},
        {"label": "Estimate: Analysis - IPC", "type": "computed"},  # numeric but not a budget label
    ]) is None


def test_find_change_request_field_skips_layout_fields():
    # tracker 85 has both a 'Change Request' fieldset and the real cb field
    fields = [
        {"field_id": 3711, "label": "Change Request", "type": "fieldset"},
        {"field_id": 3710, "label": "Change Request", "type": "cb", "values": [{"id": 1231, "label": "Change Request"}]},
    ]
    assert _find_change_request_field(fields)["field_id"] == 3710
    assert _find_change_request_field([{"label": "Change Request", "type": "fieldset"}]) is None


def test_find_technical_details_field_skips_layout_fields():
    # tracker 67 (AMAG CP Testing / 04. Tasks) has both a 'Technical Details'
    # fieldset (4120) and the real text field (4121) sharing the same label
    fields = [
        {"field_id": 4120, "label": "Technical Details", "type": "fieldset"},
        {"field_id": 4121, "label": "Technical Details", "type": "text"},
    ]
    assert _find_technical_details_field(fields)["field_id"] == 4121
    assert _find_technical_details_field([{"label": "Technical Details", "type": "fieldset"}]) is None


@pytest.mark.asyncio
async def test_assign_artifact():
    mock_client = AsyncMock(spec=TuleapClient)
    # First get: artifact → tracker_id=10
    # Second get: tracker → fields with assigned_to and user_group
    mock_client.get.side_effect = [
        {"tracker": {"id": 10}},
        {"fields": [
            {"field_id": 20, "name": "assigned_to", "type": "msb", "values": []},
            {"field_id": 30, "name": "user_group_1", "type": "sb", "values": [
                {"ugroup_reference": {"id": "40", "label": "GroupA"}},
                {"ugroup_reference": {"id": "50", "label": "GroupB"}},
            ]},
        ]},
    ]
    # get_paginated: first group has no match, second group contains user 5
    mock_client.get_paginated.side_effect = [
        [{"id": 99}],        # group 40 — user 5 not here
        [{"id": 5}, {"id": 6}],  # group 50 — user 5 found
    ]
    mock_client.put.return_value = None

    await assign_artifact(mock_client, artifact_id=100, user_id=5)

    mock_client.put.assert_called_once_with(
        "artifacts/100",
        json={"values": [
            {"field_id": 20, "bind_value_ids": [5]},
            {"field_id": 30, "bind_value_ids": ["50"]},
        ]},
    )


@pytest.mark.asyncio
async def test_update_artifact():
    client_mock = AsyncMock(spec=TuleapClient)
    client_mock.put.return_value = {"id": 123, "status": "updated"}

    values = [{"field_id": 1, "value": "New Title"}]
    comment = "Doing some work"

    result = await update_artifact(client_mock, 123, values, comment)

    client_mock.put.assert_called_once_with(
        "artifacts/123",
        json={"values": values, "comment": {"body": comment, "format": "html"}},
    )
    assert result == {"id": 123, "status": "updated"}


@pytest.mark.asyncio
async def test_update_artifact_comment_format():
    client_mock = AsyncMock(spec=TuleapClient)
    client_mock.put.return_value = None

    await update_artifact(client_mock, 123, [], "**bold**", comment_format="commonmark")

    client_mock.put.assert_called_once_with(
        "artifacts/123",
        json={"values": [], "comment": {"body": "**bold**", "format": "commonmark"}},
    )


@pytest.mark.asyncio
async def test_update_technical_details_success():
    mock_client = AsyncMock(spec=TuleapClient)
    mock_client.get.side_effect = [
        {"tracker": {"id": 67}},
        {"fields": [
            {"field_id": 4120, "label": "Technical Details", "type": "fieldset"},
            {"field_id": 4121, "label": "Technical Details", "type": "text"},
        ]},
    ]
    mock_client.put.return_value = {"id": 100, "status": "updated"}

    result = await update_technical_details(mock_client, artifact_id=100, text="Uses batch furnace API")

    mock_client.get.assert_any_call("artifacts/100")
    mock_client.get.assert_any_call("trackers/67")
    mock_client.put.assert_called_once_with(
        "artifacts/100",
        json={"values": [{
            "field_id": 4121,
            "value": {"format": "commonmark", "content": "Uses batch furnace API"},
        }]},
    )
    assert result == {"id": 100, "status": "updated"}


@pytest.mark.asyncio
async def test_update_technical_details_custom_format():
    mock_client = AsyncMock(spec=TuleapClient)
    mock_client.get.side_effect = [
        {"tracker": {"id": 67}},
        {"fields": [
            {"field_id": 4121, "label": "Technical Details", "type": "text"},
        ]},
    ]
    mock_client.put.return_value = None

    await update_technical_details(
        mock_client, artifact_id=100, text="<b>bold</b>", text_format="html"
    )

    mock_client.put.assert_called_once_with(
        "artifacts/100",
        json={"values": [{
            "field_id": 4121,
            "value": {"format": "html", "content": "<b>bold</b>"},
        }]},
    )


@pytest.mark.asyncio
async def test_update_technical_details_field_missing():
    mock_client = AsyncMock(spec=TuleapClient)
    mock_client.get.side_effect = [
        {"tracker": {"id": 10}},
        {"fields": [{"field_id": 1, "label": "Title", "type": "string"}]},
    ]

    with pytest.raises(ValueError):
        await update_technical_details(mock_client, artifact_id=100, text="anything")

    mock_client.put.assert_not_called()


@pytest.mark.asyncio
async def test_create_artifact():
    mock_client = AsyncMock(spec=TuleapClient)
    mock_client.post.return_value = {"id": 200, "title": "New Task"}

    values = [{"field_id": 1, "value": "New Task"}]
    result = await create_artifact(mock_client, tracker_id=67, values=values)

    mock_client.post.assert_called_once_with(
        "artifacts", json={"tracker": {"id": 67}, "values": values}
    )
    assert result == {"id": 200, "title": "New Task"}


@pytest.mark.asyncio
async def test_get_project_trackers_slim():
    mock_client = AsyncMock(spec=TuleapClient)
    mock_client.get.return_value = [
        {
            "id": 67, "label": "04. Tasks", "item_name": "tasks", "description": "Tasks",
            "structure": [], "semantics": {},  # bulky keys that must not leak through
            "fields": [
                {"label": "Change Request", "type": "cb", "values": [{"id": 1002, "label": "Change Request"}]},
                {"label": "Approved Hours", "type": "float"},
            ],
        },
        {"id": 19, "label": "Activities", "item_name": "activity", "description": "", "fields": []},
    ]

    result = await get_project_trackers(mock_client, project_id=121)

    mock_client.get.assert_called_once_with("projects/121/trackers")
    assert result == [
        {
            "id": 67, "label": "04. Tasks", "item_name": "tasks", "description": "Tasks",
            "has_change_request_field": True, "change_request_budget_field": "Approved Hours",
        },
        {
            "id": 19, "label": "Activities", "item_name": "activity", "description": "",
            "has_change_request_field": False, "change_request_budget_field": None,
        },
    ]


@pytest.mark.asyncio
async def test_get_project_trackers_full():
    mock_client = AsyncMock(spec=TuleapClient)
    raw = [{"id": 67, "label": "Tasks", "fields": [{"label": "Title", "type": "string"}]}]
    mock_client.get.return_value = raw

    result = await get_project_trackers(mock_client, project_id=103, full=True)

    assert result == raw


@pytest.mark.asyncio
async def test_get_tracker_fields():
    mock_client = AsyncMock(spec=TuleapClient)
    mock_client.get.return_value = {
        "fields": [
            {"field_id": 1, "label": "Title", "type": "string", "required": True, "values": []},
            {"field_id": 2, "label": "Status", "type": "sb", "required": False,
             "values": [{"id": 10, "label": "Open"}, {"id": 11, "label": "Closed"}]},
        ]
    }

    result = await get_tracker_fields(mock_client, tracker_id=67)

    mock_client.get.assert_called_once_with("trackers/67")
    assert result[0] == {"field_id": 1, "label": "Title", "type": "string", "required": True}
    assert result[1]["values"] == [{"id": 10, "label": "Open"}, {"id": 11, "label": "Closed"}]


@pytest.mark.asyncio
async def test_get_artifact_comments():
    mock_client = AsyncMock(spec=TuleapClient)
    mock_client.get_paginated.return_value = [
        {
            "submitted_by_details": {"display_name": "Alice"},
            "submitted_on": "2026-01-01T10:00:00+00:00",
            "last_comment": {"body": "First comment"},
        },
        {
            "submitted_by_details": {"display_name": "Bob"},
            "submitted_on": "2026-01-02T10:00:00+00:00",
            "last_comment": {"body": ""},  # empty — should be skipped
        },
    ]

    result = await get_artifact_comments(mock_client, artifact_id=100)

    mock_client.get_paginated.assert_called_once_with(
        "artifacts/100/changesets", params={"fields": "comments"}
    )
    assert len(result) == 1
    assert result[0] == {
        "submitted_by": "Alice",
        "submitted_on": "2026-01-01T10:00:00+00:00",
        "body": "First comment",
    }


@pytest.mark.asyncio
async def test_get_my_artifacts():
    mock_client = AsyncMock(spec=TuleapClient)
    mock_client.get_paginated.return_value = [
        {"id": 50, "title": "My Task", "values": [{"label": "Status", "value": "Open"}]},
    ]

    result = await get_my_artifacts(mock_client, user_id=5, tracker_id=10)

    mock_client.get_paginated.assert_called_once_with(
        "trackers/10/artifacts",
        params={"values": "all", "query": json.dumps({"assigned_to": {"id": 5}})},
    )
    assert result == [{"id": 50, "title": "My Task", "status": "Open"}]


@pytest.mark.asyncio
async def test_get_my_artifacts_with_status():
    mock_client = AsyncMock(spec=TuleapClient)
    mock_client.get.return_value = {
        "fields": [{"name": "status", "values": [
            {"label": "Open", "id": 10},
            {"label": "Closed", "id": 11},
        ]}]
    }
    mock_client.get_paginated.return_value = [
        {"id": 50, "title": "My Task", "values": [{"label": "Status", "value": "Open"}]},
    ]

    result = await get_my_artifacts(mock_client, user_id=5, tracker_id=10, status=["Open"])

    mock_client.get.assert_called_once_with("trackers/10")
    mock_client.get_paginated.assert_called_once_with(
        "trackers/10/artifacts",
        params={"values": "all", "query": json.dumps({"assigned_to": {"id": 5}, "status": [10]})},
    )
    assert result == [{"id": 50, "title": "My Task", "status": "Open"}]


@pytest.mark.asyncio
async def test_get_my_artifacts_status_case_insensitive():
    mock_client = AsyncMock(spec=TuleapClient)
    mock_client.get.return_value = {
        "fields": [{"name": "status", "values": [{"label": "Open", "id": 10}]}]
    }
    mock_client.get_paginated.return_value = []

    await get_my_artifacts(mock_client, user_id=5, tracker_id=10, status=["open", "OPEN"])

    mock_client.get_paginated.assert_called_once_with(
        "trackers/10/artifacts",
        params={"values": "all", "query": json.dumps({"assigned_to": {"id": 5}, "status": [10, 10]})},
    )


def _make_file_changeset(cs_id, submitted_on, file_id, filename):
    return {
        "id": cs_id,
        "submitted_on": submitted_on,
        "submitted_by_details": {"display_name": "Alice"},
        "last_comment": {"body": ""},
        "values": [
            {
                "type": "file",
                "file_descriptions": [{"id": file_id, "name": filename, "size": 1024, "type": "application/pdf", "description": "", "html_url": f"/plugins/tracker/attachments/{file_id}-{filename}"}],
            }
        ],
    }


@pytest.mark.asyncio
async def test_get_artifact_attachments_all():
    mock_client = AsyncMock(spec=TuleapClient)
    mock_client.get_paginated.return_value = [
        _make_file_changeset(1, "2026-01-01T10:00:00+00:00", 10, "a.pdf"),
        _make_file_changeset(2, "2026-01-02T10:00:00+00:00", 11, "b.pdf"),
    ]

    result = await get_artifact_attachments(mock_client, artifact_id=100)

    assert len(result) == 2
    assert result[0]["file_id"] == 11  # sorted newest first
    assert result[1]["file_id"] == 10
    assert "html_url" in result[0]


@pytest.mark.asyncio
async def test_get_artifact_attachments_last_n_changesets():
    mock_client = AsyncMock(spec=TuleapClient)
    mock_client.get_paginated.return_value = [
        _make_file_changeset(1, "2026-01-01T10:00:00+00:00", 10, "a.pdf"),
        _make_file_changeset(2, "2026-01-02T10:00:00+00:00", 11, "b.pdf"),
        _make_file_changeset(3, "2026-01-03T10:00:00+00:00", 12, "c.pdf"),
    ]

    result = await get_artifact_attachments(mock_client, artifact_id=100, last_n_changesets=2)

    assert len(result) == 2
    assert {r["file_id"] for r in result} == {11, 12}


@pytest.mark.asyncio
async def test_get_artifact_attachments_last_n_files():
    mock_client = AsyncMock(spec=TuleapClient)
    mock_client.get_paginated.return_value = [
        _make_file_changeset(1, "2026-01-01T10:00:00+00:00", 10, "a.pdf"),
        _make_file_changeset(2, "2026-01-02T10:00:00+00:00", 11, "b.pdf"),
        _make_file_changeset(3, "2026-01-03T10:00:00+00:00", 12, "c.pdf"),
    ]

    result = await get_artifact_attachments(mock_client, artifact_id=100, last_n_files=2)

    assert len(result) == 2
    assert result[0]["file_id"] == 12  # newest first
    assert result[1]["file_id"] == 11


@pytest.mark.asyncio
async def test_get_artifact_attachments_combined():
    mock_client = AsyncMock(spec=TuleapClient)
    mock_client.get_paginated.return_value = [
        _make_file_changeset(1, "2026-01-01T10:00:00+00:00", 10, "a.pdf"),
        _make_file_changeset(2, "2026-01-02T10:00:00+00:00", 11, "b.pdf"),
        _make_file_changeset(3, "2026-01-03T10:00:00+00:00", 12, "c.pdf"),
    ]

    result = await get_artifact_attachments(mock_client, artifact_id=100, last_n_changesets=2, last_n_files=1)

    assert len(result) == 1
    assert result[0]["file_id"] == 12


@pytest.mark.asyncio
async def test_get_artifact_attachments_dedup():
    mock_client = AsyncMock(spec=TuleapClient)
    # Same file_id 10 appears in two changesets
    mock_client.get_paginated.return_value = [
        _make_file_changeset(1, "2026-01-01T10:00:00+00:00", 10, "a.pdf"),
        _make_file_changeset(2, "2026-01-02T10:00:00+00:00", 10, "a.pdf"),
    ]

    result = await get_artifact_attachments(mock_client, artifact_id=100)

    assert len(result) == 1
    assert result[0]["file_id"] == 10


@pytest.mark.asyncio
async def test_download_artifact_attachment(tmp_path):
    mock_client = AsyncMock(spec=TuleapClient)
    fake_response = MagicMock()
    fake_response.headers = {
        "content-disposition": 'attachment; filename="report.pdf"',
        "content-type": "application/pdf",
    }
    fake_response.content = b"%PDF-fake-content"
    mock_client.download.return_value = fake_response

    save_path = str(tmp_path / "report.pdf")
    result = await download_artifact_attachment(mock_client, file_id=456, save_path=save_path)

    mock_client.download.assert_called_once_with("artifact_files/456")
    assert result["saved_to"] == save_path
    assert result["size_bytes"] == len(b"%PDF-fake-content")
    assert open(save_path, "rb").read() == b"%PDF-fake-content"


@pytest.mark.asyncio
async def test_download_artifact_attachment_direct(tmp_path):
    mock_client = AsyncMock(spec=TuleapClient)
    mock_client.download_binary.return_value = b"\x89PNG-binary-data"

    save_path = str(tmp_path / "image.png")
    result = await download_artifact_attachment(
        mock_client,
        file_id=4198,
        save_path=save_path,
        html_url="/plugins/tracker/attachments/4198-image.png",
    )

    mock_client.download_binary.assert_called_once_with("/plugins/tracker/attachments/4198-image.png")
    mock_client.download.assert_not_called()
    assert result["size_bytes"] == len(b"\x89PNG-binary-data")
    assert open(save_path, "rb").read() == b"\x89PNG-binary-data"


@pytest.mark.asyncio
async def test_upload_artifact_attachment(tmp_path):
    test_file = tmp_path / "report.pdf"
    test_file.write_bytes(b"%PDF-content")

    mock_client = AsyncMock(spec=TuleapClient)
    mock_client.post.return_value = {"id": 9999, "name": "report.pdf", "size": 12}

    result = await upload_artifact_attachment(mock_client, str(test_file), description="Q1 report")

    import base64
    expected_b64 = base64.b64encode(b"%PDF-content").decode()
    mock_client.post.assert_called_once_with(
        "artifact_temporary_files",
        json={
            "name": "report.pdf",
            "mimetype": "application/pdf",
            "content": expected_b64,
            "offset": 1,
            "description": "Q1 report",
        },
    )
    assert result == {"file_id": 9999, "name": "report.pdf", "size_bytes": 12}
