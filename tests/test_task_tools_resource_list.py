"""Tests for TaskTools list resource implementation.

This module contains tests for the TaskTools class that provides
MCP resource for retrieving lists of LunaTask tasks.
"""

from datetime import UTC, date, datetime
from typing import cast

import pytest
from fastmcp import Context, FastMCP
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import (
    LunaTaskAPIError,
    LunaTaskAuthenticationError,
    LunaTaskRateLimitError,
    LunaTaskServerError,
    LunaTaskTimeoutError,
)
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.tasks import TaskTools
from tests.factories import create_source, create_task_response


class TestTaskResourceRetrieval:
    """Test the get_tasks_resource method."""

    @pytest.mark.asyncio
    async def test_get_tasks_resource_success(self, mocker: MockerFixture) -> None:
        """Test successful task retrieval from the resource."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()
        mock_ctx.session_id = "test-session-123"

        # Create sample task data
        sample_task = create_task_response(
            task_id="task-1",
            status="open",
            created_at=datetime(2025, 8, 20, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 20, 10, 30, 0, tzinfo=UTC),
            priority=1,
            scheduled_on=date(2025, 8, 25),
            area_id="area-1",
            source=create_source("manual", "user_created"),
        )

        # Mock the client's get_tasks method
        mock_get_tasks = mocker.patch.object(client, "get_tasks", return_value=[sample_task])
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Call the resource method
        result = await task_tools.get_tasks_resource(mock_ctx)

        # Verify the result structure
        assert result["resource_type"] == "lunatask_tasks"
        assert result["total_count"] == 1
        assert len(result["tasks"]) == 1

        task_data = result["tasks"][0]
        assert task_data["id"] == "task-1"
        assert task_data["status"] == "open"
        assert task_data["priority"] == 1
        assert task_data["scheduled_on"] == "2025-08-25"
        assert task_data["created_at"] == "2025-08-20T10:00:00+00:00"
        assert task_data["updated_at"] == "2025-08-20T10:30:00+00:00"
        assert task_data["area_id"] == "area-1"
        assert task_data["source"]["type"] == "manual"
        assert task_data["source"]["value"] == "user_created"

        # Verify metadata
        metadata = result["metadata"]
        assert metadata["retrieved_at"] == "test-session-123"
        assert "E2E encryption" in metadata["encrypted_fields_note"]

        # Verify context logging calls
        mock_ctx.info.assert_any_call("Retrieving tasks from LunaTask API")
        mock_ctx.info.assert_any_call("Successfully retrieved 1 tasks from LunaTask")
        mock_get_tasks.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_tasks_resource_empty_list(self, mocker: MockerFixture) -> None:
        """Test resource with empty task list."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()
        mock_ctx.session_id = "test-session-123"

        # Mock empty task list
        mocker.patch.object(client, "get_tasks", return_value=[])
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await task_tools.get_tasks_resource(mock_ctx)

        assert result["resource_type"] == "lunatask_tasks"
        assert result["total_count"] == 0
        assert result["tasks"] == []
        mock_ctx.info.assert_any_call("Successfully retrieved 0 tasks from LunaTask")

    @pytest.mark.asyncio
    async def test_get_tasks_resource_lunatask_api_error(self, mocker: MockerFixture) -> None:
        """Test resource handling of LunaTask API errors."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock API error
        api_error = LunaTaskAPIError("Authentication failed", 401)
        mocker.patch.object(client, "get_tasks", side_effect=api_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Should re-raise the API error
        with pytest.raises(LunaTaskAPIError) as exc_info:
            await task_tools.get_tasks_resource(mock_ctx)

        assert exc_info.value is api_error
        mock_ctx.error.assert_called_once()
        assert "Failed to retrieve tasks from LunaTask API" in mock_ctx.error.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_tasks_resource_unexpected_error(self, mocker: MockerFixture) -> None:
        """Test resource handling of unexpected errors."""
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
        mocker.patch.object(client, "get_tasks", side_effect=unexpected_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Should wrap in LunaTaskAPIError
        with pytest.raises(LunaTaskAPIError) as exc_info:
            await task_tools.get_tasks_resource(mock_ctx)

        assert exc_info.value.__cause__ is unexpected_error
        mock_ctx.error.assert_called_once()
        assert "Unexpected error retrieving tasks" in mock_ctx.error.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_tasks_resource_with_null_optional_fields(
        self, mocker: MockerFixture
    ) -> None:
        """Test resource handles tasks with null optional fields."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Create task with null optional fields
        sample_task = create_task_response(
            task_id="task-2",
            status="completed",
            created_at=datetime(2025, 8, 18, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 8, 19, 9, 0, 0, tzinfo=UTC),
        )

        mocker.patch.object(client, "get_tasks", return_value=[sample_task])
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await task_tools.get_tasks_resource(mock_ctx)

        task_data = result["tasks"][0]
        assert task_data["id"] == "task-2"
        assert task_data["status"] == "completed"
        assert task_data["priority"] is None
        assert task_data["scheduled_on"] is None
        assert task_data["area_id"] is None
        assert task_data["source"] is None

    @pytest.mark.asyncio
    async def test_get_tasks_resource_metadata_defaults_without_session_id(
        self, mocker: MockerFixture
    ) -> None:
        """Metadata 'retrieved_at' defaults to 'unknown' without session_id (AC: 10)."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Context without a session_id attribute; info/error remain awaitable
        class Ctx:
            async def info(self, _: str) -> None:
                """Stub."""
                return

            async def error(self, _: str) -> None:
                """Stub."""
                return

        mock_ctx = Ctx()

        # Return an empty task list; focus is on metadata default
        mocker.patch.object(client, "get_tasks", return_value=[])
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await task_tools.get_tasks_resource(cast(Context, mock_ctx))
        assert result["metadata"]["retrieved_at"] == "unknown"


class TestTaskResourceErrorHandling:
    """Test comprehensive error handling in TaskTools resource methods."""

    @pytest.mark.asyncio
    async def test_authentication_error_handling(self, mocker: MockerFixture) -> None:
        """Test proper handling and propagation of authentication errors (401)."""

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
        mocker.patch.object(client, "get_tasks", side_effect=auth_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Should re-raise the authentication error
        with pytest.raises(LunaTaskAuthenticationError) as exc_info:
            await task_tools.get_tasks_resource(mock_ctx)

        assert exc_info.value is auth_error
        mock_ctx.error.assert_called_once()
        error_call_msg = mock_ctx.error.call_args[0][0]
        assert (
            error_call_msg
            == "Failed to retrieve tasks: Invalid or expired LunaTask API credentials"
        )

    @pytest.mark.asyncio
    async def test_rate_limit_error_handling(self, mocker: MockerFixture) -> None:
        """Test proper handling and propagation of rate limit errors (429)."""

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
        mocker.patch.object(client, "get_tasks", side_effect=rate_limit_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Should re-raise the rate limit error
        with pytest.raises(LunaTaskRateLimitError) as exc_info:
            await task_tools.get_tasks_resource(mock_ctx)

        assert exc_info.value is rate_limit_error
        mock_ctx.error.assert_called_once()
        error_call_msg = mock_ctx.error.call_args[0][0]
        assert (
            error_call_msg
            == "Failed to retrieve tasks: LunaTask API rate limit exceeded - please try again later"
        )

    @pytest.mark.asyncio
    async def test_server_error_handling(self, mocker: MockerFixture) -> None:
        """Test proper handling and propagation of server errors (5xx)."""

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
        server_error = LunaTaskServerError("Internal server error", status_code=500)
        mocker.patch.object(client, "get_tasks", side_effect=server_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Should re-raise the server error
        with pytest.raises(LunaTaskServerError) as exc_info:
            await task_tools.get_tasks_resource(mock_ctx)

        assert exc_info.value is server_error
        mock_ctx.error.assert_called_once()
        error_call_msg = mock_ctx.error.call_args[0][0]
        assert (
            error_call_msg
            == "Failed to retrieve tasks: LunaTask server error (500) - please try again"
        )

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, mocker: MockerFixture) -> None:
        """Test proper handling and propagation of timeout errors."""

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
        timeout_error = LunaTaskTimeoutError("Request timeout", status_code=524)
        mocker.patch.object(client, "get_tasks", side_effect=timeout_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Should re-raise the timeout error
        with pytest.raises(LunaTaskTimeoutError) as exc_info:
            await task_tools.get_tasks_resource(mock_ctx)

        assert exc_info.value is timeout_error
        mock_ctx.error.assert_called_once()
        error_call_msg = mock_ctx.error.call_args[0][0]
        assert (
            error_call_msg
            == "Failed to retrieve tasks: Request to LunaTask API timed out - please try again"
        )

    @pytest.mark.asyncio
    async def test_error_logging_uses_ctx_error_method(self, mocker: MockerFixture) -> None:
        """Test that all error scenarios properly use ctx.error for MCP logging."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock a generic API error
        api_error = LunaTaskAPIError("Generic API error", status_code=400)
        mocker.patch.object(client, "get_tasks", side_effect=api_error)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Should re-raise the error
        with pytest.raises(LunaTaskAPIError):
            await task_tools.get_tasks_resource(mock_ctx)

        # Verify ctx.error was called with appropriate message format
        mock_ctx.error.assert_called_once()
        error_call_msg = mock_ctx.error.call_args[0][0]
        assert "Failed to retrieve tasks from LunaTask API:" in error_call_msg
        assert "Generic API error" in error_call_msg
