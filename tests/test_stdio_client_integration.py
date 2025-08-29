"""Legacy stdio client integration test aggregator.

The original monolithic tests were split into focused modules to adhere to
the test organization guidelines. This module remains importable and provides
an optional standalone runner that executes the split tests in sequence.
"""

import asyncio
import logging
import sys
import tempfile
from pathlib import Path

from tests.test_stdio_client_ping_and_capabilities import (
    TestStdioClientPingAndCapabilities,
)
from tests.test_stdio_update_task_discovery import TestStdioUpdateTaskDiscovery
from tests.test_stdio_update_task_errors import TestStdioUpdateTaskErrors
from tests.test_stdio_update_task_execution_flow import TestStdioUpdateTaskExecution
from tests.test_stdio_update_task_rate_limit import TestStdioUpdateTaskRateLimiting
from tests.test_stdio_update_task_timezone import TestStdioUpdateTaskTimezone


def setup_logging() -> None:
    """Configure logging to stderr for test output."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        stream=sys.stderr,
    )


async def run_integration_tests() -> None:
    """Run all stdio client integration tests as a standalone script."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting LunaTask MCP stdio client integration tests...")

    config_content = """
lunatask_bearer_token = "test_integration_token"
port = 8080
log_level = "INFO"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(config_content)
        temp_config_path = f.name

    try:
        ping_caps = TestStdioClientPingAndCapabilities()
        update_discovery = TestStdioUpdateTaskDiscovery()
        update_exec = TestStdioUpdateTaskExecution()
        update_errors = TestStdioUpdateTaskErrors()
        update_rate = TestStdioUpdateTaskRateLimiting()
        update_tz = TestStdioUpdateTaskTimezone()

        logger.info("Running ping functionality test...")
        await ping_caps.test_ping_functionality(temp_config_path)
        logger.info("✓ Ping functionality test passed")

        logger.info("Running protocol version test...")
        await ping_caps.test_protocol_version_handling(temp_config_path)
        logger.info("✓ Protocol version test passed")

        logger.info("Running capability handling test...")
        await ping_caps.test_graceful_capability_handling(temp_config_path)
        logger.info("✓ Capability handling test passed")

        logger.info("Running update_task tool discovery test...")
        await update_discovery.test_update_task_tool_discovery(temp_config_path)
        logger.info("✓ update_task tool discovery test passed")

        logger.info("Running update_task tool execution flow test...")
        await update_exec.test_update_task_tool_execution_flow()
        logger.info("✓ update_task tool execution flow test passed")

        logger.info("Running update_task MCP error responses test...")
        await update_errors.test_update_task_mcp_error_responses()
        logger.info("✓ update_task MCP error responses test passed")

        logger.info("Running update_task rate limiter application test...")
        await update_rate.test_update_task_rate_limiter_application()
        logger.info("✓ update_task rate limiter application test passed")

        logger.info("Running update_task timezone handling test...")
        await update_tz.test_update_task_timezone_handling()
        logger.info("✓ update_task timezone handling test passed")

        logger.info("🎉 All integration tests passed!")

    except Exception:
        logger.exception("❌ Integration tests failed!")
        sys.exit(1)
    finally:
        Path(temp_config_path).unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(run_integration_tests())
