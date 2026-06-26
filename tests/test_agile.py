import pytest
from unittest.mock import AsyncMock
from tuleap_mcp.tools import agile


@pytest.mark.asyncio
async def test_search_projects():
    mock_client = AsyncMock()
    mock_client.get.return_value = [{"id": 1, "shortname": "demo"}]

    result = await agile.search_projects(mock_client)

    mock_client.get.assert_called_once_with("projects", params={"query": '{"is_member_of": true}'})
    assert result == [{"id": 1, "shortname": "demo"}]


@pytest.mark.asyncio
async def test_get_epics():
    mock_client = AsyncMock()
    mock_client.get.return_value = [{"id": 15, "name": "Epics", "item_name": "epic"}]
    mock_client.get_paginated.return_value = [{"id": 200, "title": "Epic 1"}]

    result = await agile.get_epics(mock_client, project_id=1)

    mock_client.get.assert_called_once_with("projects/1/trackers")
    mock_client.get_paginated.assert_called_once_with("trackers/15/artifacts")
    assert result == [{"id": 200, "title": "Epic 1"}]


@pytest.mark.asyncio
async def test_get_user_stories():
    mock_client = AsyncMock()
    mock_client.get.return_value = [{"id": 20, "item_name": "user story"}]
    mock_client.get_paginated.return_value = [{"id": 300, "title": "Story 1"}]

    result = await agile.get_user_stories(mock_client, project_id=1, epic_id=200)

    mock_client.get_paginated.assert_called_once_with(
        "trackers/20/artifacts", params={"query": "parent_id=200"}
    )
    assert result == [{"id": 300, "title": "Story 1"}]


@pytest.mark.asyncio
async def test_create_user_story():
    client_mock = AsyncMock()
    client_mock.get.return_value = [{"id": 42, "item_name": "User Story"}]
    client_mock.post.return_value = {"id": 99, "title": "New Story"}

    values = [{"field_id": 1, "value": "New Story"}]
    result = await agile.create_user_story(client_mock, project_id=1, values=values)

    client_mock.get.assert_called_once_with("projects/1/trackers")
    client_mock.post.assert_called_once_with(
        "artifacts", json={"tracker": {"id": 42}, "values": values}
    )
    assert result == {"id": 99, "title": "New Story"}


@pytest.mark.asyncio
async def test_create_epic():
    client_mock = AsyncMock()
    client_mock.get.return_value = [{"id": 15, "name": "Epics"}]
    client_mock.post.return_value = {"id": 101, "title": "Big Feature"}

    values = [{"field_id": 1, "value": "Big Feature"}]
    result = await agile.create_epic(client_mock, project_id=1, values=values)

    client_mock.get.assert_called_once_with("projects/1/trackers")
    client_mock.post.assert_called_once_with(
        "artifacts", json={"tracker": {"id": 15}, "values": values}
    )
    assert result == {"id": 101, "title": "Big Feature"}


@pytest.mark.asyncio
async def test_link_to_epic():
    client_mock = AsyncMock()
    client_mock.put.return_value = None

    await agile.link_to_epic(client_mock, epic_id=101, child_artifact_id=200)

    client_mock.put.assert_called_once_with(
        "artifacts/200/links",
        json={"all_links": [{"id": 101, "type": "_is_child"}]},
    )


@pytest.mark.asyncio
async def test_get_epic_progress():
    client_mock = AsyncMock()
    client_mock.get.return_value = {
        "id": 101,
        "values": [
            {"label": "Status", "value": "Open"},
            {"label": "Progress", "value": 45},
            {"label": "Remaining Effort", "value": 10},
            {"label": "Total Effort", "value": 22},
        ],
    }

    result = await agile.get_epic_progress(client_mock, epic_id=101)

    assert result["id"] == 101
    assert result["Status"] == "Open"
    assert result["Progress"] == 45
    assert result["Remaining Effort"] == 10


@pytest.mark.asyncio
async def test_get_project_milestones():
    client_mock = AsyncMock()
    client_mock.get_paginated.return_value = [
        {
            "id": 22,
            "label": "02/2023",
            "status_value": "Delivered to customer",
            "semantic_status": "closed",
            "start_date": "2022-12-31",
            "end_date": "2023-02-27",
            "capacity": None,
            "remaining_effort": None,
        }
    ]

    result = await agile.get_project_milestones(client_mock, project_id=103, status="closed")

    client_mock.get_paginated.assert_called_once_with(
        "projects/103/milestones", params={"query": '{"status": "closed"}'}
    )
    assert result == [
        {
            "id": 22,
            "label": "02/2023",
            "status": "Delivered to customer",
            "semantic_status": "closed",
            "start_date": "2022-12-31",
            "end_date": "2023-02-27",
            "capacity": None,
            "remaining_effort": None,
        }
    ]
