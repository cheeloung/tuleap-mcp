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
async def test_link_to_epic():
    client_mock = AsyncMock()
    client_mock.put.return_value = None

    await agile.link_to_epic(client_mock, epic_id=101, child_artifact_id=200)

    client_mock.put.assert_called_once_with(
        "artifacts/200/links",
        json={"all_links": [{"id": 101, "type": "_is_child"}]},
    )


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
