"""Tests for LunaTaskClient.get_tasks()."""
# pyright: reportPrivateUsage=false

from __future__ import annotations

from typing import Any

import pytest
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import (
    LunaTaskAPIError,
    LunaTaskAuthenticationError,
    LunaTaskRateLimitError,
)
from lunatask_mcp.api.models import TaskResponse
from lunatask_mcp.config import ServerConfig
from tests.test_api_client_common import DEFAULT_API_URL, INVALID_TOKEN, VALID_TOKEN


class TestLunaTaskClientGetTasks:
    """Test get_tasks method for retrieving all tasks."""

    @pytest.mark.asyncio
    async def test_get_tasks_success_with_data(self, mocker: MockerFixture) -> None:
        """Test successful get_tasks request with task data."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        # Mock successful response with tasks wrapped in API format
        mock_response_data: dict[str, list[dict[str, Any]]] = {
            "tasks": [
                {
                    "id": "task-1",
                    "area_id": "area-1",
                    "status": "open",
                    "priority": 1,
                    "due_date": "2025-08-20T10:00:00Z",
                    "created_at": "2025-08-19T10:00:00Z",
                    "updated_at": "2025-08-19T10:00:00Z",
                    "source": {"type": "manual", "value": "user_created"},
                },
                {
                    "id": "task-2",
                    "area_id": None,
                    "status": "completed",
                    "priority": None,
                    "due_date": None,
                    "created_at": "2025-08-18T10:00:00Z",
                    "updated_at": "2025-08-19T09:00:00Z",
                    "source": None,
                },
            ]
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.get_tasks()

        expected_task_count = 2
        assert len(result) == expected_task_count
        assert all(isinstance(task, TaskResponse) for task in result)
        assert result[0].id == "task-1"
        assert result[0].status == "open"
        assert result[0].priority == 1
        assert result[1].id == "task-2"
        assert result[1].status == "completed"
        assert result[1].priority is None
        mock_request.assert_called_once_with("GET", "tasks")

    @pytest.mark.asyncio
    async def test_get_tasks_success_empty_list(self, mocker: MockerFixture) -> None:
        """Test successful get_tasks request with empty task list."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value={"tasks": []},
        )

        result = await client.get_tasks()

        assert result == []
        mock_request.assert_called_once_with("GET", "tasks")

    @pytest.mark.asyncio
    async def test_get_tasks_handles_missing_encrypted_fields(self, mocker: MockerFixture) -> None:
        """Test get_tasks gracefully handles absence of encrypted fields (name, note)."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        # Response without encrypted fields (name, note) as expected from E2E encryption
        mock_response_data: dict[str, list[dict[str, Any]]] = {
            "tasks": [
                {
                    "id": "task-1",
                    "status": "open",
                    "created_at": "2025-08-19T10:00:00Z",
                    "updated_at": "2025-08-19T10:00:00Z",
                    # Note: 'name' and 'note' fields intentionally missing
                }
            ]
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.get_tasks()

        assert len(result) == 1
        assert result[0].id == "task-1"
        assert result[0].status == "open"
        # Encrypted fields should not be present in the model
        assert not hasattr(result[0], "name")
        assert not hasattr(result[0], "note")
        mock_request.assert_called_once_with("GET", "tasks")

    @pytest.mark.asyncio
    async def test_get_tasks_authentication_error(self, mocker: MockerFixture) -> None:
        """Test get_tasks handles authentication error."""
        config = ServerConfig(
            lunatask_bearer_token=INVALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskAuthenticationError(),
        )

        with pytest.raises(LunaTaskAuthenticationError):
            await client.get_tasks()

    @pytest.mark.asyncio
    async def test_get_tasks_rate_limit_error(self, mocker: MockerFixture) -> None:
        """Test get_tasks handles rate limit error."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskRateLimitError(),
        )

        with pytest.raises(LunaTaskRateLimitError):
            await client.get_tasks()

    @pytest.mark.asyncio
    async def test_get_tasks_with_pagination_params(self, mocker: MockerFixture) -> None:
        """Test get_tasks accepts and forwards pagination/filter parameters."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value={"tasks": []},
        )

        # Test with optional pagination/filter parameters
        await client.get_tasks(limit=10, offset=20, status="open")

        # "open" is a composite status not forwarded upstream; verify it's removed
        mock_request.assert_called_once_with("GET", "tasks", params={"limit": 10, "offset": 20})

    @pytest.mark.asyncio
    async def test_task_response_missing_additional_fields(self, mocker: MockerFixture) -> None:
        """Test TaskResponse model fails with additional fields from actual API."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        # Mock response with additional fields that should be in TaskResponse
        mock_response_data: dict[str, list[dict[str, Any]]] = {
            "tasks": [
                {
                    "id": "task-1",
                    "status": "open",
                    "created_at": "2025-08-19T10:00:00Z",
                    "updated_at": "2025-08-19T10:00:00Z",
                    "goal_id": "goal-123",
                    "estimate": 60,  # Duration in minutes
                    "motivation": "must",
                    "eisenhower": 2,  # Quadrant 2: Important, not urgent
                    "previous_status": "todo",
                    "progress": 25,
                    "scheduled_on": "2025-08-20",
                    "completed_at": "2025-08-19T15:30:00Z",
                }
            ]
        }

        mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        # This should now pass since we added the additional fields to TaskResponse
        result = await client.get_tasks()

        # Verify the task was parsed successfully with new fields
        expected_estimate_minutes = 60
        expected_eisenhower_quadrant = 2

        assert len(result) == 1
        assert result[0].id == "task-1"
        assert result[0].goal_id == "goal-123"
        assert result[0].estimate == expected_estimate_minutes
        assert result[0].motivation == "must"
        assert result[0].eisenhower == expected_eisenhower_quadrant

    @pytest.mark.asyncio
    async def test_get_tasks_key_error_during_item_parse(self, mocker: MockerFixture) -> None:
        """Force KeyError inside item parsing to hit KeyError branch."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        mock_response_data: dict[str, list[dict[str, Any]]] = {
            "tasks": [
                {
                    "id": "task-1",
                    "status": "open",
                    "created_at": "2025-08-21T10:00:00Z",
                    "updated_at": "2025-08-21T10:00:00Z",
                }
            ]
        }

        mocker.patch.object(client, "make_request", return_value=mock_response_data)
        # Patch constructor used in client module to raise KeyError
        mocker.patch("lunatask_mcp.api.client.TaskResponse", side_effect=KeyError("boom"))

        with pytest.raises(LunaTaskAPIError):
            await client.get_tasks()

    @pytest.mark.asyncio
    async def test_get_tasks_general_exception_during_item_parse(
        self, mocker: MockerFixture
    ) -> None:
        """Invalid items cause validation failure -> general Exception branch."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        mock_response_data: dict[str, list[dict[str, Any]]] = {
            "tasks": [
                {
                    "id": "task-2",
                    "status": "open",
                    # created_at / updated_at missing intentionally
                }
            ]
        }

        mocker.patch.object(client, "make_request", return_value=mock_response_data)

        with pytest.raises(LunaTaskAPIError) as exc_info:
            await client.get_tasks()

        assert "endpoint=tasks" in str(exc_info.value)
