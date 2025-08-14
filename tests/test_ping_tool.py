"""Unit tests for the ping tool in the LunaTask MCP server."""

import pytest
from fastmcp import Context
from pytest_mock import MockerFixture

from lunatask_mcp.config import ServerConfig
from lunatask_mcp.main import CoreServer


class TestPingTool:
    """Test cases for the ping health-check tool."""

    @pytest.mark.asyncio
    async def test_core_server_has_ping_tool_registered(self, default_config: ServerConfig) -> None:
        """Test that the ping tool is registered with the FastMCP instance."""
        server = CoreServer(default_config)

        # Check that the ping tool is registered in the FastMCP app
        tools = await server.app.get_tools()
        tool_names = list(tools.keys())
        assert "ping" in tool_names

    @pytest.mark.asyncio
    async def test_ping_tool_returns_pong(
        self,
        default_config: ServerConfig,
        mocker: MockerFixture,
    ) -> None:
        """Test that the ping tool returns 'pong' response."""
        server = CoreServer(default_config)

        # Create a mock context
        mock_context = mocker.Mock(spec=Context)
        mock_context.info = mocker.AsyncMock()

        # Call the ping tool directly
        result = await server.ping_tool(mock_context)

        # Verify the response
        assert result == "pong"

    @pytest.mark.asyncio
    async def test_ping_tool_uses_context_logger(
        self,
        default_config: ServerConfig,
        mocker: MockerFixture,
    ) -> None:
        """Test that the ping tool uses the execution context's scoped logger."""
        server = CoreServer(default_config)

        # Create a mock context with logger
        mock_context = mocker.Mock(spec=Context)
        mock_context.info = mocker.AsyncMock()

        # Call the ping tool
        await server.ping_tool(mock_context)

        # Verify that the context logger was used
        mock_context.info.assert_called_once_with("Ping tool called, returning pong")

    @pytest.mark.asyncio
    async def test_ping_tool_metadata(self, default_config: ServerConfig) -> None:
        """Test that the ping tool has correct metadata."""
        server = CoreServer(default_config)

        # Get tool metadata
        tools = await server.app.get_tools()
        ping_tool = tools["ping"]

        # Verify tool metadata
        assert ping_tool.name == "ping"
        assert ping_tool.description is not None
        assert (
            "health-check" in ping_tool.description.lower()
            or "ping" in ping_tool.description.lower()
        )
