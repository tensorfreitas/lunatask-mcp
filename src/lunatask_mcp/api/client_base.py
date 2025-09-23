"""Base client for LunaTask API with HTTP plumbing and authentication.

This module provides the BaseClient class containing all HTTP infrastructure,
authentication, error handling, rate limiting, and retry logic that will be
shared by feature-specific mixins during client modularization.
"""

import asyncio
import logging
import types
from dataclasses import dataclass
from typing import Any, NoReturn

import httpx

from lunatask_mcp.api.exceptions import (
    LunaTaskAPIError,
    LunaTaskAuthenticationError,
    LunaTaskBadRequestError,
    LunaTaskNetworkError,
    LunaTaskNotFoundError,
    LunaTaskRateLimitError,
    LunaTaskServerError,
    LunaTaskServiceUnavailableError,
    LunaTaskSubscriptionRequiredError,
    LunaTaskTimeoutError,
    LunaTaskValidationError,
)
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.rate_limiter import TokenBucketLimiter

# HTTP status code constants
_HTTP_NO_CONTENT = 204
_HTTP_BAD_REQUEST = 400
_HTTP_UNAUTHORIZED = 401
_HTTP_PAYMENT_REQUIRED = 402
_HTTP_NOT_FOUND = 404
_HTTP_UNPROCESSABLE_ENTITY = 422
_HTTP_TOO_MANY_REQUESTS = 429
_HTTP_INTERNAL_SERVER_ERROR = 500
_HTTP_SERVICE_UNAVAILABLE = 503
_HTTP_TIMEOUT = 524
_HTTP_BAD_GATEWAY = 502
_HTTP_MAX_SERVER_ERROR = 600

_RETRYABLE_STATUS_CODES = {
    _HTTP_INTERNAL_SERVER_ERROR,
    _HTTP_BAD_GATEWAY,
    _HTTP_SERVICE_UNAVAILABLE,
    _HTTP_TIMEOUT,
}

# Guardrail constants
_MAX_LIST_LIMIT = 50

# Configure logger to write to stderr
logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _RetryContext:
    """Internal container storing retry metadata for a single attempt."""

    attempt: int
    max_attempts: int
    backoff: float
    method: str
    url: str


class BaseClient:
    """Base client providing HTTP plumbing and authentication for LunaTask API.

    This class contains the core HTTP infrastructure including connection management,
    authentication, error handling, retry logic, and rate limiting that can be
    composed with feature-specific mixins.
    """

    def __init__(self, config: ServerConfig) -> None:
        """Initialize the base LunaTask API client.

        Args:
            config: Server configuration containing bearer token and base URL
        """
        self._config = config
        self._base_url = str(config.lunatask_base_url).rstrip("/")
        self._bearer_token = config.lunatask_bearer_token
        self._http_client: httpx.AsyncClient | None = None

        # Initialize rate limiter with configuration
        self._rate_limiter = TokenBucketLimiter(
            rpm=config.rate_limit_rpm, burst=config.rate_limit_burst
        )

    def __str__(self) -> str:
        """Return string representation without exposing bearer token."""
        return f"BaseClient(base_url={self._base_url}, token=***redacted***)"

    def __repr__(self) -> str:
        """Return repr without exposing bearer token."""
        return f"BaseClient(base_url='{self._base_url}', token='***redacted***')"

    async def __aenter__(self) -> "BaseClient":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Async context manager exit with cleanup."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with proper configuration.

        Returns:
            httpx.AsyncClient: Configured async HTTP client
        """
        if self._http_client is None:
            timeout = httpx.Timeout(
                connect=self._config.timeout_connect,
                read=self._config.timeout_read,
                write=10.0,
                pool=10.0,
            )

            limits = httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10,
            )

            headers = {"User-Agent": self._config.http_user_agent}

            self._http_client = httpx.AsyncClient(
                timeout=timeout,
                limits=limits,
                follow_redirects=True,
                headers=headers,
            )

        return self._http_client

    @staticmethod
    def _is_retryable_status(status_code: int) -> bool:
        """Check whether an HTTP status code should trigger a retry."""
        return status_code in _RETRYABLE_STATUS_CODES

    @staticmethod
    def _has_remaining_attempts(context: _RetryContext) -> bool:
        """Determine whether another retry attempt is allowed."""
        return context.attempt < context.max_attempts - 1

    def _handle_http_status_retry(
        self,
        error: httpx.HTTPStatusError,
        context: _RetryContext,
    ) -> bool:
        """Handle retryable HTTP status errors.

        Returns:
            bool: True when caller should retry after applying backoff.
        """
        status_code = error.response.status_code
        if not self._has_remaining_attempts(context):
            self._handle_http_error(error)
        if not self._is_retryable_status(status_code):
            self._handle_http_error(error)

        logger.warning(
            "Retryable HTTP status %s for %s %s; retrying in %.2fs (attempt %d of %d)",
            status_code,
            context.method,
            context.url,
            context.backoff,
            context.attempt + 1,
            context.max_attempts,
        )
        return True

    def _handle_transient_exception(
        self,
        error: httpx.TimeoutException | httpx.NetworkError,
        context: _RetryContext,
    ) -> bool:
        """Handle timeout or network errors with exponential backoff.

        Returns:
            bool: True when caller should retry after applying backoff.
        """
        if not self._has_remaining_attempts(context):
            if isinstance(error, httpx.TimeoutException):
                logger.exception("Request timeout")
                raise LunaTaskTimeoutError from error
            logger.exception("Network error")
            raise LunaTaskNetworkError from error

        message = (
            "Timeout during %s %s; retrying in %.2fs (attempt %d of %d)"
            if isinstance(error, httpx.TimeoutException)
            else "Network error during %s %s; retrying in %.2fs (attempt %d of %d)"
        )
        logger.warning(
            message,
            context.method,
            context.url,
            context.backoff,
            context.attempt + 1,
            context.max_attempts,
        )
        return True

    def _get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers with bearer token.

        Returns:
            Dict[str, str]: Headers including Authorization and Content-Type
        """
        return {
            "Authorization": f"Bearer {self._bearer_token}",
            "Content-Type": "application/json",
        }

    def _get_redacted_headers(self) -> dict[str, str]:
        """Get headers with redacted bearer token for logging.

        Returns:
            Dict[str, str]: Headers with redacted authorization token
        """
        return {
            "Authorization": "Bearer ***redacted***",
            "Content-Type": "application/json",
        }

    def _handle_http_error(self, error: httpx.HTTPStatusError) -> NoReturn:
        """Handle HTTP status errors and raise appropriate exceptions.

        Args:
            error: HTTP status error from httpx

        Raises:
            LunaTaskBadRequestError: For 400 Bad Request
            LunaTaskAuthenticationError: For 401 Unauthorized
            LunaTaskSubscriptionRequiredError: For 402 Payment Required
            LunaTaskNotFoundError: For 404 Not Found
            LunaTaskValidationError: For 422 Unprocessable Entity
            LunaTaskRateLimitError: For 429 Too Many Requests
            LunaTaskServerError: For 5xx server errors
            LunaTaskServiceUnavailableError: For 503 Service Unavailable
            LunaTaskTimeoutError: For 524 Request Timed Out
            LunaTaskAPIError: For other HTTP errors
        """
        status_code = error.response.status_code

        if status_code == _HTTP_BAD_REQUEST:
            logger.error("Bad request to LunaTask API - invalid parameters")
            raise LunaTaskBadRequestError from error
        if status_code == _HTTP_UNAUTHORIZED:
            logger.error("Authentication failed with LunaTask API")
            raise LunaTaskAuthenticationError from error
        if status_code == _HTTP_PAYMENT_REQUIRED:
            logger.error("LunaTask subscription required - free plan limit reached")
            raise LunaTaskSubscriptionRequiredError from error
        if status_code == _HTTP_NOT_FOUND:
            logger.error("Resource not found: %s", error.request.url)
            raise LunaTaskNotFoundError from error
        if status_code == _HTTP_UNPROCESSABLE_ENTITY:
            logger.error("LunaTask API validation error - entity not valid")
            raise LunaTaskValidationError from error
        if status_code == _HTTP_TOO_MANY_REQUESTS:
            logger.error("Rate limit exceeded for LunaTask API")
            raise LunaTaskRateLimitError from error
        if status_code == _HTTP_SERVICE_UNAVAILABLE:
            logger.error("LunaTask API temporarily unavailable for maintenance")
            raise LunaTaskServiceUnavailableError from error
        if status_code == _HTTP_TIMEOUT:
            logger.error("LunaTask API request timed out")
            raise LunaTaskTimeoutError(status_code=status_code) from error
        if _HTTP_INTERNAL_SERVER_ERROR <= status_code < _HTTP_MAX_SERVER_ERROR:
            logger.error("LunaTask API server error: %s", status_code)
            raise LunaTaskServerError("", status_code) from error
        logger.error("LunaTask API error: %s", status_code)
        raise LunaTaskAPIError("", status_code) from error

    async def make_request(  # noqa: C901
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an authenticated request to the LunaTask API.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            endpoint: API endpoint (without base URL)
            data: JSON data for request body
            params: Query parameters

        Returns:
            Dict[str, Any]: Parsed JSON response

        Raises:
            LunaTaskBadRequestError: Invalid request parameters
            LunaTaskAuthenticationError: Authentication failed
            LunaTaskSubscriptionRequiredError: Subscription required
            LunaTaskNotFoundError: Resource not found
            LunaTaskValidationError: Entity validation failed
            LunaTaskRateLimitError: Rate limit exceeded
            LunaTaskServerError: Server error
            LunaTaskServiceUnavailableError: Service unavailable
            LunaTaskNetworkError: Network connectivity error
            LunaTaskTimeoutError: Request timeout
            LunaTaskAPIError: Other API errors
        """
        method_upper = method.upper()
        url = f"{self._base_url}/{endpoint.lstrip('/')}"
        max_attempts = self._config.http_retries + 1
        backoff = self._config.http_backoff_start_seconds

        for attempt in range(max_attempts):
            await self._rate_limiter.acquire()

            if method_upper in {"POST", "PATCH", "DELETE"}:
                min_delay = self._config.http_min_mutation_interval_seconds
                if min_delay > 0:
                    await asyncio.sleep(min_delay)

            headers = self._get_auth_headers()

            try:
                http_client = self._get_http_client()

                redacted_headers = self._get_redacted_headers()
                logger.debug(
                    "Making %s request to %s with headers: %s",
                    method_upper,
                    url,
                    redacted_headers,
                )

                response = await http_client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                    params=params,
                )

                response.raise_for_status()

            except httpx.HTTPStatusError as error:
                context = _RetryContext(
                    attempt=attempt,
                    max_attempts=max_attempts,
                    backoff=backoff,
                    method=method_upper,
                    url=url,
                )
                should_retry = self._handle_http_status_retry(error, context)
                if should_retry:
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
                    continue
            except (httpx.TimeoutException, httpx.NetworkError) as error:
                context = _RetryContext(
                    attempt=attempt,
                    max_attempts=max_attempts,
                    backoff=backoff,
                    method=method_upper,
                    url=url,
                )
                should_retry = self._handle_transient_exception(error, context)
                if should_retry:
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
                    continue
            except Exception as error:
                logger.exception("Unexpected error during API request")
                raise LunaTaskAPIError.create_unexpected_error(method, endpoint) from error
            else:
                if response.status_code == _HTTP_NO_CONTENT:
                    logger.debug(
                        "Successful API response: %s (No Content)",
                        response.status_code,
                    )
                    return {}

                result = response.json()
                logger.debug("Successful API response: %s", response.status_code)
                return result

        msg = f"Exhausted retry attempts for {method_upper} {url}"
        logger.error(msg)
        raise LunaTaskAPIError(msg)

    async def test_connectivity(self) -> bool:
        """Test connectivity to the LunaTask API.

        Makes a simple authenticated request to verify that the bearer token
        is valid and the API is accessible.

        Returns:
            bool: True if connectivity test succeeds, False otherwise
        """
        try:
            result = await self.make_request("GET", "ping")
        except LunaTaskAPIError as e:
            logger.warning("LunaTask API connectivity test failed: %s", e)
            return False
        except Exception:
            logger.exception("LunaTask API connectivity test failed with unexpected error")
            return False
        else:
            if result.get("message") == "pong":
                logger.info("LunaTask API connectivity test successful")
                return True
            logger.warning("LunaTask API connectivity test failed: unexpected response")
            return False
