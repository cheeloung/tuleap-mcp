import json
import pytest
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from tuleap_mcp.tools.trackers import (
    get_artifact_details,
    search_artifacts,
    update_artifact,
    create_artifact,
    get_project_trackers,
    get_tracker_fields,
    get_artifact_comments,
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
async def test_search_artifacts_with_filters():
    mock_client = AsyncMock()
    mock_client.get_paginated.return_value = [
        {"id": 100, "title": "Task A", "values": [{"label": "Status", "value": "Open"}]},
    ]
    filters = {"assigned_to": {"id": 5}}

    result = await search_artifacts(mock_client, tracker_id=5, filters=filters)

    mock_client.get_paginated.assert_called_once_with(
        "trackers/5/artifacts", params={"query": json.dumps(filters)}
    )
    assert result == [{"id": 100, "title": "Task A", "status": "Open"}]


@pytest.mark.asyncio
async def test_search_artifacts_no_filters():
    mock_client = AsyncMock()
    mock_client.get_paginated.return_value = []

    await search_artifacts(mock_client, tracker_id=5)

    mock_client.get_paginated.assert_called_once_with("trackers/5/artifacts", params={})


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
async def test_get_project_trackers():
    mock_client = AsyncMock(spec=TuleapClient)
    mock_client.get.return_value = [{"id": 67, "label": "Tasks"}]

    result = await get_project_trackers(mock_client, project_id=103)

    mock_client.get.assert_called_once_with("projects/103/trackers")
    assert result == [{"id": 67, "label": "Tasks"}]


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
        params={"query": json.dumps({"assigned_to": {"id": 5}})},
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
        params={"query": json.dumps({"assigned_to": {"id": 5}, "status": [10]})},
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
        params={"query": json.dumps({"assigned_to": {"id": 5}, "status": [10, 10]})},
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
