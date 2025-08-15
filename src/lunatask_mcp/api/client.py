"""LunaTask API client for secure authentication and request handling.

This module provides the LunaTaskClient class for making authenticated
requests to the LunaTask API with proper error handling and security.
"""

import logging
import types
from typing import Any, NoReturn

import httpx

from lunatask_mcp.api.exceptions import (
    LunaTaskAPIError,
    LunaTaskAuthenticationError,
    LunaTaskNetworkError,
    LunaTaskNotFoundError,
    LunaTaskRateLimitError,
    LunaTaskServerError,
    LunaTaskTimeoutError,
)
from lunatask_mcp.config import ServerConfig

# HTTP status code constants
_HTTP_UNAUTHORIZED = 401
_HTTP_NOT_FOUND = 404
_HTTP_TOO_MANY_REQUESTS = 429
_HTTP_INTERNAL_SERVER_ERROR = 500
_HTTP_BAD_GATEWAY = 600

# Configure logger to write to stderr
logger = logging.getLogger(__name__)


class LunaTaskClient:
    """Client for making authenticated requests to the LunaTask API.

    This client handles secure bearer token authentication, HTTP connection
    management, and comprehensive error handling while ensuring that
    bearer tokens are never exposed in logs or error messages.
    """

    def __init__(self, config: ServerConfig) -> None:
        """Initialize the LunaTask API client.

        Args:
            config: Server configuration containing bearer token and base URL
        """
        self._config = config
        self._base_url = str(config.lunatask_base_url).rstrip("/")
        self._bearer_token = config.lunatask_bearer_token
        self._http_client: httpx.AsyncClient | None = None

    def __str__(self) -> str:
        """Return string representation without exposing bearer token."""
        return f"LunaTaskClient(base_url={self._base_url}, token=***redacted***)"

    def __repr__(self) -> str:
        """Return repr without exposing bearer token."""
        return f"LunaTaskClient(base_url='{self._base_url}', token='***redacted***')"

    async def __aenter__(self) -> "LunaTaskClient":
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
                connect=5.0,  # 5 seconds to establish connection
                read=10.0,  # 10 seconds to read response
                write=10.0,  # 10 seconds to send request
                pool=10.0,  # 10 seconds for connection pooling
            )

            limits = httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10,
            )

            self._http_client = httpx.AsyncClient(
                timeout=timeout,
                limits=limits,
                follow_redirects=True,
            )

        return self._http_client

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
            LunaTaskAuthenticationError: For 401 Unauthorized
            LunaTaskNotFoundError: For 404 Not Found
            LunaTaskRateLimitError: For 429 Too Many Requests
            LunaTaskServerError: For 5xx server errors
            LunaTaskAPIError: For other HTTP errors
        """
        status_code = error.response.status_code

        if status_code == _HTTP_UNAUTHORIZED:
            logger.error("Authentication failed with LunaTask API")
            raise LunaTaskAuthenticationError from error
        if status_code == _HTTP_NOT_FOUND:
            logger.error("Resource not found: %s", error.request.url)
            raise LunaTaskNotFoundError from error
        if status_code == _HTTP_TOO_MANY_REQUESTS:
            logger.error("Rate limit exceeded for LunaTask API")
            raise LunaTaskRateLimitError from error
        if _HTTP_INTERNAL_SERVER_ERROR <= status_code < _HTTP_BAD_GATEWAY:
            logger.error("LunaTask API server error: %s", status_code)
            raise LunaTaskServerError("Error", status_code) from error
        logger.error("LunaTask API error: %s", status_code)
        raise LunaTaskAPIError("Error", status_code) from error

    async def make_request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an authenticated request to the LunaTask API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without base URL)
            data: JSON data for request body
            params: Query parameters

        Returns:
            Dict[str, Any]: Parsed JSON response

        Raises:
            LunaTaskAuthenticationError: Authentication failed
            LunaTaskNotFoundError: Resource not found
            LunaTaskRateLimitError: Rate limit exceeded
            LunaTaskServerError: Server error
            LunaTaskNetworkError: Network connectivity error
            LunaTaskTimeoutError: Request timeout
            LunaTaskAPIError: Other API errors
        """
        url = f"{self._base_url}/{endpoint.lstrip('/')}"
        headers = self._get_auth_headers()

        try:
            http_client = self._get_http_client()

            # Log request with redacted headers
            redacted_headers = self._get_redacted_headers()
            logger.debug(
                "Making %s request to %s with headers: %s",
                method,
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

            # Raise for HTTP status errors
            response.raise_for_status()

            # Parse and return JSON response
            result = response.json()
            logger.debug("Successful API response: %s", response.status_code)

        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
        except httpx.TimeoutException as e:
            logger.exception("Request timeout")
            raise LunaTaskTimeoutError from e
        except httpx.NetworkError as e:
            logger.exception("Network error")
            raise LunaTaskNetworkError from e
        except Exception as e:
            logger.exception("Unexpected error")
            raise LunaTaskAPIError("Error") from e
        else:
            return result

    async def test_connectivity(self) -> bool:
        """Test connectivity to the LunaTask API.

        Makes a simple authenticated request to verify that the bearer token
        is valid and the API is accessible.

        Returns:
            bool: True if connectivity test succeeds, False otherwise
        """
        try:
            result = await self.make_request("GET", "ping")
            if result.get("message") == "pong":
                logger.info("LunaTask API connectivity test successful")
                return True
            # Early return pattern is clearer here than else block
            logger.warning("LunaTask API connectivity test failed: unexpected response")
            return False  # noqa: TRY300
        except LunaTaskAPIError as e:
            logger.warning("LunaTask API connectivity test failed: %s", e)
            return False
        except Exception:
            logger.exception("LunaTask API connectivity test failed with unexpected error")
            return False
