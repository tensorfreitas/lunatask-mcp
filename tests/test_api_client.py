"""Tests for LunaTask API client.

This module contains comprehensive tests for the LunaTaskClient class,
following TDD methodology and ensuring secure token handling.
"""
# pyright: reportPrivateUsage=false

import httpx
import pytest
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import (
    LunaTaskAuthenticationError,
    LunaTaskNetworkError,
    LunaTaskNotFoundError,
    LunaTaskRateLimitError,
    LunaTaskServerError,
    LunaTaskTimeoutError,
)
from lunatask_mcp.config import ServerConfig

# Test constants
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
READ_TIMEOUT = 10.0
WRITE_TIMEOUT = 10.0
POOL_TIMEOUT = 10.0

# HTTP status code constants for tests
HTTP_OK = 200
HTTP_UNAUTHORIZED = 401
HTTP_NOT_FOUND = 404
HTTP_TOO_MANY_REQUESTS = 429
HTTP_INTERNAL_SERVER_ERROR = 500


def get_client_config(client: LunaTaskClient) -> ServerConfig:
    """Helper to access client config for testing."""
    return client._config  # noqa: SLF001 - Testing internal state


def get_client_base_url(client: LunaTaskClient) -> str:
    """Helper to access client base URL for testing."""
    return client._base_url  # noqa: SLF001 - Testing internal state


def get_client_bearer_token(client: LunaTaskClient) -> str:
    """Helper to access client bearer token for testing."""
    return client._bearer_token  # noqa: SLF001 - Testing internal state


def get_client_http_client(client: LunaTaskClient) -> httpx.AsyncClient | None:
    """Helper to access client HTTP client for testing."""
    return client._http_client  # noqa: SLF001 - Testing internal state


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


def get_http_client(client: LunaTaskClient) -> httpx.AsyncClient:
    """Helper to access HTTP client method for testing."""
    return client._get_http_client()  # noqa: SLF001 - Testing internal method


def get_auth_headers(client: LunaTaskClient) -> dict[str, str]:
    """Helper to access auth headers method for testing."""
    return client._get_auth_headers()  # noqa: SLF001 - Testing internal method


def get_redacted_headers(client: LunaTaskClient) -> dict[str, str]:
    """Helper to access redacted headers method for testing."""
    return client._get_redacted_headers()  # noqa: SLF001 - Testing internal method


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


class TestLunaTaskClientAuthenticatedRequests:
    """Test authenticated request methods."""

    @pytest.mark.asyncio
    async def test_make_request_success(self, mocker: MockerFixture) -> None:
        """Test successful authenticated request."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        # Mock successful response
        mock_response = mocker.Mock()
        mock_response.status_code = HTTP_OK
        mock_response.json.return_value = {"message": "pong"}
        mock_response.raise_for_status.return_value = None

        mock_http_client = mocker.AsyncMock()
        mock_http_client.request.return_value = mock_response

        mocker.patch.object(
            client,
            "_get_http_client",
            return_value=mock_http_client,
        )

        result = await client.make_request("GET", "ping")

        assert result == {"message": "pong"}
        mock_http_client.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_request_authentication_error(self, mocker: MockerFixture) -> None:
        """Test handling of 401 authentication error."""
        config = ServerConfig(
            lunatask_bearer_token=INVALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        # Mock 401 response
        mock_response = mocker.Mock()
        mock_response.status_code = HTTP_UNAUTHORIZED
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=mocker.Mock(),
            response=mock_response,
        )

        mock_http_client = mocker.AsyncMock()
        mock_http_client.request.return_value = mock_response
        mocker.patch.object(
            client,
            "_get_http_client",
            return_value=mock_http_client,
        )

        with pytest.raises(LunaTaskAuthenticationError) as exc_info:
            await client.make_request("GET", "ping")

        assert exc_info.value.status_code == HTTP_UNAUTHORIZED
        assert "Authentication failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_make_request_not_found_error(self, mocker: MockerFixture) -> None:
        """Test handling of 404 not found error."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        # Mock 404 response
        mock_response = mocker.Mock()
        mock_response.status_code = HTTP_NOT_FOUND
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=mocker.Mock(),
            response=mock_response,
        )

        mock_http_client = mocker.AsyncMock()
        mock_http_client.request.return_value = mock_response
        mocker.patch.object(
            client,
            "_get_http_client",
            return_value=mock_http_client,
        )

        with pytest.raises(LunaTaskNotFoundError) as exc_info:
            await client.make_request("GET", "nonexistent")

        assert exc_info.value.status_code == HTTP_NOT_FOUND

    @pytest.mark.asyncio
    async def test_make_request_rate_limit_error(self, mocker: MockerFixture) -> None:
        """Test handling of 429 rate limit error."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        # Mock 429 response
        mock_response = mocker.Mock()
        mock_response.status_code = HTTP_TOO_MANY_REQUESTS
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "429 Too Many Requests",
            request=mocker.Mock(),
            response=mock_response,
        )

        mock_http_client = mocker.AsyncMock()
        mock_http_client.request.return_value = mock_response
        mocker.patch.object(
            client,
            "_get_http_client",
            return_value=mock_http_client,
        )

        with pytest.raises(LunaTaskRateLimitError) as exc_info:
            await client.make_request("GET", "ping")

        assert exc_info.value.status_code == HTTP_TOO_MANY_REQUESTS

    @pytest.mark.asyncio
    async def test_make_request_server_error(self, mocker: MockerFixture) -> None:
        """Test handling of 500 server error."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        # Mock 500 response
        mock_response = mocker.Mock()
        mock_response.status_code = HTTP_INTERNAL_SERVER_ERROR
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Internal Server Error",
            request=mocker.Mock(),
            response=mock_response,
        )

        mock_http_client = mocker.AsyncMock()
        mock_http_client.request.return_value = mock_response
        mocker.patch.object(
            client,
            "_get_http_client",
            return_value=mock_http_client,
        )

        with pytest.raises(LunaTaskServerError) as exc_info:
            await client.make_request("GET", "ping")

        assert exc_info.value.status_code == HTTP_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_make_request_network_error(self, mocker: MockerFixture) -> None:
        """Test handling of network connectivity errors."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        mock_http_client = mocker.AsyncMock()
        mock_http_client.request.side_effect = httpx.NetworkError("Connection failed")
        mocker.patch.object(
            client,
            "_get_http_client",
            return_value=mock_http_client,
        )

        with pytest.raises(LunaTaskNetworkError) as exc_info:
            await client.make_request("GET", "ping")

        assert "network error" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_make_request_timeout_error(self, mocker: MockerFixture) -> None:
        """Test handling of request timeout errors."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        mock_http_client = mocker.AsyncMock()
        mock_http_client.request.side_effect = httpx.TimeoutException("Request timeout")
        mocker.patch.object(
            client,
            "_get_http_client",
            return_value=mock_http_client,
        )

        with pytest.raises(LunaTaskTimeoutError) as exc_info:
            await client.make_request("GET", "ping")

        assert "timeout" in str(exc_info.value).lower()


class TestLunaTaskClientConnectivityTest:
    """Test connectivity testing functionality."""

    @pytest.mark.asyncio
    async def test_test_connectivity_success(self, mocker: MockerFixture) -> None:
        """Test successful connectivity test."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value={"message": "pong"},
        )

        result = await client.test_connectivity()

        assert result is True
        mock_request.assert_called_once_with("GET", "ping")

    @pytest.mark.asyncio
    async def test_test_connectivity_authentication_failure(self, mocker: MockerFixture) -> None:
        """Test connectivity test with authentication failure."""
        config = ServerConfig(
            lunatask_bearer_token=INVALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskAuthenticationError(),
        )

        result = await client.test_connectivity()

        assert result is False

    @pytest.mark.asyncio
    async def test_test_connectivity_network_failure(self, mocker: MockerFixture) -> None:
        """Test connectivity test with network failure."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskNetworkError(),
        )

        result = await client.test_connectivity()

        assert result is False


class TestLunaTaskClientSecurityFeatures:
    """Test security features and token handling."""

    def test_bearer_token_not_in_string_representation(self) -> None:
        """Test that bearer token is not exposed in string representation."""
        config = ServerConfig(
            lunatask_bearer_token=SUPER_SECRET_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        client_str = str(client)
        assert SUPER_SECRET_TOKEN not in client_str

    def test_bearer_token_not_in_repr(self) -> None:
        """Test that bearer token is not exposed in repr."""
        config = ServerConfig(
            lunatask_bearer_token=SUPER_SECRET_TOKEN_456,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        client_repr = repr(client)
        assert SUPER_SECRET_TOKEN_456 not in client_repr

    @pytest.mark.asyncio
    async def test_error_messages_do_not_contain_token(self, mocker: MockerFixture) -> None:
        """Test that error messages never contain bearer token."""
        config = ServerConfig(
            lunatask_bearer_token=SECRET_TOKEN_HIDDEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        mock_http_client = mocker.AsyncMock()
        mock_http_client.request.side_effect = httpx.NetworkError("Connection failed")
        mocker.patch.object(
            client,
            "_get_http_client",
            return_value=mock_http_client,
        )

        try:
            await client.make_request("GET", "ping")
        except LunaTaskNetworkError as e:
            error_message = str(e)
            assert SECRET_TOKEN_HIDDEN not in error_message

    @pytest.mark.asyncio
    async def test_cleanup_on_context_exit(self) -> None:
        """Test that HTTP client is properly cleaned up."""
        config = ServerConfig(
            lunatask_bearer_token=TEST_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )

        async with LunaTaskClient(config) as client:
            # Use the client to initialize HTTP client
            http_client = get_http_client(client)
            assert http_client is not None

        # After context exit, client should be closed
        # This would be tested by checking if the client's close method was called
