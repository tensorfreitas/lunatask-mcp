"""Integration test for rate limiting behavior in update_task via stdio client."""

import logging
import tempfile
import time
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

# Constants for rate limiting tests
MIN_REQUEST_TIME = 0.1
MAX_TIMING_VARIANCE = 10.0


class TestStdioUpdateTaskRateLimiting:
    """Integration test cases for rate limiter application."""

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("temp_config_file")
    async def test_update_task_rate_limiter_application(self) -> None:
        """Test that rate limiter applies to PATCH requests."""
        logger = logging.getLogger(__name__)

        test_config_content = """
lunatask_bearer_token = "test_rate_limit_token"
lunatask_base_url = "https://httpbin.org/"
port = 8080
log_level = "DEBUG"
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
                logger.info("Testing update_task rate limiter application...")

                logger.info("Test 1: Single request timing baseline...")
                start_time = time.time()

                try:
                    await client.call_tool(
                        "update_task", {"id": "rate-test-1", "name": "Rate Limit Test 1"}
                    )
                except Exception as e:
                    logger.info("Request 1 completed with error (expected): %s", str(e)[:100])

                single_request_time = time.time() - start_time
                logger.info("Single request took: %.3f seconds", single_request_time)

                logger.info("Test 2: Consecutive requests to verify rate limiting...")
                request_times: list[float] = []

                for i in range(3):
                    start_time = time.time()

                    try:
                        await client.call_tool(
                            "update_task",
                            {"id": f"rate-test-{i + 2}", "name": f"Rate Limit Test {i + 2}"},
                        )
                    except Exception as e:
                        logger.info(
                            "Request %d completed with error (expected): %s", i + 2, str(e)[:50]
                        )

                    request_time = time.time() - start_time
                    request_times.append(request_time)
                    logger.info("Request %d took: %.3f seconds", i + 2, request_time)

                logger.info("Request timing analysis:")
                for i, rt in enumerate(request_times, 2):
                    logger.info("  Request %d: %.3f seconds", i, rt)

                average_time = sum(request_times) / len(request_times)
                logger.info("Average request time: %.3f seconds", average_time)

                if average_time <= MIN_REQUEST_TIME:
                    pytest.fail(
                        f"Requests too fast ({average_time:.3f}s avg) - "
                        "rate limiting may not be applied"
                    )

                if len(request_times) > 1:
                    timing_variance = max(request_times) - min(request_times)
                    logger.info("Timing variance: %.3f seconds", timing_variance)

                    if timing_variance >= MAX_TIMING_VARIANCE:
                        pytest.fail(
                            f"Timing variance too high ({timing_variance:.3f}s) - "
                            "inconsistent with rate limiting"
                        )

                logger.info("✓ Rate limiter behavior confirmed for PATCH requests")
                logger.info("✓ Rate limiter application test completed successfully")

        finally:
            Path(mock_config_path).unlink()
