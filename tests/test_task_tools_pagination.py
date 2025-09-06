"""Tests for TaskTools pagination and filtering functionality."""

import inspect

import pytest
from fastmcp import FastMCP
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.tasks import TaskTools


class TestTaskToolsPaginationAndFiltering:
    """Test pagination and filtering capabilities in TaskTools."""

    @pytest.mark.asyncio
    async def test_resource_uses_client_pagination_support(self, mocker: MockerFixture) -> None:
        """Test that TaskTools resource leverages LunaTaskClient's pagination support."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        task_tools = TaskTools(mcp, client)

        # Mock context
        mock_ctx = mocker.AsyncMock()

        # Mock the client's get_tasks method to verify it accepts parameters
        mock_get_tasks = mocker.patch.object(client, "get_tasks", return_value=[])
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        # Call the resource method
        await task_tools.get_tasks_resource(mock_ctx)

        # Verify get_tasks was called (currently without parameters at resource level)
        # This confirms the foundation is in place for parameter support
        mock_get_tasks.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_client_pagination_parameter_forwarding(self, mocker: MockerFixture) -> None:
        """Test that LunaTaskClient properly forwards pagination parameters."""
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        # Mock the make_request method to verify parameter forwarding
        mock_make_request = mocker.patch.object(client, "make_request", return_value={"tasks": []})

        # Test pagination parameter forwarding
        await client.get_tasks(limit=50, offset=100, status="open")

        # "open" is composite; ensure it is not forwarded to the upstream API
        mock_make_request.assert_called_once_with(
            "GET", "tasks", params={"limit": 50, "offset": 100}
        )

    @pytest.mark.asyncio
    async def test_client_filters_none_parameters(self, mocker: MockerFixture) -> None:
        """Test that client properly filters out None parameters."""
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        # Mock the make_request method
        mock_make_request = mocker.patch.object(client, "make_request", return_value={"tasks": []})

        # Test with mixed parameters including None values
        await client.get_tasks(limit=25, offset=None, status="completed", priority=None)

        # Verify None parameters were filtered out
        mock_make_request.assert_called_once_with(
            "GET", "tasks", params={"limit": 25, "status": "completed"}
        )

    def test_pagination_api_documentation_compliance(self) -> None:
        """Test that pagination implementation follows API documentation patterns."""

        # This test documents the current state: MCP resources don't support parameters
        # but the underlying client does, enabling future tool implementations

        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        # Verify client method signature supports pagination
        signature = inspect.signature(client.get_tasks)

        # Should accept **params for flexibility
        param_names = list(signature.parameters.keys())
        assert "params" in param_names or any(
            param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values()
        ), "get_tasks should accept **params for pagination/filtering"
