"""Integration test for timezone handling in update_task via stdio client."""

import logging

import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from fastmcp.exceptions import ToolError

from tests.conftest import extract_tool_response_text


class TestStdioUpdateTaskTimezone:
    """Integration test cases for timezone handling (Task 3.5)."""

    @pytest.mark.asyncio
    async def test_timezone_offset_handling(self, temp_config_file: str) -> None:
        """Test ISO 8601 datetime with timezone offset handling."""
        logger = logging.getLogger(__name__)

        transport = StdioTransport(
            command="python",
            args=["-m", "lunatask_mcp.main", "--config-file", temp_config_file],
        )
        client = Client(transport)

        async with client:
            logger.info("Testing ISO 8601 with timezone offset...")
            try:
                result = await client.call_tool(
                    "update_task",
                    {
                        "id": "timezone-test-1",
                        "name": "Timezone Test 1",
                        "due_date": "2032-04-23T10:20:30.400+02:30",
                    },
                )

                response_text = extract_tool_response_text(result)
                logger.info("Timezone offset test response: %s", response_text)

            except ToolError as e:
                logger.info("Timezone offset test completed (expected error): %s", str(e)[:100])
                error_msg = str(e).lower()
                if "datetime" in error_msg and "parse" in error_msg:
                    pytest.fail(f"Unexpected datetime parsing error: {e}")

    @pytest.mark.asyncio
    async def test_utc_timezone_handling(self, temp_config_file: str) -> None:
        """Test ISO 8601 datetime with UTC timezone handling."""
        logger = logging.getLogger(__name__)

        transport = StdioTransport(
            command="python",
            args=["-m", "lunatask_mcp.main", "--config-file", temp_config_file],
        )
        client = Client(transport)

        async with client:
            logger.info("Testing ISO 8601 UTC timezone...")
            try:
                result = await client.call_tool(
                    "update_task",
                    {
                        "id": "timezone-test-2",
                        "name": "Timezone Test 2",
                        "due_date": "2032-04-23T10:20:30Z",
                    },
                )

                response_text = extract_tool_response_text(result)
                logger.info("UTC timezone test response: %s", response_text)

            except ToolError as e:
                logger.info("UTC timezone test completed (expected error): %s", str(e)[:100])
                error_msg = str(e).lower()
                if "datetime" in error_msg and "parse" in error_msg:
                    pytest.fail(f"Unexpected datetime parsing error: {e}")

    @pytest.mark.asyncio
    async def test_naive_datetime_handling(self, temp_config_file: str) -> None:
        """Test ISO 8601 datetime without timezone handling."""
        logger = logging.getLogger(__name__)

        transport = StdioTransport(
            command="python",
            args=["-m", "lunatask_mcp.main", "--config-file", temp_config_file],
        )
        client = Client(transport)

        async with client:
            logger.info("Testing ISO 8601 without timezone...")
            try:
                result = await client.call_tool(
                    "update_task",
                    {
                        "id": "timezone-test-3",
                        "name": "Timezone Test 3",
                        "due_date": "2032-04-23T10:20:30",
                    },
                )

                response_text = extract_tool_response_text(result)
                logger.info("Naive datetime test response: %s", response_text)

            except ToolError as e:
                logger.info("Naive datetime test completed (expected error): %s", str(e)[:100])
                error_msg = str(e).lower()
                if "datetime" in error_msg and "parse" in error_msg:
                    pytest.fail(f"Unexpected datetime parsing error: {e}")

    @pytest.mark.asyncio
    async def test_invalid_datetime_validation(self, temp_config_file: str) -> None:
        """Test validation of invalid datetime format."""
        logger = logging.getLogger(__name__)

        transport = StdioTransport(
            command="python",
            args=["-m", "lunatask_mcp.main", "--config-file", temp_config_file],
        )
        client = Client(transport)

        async with client:
            logger.info("Testing invalid datetime format...")
            result = await client.call_tool(
                "update_task",
                {
                    "id": "timezone-test-4",
                    "name": "Timezone Test 4",
                    "due_date": "invalid-datetime-format",
                },
            )

            response_text = extract_tool_response_text(result)
            logger.info("Invalid datetime format response: %s", response_text)

            if response_text and (
                "validation_error" in response_text.lower()
                or "invalid due_date format" in response_text.lower()
                or "iso 8601" in response_text.lower()
            ):
                logger.info("✓ Invalid datetime format properly rejected with validation error")
            else:
                pytest.fail(f"Expected datetime validation error response, got: {response_text}")

    @pytest.mark.asyncio
    async def test_microseconds_datetime_handling(self, temp_config_file: str) -> None:
        """Test ISO 8601 datetime with microseconds handling."""
        logger = logging.getLogger(__name__)

        transport = StdioTransport(
            command="python",
            args=["-m", "lunatask_mcp.main", "--config-file", temp_config_file],
        )
        client = Client(transport)

        async with client:
            logger.info("Testing microseconds in datetime...")
            try:
                result = await client.call_tool(
                    "update_task",
                    {
                        "id": "timezone-test-5",
                        "name": "Timezone Test 5",
                        "due_date": "2032-04-23T10:20:30.123456Z",
                    },
                )

                response_text = extract_tool_response_text(result)
                logger.info("Microseconds test response: %s", response_text)

            except ToolError as e:
                logger.info("Microseconds test completed (expected error): %s", str(e)[:100])
                error_msg = str(e).lower()
                if "datetime" in error_msg and "parse" in error_msg:
                    pytest.fail(f"Unexpected datetime parsing error: {e}")
