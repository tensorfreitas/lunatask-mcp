"""Tests for TaskTools delete task tool implementation.

This module contains tests for the TaskTools class that provides
MCP tool for deleting LunaTask tasks.
"""

import pytest
from fastmcp import FastMCP
from pydantic import HttpUrl
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
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.tasks import TaskTools


class TestDeleteTaskTool:
    """Test suite for TaskTools.delete_task_tool() method."""

    @pytest.mark.asyncio
    async def test_delete_task_tool_success(self, mocker: MockerFixture) -> None:
        """Test successful task deletion."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock successful deletion
        client_mock = mocker.patch.object(client, "delete_task", return_value=True)

        result = await task_tools.delete_task_tool(mock_ctx, id="delete-task-123")

        # Verify the result structure
        assert result["success"] is True
        assert result["task_id"] == "delete-task-123"
        assert result["message"] == "Task deleted successfully"

        # Verify client was called
        client_mock.assert_called_once_with("delete-task-123")

    @pytest.mark.asyncio
    async def test_delete_task_tool_not_found_error_404(self, mocker: MockerFixture) -> None:
        """Test delete_task tool handles TaskNotFoundError correctly."""
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
        mocker.patch.object(
            client, "delete_task", side_effect=LunaTaskNotFoundError("Task not found")
        )

        result = await task_tools.delete_task_tool(mock_ctx, id="nonexistent-task")

        # Verify error response
        assert result["success"] is False
        assert result["error"] == "not_found_error"
        assert "Task not found" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_task_tool_authentication_error_401(self, mocker: MockerFixture) -> None:
        """Test delete_task tool handles authentication errors correctly."""
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
        mocker.patch.object(
            client, "delete_task", side_effect=LunaTaskAuthenticationError("Invalid bearer token")
        )

        result = await task_tools.delete_task_tool(mock_ctx, id="auth-task-123")

        # Verify error response
        assert result["success"] is False
        assert result["error"] == "authentication_error"
        assert "Invalid bearer token" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_task_tool_rate_limit_error_429(self, mocker: MockerFixture) -> None:
        """Test delete_task tool handles rate limit errors correctly."""
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
        mocker.patch.object(
            client, "delete_task", side_effect=LunaTaskRateLimitError("Rate limit exceeded")
        )

        result = await task_tools.delete_task_tool(mock_ctx, id="rate-limited-task")

        # Verify error response
        assert result["success"] is False
        assert result["error"] == "rate_limit_error"
        assert "Rate limit exceeded" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_task_tool_server_error_500(self, mocker: MockerFixture) -> None:
        """Test delete_task tool handles server errors correctly."""
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
        mocker.patch.object(
            client, "delete_task", side_effect=LunaTaskServerError("Internal server error")
        )

        result = await task_tools.delete_task_tool(mock_ctx, id="server-error-task")

        # Verify error response
        assert result["success"] is False
        assert result["error"] == "server_error"
        assert "Internal server error" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_task_tool_timeout_error(self, mocker: MockerFixture) -> None:
        """Test delete_task tool handles timeout errors correctly."""
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
        mocker.patch.object(
            client, "delete_task", side_effect=LunaTaskTimeoutError("Request timeout")
        )

        result = await task_tools.delete_task_tool(mock_ctx, id="timeout-task")

        # Verify error response
        assert result["success"] is False
        assert result["error"] == "timeout_error"
        assert "Request timeout" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_task_tool_generic_api_error(self, mocker: MockerFixture) -> None:
        """Test delete_task tool handles generic API errors correctly."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock generic API error
        mocker.patch.object(
            client, "delete_task", side_effect=LunaTaskAPIError("Generic API error")
        )

        result = await task_tools.delete_task_tool(mock_ctx, id="api-error-task")

        # Verify error response
        assert result["success"] is False
        assert result["error"] == "api_error"
        assert "Generic API error" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_task_tool_empty_task_id_validation(self, mocker: MockerFixture) -> None:
        """Test delete_task tool validates empty task_id parameter."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock client method (should not be called)
        client_mock = mocker.patch.object(client, "delete_task")

        result = await task_tools.delete_task_tool(mock_ctx, id="")

        # Verify error response
        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "Task ID cannot be empty" in result["message"]

        # Verify client was not called due to validation error
        client_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_task_tool_whitespace_only_task_id_validation(
        self, mocker: MockerFixture
    ) -> None:
        """Test delete_task tool validates whitespace-only task_id parameter."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock client method (should not be called)
        client_mock = mocker.patch.object(client, "delete_task")

        result = await task_tools.delete_task_tool(mock_ctx, id="   ")

        # Verify error response
        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "Task ID cannot be empty" in result["message"]

        # Verify client was not called due to validation error
        client_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_task_tool_unexpected_error(self, mocker: MockerFixture) -> None:
        """Test delete_task tool handles unexpected errors correctly."""
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
        mocker.patch.object(client, "delete_task", side_effect=Exception("Unexpected error"))

        result = await task_tools.delete_task_tool(mock_ctx, id="unexpected-error-task")

        # Verify error response
        assert result["success"] is False
        assert result["error"] == "unexpected_error"
        assert "Unexpected error" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_task_tool_non_idempotent_behavior(self, mocker: MockerFixture) -> None:
        """Test delete_task tool non-idempotent behavior - second delete returns error."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        task_id = "already-deleted-task"

        # First call succeeds
        mocker.patch.object(client, "delete_task", return_value=True)

        result = await task_tools.delete_task_tool(mock_ctx, id=task_id)
        assert result["success"] is True

        # Second call fails with not found error
        mocker.patch.object(
            client, "delete_task", side_effect=LunaTaskNotFoundError("Task not found")
        )

        result = await task_tools.delete_task_tool(mock_ctx, id=task_id)
        assert result["success"] is False
        assert result["error"] == "not_found_error"
