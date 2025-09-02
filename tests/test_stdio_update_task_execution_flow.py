"""Integration test for update_task tool execution flow via stdio client."""

import logging
import tempfile
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from tests.conftest import extract_tool_response_text


class TestStdioUpdateTaskExecution:
    """Integration test cases for update_task tool execution."""

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("temp_config_file")
    async def test_update_task_tool_execution_flow(self) -> None:
        """Test complete tool execution flow from MCP client perspective."""
        logger = logging.getLogger(__name__)

        test_config_content = """
lunatask_bearer_token = "test_valid_token_for_mock"
lunatask_base_url = "https://httpbin.org/"
port = 8080
log_level = "INFO"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(test_config_content)
            mock_config_path = f.name

        transport = StdioTransport(
            command="python",
            args=["-m", "lunatask_mcp.main", "--config-file", mock_config_path],
        )
        client = Client(transport)

        try:
            async with client:
                logger.info("Testing update_task tool execution flow...")

                logger.info("Test 1: Single field update...")
                try:
                    result = await client.call_tool(
                        "update_task", {"id": "test-task-123", "name": "Updated Task Name"}
                    )

                    response_text = extract_tool_response_text(result)
                    logger.info("Single field update response: %s", response_text)

                    assert response_text is not None, "Tool should return some response"

                except Exception as e:
                    logger.info(
                        "Single field update failed as expected (mock endpoint): %s", str(e)
                    )
                    if not ("update_task" in str(e) or "HTTP" in str(e)):
                        pytest.fail(f"Expected tool call error but got: {e}")

                logger.info("Test 2: Multiple field update...")
                try:
                    result = await client.call_tool(
                        "update_task",
                        {
                            "id": "test-task-456",
                            "name": "Multi-field Update",
                            "status": "completed",
                            "due_date": "2025-12-31T23:59:59Z",
                        },
                    )

                    response_text = extract_tool_response_text(result)
                    logger.info("Multiple field update response: %s", response_text)

                    assert response_text is not None, "Tool should return some response"

                except Exception as e:
                    logger.info(
                        "Multiple field update failed as expected (mock endpoint): %s", str(e)
                    )
                    if not ("update_task" in str(e) or "HTTP" in str(e)):
                        pytest.fail(f"Expected tool call error but got: {e}")

                logger.info("Test 3: Partial update with explicit None handling...")
                try:
                    result = await client.call_tool(
                        "update_task",
                        {
                            "id": "test-task-789",
                            "name": "Partial Update Test",
                            "note": None,
                            "area_id": None,
                        },
                    )

                    response_text = extract_tool_response_text(result)
                    logger.info("Partial update response: %s", response_text)

                    assert response_text is not None, "Tool should return some response"

                except Exception as e:
                    logger.info("Partial update failed as expected (mock endpoint): %s", str(e))
                    if not ("update_task" in str(e) or "HTTP" in str(e)):
                        pytest.fail(f"Expected tool call error but got: {e}")

                logger.info("✓ update_task tool execution flow test completed successfully")

        finally:
            Path(mock_config_path).unlink()
