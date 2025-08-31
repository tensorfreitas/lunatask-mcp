"""Tests for TaskTools single task resource implementation.

This module contains tests for the TaskTools class that provides
MCP resource for retrieving a single LunaTask task.
"""

from datetime import UTC, datetime

import pytest
from fastmcp import FastMCP
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import (
    LunaTaskAPIError,
    LunaTaskAuthenticationError,
    LunaTaskBadRequestError,
    LunaTaskNotFoundError,
    LunaTaskRateLimitError,
    LunaTaskServerError,
    LunaTaskTimeoutError,
)
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.tasks import TaskTools
from tests.factories import create_source, create_task_response


class TestSingleTaskResource:
    """Test the single task resource template lunatask://tasks/{task_id}."""

    def test_single_task_resource_registration(self, mocker: MockerFixture) -> None:
        """Test that TaskTools registers the lunatask://tasks/{task_id} resource template."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        # Mock the resource registration
        mock_resource = mocker.patch.object(mcp, "resource")

        TaskTools(mcp, client)

        # Verify both resources were registered
        mock_resource.assert_any_call("lunatask://tasks")
        mock_resource.assert_any_call("lunatask://tasks/{task_id}")
        expected_resource_count = 2
        assert mock_resource.call_count == expected_resource_count

    @pytest.mark.asyncio
    async def test_get_task_resource_success(self, mocker: MockerFixture) -> None:
        """Test successful single task retrieval from the resource template."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()
        mock_ctx.session_id = "test-session-456"

        # Create sample task data
        sample_task = create_task_response(
            task_id="task-123",
            status="open",
            created_at=datetime(2025, 8, 20, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 20, 10, 30, 0, tzinfo=UTC),
            priority=2,
            due_date=datetime(2025, 8, 25, 14, 30, 0, tzinfo=UTC),
            area_id="area-456",
            source=create_source("manual", "user_created"),
        )

        # Mock the client's get_task method
        mock_get_task = mocker.patch.object(client, "get_task", return_value=sample_task)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Call the resource method with task_id parameter
        result = await task_tools.get_task_resource(mock_ctx, task_id="task-123")

        # Verify the result structure
        assert result["resource_type"] == "lunatask_task"
        assert result["task_id"] == "task-123"

        task_data = result["task"]
        assert task_data["id"] == "task-123"
        assert task_data["status"] == "open"
        expected_priority = 2
        assert task_data["priority"] == expected_priority
        assert task_data["due_date"] == "2025-08-25T14:30:00+00:00"
        assert task_data["created_at"] == "2025-08-20T10:00:00+00:00"
        assert task_data["updated_at"] == "2025-08-20T10:30:00+00:00"
        assert task_data["area_id"] == "area-456"
        assert task_data["source"]["type"] == "manual"
        assert task_data["source"]["value"] == "user_created"

        # Verify metadata
        metadata = result["metadata"]
        assert metadata["retrieved_at"] == "test-session-456"
        assert "E2E encryption" in metadata["encrypted_fields_note"]

        # Verify context logging calls
        mock_ctx.info.assert_any_call("Retrieving task task-123 from LunaTask API")
        mock_ctx.info.assert_any_call("Successfully retrieved task task-123 from LunaTask")
        mock_get_task.assert_called_once_with("task-123")

    @pytest.mark.asyncio
    async def test_get_task_resource_minimal_data(self, mocker: MockerFixture) -> None:
        """Test single task resource with minimal task data."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Create task with minimal data
        minimal_task = create_task_response(
            task_id="task-minimal",
            status="completed",
            created_at=datetime(2025, 8, 18, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 19, 9, 0, 0, tzinfo=UTC),
        )

        mocker.patch.object(client, "get_task", return_value=minimal_task)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await task_tools.get_task_resource(mock_ctx, task_id="task-minimal")

        task_data = result["task"]
        assert task_data["id"] == "task-minimal"
        assert task_data["status"] == "completed"
        assert task_data["priority"] is None
        assert task_data["due_date"] is None
        assert task_data["area_id"] is None
        assert task_data["source"] is None

    @pytest.mark.asyncio
    async def test_get_task_resource_not_found_error(self, mocker: MockerFixture) -> None:
        """Test single task resource handles TaskNotFoundError (404)."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock task not found error

        not_found_error = LunaTaskNotFoundError("Task not found")
        mocker.patch.object(client, "get_task", side_effect=not_found_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Should re-raise the not found error
        with pytest.raises(LunaTaskNotFoundError) as exc_info:
            await task_tools.get_task_resource(mock_ctx, task_id="nonexistent-task")

        assert exc_info.value is not_found_error
        mock_ctx.error.assert_called_once()
        error_call_msg = mock_ctx.error.call_args[0][0]
        assert "Task nonexistent-task not found" in error_call_msg

    @pytest.mark.asyncio
    async def test_get_task_resource_authentication_error(self, mocker: MockerFixture) -> None:
        """Test single task resource handles authentication error."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="invalid_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock authentication error
        auth_error = LunaTaskAuthenticationError("Authentication failed")
        mocker.patch.object(client, "get_task", side_effect=auth_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Should re-raise the authentication error
        with pytest.raises(LunaTaskAuthenticationError) as exc_info:
            await task_tools.get_task_resource(mock_ctx, task_id="task-123")

        assert exc_info.value is auth_error
        mock_ctx.error.assert_called_once()
        error_call_msg = mock_ctx.error.call_args[0][0]
        assert (
            "Failed to retrieve task task-123: Invalid or expired LunaTask API credentials"
            in error_call_msg
        )

    @pytest.mark.asyncio
    async def test_get_task_resource_rate_limit_error(self, mocker: MockerFixture) -> None:
        """Test single task resource handles rate limit error."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock rate limit error
        rate_limit_error = LunaTaskRateLimitError("Rate limit exceeded")
        mocker.patch.object(client, "get_task", side_effect=rate_limit_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Should re-raise the rate limit error
        with pytest.raises(LunaTaskRateLimitError) as exc_info:
            await task_tools.get_task_resource(mock_ctx, task_id="task-123")

        assert exc_info.value is rate_limit_error
        mock_ctx.error.assert_called_once()
        error_call_msg = mock_ctx.error.call_args[0][0]
        assert (
            "Failed to retrieve task task-123: LunaTask API rate limit exceeded" in error_call_msg
        )

    @pytest.mark.asyncio
    async def test_get_task_resource_server_error(self, mocker: MockerFixture) -> None:
        """Test single task resource handles server error."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock server error
        server_error = LunaTaskServerError("Internal server error", 500)
        mocker.patch.object(client, "get_task", side_effect=server_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Should re-raise the server error
        with pytest.raises(LunaTaskServerError) as exc_info:
            await task_tools.get_task_resource(mock_ctx, task_id="task-123")

        assert exc_info.value is server_error
        mock_ctx.error.assert_called_once()
        error_call_msg = mock_ctx.error.call_args[0][0]
        assert "Failed to retrieve task task-123: LunaTask server error (500)" in error_call_msg

    @pytest.mark.asyncio
    async def test_get_task_resource_timeout_error(self, mocker: MockerFixture) -> None:
        """Test single task resource handles timeout error."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock timeout error
        timeout_error = LunaTaskTimeoutError("Request timeout")
        mocker.patch.object(client, "get_task", side_effect=timeout_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Should re-raise the timeout error
        with pytest.raises(LunaTaskTimeoutError) as exc_info:
            await task_tools.get_task_resource(mock_ctx, task_id="task-123")

        assert exc_info.value is timeout_error
        mock_ctx.error.assert_called_once()
        error_call_msg = mock_ctx.error.call_args[0][0]
        assert (
            "Failed to retrieve task task-123: Request to LunaTask API timed out" in error_call_msg
        )

    @pytest.mark.asyncio
    async def test_get_task_resource_unexpected_error(self, mocker: MockerFixture) -> None:
        """Test single task resource handles unexpected errors."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock unexpected error
        unexpected_error = ValueError("Unexpected error")
        mocker.patch.object(client, "get_task", side_effect=unexpected_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Should wrap in LunaTaskAPIError
        with pytest.raises(LunaTaskAPIError) as exc_info:
            await task_tools.get_task_resource(mock_ctx, task_id="task-123")

        assert exc_info.value.__cause__ is unexpected_error
        mock_ctx.error.assert_called_once()
        error_call_msg = mock_ctx.error.call_args[0][0]
        assert "Unexpected error retrieving task task-123" in error_call_msg

    @pytest.mark.asyncio
    async def test_get_task_resource_empty_task_id(self, mocker: MockerFixture) -> None:
        """Test single task resource with empty task_id parameter."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock client methods (should not be called due to early validation)
        mock_get_task = mocker.patch.object(client, "get_task")
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Should raise bad request error for empty task_id
        with pytest.raises(LunaTaskBadRequestError) as exc_info:
            await task_tools.get_task_resource(mock_ctx, task_id="")

        # Verify defensive validation caught empty task_id
        assert str(exc_info.value) == "Task ID cannot be empty"
        mock_ctx.error.assert_called_once_with("Empty or invalid task_id parameter provided")

        # Client should not have been called due to early validation
        mock_get_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_task_resource_special_characters_in_id(self, mocker: MockerFixture) -> None:
        """Test single task resource with special characters in task_id."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Create task with special characters in ID
        special_task = create_task_response(
            task_id="task-with-special/chars",
            status="open",
            created_at=datetime(2025, 8, 20, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 20, 10, 30, 0, tzinfo=UTC),
        )

        mocker.patch.object(client, "get_task", return_value=special_task)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await task_tools.get_task_resource(mock_ctx, task_id="task-with-special/chars")

        assert result["task_id"] == "task-with-special/chars"
        assert result["task"]["id"] == "task-with-special/chars"

    @pytest.mark.asyncio
    async def test_get_task_resource_handles_missing_encrypted_fields(
        self, mocker: MockerFixture
    ) -> None:
        """Test that single task resource gracefully handles absence of encrypted fields."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Create task without encrypted fields (as expected from E2E encryption)
        encrypted_task = create_task_response(
            task_id="task-encrypted",
            status="open",
            created_at=datetime(2025, 8, 20, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 20, 10, 30, 0, tzinfo=UTC),
        )

        mocker.patch.object(client, "get_task", return_value=encrypted_task)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await task_tools.get_task_resource(mock_ctx, task_id="task-encrypted")

        task_data = result["task"]
        assert task_data["id"] == "task-encrypted"
        assert task_data["status"] == "open"
        # Encrypted fields should not be present
        assert "name" not in task_data
        assert "note" not in task_data

        # Metadata should note encryption
        assert "E2E encryption" in result["metadata"]["encrypted_fields_note"]
