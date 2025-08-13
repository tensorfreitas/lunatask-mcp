"""Test suite for client test script functionality."""

from unittest.mock import AsyncMock, Mock

import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport


class TestClientTestScript:
    """Test cases for client test script functionality."""

    def test_stdio_integration_module_exists(self) -> None:
        """Test that the stdio integration test module exists and is importable."""
        try:
            import tests.test_stdio_client_integration  # noqa: F401,PLC0415  # type: ignore[reportUnusedImport]
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
    async def test_ping_tool_invocation_mock(self) -> None:
        """Test ping tool invocation with mocked client."""
        # Mock the client and its methods
        mock_client = AsyncMock(spec=Client)

        # Mock context manager behavior
        mock_context = AsyncMock()
        mock_context.ping.return_value = True
        mock_context.call_tool.return_value = Mock(text="pong")

        # Create a proper mock tool object
        mock_tool = Mock()
        mock_tool.name = "ping"
        mock_tool.description = "Ping health-check tool"
        mock_context.list_tools.return_value = [mock_tool]

        mock_client.__aenter__.return_value = mock_context

        # Simulate the workflow
        async with mock_client as client:  # type: ignore[reportUnknownVariableType]
            # Test capabilities check
            tools = await client.list_tools()  # type: ignore[reportUnknownMemberType,reportUnknownVariableType]
            assert len(tools) == 1  # type: ignore[reportUnknownArgumentType]
            assert tools[0].name == "ping"  # type: ignore[reportUnknownMemberType]

            # Test ping functionality
            ping_result = await client.ping()  # type: ignore[reportUnknownMemberType,reportUnknownVariableType]
            assert ping_result is True

            # Test tool call
            result = await client.call_tool("ping", {})  # type: ignore[reportUnknownMemberType,reportUnknownVariableType]
            assert result.text == "pong"  # type: ignore[reportUnknownMemberType]
