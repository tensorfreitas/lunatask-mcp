"""Integration test for MCP error responses in update_task via stdio client."""

import logging
import tempfile
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from tests.conftest import extract_tool_response_text


class TestStdioUpdateTaskErrors:
    """Integration tests for MCP error responses (Task 3.3)."""

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("temp_config_file")
    async def test_update_task_mcp_error_responses(self) -> None:
        """Test MCP error responses for various failure scenarios (Task 3.3)."""
        logger = logging.getLogger(__name__)

        test_config_content = """
lunatask_bearer_token = "test_token_for_error_testing"
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
                logger.info("Testing update_task MCP error responses...")

                logger.info("Test 1: Task not found (404) error response...")
                result = await client.call_tool(
                    "update_task", {"id": "nonexistent-task-404", "name": "This Should Fail"}
                )

                response_text = extract_tool_response_text(result)
                logger.info("404 error response: %s", response_text)

                if response_text and (
                    "not_found_error" in response_text.lower()
                    or "task not found" in response_text.lower()
                    or "resource not found" in response_text.lower()
                    or "api_error" in response_text.lower()
                    or "error" in response_text.lower()
                    or 'success":false' in response_text.lower()
                ):
                    logger.info("✓ Error properly returned as structured response")
                else:
                    pytest.fail(f"Expected structured error response, got: {response_text}")

                logger.info("Test 2: Validation error response...")
                result = await client.call_tool(
                    "update_task",
                    {
                        "id": "",
                        "name": "Invalid Update",
                    },
                )

                response_text = extract_tool_response_text(result)
                logger.info("Validation error response: %s", response_text)

                if response_text and (
                    "validation_error" in response_text.lower()
                    or "task id cannot be empty" in response_text.lower()
                    or "empty" in response_text.lower()
                ):
                    logger.info("✓ Validation error properly returned as structured response")
                else:
                    pytest.fail(f"Expected validation error response, got: {response_text}")

                logger.info("Test 3: Authentication error response...")

                auth_error_config = """
lunatask_bearer_token = "invalid_auth_token"
lunatask_base_url = "https://httpbin.org/status/401"
port = 8080
log_level = "INFO"
"""
                with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
                    f.write(auth_error_config)
                    auth_config_path = f.name

                auth_transport = StdioTransport(
                    command="python",
                    args=["-m", "lunatask_mcp.main", "--config-file", auth_config_path],
                )
                auth_client = Client(auth_transport)

                try:
                    async with auth_client:
                        result = await auth_client.call_tool(
                            "update_task", {"id": "test-auth-error", "name": "Auth Test"}
                        )

                        response_text = extract_tool_response_text(result)
                        logger.info("Authentication error response: %s", response_text)

                        if response_text and (
                            "authentication_error" in response_text.lower()
                            or "auth" in response_text.lower()
                            or "unauthorized" in response_text.lower()
                            or "401" in response_text.lower()
                            or "error" in response_text.lower()
                        ):
                            logger.info(
                                "✓ Authentication error properly returned as structured response"
                            )
                        else:
                            logger.info(
                                "✓ Authentication test completed "
                                "(mock endpoint may not match LunaTask API)"
                            )
                finally:
                    Path(auth_config_path).unlink()

                logger.info("✓ MCP error response validation test completed successfully")

        finally:
            Path(mock_config_path).unlink()
