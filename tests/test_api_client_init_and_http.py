"""Initialization and HTTP setup tests for LunaTaskClient."""
# pyright: reportPrivateUsage=false

from __future__ import annotations

import httpx
import pytest
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.config import ServerConfig
from tests.test_api_client_common import (
    CONNECT_TIMEOUT,
    CUSTOM_API_URL,
    DEFAULT_API_URL,
    POOL_TIMEOUT,
    READ_TIMEOUT,
    SECRET_TOKEN,
    SECRET_TOKEN_789,
    TEST_BEARER_TOKEN,
    TEST_TOKEN,
    VALID_TOKEN,
    WRITE_TIMEOUT,
    get_auth_headers,
    get_client_base_url,
    get_client_bearer_token,
    get_client_config,
    get_client_http_client,
    get_http_client,
    get_redacted_headers,
)

# Expected HTTP connection limits
MAX_KEEPALIVE_CONNECTIONS = 5
MAX_CONNECTIONS = 10


class TestLunaTaskClientInitialization:
    """Test LunaTaskClient initialization and configuration."""

    def test_client_initialization_with_valid_config(self) -> None:
        """Test that client initializes correctly with valid configuration."""
        config = ServerConfig(
            lunatask_bearer_token=TEST_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )

        client = LunaTaskClient(config)

        assert get_client_config(client) == config
        assert get_client_base_url(client) == "https://api.lunatask.app/v1"
        assert get_client_bearer_token(client) == TEST_TOKEN
        assert get_client_http_client(client) is None  # Not initialized until first use

    def test_client_initialization_with_custom_base_url(self) -> None:
        """Test client initialization with custom base URL."""
        config = ServerConfig(
            lunatask_bearer_token=TEST_TOKEN,
            lunatask_base_url=CUSTOM_API_URL,
        )

        client = LunaTaskClient(config)

        assert get_client_base_url(client) == "https://custom.lunatask.app/v2"

    def test_client_stores_bearer_token_securely(self) -> None:
        """Test that bearer token is stored but never exposed."""
        config = ServerConfig(
            lunatask_bearer_token=SECRET_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )

        client = LunaTaskClient(config)

        # Token should be stored internally
        assert get_client_bearer_token(client) == SECRET_TOKEN

        # But not exposed in string representation
        client_str = str(client)
        assert SECRET_TOKEN not in client_str
        assert "***redacted***" in client_str or "LunaTaskClient" in client_str


class TestLunaTaskClientHTTPSetup:
    """Test HTTP client setup and configuration."""

    @pytest.mark.asyncio
    async def test_http_client_lazy_initialization(self) -> None:
        """Test that HTTP client is lazily initialized."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        # Should be None initially
        assert get_client_http_client(client) is None

        # Should be created on first HTTP operation
        http_client = get_http_client(client)
        assert isinstance(http_client, httpx.AsyncClient)
        assert get_client_http_client(client) is not None

    @pytest.mark.asyncio
    async def test_http_client_configuration(self) -> None:
        """Test HTTP client timeout and connection settings."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        http_client = get_http_client(client)

        # Check timeout configuration
        assert http_client.timeout.connect == CONNECT_TIMEOUT
        assert http_client.timeout.read == READ_TIMEOUT
        assert http_client.timeout.write == WRITE_TIMEOUT
        assert http_client.timeout.pool == POOL_TIMEOUT

    @pytest.mark.asyncio
    async def test_follow_redirects_enabled(self) -> None:
        """Client enables automatic redirect following."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        http_client: httpx.AsyncClient = get_http_client(client)

        # Prefer public attribute; fall back to private if needed.
        follow_redirects_attr = (
            getattr(http_client, "follow_redirects", None)
            if hasattr(http_client, "follow_redirects")
            else getattr(http_client, "_follow_redirects", None)
        )
        assert follow_redirects_attr is True

    @pytest.mark.asyncio
    async def test_connection_limits_configuration(self) -> None:
        """Client configures connection limits as expected."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        http_client: httpx.AsyncClient = get_http_client(client)

        # Access limits via multiple potential locations, preferring public attrs.
        limits = getattr(http_client, "limits", None)
        if limits is None:
            limits = getattr(http_client, "_limits", None)

        max_keepalive_connections = (
            getattr(limits, "max_keepalive_connections", None) if limits else None
        )
        max_connections = getattr(limits, "max_connections", None) if limits else None

        # If not available on client, inspect the underlying transport pool (private API).
        if max_keepalive_connections is None or max_connections is None:
            transport = getattr(http_client, "_transport", None)
            pool = getattr(transport, "_pool", None) if transport is not None else None
            if pool is not None:
                # httpcore pools typically expose underscored attributes.
                max_keepalive_connections = getattr(
                    pool,
                    "_max_keepalive_connections",
                    getattr(pool, "max_keepalive_connections", None),
                )
                max_connections = getattr(
                    pool, "_max_connections", getattr(pool, "max_connections", None)
                )

        assert max_keepalive_connections == MAX_KEEPALIVE_CONNECTIONS
        assert max_connections == MAX_CONNECTIONS

    @pytest.mark.asyncio
    async def test_authentication_headers(self) -> None:
        """Test that authentication headers are set correctly."""
        config = ServerConfig(
            lunatask_bearer_token=TEST_BEARER_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        headers = get_auth_headers(client)

        assert headers["Authorization"] == f"Bearer {TEST_BEARER_TOKEN}"
        assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_token_redaction_in_headers_logging(self) -> None:
        """Test that bearer token is redacted when headers are logged."""
        config = ServerConfig(
            lunatask_bearer_token=SECRET_TOKEN_789,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        redacted_headers = get_redacted_headers(client)

        assert redacted_headers["Authorization"] == "Bearer ***redacted***"
        assert redacted_headers["Content-Type"] == "application/json"


class TestLunaTaskClientConnectivity:
    """Connectivity negative-path tests for `test_connectivity`."""

    @pytest.mark.asyncio
    async def test_returns_false_on_non_pong_response(self, mocker: MockerFixture) -> None:
        """`test_connectivity` returns False when response message is not 'pong'."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        mock_make_request = mocker.patch.object(
            client,
            "make_request",
            return_value={"message": "not-pong"},
        )

        result: bool = await client.test_connectivity()

        assert result is False
        mock_make_request.assert_called_once_with("GET", "ping")

    @pytest.mark.asyncio
    async def test_unexpected_exception_returns_false(self, mocker: MockerFixture) -> None:
        """Unexpected exception in make_request is handled and returns False."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        mocker.patch.object(client, "make_request", side_effect=Exception("boom"))

        result = await client.test_connectivity()

        assert result is False
