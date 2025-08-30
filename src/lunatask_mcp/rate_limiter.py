"""
Token bucket rate limiter implementation.

This module provides a token bucket rate limiter with async support for controlling
request rates to the LunaTask API.
"""

import asyncio
import time


class InvalidRPMError(ValueError):
    """RPM must be positive."""


class InvalidBurstError(ValueError):
    """Burst must be positive."""


class TokenBucketLimiter:
    """
    Token bucket rate limiter with async support.

    Implements the token bucket algorithm to control request rates. Allows burst
    traffic up to the bucket capacity, then enforces steady-state rate limiting.

    Args:
        rpm: Requests per minute (must be positive)
        burst: Maximum burst capacity (must be positive)

    Raises:
        ValueError: If rpm or burst are not positive values
    """

    def __init__(self, rpm: int, burst: int) -> None:
        if rpm <= 0:
            raise InvalidRPMError
        if burst <= 0:
            raise InvalidBurstError

        self._rpm = rpm
        self._burst = burst
        self._tokens = float(burst)  # Start with full bucket
        self._last_refill = time.time()
        self._lock = asyncio.Lock()

        # Calculate token refill rate (tokens per second)
        self._refill_rate = rpm / 60.0

        # Log configuration (to stderr as per coding standards)

    async def acquire(self) -> None:
        """
        Acquire a token, waiting if necessary.

        This method will wait until a token becomes available. It's the primary
        method for rate-limited operations.
        """
        async with self._lock:
            while not self._try_acquire_internal():
                # Calculate wait time for next token
                wait_time = 1.0 / self._refill_rate
                await asyncio.sleep(wait_time)
                self._refill_tokens()

    def try_acquire(self) -> bool:
        """
        Try to acquire a token without waiting.

        Returns:
            True if token acquired, False if no tokens available
        """
        # Note: This is synchronous, so we can't use the async lock here
        # We'll use a simple approach for the sync version
        self._refill_tokens()

        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return True
        return False

    def _try_acquire_internal(self) -> bool:
        """
        Internal helper for acquiring tokens (assumes lock is held).

        Returns:
            True if token acquired, False if no tokens available
        """
        self._refill_tokens()

        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return True
        return False

    def _refill_tokens(self) -> None:
        """
        Refill tokens based on elapsed time since last refill.

        This implements the core token bucket algorithm by adding tokens
        at the configured rate, capped at the burst capacity.
        """
        now = time.time()
        elapsed = now - self._last_refill

        if elapsed > 0:
            # Add tokens based on elapsed time and refill rate
            tokens_to_add = elapsed * self._refill_rate
            self._tokens = min(self._burst, self._tokens + tokens_to_add)
            self._last_refill = now

    @property
    def current_tokens(self) -> float:
        """
        Get current token count (for testing/monitoring).

        Returns:
            Current number of available tokens
        """
        self._refill_tokens()
        return self._tokens

    @property
    def rpm(self) -> int:
        """Get configured requests per minute."""
        return self._rpm

    @property
    def burst(self) -> int:
        """Get configured burst capacity."""
        return self._burst

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"TokenBucketLimiter(rpm={self._rpm}, burst={self._burst}, tokens={self._tokens:.2f})"
        )


class RateLimitExceededError(Exception):
    """
    Exception raised when rate limit is exceeded and no fallback is available.

    This exception can be used in scenarios where immediate failure is preferred
    over waiting for tokens to become available.
    """

    def __init__(self, message: str = "Rate limit exceeded") -> None:
        super().__init__(message)
        self.message = message
