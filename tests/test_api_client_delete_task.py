"""Tests for LunaTaskClient.delete_task()."""
# pyright: reportPrivateUsage=false

from __future__ import annotations

import pytest
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import (
    LunaTaskAuthenticationError,
    LunaTaskBadRequestError,
    LunaTaskNetworkError,
    LunaTaskNotFoundError,
    LunaTaskRateLimitError,
    LunaTaskServerError,
    LunaTaskTimeoutError,
)
from lunatask_mcp.config import ServerConfig
from tests.test_api_client_common import DEFAULT_API_URL, INVALID_TOKEN, VALID_TOKEN


class TestLunaTaskClientDeleteTask:
    """Test suite for LunaTaskClient.delete_task() method."""

    @pytest.mark.asyncio
    async def test_delete_task_success_204_response(self, mocker: MockerFixture) -> None:
        """Test successful task deletion with 204 No Content response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-to-delete"

        # Mock 204 response (No Content - empty response)
        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value={},  # 204 responses return empty dict
        )

        result = await client.delete_task(task_id)

        assert result is True
        mock_request.assert_called_once_with("DELETE", "tasks/task-to-delete")

    @pytest.mark.asyncio
    async def test_delete_task_not_found_error_404(self, mocker: MockerFixture) -> None:
        """Test delete_task raises LunaTaskNotFoundError on 404 response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "nonexistent-task"

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskNotFoundError("Task not found"),
        )

        with pytest.raises(LunaTaskNotFoundError, match="Task not found"):
            await client.delete_task(task_id)

        mock_request.assert_called_once_with("DELETE", "tasks/nonexistent-task")

    @pytest.mark.asyncio
    async def test_delete_task_authentication_error_401(self, mocker: MockerFixture) -> None:
        """Test delete_task raises LunaTaskAuthenticationError on 401 response."""
        config = ServerConfig(
            lunatask_bearer_token=INVALID_TOKEN, lunatask_base_url=DEFAULT_API_URL
        )
        client = LunaTaskClient(config)

        task_id = "task-123"

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskAuthenticationError("Invalid token"),
        )

        with pytest.raises(LunaTaskAuthenticationError, match="Invalid token"):
            await client.delete_task(task_id)

        mock_request.assert_called_once_with("DELETE", "tasks/task-123")

    @pytest.mark.asyncio
    async def test_delete_task_rate_limit_error_429(self, mocker: MockerFixture) -> None:
        """Test delete_task raises LunaTaskRateLimitError on 429 response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-rate-limited"

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskRateLimitError("Rate limit exceeded"),
        )

        with pytest.raises(LunaTaskRateLimitError, match="Rate limit exceeded"):
            await client.delete_task(task_id)

        mock_request.assert_called_once_with("DELETE", "tasks/task-rate-limited")

    @pytest.mark.asyncio
    async def test_delete_task_server_error_500(self, mocker: MockerFixture) -> None:
        """Test delete_task raises LunaTaskServerError on 500 response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-server-error"

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskServerError("Internal server error"),
        )

        with pytest.raises(LunaTaskServerError, match="Internal server error"):
            await client.delete_task(task_id)

        mock_request.assert_called_once_with("DELETE", "tasks/task-server-error")

    @pytest.mark.asyncio
    async def test_delete_task_timeout_error(self, mocker: MockerFixture) -> None:
        """Test delete_task raises LunaTaskTimeoutError on network timeout."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-timeout"

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskTimeoutError("Request timeout"),
        )

        with pytest.raises(LunaTaskTimeoutError, match="Request timeout"):
            await client.delete_task(task_id)

        mock_request.assert_called_once_with("DELETE", "tasks/task-timeout")

    @pytest.mark.asyncio
    async def test_delete_task_network_error(self, mocker: MockerFixture) -> None:
        """Test delete_task raises LunaTaskNetworkError on network error."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-network-error"

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskNetworkError("Network error"),
        )

        with pytest.raises(LunaTaskNetworkError, match="Network error"):
            await client.delete_task(task_id)

        mock_request.assert_called_once_with("DELETE", "tasks/task-network-error")

    @pytest.mark.asyncio
    async def test_delete_task_empty_string_id(self, mocker: MockerFixture) -> None:
        """Test delete_task with empty string task_id."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = ""

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskBadRequestError("Invalid task ID"),
        )

        with pytest.raises(LunaTaskBadRequestError):
            await client.delete_task(task_id)

        mock_request.assert_called_once_with("DELETE", "tasks/")

    @pytest.mark.asyncio
    async def test_delete_task_special_characters_in_id(self, mocker: MockerFixture) -> None:
        """Test delete_task with special characters in task_id."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-with-special/chars"

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value={},  # 204 success response
        )

        result = await client.delete_task(task_id)

        assert result is True
        mock_request.assert_called_once_with("DELETE", "tasks/task-with-special/chars")

    @pytest.mark.asyncio
    async def test_delete_task_rate_limiter_integration(self, mocker: MockerFixture) -> None:
        """Test delete_task applies rate limiting before request."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "rate-limited-delete"

        # Mock make_request (which applies rate limiting)
        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value={},  # 204 success response
        )

        result = await client.delete_task(task_id)

        # Verify make_request was called (which applies rate limiting)
        mock_request.assert_called_once_with("DELETE", "tasks/rate-limited-delete")
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_task_non_idempotent_behavior(self, mocker: MockerFixture) -> None:
        """Test delete_task non-idempotent behavior - second delete returns 404."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-already-deleted"

        # First call succeeds (task exists and gets deleted)
        mock_request_success = mocker.patch.object(
            client,
            "make_request",
            return_value={},  # 204 success response
        )

        result = await client.delete_task(task_id)
        assert result is True

        # Second call fails (task no longer exists)
        mock_request_success.side_effect = LunaTaskNotFoundError("Task not found")

        with pytest.raises(LunaTaskNotFoundError):
            await client.delete_task(task_id)
