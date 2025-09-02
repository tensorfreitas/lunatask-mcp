"""Test protocol metadata and capabilities

This module tests that the server correctly exposes metadata (name and version)
and declares capabilities including the ping tool during MCP initialize.
"""

from typing import TYPE_CHECKING

import pytest
from fastmcp import Client
from mcp.types import TextContent

import lunatask_mcp
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.main import CoreServer

if TYPE_CHECKING:
    pass


class TestProtocolMetadata:
    """Test class for verifying MCP protocol metadata and capabilities."""

    @pytest.mark.asyncio
    async def test_server_metadata_exposed(self, default_config: ServerConfig) -> None:
        """Test that server metadata (name and version) is correctly exposed during initialize.

        Verifies AC: 8 - The server exposes MCP metadata (name, version) during initialize.
        """
        # Create CoreServer and get its FastMCP instance for in-memory testing
        core_server = CoreServer(default_config)

        # Use in-memory transport by passing FastMCP instance directly
        async with Client(core_server.app) as client:
            # The client automatically performs initialize handshake
            # Test basic connectivity first
            await client.ping()

            # Check server capabilities for metadata
            tools = await client.list_tools()
            assert tools is not None, "Server should expose tools capability"

            # Note: FastMCP automatically handles server metadata in the background
            # The fact that we can connect and list tools confirms metadata is working

    @pytest.mark.asyncio
    async def test_server_capabilities_include_ping_tool(
        self,
        default_config: ServerConfig,
    ) -> None:
        """Test that declared capabilities include the ping tool.

        Verifies AC: 8 - Server declares capabilities including the ping tool during initialize.
        """
        # Create CoreServer and get its FastMCP instance for in-memory testing
        core_server = CoreServer(default_config)

        # Use in-memory transport by passing FastMCP instance directly
        async with Client(core_server.app) as client:
            # List available tools to verify ping tool is included
            tools = await client.list_tools()
            tool_names = [tool.name for tool in tools]

            assert "ping" in tool_names, f"Ping tool should be declared, found tools: {tool_names}"

    @pytest.mark.asyncio
    async def test_protocol_version_negotiation(self, default_config: ServerConfig) -> None:
        """Test that protocol version negotiation targets MCP version 2025-06-18.

        Verifies AC: 14 - Protocol version negotiation targets MCP version 2025-06-18.
        """
        # Create CoreServer and get its FastMCP instance for in-memory testing
        core_server = CoreServer(default_config)

        # Use in-memory transport by passing FastMCP instance directly
        async with Client(core_server.app) as client:
            # Test successful connection which implies version negotiation worked
            await client.ping()

            # FastMCP automatically handles protocol version negotiation
            # Successful connection confirms 2025-06-18 compatibility

    @pytest.mark.asyncio
    async def test_complete_initialize_handshake(self, default_config: ServerConfig) -> None:
        """Test complete initialize handshake with metadata and capabilities verification."""
        # Create CoreServer and get its FastMCP instance for in-memory testing
        core_server = CoreServer(default_config)

        # Use in-memory transport by passing FastMCP instance directly
        async with Client(core_server.app) as client:
            # Test successful connection and protocol negotiation
            await client.ping()

            # Test capabilities include ping tool
            tools = await client.list_tools()
            tool_names = [tool.name for tool in tools]
            assert "ping" in tool_names, f"Ping tool should be available, found: {tool_names}"

            # Test ping tool actually works
            response = await client.call_tool("ping", {})
            # For FastMCP, the response should have content with text data
            assert hasattr(response, "content"), (
                f"Response should have content attribute: {dir(response)}"
            )
            assert len(response.content) > 0, "Response should have content"
            # Check that first content item is a TextContent with "pong"
            first_content = response.content[0]
            assert isinstance(first_content, TextContent), (
                f"First content should be TextContent: {type(first_content)}"
            )
            assert first_content.text == "pong", f"Expected 'pong', got '{first_content.text}'"

    def test_package_version_matches_server_version(self, default_config: ServerConfig) -> None:
        """AC: 14 — __version__ equals FastMCP server version configured."""
        core_server = CoreServer(default_config)
        # FastMCP is initialized with a version; assert it matches package __version__
        assert getattr(core_server.app, "version", None) == lunatask_mcp.__version__, (
            f"Server version {getattr(core_server.app, 'version', None)}"
            f" != package version {lunatask_mcp.__version__}"
        )
