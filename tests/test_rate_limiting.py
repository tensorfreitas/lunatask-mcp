"""
Rate limiting tests for token bucket implementation.

Test cases for burst behavior, steady-state rate enforcement, and token exhaustion.
"""

import asyncio
import time

import pytest

from lunatask_mcp.rate_limiter import InvalidBurstError, InvalidRPMError, TokenBucketLimiter

# Test constants to avoid magic values
FAST_BURST_TIME_LIMIT = 0.1
STEADY_STATE_MIN_TIME = 0.8
STEADY_STATE_MAX_TIME = 1.2
TOKEN_WAIT_MIN_TIME = 0.4
TOKEN_WAIT_MAX_TIME = 0.6
HIGH_PRECISION_MIN_TIME = 0.01
HIGH_PRECISION_MAX_TIME = 0.03
CONCURRENT_MIN_TIME = 1.8
EXPECTED_RESULTS_COUNT = 5
TEST_RPM_VALUE = 120
TEST_BURST_VALUE = 15


class TestTokenBucketLimiter:
    """Test cases for the TokenBucketLimiter implementation."""

    @pytest.mark.asyncio
    async def test_burst_behavior_allows_rapid_requests(self) -> None:
        """Test that burst capacity allows rapid initial requests."""
        limiter = TokenBucketLimiter(rpm=60, burst=10)  # 1 request per second, burst of 10

        # Should be able to make 10 rapid requests (burst capacity)
        start_time = time.time()
        for _ in range(10):
            await limiter.acquire()
        end_time = time.time()

        # All 10 requests should complete quickly (well under 1 second)
        assert end_time - start_time < FAST_BURST_TIME_LIMIT

    @pytest.mark.asyncio
    async def test_steady_state_rate_enforcement(self) -> None:
        """Test that steady-state rate is enforced after burst is exhausted."""
        limiter = TokenBucketLimiter(rpm=60, burst=2)  # 1 req/sec, small burst

        # Exhaust burst
        await limiter.acquire()
        await limiter.acquire()

        # Next request should wait ~1 second
        start_time = time.time()
        await limiter.acquire()
        end_time = time.time()

        # Should have waited approximately 1 second (with some tolerance)
        elapsed = end_time - start_time
        assert STEADY_STATE_MIN_TIME <= elapsed <= STEADY_STATE_MAX_TIME

    @pytest.mark.asyncio
    async def test_token_exhaustion_and_waiting(self) -> None:
        """Test behavior when tokens are exhausted and must wait."""
        limiter = TokenBucketLimiter(rpm=120, burst=3)  # 2 req/sec, burst of 3

        # Exhaust all tokens
        for _ in range(3):
            await limiter.acquire()

        # Should wait ~0.5 seconds for next token
        start_time = time.time()
        await limiter.acquire()
        end_time = time.time()

        elapsed = end_time - start_time
        assert TOKEN_WAIT_MIN_TIME <= elapsed <= TOKEN_WAIT_MAX_TIME

    def test_try_acquire_without_waiting_success(self) -> None:
        """Test try_acquire returns True when tokens available."""
        limiter = TokenBucketLimiter(rpm=60, burst=5)

        # Should succeed without waiting
        assert limiter.try_acquire() is True

    def test_try_acquire_without_waiting_failure(self) -> None:
        """Test try_acquire returns False when no tokens available."""
        limiter = TokenBucketLimiter(rpm=60, burst=2)

        # Exhaust tokens
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is True

        # Should fail now
        assert limiter.try_acquire() is False

    @pytest.mark.asyncio
    async def test_token_refill_over_time(self) -> None:
        """Test that tokens refill over time at the correct rate."""
        limiter = TokenBucketLimiter(rpm=120, burst=1)  # 2 req/sec, minimal burst

        # Use the only token
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is False

        # Wait for refill (0.5 seconds at 2 req/sec)
        await asyncio.sleep(0.6)

        # Should have a token now
        assert limiter.try_acquire() is True

    @pytest.mark.asyncio
    async def test_concurrent_requests_respect_limits(self) -> None:
        """Test that concurrent requests properly respect rate limits."""
        limiter = TokenBucketLimiter(rpm=60, burst=3)

        # Create 5 concurrent requests
        tasks = [limiter.acquire() for _ in range(5)]

        start_time = time.time()
        await asyncio.gather(*tasks)
        end_time = time.time()

        # First 3 should be immediate (burst), last 2 should wait
        # Should take at least 2 seconds for all to complete
        elapsed = end_time - start_time
        assert elapsed >= CONCURRENT_MIN_TIME

    def test_invalid_rpm_raises_error(self) -> None:
        """Test that invalid RPM values raise appropriate errors."""
        with pytest.raises(InvalidRPMError):
            TokenBucketLimiter(rpm=0, burst=1)

        with pytest.raises(InvalidRPMError):
            TokenBucketLimiter(rpm=-1, burst=1)

    def test_invalid_burst_raises_error(self) -> None:
        """Test that invalid burst values raise appropriate errors."""
        with pytest.raises(InvalidBurstError):
            TokenBucketLimiter(rpm=60, burst=0)

        with pytest.raises(InvalidBurstError):
            TokenBucketLimiter(rpm=60, burst=-1)

    @pytest.mark.asyncio
    async def test_high_rpm_precision(self) -> None:
        """Test rate limiting works correctly with high RPM values."""
        limiter = TokenBucketLimiter(rpm=3600, burst=2)  # 60 req/sec

        # Should be able to make 2 rapid requests
        await limiter.acquire()
        await limiter.acquire()

        # Next should wait ~1/60 second (0.0167s)
        start_time = time.time()
        await limiter.acquire()
        end_time = time.time()

        elapsed = end_time - start_time
        assert HIGH_PRECISION_MIN_TIME <= elapsed <= HIGH_PRECISION_MAX_TIME


class TestRateLimiterIntegration:
    """Integration tests for rate limiter usage patterns."""

    @pytest.mark.asyncio
    async def test_api_client_integration_pattern(self) -> None:
        """Test the expected integration pattern with API client."""
        limiter = TokenBucketLimiter(rpm=60, burst=10)

        async def mock_api_call() -> str:
            """Simulate an API call with rate limiting."""
            await limiter.acquire()
            return "api_response"

        # Should handle multiple calls efficiently
        results: list[str] = []
        for _ in range(5):
            result = await mock_api_call()
            results.append(result)

        assert len(results) == EXPECTED_RESULTS_COUNT
        assert all(r == "api_response" for r in results)

    def test_configuration_from_settings(self) -> None:
        """Test limiter configuration from application settings."""
        # Simulate configuration values
        config = {"rate_limit_rpm": TEST_RPM_VALUE, "rate_limit_burst": TEST_BURST_VALUE}

        limiter = TokenBucketLimiter(rpm=config["rate_limit_rpm"], burst=config["rate_limit_burst"])

        # Should be configured correctly
        assert limiter.rpm == TEST_RPM_VALUE
        assert limiter.burst == TEST_BURST_VALUE
