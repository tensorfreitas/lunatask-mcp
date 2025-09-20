"""Common helpers and constants for API client tests.

This module centralizes shared constants and small helper functions used across
the split `test_api_client_*` modules to keep individual test files focused and
under the 500-line limit.
"""

from __future__ import annotations

import httpx
from pydantic import HttpUrl

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.config import ServerConfig

# Test constants
# S105 flags hardcoded cryptographic keys, passwords, or secrets
TEST_TOKEN = "test_token_123"  # noqa: S105
SECRET_TOKEN = "secret_token_456"  # noqa: S105
VALID_TOKEN = "valid_token"  # noqa: S105
INVALID_TOKEN = "invalid_token"  # noqa: S105
SUPER_SECRET_TOKEN = "super_secret_token_123"  # noqa: S105
SUPER_SECRET_TOKEN_456 = "super_secret_token_456"  # noqa: S105
SECRET_TOKEN_HIDDEN = "secret_token_that_should_not_appear"  # noqa: S105
TEST_BEARER_TOKEN = "test_bearer_token"  # noqa: S105
SECRET_TOKEN_789 = "secret_token_789"  # noqa: S105

# URL constants
DEFAULT_API_URL = HttpUrl("https://api.lunatask.app/v1/")
CUSTOM_API_URL = HttpUrl("https://custom.lunatask.app/v2/")

# HTTP timeout constants
CONNECT_TIMEOUT = 5.0
READ_TIMEOUT = 30.0
WRITE_TIMEOUT = 10.0
POOL_TIMEOUT = 10.0

# Task priority constants
TEST_PRIORITY_HIGH = 2

# HTTP status code constants for tests
HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_PAYMENT_REQUIRED = 402
HTTP_NOT_FOUND = 404
HTTP_UNPROCESSABLE_ENTITY = 422
HTTP_TOO_MANY_REQUESTS = 429
HTTP_INTERNAL_SERVER_ERROR = 500
HTTP_BAD_GATEWAY = 502
HTTP_SERVICE_UNAVAILABLE = 503
HTTP_TIMEOUT = 524


def get_client_config(client: LunaTaskClient) -> ServerConfig:
    """Helper to access client config for testing."""
    return client._config  # pyright: ignore[reportPrivateUsage]


def get_client_base_url(client: LunaTaskClient) -> str:
    """Helper to access client base URL for testing."""
    return client._base_url  # pyright: ignore[reportPrivateUsage]


def get_client_bearer_token(client: LunaTaskClient) -> str:
    """Helper to access client bearer token for testing."""
    return client._bearer_token  # pyright: ignore[reportPrivateUsage]


def get_client_http_client(client: LunaTaskClient) -> httpx.AsyncClient | None:
    """Helper to access client HTTP client for testing."""
    return client._http_client  # pyright: ignore[reportPrivateUsage]


def get_http_client(client: LunaTaskClient) -> httpx.AsyncClient:
    """Helper to access HTTP client method for testing."""
    return client._get_http_client()  # pyright: ignore[reportPrivateUsage]


def get_auth_headers(client: LunaTaskClient) -> dict[str, str]:
    """Helper to access auth headers method for testing."""
    return client._get_auth_headers()  # pyright: ignore[reportPrivateUsage]


def get_redacted_headers(client: LunaTaskClient) -> dict[str, str]:
    """Helper to access redacted headers method for testing."""
    return client._get_redacted_headers()  # pyright: ignore[reportPrivateUsage]
