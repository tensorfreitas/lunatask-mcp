"""Tests for TaskTools initialization and registration.

This module contains tests for the TaskTools class initialization and
MCP resource/tool registration.
"""

from fastmcp import FastMCP
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.tasks import TaskTools


class TestTaskToolsInitialization:
    """Test TaskTools initialization and resource registration."""

    def test_task_tools_initialization(self) -> None:
        """Test that TaskTools initializes correctly with MCP and client."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        # Should initialize without error
        task_tools = TaskTools(mcp, client)

        assert task_tools.mcp is mcp
        assert task_tools.lunatask_client is client

    def test_task_tools_registers_resources(self, mocker: MockerFixture) -> None:
        """Test that TaskTools registers both lunatask://tasks resources and all MCP tools."""
        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)

        # Mock the resource and tool registration
        mock_resource = mocker.patch.object(mcp, "resource")
        mock_tool = mocker.patch.object(mcp, "tool")

        TaskTools(mcp, client)

        # Verify both resources were registered
        mock_resource.assert_any_call("lunatask://tasks")
        mock_resource.assert_any_call("lunatask://tasks/{task_id}")
        expected_resource_count = 2
        assert mock_resource.call_count == expected_resource_count

        # Verify all tools were registered
        mock_tool.assert_any_call("create_task")
        mock_tool.assert_any_call("update_task")
        mock_tool.assert_any_call("delete_task")
        expected_tool_count = 3
        assert mock_tool.call_count == expected_tool_count
