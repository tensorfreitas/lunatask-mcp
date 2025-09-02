"""Integration test for update_task tool discovery via stdio client."""

import logging
from typing import Any

import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport


class TestStdioUpdateTaskDiscovery:
    """Integration test cases for update_task tool discovery."""

    @pytest.mark.asyncio
    async def test_update_task_tool_discovery(self, temp_config_file: str) -> None:
        """Test that update_task tool is discoverable by MCP clients."""
        logger = logging.getLogger(__name__)

        transport = StdioTransport(
            command="python",
            args=["-m", "lunatask_mcp.main", "--config-file", temp_config_file],
        )
        client = Client(transport)

        async with client:
            logger.info("Testing update_task tool discovery...")

            tools = await client.list_tools()
            tool_names = [tool.name for tool in tools]
            logger.info("Available tools: %s", tool_names)

            assert "update_task" in tool_names, "update_task tool not found in server capabilities"
            logger.info("✓ update_task tool found in capabilities")

            update_task_tool = next(tool for tool in tools if tool.name == "update_task")

            expected_params = {
                "id": True,
                "name": False,
                "note": False,
                "area_id": False,
                "status": False,
                "priority": False,
                "due_date": False,
            }

            input_schema = update_task_tool.inputSchema
            properties: dict[str, Any] = input_schema.get("properties", {}) if input_schema else {}
            required_fields: set[str] = (
                set(input_schema.get("required", [])) if input_schema else set()
            )

            for param_name, is_required in expected_params.items():
                assert param_name in properties, (
                    f"Parameter '{param_name}' not found in tool schema"
                )
                if is_required:
                    assert param_name in required_fields, (
                        f"Required parameter '{param_name}' not in required fields"
                    )
                else:
                    assert param_name not in required_fields, (
                        f"Optional parameter '{param_name}' incorrectly marked as required"
                    )

            logger.info("✓ update_task tool has correct parameter schema")
            logger.info("✓ Tool discovery test completed successfully")
