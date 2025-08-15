"""Test suite for client test script functionality."""

from typing import Any, cast

import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from pytest_mock import MockerFixture


class TestClientTestScript:
    """Test cases for client test script functionality."""

    def test_stdio_integration_module_exists(self) -> None:
        """Test that the stdio integration test module exists and is importable."""
        try:
            import tests.test_stdio_client_integration  # noqa: F401,PLC0415  # pyright: ignore[reportUnusedImport]
        except ImportError:
            pytest.fail("tests.test_stdio_client_integration module should be importable")

    @pytest.mark.asyncio
    async def test_stdio_transport_creation(self) -> None:
        """Test that StdioTransport can be created correctly."""
        transport = StdioTransport(command="python", args=["-m", "lunatask_mcp.main"])

        # Verify transport properties
        assert transport.command == "python"
        assert transport.args == ["-m", "lunatask_mcp.main"]

    @pytest.mark.asyncio
    async def test_client_creation_with_stdio_transport(self) -> None:
        """Test that Client can be created with StdioTransport."""
        transport = StdioTransport(command="python", args=["-m", "lunatask_mcp.main"])
        client = Client(transport)

        # Verify client was created
        assert client is not None

    @pytest.mark.asyncio
    async def test_ping_tool_invocation_mock(self, mocker: MockerFixture) -> None:
        """Test ping tool invocation with mocked client."""
        # Mock the client and its methods
        mock_client = mocker.AsyncMock(spec=Client)

        # Mock context manager behavior
        mock_context = mocker.AsyncMock()
        mock_context.ping.return_value = True
        mock_context.call_tool.return_value = mocker.Mock(text="pong")

        # Create a proper mock tool object
        mock_tool = mocker.Mock()
        mock_tool.name = "ping"
        mock_tool.description = "Ping health-check tool"
        mock_context.list_tools.return_value = [mock_tool]

        mock_client.__aenter__.return_value = mock_context

        # Simulate the workflow
        async with cast(Any, mock_client) as client:
            # Use client directly since it's already cast through context manager
            client_any = client

            # Test capabilities check
            tools: list[Any] = await client_any.list_tools()
            assert len(tools) == 1
            assert tools[0].name == "ping"

            # Test ping functionality
            ping_result: bool = await client_any.ping()
            assert ping_result is True

            # Test tool call
            result = await client_any.call_tool("ping", {})
            assert result.text == "pong"
