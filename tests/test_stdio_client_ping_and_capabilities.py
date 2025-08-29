"""Integration tests for stdio client ping and capabilities.

This module contains integration tests that verify the ping tool functionality,
protocol negotiation, and capability handling using a real FastMCP client
configured with stdio transport.
"""

import logging
from typing import Any

import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from fastmcp.exceptions import ToolError


class TestStdioClientPingAndCapabilities:
    """Integration tests for ping, protocol, and capability handling."""

    @pytest.mark.asyncio
    async def test_ping_functionality(self, temp_config_file: str) -> None:
        """Test the ping tool functionality with the MCP server (AC: 5, 10).

        This test verifies:
        - Client can connect via stdio transport
        - Server capabilities can be read
        - Ping tool exists and can be called
        - Ping/pong response cycle works correctly
        """
        logger = logging.getLogger(__name__)

        transport = StdioTransport(
            command="python",
            args=["-m", "lunatask_mcp.main", "--config-file", temp_config_file],
        )
        client = Client(transport)

        async with client:
            logger.info("Connected to MCP server via stdio transport")

            logger.info("Checking server capabilities...")
            tools = await client.list_tools()
            logger.info("Available tools: %s", [tool.name for tool in tools])

            ping_tool_available = any(tool.name == "ping" for tool in tools)
            assert ping_tool_available, "Ping tool not found in server capabilities"
            logger.info("✓ Ping tool found in server capabilities")

            logger.info("Testing ping method...")
            ping_result = await client.ping()
            assert ping_result, "Ping method failed"
            logger.info("✓ Ping method successful")

            logger.info("Testing ping tool call...")
            result = await client.call_tool("ping", {})

            response_text: str = "No response"
            result_any: Any = result
            content_list = getattr(result_any, "content", None)

            if content_list:
                for content_item in content_list:
                    text_value = getattr(content_item, "text", None)
                    if text_value is not None:
                        response_text = str(text_value)
                        break
                else:
                    response_text = str(content_list[0])
            else:
                response_text = str(result_any)

            assert "pong" in response_text.lower(), f"Expected 'pong' in response: {response_text}"
            logger.info("✓ Ping tool responded with: %s", response_text)

    @pytest.mark.asyncio
    async def test_protocol_version_handling(self, temp_config_file: str) -> None:
        """Test client behavior with protocol version negotiation (AC: 14)."""
        logger = logging.getLogger(__name__)

        transport = StdioTransport(
            command="python",
            args=["-m", "lunatask_mcp.main", "--config-file", temp_config_file],
        )
        client = Client(transport)

        async with client:
            init_result = client.initialize_result
            assert hasattr(init_result, "protocolVersion"), (
                "No protocol version in initialization result"
            )

            protocol_version = init_result.protocolVersion
            logger.info("Protocol version negotiated: %s", protocol_version)

            assert protocol_version == "2025-06-18", (
                f"Unexpected protocol version: {protocol_version}"
            )
            logger.info("✓ Protocol version negotiation successful")

    @pytest.mark.asyncio
    async def test_graceful_capability_handling(self, temp_config_file: str) -> None:
        """Test that the client handles capability mismatches gracefully (AC: 18)."""
        logger = logging.getLogger(__name__)

        transport = StdioTransport(
            command="python",
            args=["-m", "lunatask_mcp.main", "--config-file", temp_config_file],
        )
        client = Client(transport)

        async with client:
            logger.info("Testing call to non-existent tool...")
            with pytest.raises(ToolError) as exc_info:
                await client.call_tool("nonexistent_tool", {})

            logger.info(
                "✓ Properly handled call to non-existent tool: %s",
                type(exc_info.value).__name__,
            )

            tools = await client.list_tools()
            tool_names = [tool.name for tool in tools]

            assert "ping" in tool_names, "Ping tool not found in capabilities"
            logger.info("✓ Client verified tool existence before calling")

            await client.call_tool("ping", {})
            logger.info("✓ Valid tool call succeeded after capability check")
