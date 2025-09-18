"""Tests for LunaTaskClient.update_task()."""
# pyright: reportPrivateUsage=false

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from pydantic import ValidationError
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import (
    LunaTaskAPIError,
    LunaTaskAuthenticationError,
    LunaTaskNotFoundError,
    LunaTaskRateLimitError,
    LunaTaskServerError,
    LunaTaskTimeoutError,
)
from lunatask_mcp.api.models import TaskResponse, TaskUpdate
from lunatask_mcp.config import ServerConfig
from tests.test_api_client_common import (
    DEFAULT_API_URL,
    INVALID_TOKEN,
    TEST_PRIORITY_HIGH,
    VALID_TOKEN,
)


class TestLunaTaskClientUpdateTask:
    """Test suite for LunaTaskClient.update_task() method."""

    @pytest.mark.asyncio
    async def test_update_task_success_single_field(self, mocker: MockerFixture) -> None:
        """Test successful task update with single field change."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-123"
        update_data = TaskUpdate(id=task_id, status="completed")

        mock_response_data: dict[str, Any] = {
            "task": {
                "id": "task-123",
                "area_id": "area-1",
                "status": "completed",
                "priority": 0,
                "created_at": "2025-08-21T10:00:00Z",
                "updated_at": "2025-08-21T11:00:00Z",
            }
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.update_task(task_id, update_data)

        assert result.id == "task-123"
        assert result.status == "completed"
        mock_request.assert_called_once_with(
            "PATCH",
            "tasks/task-123",
            data={"id": task_id, "status": "completed"},
        )

    @pytest.mark.asyncio
    async def test_update_task_success_multiple_fields(self, mocker: MockerFixture) -> None:
        """Test successful task update with multiple field changes."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-456"
        scheduled_on = date(2025, 8, 30)
        update_data = TaskUpdate(
            id=task_id,
            area_id="area-2",
            name="Updated Task Name",
            status="started",
            priority=2,
            scheduled_on=scheduled_on,
        )

        mock_response_data: dict[str, Any] = {
            "task": {
                "id": "task-456",
                "area_id": "area-2",
                "status": "started",
                "priority": 2,
                "scheduled_on": "2025-08-30",
                "created_at": "2025-08-21T10:00:00Z",
                "updated_at": "2025-08-21T11:30:00Z",
            }
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.update_task(task_id, update_data)

        assert result.id == "task-456"
        assert result.status == "started"
        expected_priority = 2
        assert result.priority == expected_priority
        mock_request.assert_called_once_with(
            "PATCH",
            "tasks/task-456",
            data={
                "id": task_id,
                "area_id": "area-2",
                "name": "Updated Task Name",
                "status": "started",
                "priority": 2,
                "scheduled_on": scheduled_on.isoformat(),
            },
        )

    @pytest.mark.asyncio
    async def test_update_task_partial_update_excludes_none(self, mocker: MockerFixture) -> None:
        """Test that only non-None fields are sent in partial update."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-partial"
        # Only set status field in addition to required identifiers
        update_data = TaskUpdate(id=task_id, area_id="area-3", status="completed")

        mock_response_data: dict[str, Any] = {
            "task": {
                "id": "task-partial",
                "area_id": "area-3",
                "status": "completed",
                "priority": 0,
                "created_at": "2025-08-21T10:00:00Z",
                "updated_at": "2025-08-21T11:00:00Z",
            }
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.update_task(task_id, update_data)

        # Verify only expected fields were sent (no None values)
        mock_request.assert_called_once_with(
            "PATCH",
            "tasks/task-partial",
            data={"id": task_id, "area_id": "area-3", "status": "completed"},
        )
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_update_task_handles_204_no_content(self, mocker: MockerFixture) -> None:
        """Test handling of 204 No Content response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-no-content"
        update_data = TaskUpdate(id=task_id, area_id="area-4", status="completed")

        # Mock 204 response which returns minimal data
        mock_response_data: dict[str, Any] = {
            "task": {
                "id": "task-no-content",
                "area_id": "area-4",
                "status": "completed",
                "priority": 0,
                "created_at": "2025-08-21T10:00:00Z",
                "updated_at": "2025-08-21T11:00:00Z",
            }
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.update_task(task_id, update_data)

        assert result.id == "task-no-content"
        assert result.status == "completed"
        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_not_found_error_404(self, mocker: MockerFixture) -> None:
        """Test update_task raises TaskNotFoundError on 404 response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "nonexistent-task"
        update_data = TaskUpdate(id=task_id, area_id="area-x", status="completed")

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskNotFoundError("Task not found"),
        )

        with pytest.raises(LunaTaskNotFoundError, match="Task not found"):
            await client.update_task(task_id, update_data)

        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_validation_error_400(self) -> None:
        """Test update_task model validation rejects invalid status values."""
        # Test that validation error occurs at model creation time (invalid status)
        with pytest.raises(ValidationError):
            TaskUpdate(
                id="invalid",
                area_id="area-invalid",
                status="invalid_status",  # type: ignore[arg-type]
            )

    @pytest.mark.asyncio
    async def test_update_task_authentication_error_401(self, mocker: MockerFixture) -> None:
        """Test update_task raises LunaTaskAuthenticationError on 401 response."""
        config = ServerConfig(
            lunatask_bearer_token=INVALID_TOKEN, lunatask_base_url=DEFAULT_API_URL
        )
        client = LunaTaskClient(config)

        task_id = "task-123"
        update_data = TaskUpdate(id=task_id, area_id="area-auth", status="completed")

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskAuthenticationError("Invalid token"),
        )

        with pytest.raises(LunaTaskAuthenticationError, match="Invalid token"):
            await client.update_task(task_id, update_data)

        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_rate_limit_error_429(self, mocker: MockerFixture) -> None:
        """Test update_task raises LunaTaskRateLimitError on 429 response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-123"
        update_data = TaskUpdate(id=task_id, area_id="area-rl", status="completed")

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskRateLimitError("Rate limit exceeded"),
        )

        with pytest.raises(LunaTaskRateLimitError, match="Rate limit exceeded"):
            await client.update_task(task_id, update_data)

        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_server_error_500(self, mocker: MockerFixture) -> None:
        """Test update_task raises LunaTaskServerError on 500 response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-123"
        update_data = TaskUpdate(id=task_id, area_id="area-timeout", status="completed")

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskServerError("Internal server error"),
        )

        with pytest.raises(LunaTaskServerError, match="Internal server error"):
            await client.update_task(task_id, update_data)

        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_timeout_error(self, mocker: MockerFixture) -> None:
        """Test update_task raises LunaTaskTimeoutError on network timeout."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-123"
        update_data = TaskUpdate(id="id_1123232", status="completed", area_id="area_1")

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskTimeoutError("Request timeout"),
        )

        with pytest.raises(LunaTaskTimeoutError, match="Request timeout"):
            await client.update_task(task_id, update_data)

        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_response_parsing_success(self, mocker: MockerFixture) -> None:
        """Test update_task correctly parses task response with updated fields."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "parse-test-task"
        update_data = TaskUpdate(
            id=task_id,
            area_id="new-area",
            priority=TEST_PRIORITY_HIGH,
        )

        mock_response_data: dict[str, Any] = {
            "task": {
                "id": "parse-test-task",
                "area_id": "new-area",
                "status": "started",
                "priority": TEST_PRIORITY_HIGH,
                "created_at": "2025-08-21T10:00:00Z",
                "updated_at": "2025-08-21T12:00:00Z",
                "sources": [
                    {
                        "source": "api",
                        "source_id": "mcp-update",
                    }
                ],
            }
        }

        mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.update_task(task_id, update_data)

        assert isinstance(result, TaskResponse)
        assert result.id == "parse-test-task"
        assert result.area_id == "new-area"
        assert result.priority == TEST_PRIORITY_HIGH
        assert result.source == "api"
        assert result.source_id == "mcp-update"

    @pytest.mark.asyncio
    async def test_update_task_parsing_error(self, mocker: MockerFixture) -> None:
        """Test update_task handles JSON parsing error."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-123"
        update_data = TaskUpdate(id=task_id, area_id="area-parse", status="completed")

        # Mock response with invalid data that cannot be parsed into TaskResponse
        mock_response_data = {"invalid": "data", "missing": "required_fields"}

        mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        with pytest.raises(LunaTaskAPIError):
            await client.update_task(task_id, update_data)

    @pytest.mark.asyncio
    async def test_update_task_rate_limiter_integration(self, mocker: MockerFixture) -> None:
        """Test update_task applies rate limiting before request."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "rate-limited-update"
        update_data = TaskUpdate(id=task_id, status="completed")

        mock_response_data: dict[str, Any] = {
            "task": {
                "id": "rate-limited-update",
                "area_id": "area-rl-2",
                "status": "completed",
                "priority": 0,
                "created_at": "2025-08-21T10:00:00Z",
                "updated_at": "2025-08-21T11:00:00Z",
            }
        }

        # Mock make_request (which applies rate limiting)
        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.update_task(task_id, update_data)

        # Verify make_request was called (which applies rate limiting)
        mock_request.assert_called_once_with(
            "PATCH",
            "tasks/rate-limited-update",
            data={
                "id": task_id,
                "status": "completed",
            },
        )
        assert result.id == "rate-limited-update"

    @pytest.mark.asyncio
    async def test_update_task_minimal_update_fields(self, mocker: MockerFixture) -> None:
        """Test update_task with only required identifiers sends defaulted fields."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-empty"
        # Create TaskUpdate with required identifiers only
        update_data = TaskUpdate(id=task_id)

        mock_response_data: dict[str, Any] = {
            "task": {
                "id": "task-empty",
                "area_id": "area-empty",
                "status": "later",
                "priority": 0,
                "created_at": "2025-08-21T10:00:00Z",
                "updated_at": "2025-08-21T10:00:00Z",
            }
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.update_task(task_id, update_data)

        # Verify required identifiers were sent (no defaulted fields)
        mock_request.assert_called_once_with(
            "PATCH",
            "tasks/task-empty",
            data={"id": task_id},
        )
        assert result.id == "task-empty"

    @pytest.mark.asyncio
    async def test_update_task_handles_missing_encrypted_fields(
        self, mocker: MockerFixture
    ) -> None:
        """Test update_task handles missing encrypted fields (name, note) in response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-encrypted-update"
        update_data = TaskUpdate(id=task_id, area_id="area-enc", status="completed")

        # Response without encrypted fields (name, note) as expected from E2E encryption
        mock_response_data: dict[str, Any] = {
            "task": {
                "id": "task-encrypted-update",
                "area_id": "area-enc",
                "status": "completed",
                "priority": 0,
                "created_at": "2025-08-21T10:00:00Z",
                "updated_at": "2025-08-21T11:00:00Z",
                # Note: 'name' and 'note' fields intentionally missing
            }
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.update_task(task_id, update_data)

        assert result.id == "task-encrypted-update"
        assert result.status == "completed"
        # Encrypted fields should not be present in the model
        assert not hasattr(result, "name")
        assert not hasattr(result, "note")
        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_special_characters_in_id(self, mocker: MockerFixture) -> None:
        """Test update_task with special characters in task_id."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-with-special/chars"
        update_data = TaskUpdate(id=task_id, area_id="area-special")

        mock_response_data: dict[str, Any] = {
            "task": {
                "id": "task-with-special/chars",
                "area_id": "area-special",
                "status": "completed",
                "priority": 0,
                "created_at": "2025-08-21T10:00:00Z",
                "updated_at": "2025-08-21T11:00:00Z",
            }
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.update_task(task_id, update_data)

        assert result.id == "task-with-special/chars"
        mock_request.assert_called_once_with(
            "PATCH",
            "tasks/task-with-special/chars",
            data={
                "id": task_id,
                "area_id": "area-special",
            },
        )

    @pytest.mark.asyncio
    async def test_update_task_parsing_validation_error_compact(
        self, mocker: MockerFixture
    ) -> None:
        """Malformed 'task' payload triggers general Exception branch (parsing failure)."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)
        task_id = "task-update-parse-error"
        update_data = TaskUpdate(id=task_id, area_id="area-parse-2", status="completed")

        mock_response_data: dict[str, Any] = {"task": {"id": task_id, "status": "completed"}}
        mocker.patch.object(client, "make_request", return_value=mock_response_data)

        with pytest.raises(LunaTaskAPIError) as exc_info:
            await client.update_task(task_id, update_data)

        assert f"endpoint=tasks/{task_id}" in str(exc_info.value)
