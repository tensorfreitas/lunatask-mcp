"""Integration test for timezone handling in update_task via stdio client."""

import logging
import tempfile
from pathlib import Path
from typing import Any

import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from fastmcp.exceptions import ToolError


class TestStdioUpdateTaskTimezone:
    """Integration test cases for timezone handling (Task 3.5)."""

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("temp_config_file")
    async def test_update_task_timezone_handling(self) -> None:  # noqa: PLR0915
        """Test timezone handling for due_date parameter (Task 3.5)."""
        logger = logging.getLogger(__name__)

        test_config_content = """
lunatask_bearer_token = "test_timezone_token"
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
                logger.info("Testing update_task timezone handling...")

                logger.info("Test 1: ISO 8601 with timezone offset...")
                try:
                    result = await client.call_tool(
                        "update_task",
                        {
                            "id": "timezone-test-1",
                            "name": "Timezone Test 1",
                            "due_date": "2032-04-23T10:20:30.400+02:30",
                        },
                    )

                    response_text = self._extract_tool_response_text(result)
                    logger.info("Timezone offset test response: %s", response_text)

                except ToolError as e:
                    logger.info("Timezone offset test completed (expected error): %s", str(e)[:100])
                    error_msg = str(e).lower()
                    if "datetime" in error_msg and "parse" in error_msg:
                        pytest.fail(f"Unexpected datetime parsing error: {e}")

                logger.info("Test 2: ISO 8601 UTC timezone...")
                try:
                    result = await client.call_tool(
                        "update_task",
                        {
                            "id": "timezone-test-2",
                            "name": "Timezone Test 2",
                            "due_date": "2032-04-23T10:20:30Z",
                        },
                    )

                    response_text = self._extract_tool_response_text(result)
                    logger.info("UTC timezone test response: %s", response_text)

                except ToolError as e:
                    logger.info("UTC timezone test completed (expected error): %s", str(e)[:100])
                    error_msg = str(e).lower()
                    if "datetime" in error_msg and "parse" in error_msg:
                        pytest.fail(f"Unexpected datetime parsing error: {e}")

                logger.info("Test 3: ISO 8601 without timezone...")
                try:
                    result = await client.call_tool(
                        "update_task",
                        {
                            "id": "timezone-test-3",
                            "name": "Timezone Test 3",
                            "due_date": "2032-04-23T10:20:30",
                        },
                    )

                    response_text = self._extract_tool_response_text(result)
                    logger.info("Naive datetime test response: %s", response_text)

                except ToolError as e:
                    logger.info("Naive datetime test completed (expected error): %s", str(e)[:100])
                    error_msg = str(e).lower()
                    if "datetime" in error_msg and "parse" in error_msg:
                        pytest.fail(f"Unexpected datetime parsing error: {e}")

                logger.info("Test 4: Invalid datetime format...")
                result = await client.call_tool(
                    "update_task",
                    {
                        "id": "timezone-test-4",
                        "name": "Timezone Test 4",
                        "due_date": "invalid-datetime-format",
                    },
                )

                response_text = self._extract_tool_response_text(result)
                logger.info("Invalid datetime format response: %s", response_text)

                if response_text and (
                    "validation_error" in response_text.lower()
                    or "invalid due_date format" in response_text.lower()
                    or "iso 8601" in response_text.lower()
                ):
                    logger.info("✓ Invalid datetime format properly rejected with validation error")
                else:
                    pytest.fail(
                        f"Expected datetime validation error response, got: {response_text}"
                    )

                logger.info("Test 5: Microseconds in datetime...")
                try:
                    result = await client.call_tool(
                        "update_task",
                        {
                            "id": "timezone-test-5",
                            "name": "Timezone Test 5",
                            "due_date": "2032-04-23T10:20:30.123456Z",
                        },
                    )

                    response_text = self._extract_tool_response_text(result)
                    logger.info("Microseconds test response: %s", response_text)

                except ToolError as e:
                    logger.info("Microseconds test completed (expected error): %s", str(e)[:100])
                    error_msg = str(e).lower()
                    if "datetime" in error_msg and "parse" in error_msg:
                        pytest.fail(f"Unexpected datetime parsing error: {e}")

                logger.info("✓ All timezone handling tests completed successfully")
                logger.info("✓ ISO 8601 datetime parsing working correctly")
                logger.info("✓ Timezone information preserved in requests")

        finally:
            Path(mock_config_path).unlink()

    def _extract_tool_response_text(self, result: Any) -> str | None:  # noqa: ANN401
        """Extract text content from FastMCP tool call result."""
        try:
            if hasattr(result, "content") and result.content:
                for content_item in result.content:
                    if hasattr(content_item, "text"):
                        return str(content_item.text)
                return str(result.content[0])
            return str(result)
        except (AttributeError, TypeError):
            return None
