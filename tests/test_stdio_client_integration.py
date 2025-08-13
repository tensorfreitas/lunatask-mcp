"""Integration tests for stdio client functionality.

This module contains integration tests that verify the ping tool functionality
using a real FastMCP client configured with stdio transport. These tests fulfill
the acceptance criteria for client-server communication over stdio.
"""

import asyncio
import logging
import sys
from typing import Any

import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from fastmcp.exceptions import ToolError


class TestStdioClientIntegration:
    """Integration test cases for stdio client functionality."""

    @pytest.mark.asyncio
    async def test_ping_functionality(self) -> None:
        """Test the ping tool functionality with the MCP server (AC: 5, 10).

        This test verifies:
        - Client can connect via stdio transport
        - Server capabilities can be read
        - Ping tool exists and can be called
        - Ping/pong response cycle works correctly
        """
        logger = logging.getLogger(__name__)

        # Create stdio transport to launch the server
        transport = StdioTransport(command="python", args=["-m", "lunatask_mcp.main"])
        client = Client(transport)

        async with client:
            logger.info("Connected to MCP server via stdio transport")

            # Test server capabilities first (AC: 18)
            logger.info("Checking server capabilities...")
            tools = await client.list_tools()
            logger.info("Available tools: %s", [tool.name for tool in tools])

            # Verify ping tool is available
            ping_tool_available = any(tool.name == "ping" for tool in tools)
            assert ping_tool_available, "Ping tool not found in server capabilities"

            logger.info("✓ Ping tool found in server capabilities")

            # Test basic ping functionality (AC: 5)
            logger.info("Testing ping method...")
            ping_result = await client.ping()
            assert ping_result, "Ping method failed"

            logger.info("✓ Ping method successful")

            # Test ping tool call (AC: 5, 10)
            logger.info("Testing ping tool call...")
            result = await client.call_tool("ping", {})

            # Verify pong response - FastMCP returns a CallToolResult with content
            response_text: str = "No response"

            # FastMCP CallToolResult has a content list with various content types
            result_any: Any = result
            content_list = getattr(result_any, "content", None)

            if content_list:
                # Look for text content in the content list
                for content_item in content_list:
                    text_value = getattr(content_item, "text", None)
                    if text_value is not None:
                        # This is a TextContent item
                        response_text = str(text_value)
                        break
                else:
                    # No text content found, convert first item to string
                    response_text = str(content_list[0])
            else:
                # Fallback: convert entire result to string
                response_text = str(result_any)

            assert "pong" in response_text.lower(), f"Expected 'pong' in response: {response_text}"
            logger.info("✓ Ping tool responded with: %s", response_text)

    @pytest.mark.asyncio
    async def test_protocol_version_handling(self) -> None:
        """Test client behavior with protocol version negotiation (AC: 14)."""
        logger = logging.getLogger(__name__)

        transport = StdioTransport(command="python", args=["-m", "lunatask_mcp.main"])
        client = Client(transport)

        async with client:
            # Check initialization result for protocol version
            init_result = client.initialize_result
            assert hasattr(init_result, "protocolVersion"), (
                "No protocol version in initialization result"
            )

            protocol_version = init_result.protocolVersion
            logger.info("Protocol version negotiated: %s", protocol_version)

            # Verify it's the expected version (AC: 14)
            assert protocol_version == "2025-06-18", (
                f"Unexpected protocol version: {protocol_version}"
            )
            logger.info("✓ Protocol version negotiation successful")

    @pytest.mark.asyncio
    async def test_graceful_capability_handling(self) -> None:
        """Test that the client handles capability mismatches gracefully (AC: 18)."""
        logger = logging.getLogger(__name__)

        transport = StdioTransport(command="python", args=["-m", "lunatask_mcp.main"])
        client = Client(transport)

        async with client:
            # Test calling a non-existent tool
            logger.info("Testing call to non-existent tool...")
            with pytest.raises(ToolError) as exc_info:
                await client.call_tool("nonexistent_tool", {})

            logger.info(
                "✓ Properly handled call to non-existent tool: %s",
                type(exc_info.value).__name__,
            )

            # Test proper tool verification before calling
            tools = await client.list_tools()
            tool_names = [tool.name for tool in tools]

            assert "ping" in tool_names, "Ping tool not found in capabilities"
            logger.info("✓ Client verified tool existence before calling")

            # Test valid tool call after verification
            await client.call_tool("ping", {})
            logger.info("✓ Valid tool call succeeded after capability check")


def setup_logging() -> None:
    """Configure logging to stderr for test output."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        stream=sys.stderr,
    )


async def run_integration_tests() -> None:
    """Main function to run all integration tests independently.

    This function allows the integration tests to be run as a standalone script
    for manual testing while still being compatible with pytest.
    """
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting LunaTask MCP stdio client integration tests...")

    test_instance = TestStdioClientIntegration()

    try:
        # Run ping functionality test
        logger.info("Running ping functionality test...")
        await test_instance.test_ping_functionality()
        logger.info("✓ Ping functionality test passed")

        # Run protocol version test
        logger.info("Running protocol version test...")
        await test_instance.test_protocol_version_handling()
        logger.info("✓ Protocol version test passed")

        # Run capability handling test
        logger.info("Running capability handling test...")
        await test_instance.test_graceful_capability_handling()
        logger.info("✓ Capability handling test passed")

        logger.info("🎉 All integration tests passed!")

    except Exception:
        logger.exception("❌ Integration tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_integration_tests())
