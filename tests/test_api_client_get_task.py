"""Tests for LunaTaskClient.get_task()."""
# pyright: reportPrivateUsage=false

from __future__ import annotations

from typing import Any

import pytest
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import (
    LunaTaskAPIError,
    LunaTaskAuthenticationError,
    LunaTaskBadRequestError,
    LunaTaskNetworkError,
    LunaTaskNotFoundError,
    LunaTaskRateLimitError,
    LunaTaskServerError,
    LunaTaskTimeoutError,
)
from lunatask_mcp.api.models import TaskResponse
from lunatask_mcp.config import ServerConfig
from tests.test_api_client_common import DEFAULT_API_URL, INVALID_TOKEN, VALID_TOKEN


class TestLunaTaskClientGetTask:
    """Test get_task method for retrieving a single task."""

    @pytest.mark.asyncio
    async def test_get_task_success_with_data(self, mocker: MockerFixture) -> None:
        """Test successful get_task request with complete task data."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)
        task_id = "task-123"

        # Mock successful response with task data
        mock_response_data: dict[str, Any] = {
            "task": {
                "id": "task-123",
                "area_id": "area-456",
                "status": "later",
                "priority": 2,
                "motivation": "want",
                "eisenhower": 1,
                "scheduled_on": "2025-08-25",
                "created_at": "2025-08-20T10:00:00Z",
                "updated_at": "2025-08-20T11:00:00Z",
                "source": {"type": "manual", "value": "user_created"},
            }
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.get_task(task_id)

        assert isinstance(result, TaskResponse)
        assert result.id == "task-123"
        assert result.area_id == "area-456"
        assert result.status == "later"
        expected_priority = 2
        assert result.priority == expected_priority
        assert result.scheduled_on is not None
        assert result.scheduled_on.isoformat() == "2025-08-25"
        assert result.source is not None
        assert result.source.type == "manual"
        assert result.source.value == "user_created"
        mock_request.assert_called_once_with("GET", "tasks/task-123")

    @pytest.mark.asyncio
    async def test_get_task_success_minimal_data(self, mocker: MockerFixture) -> None:
        """Test successful get_task request with minimal task data."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)
        task_id = "task-minimal"

        # Mock response with minimal required fields
        mock_response_data: dict[str, Any] = {
            "task": {
                "id": "task-minimal",
                "area_id": "area-minimal",
                "status": "completed",
                "priority": 0,
                "motivation": "unknown",
                "eisenhower": 0,
                "created_at": "2025-08-20T10:00:00Z",
                "updated_at": "2025-08-20T10:00:00Z",
                "scheduled_on": None,
                "source": None,
            }
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.get_task(task_id)

        assert isinstance(result, TaskResponse)
        assert result.id == "task-minimal"
        assert result.status == "completed"
        assert result.area_id == "area-minimal"
        assert result.priority == 0
        assert result.scheduled_on is None
        assert result.source is None
        mock_request.assert_called_once_with("GET", "tasks/task-minimal")

    @pytest.mark.asyncio
    async def test_get_task_handles_missing_encrypted_fields(self, mocker: MockerFixture) -> None:
        """Test get_task gracefully handles absence of encrypted fields (name, note)."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)
        task_id = "task-encrypted"

        # Response without encrypted fields (name, note) as expected from E2E encryption
        mock_response_data: dict[str, Any] = {
            "task": {
                "id": "task-encrypted",
                "area_id": "area-encrypted",
                "status": "started",
                "priority": 1,
                "motivation": "should",
                "eisenhower": 2,
                "created_at": "2025-08-20T10:00:00Z",
                "updated_at": "2025-08-20T10:00:00Z",
                # Note: 'name' and 'note' fields intentionally missing due to E2E encryption
            }
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.get_task(task_id)

        assert isinstance(result, TaskResponse)
        assert result.id == "task-encrypted"
        assert result.status == "started"
        # Encrypted fields should not be present in the model
        assert not hasattr(result, "name")
        assert not hasattr(result, "note")
        mock_request.assert_called_once_with("GET", "tasks/task-encrypted")

    @pytest.mark.asyncio
    async def test_get_task_not_found_error(self, mocker: MockerFixture) -> None:
        """Test get_task handles task not found (404) error."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)
        task_id = "nonexistent-task"

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskNotFoundError(),
        )

        with pytest.raises(LunaTaskNotFoundError):
            await client.get_task(task_id)

    @pytest.mark.asyncio
    async def test_get_task_authentication_error(self, mocker: MockerFixture) -> None:
        """Test get_task handles authentication error."""
        config = ServerConfig(
            lunatask_bearer_token=INVALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)
        task_id = "task-123"

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskAuthenticationError(),
        )

        with pytest.raises(LunaTaskAuthenticationError):
            await client.get_task(task_id)

    @pytest.mark.asyncio
    async def test_get_task_rate_limit_error(self, mocker: MockerFixture) -> None:
        """Test get_task handles rate limit error."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)
        task_id = "task-123"

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskRateLimitError(),
        )

        with pytest.raises(LunaTaskRateLimitError):
            await client.get_task(task_id)

    @pytest.mark.asyncio
    async def test_get_task_server_error(self, mocker: MockerFixture) -> None:
        """Test get_task handles server error."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)
        task_id = "task-123"

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskServerError("Server error", 500),
        )

        with pytest.raises(LunaTaskServerError):
            await client.get_task(task_id)

    @pytest.mark.asyncio
    async def test_get_task_network_error(self, mocker: MockerFixture) -> None:
        """Test get_task handles network error."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)
        task_id = "task-123"

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskNetworkError(),
        )

        with pytest.raises(LunaTaskNetworkError):
            await client.get_task(task_id)

    @pytest.mark.asyncio
    async def test_get_task_timeout_error(self, mocker: MockerFixture) -> None:
        """Test get_task handles timeout error."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)
        task_id = "task-123"

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskTimeoutError(),
        )

        with pytest.raises(LunaTaskTimeoutError):
            await client.get_task(task_id)

    @pytest.mark.asyncio
    async def test_get_task_parsing_error(self, mocker: MockerFixture) -> None:
        """Test get_task handles JSON parsing error."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)
        task_id = "task-123"

        # Mock response with invalid data that cannot be parsed into TaskResponse
        mock_response_data = {"invalid": "data", "missing": "required_fields"}

        mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        with pytest.raises(LunaTaskAPIError):
            await client.get_task(task_id)

    @pytest.mark.asyncio
    async def test_get_task_rate_limiter_applied(self, mocker: MockerFixture) -> None:
        """Test that rate limiter is applied to get_task requests."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
            rate_limit_rpm=60,
            rate_limit_burst=10,
        )
        client = LunaTaskClient(config)
        task_id = "task-123"

        # Mock successful task response
        mock_response_data: dict[str, Any] = {
            "task": {
                "id": "task-123",
                "area_id": "area-123",
                "status": "next",
                "priority": 1,
                "motivation": "must",
                "eisenhower": 3,
                "created_at": "2025-08-20T10:00:00Z",
                "updated_at": "2025-08-20T10:00:00Z",
            }
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        await client.get_task(task_id)

        # Verify make_request was called (which applies rate limiting)
        mock_request.assert_called_once_with("GET", "tasks/task-123")

    @pytest.mark.asyncio
    async def test_get_task_empty_string_id(self, mocker: MockerFixture) -> None:
        """Test get_task with empty string task_id."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)
        task_id = ""

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskBadRequestError(),
        )

        with pytest.raises(LunaTaskBadRequestError):
            await client.get_task(task_id)

        mock_request.assert_called_once_with("GET", "tasks/")

    @pytest.mark.asyncio
    async def test_get_task_special_characters_in_id(self, mocker: MockerFixture) -> None:
        """Test get_task with special characters in task_id."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)
        task_id = "task-with-special/chars"

        mock_response_data: dict[str, Any] = {
            "task": {
                "id": "task-with-special/chars",
                "area_id": "area-special",
                "status": "waiting",
                "priority": -1,
                "motivation": "want",
                "eisenhower": 4,
                "created_at": "2025-08-20T10:00:00Z",
                "updated_at": "2025-08-20T10:00:00Z",
            }
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.get_task(task_id)

        assert result.id == "task-with-special/chars"
        mock_request.assert_called_once_with("GET", "tasks/task-with-special/chars")

    @pytest.mark.asyncio
    async def test_get_task_parsing_validation_error(self, mocker: MockerFixture) -> None:
        """Provide malformed 'task' payload to trigger general parse error path."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)
        task_id = "task-parse-error"

        mock_response_data: dict[str, Any] = {
            "task": {
                "id": task_id,
                "status": "started",
                # missing created_at / updated_at - these are required fields
            }
        }

        mocker.patch.object(client, "make_request", return_value=mock_response_data)

        with pytest.raises(LunaTaskAPIError) as exc_info:
            await client.get_task(task_id)

        assert f"endpoint=tasks/{task_id}" in str(exc_info.value)
