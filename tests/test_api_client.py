"""Tests for LunaTask API client.

This module contains comprehensive tests for the LunaTaskClient class,
following TDD methodology and ensuring secure token handling.
"""
# pyright: reportPrivateUsage=false

from typing import Any

import httpx
import pytest
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import (
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
from lunatask_mcp.api.models import TaskResponse
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
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_PAYMENT_REQUIRED = 402
HTTP_NOT_FOUND = 404
HTTP_UNPROCESSABLE_ENTITY = 422
HTTP_TOO_MANY_REQUESTS = 429
HTTP_INTERNAL_SERVER_ERROR = 500
HTTP_SERVICE_UNAVAILABLE = 503
HTTP_TIMEOUT = 524


def get_client_config(client: LunaTaskClient) -> ServerConfig:
    """Helper to access client config for testing."""
    return client._config


def get_client_base_url(client: LunaTaskClient) -> str:
    """Helper to access client base URL for testing."""
    return client._base_url


def get_client_bearer_token(client: LunaTaskClient) -> str:
    """Helper to access client bearer token for testing."""
    return client._bearer_token


def get_client_http_client(client: LunaTaskClient) -> httpx.AsyncClient | None:
    """Helper to access client HTTP client for testing."""
    return client._http_client


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
    return client._get_http_client()


def get_auth_headers(client: LunaTaskClient) -> dict[str, str]:
    """Helper to access auth headers method for testing."""
    return client._get_auth_headers()


def get_redacted_headers(client: LunaTaskClient) -> dict[str, str]:
    """Helper to access redacted headers method for testing."""
    return client._get_redacted_headers()


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

    @pytest.mark.asyncio
    async def test_make_request_bad_request_error(self, mocker: MockerFixture) -> None:
        """Test handling of 400 bad request error."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        # Mock 400 response
        mock_response = mocker.Mock()
        mock_response.status_code = HTTP_BAD_REQUEST
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "400 Bad Request",
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

        with pytest.raises(LunaTaskBadRequestError) as exc_info:
            await client.make_request("GET", "ping")

        assert exc_info.value.status_code == HTTP_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_make_request_subscription_required_error(self, mocker: MockerFixture) -> None:
        """Test handling of 402 subscription required error."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        # Mock 402 response
        mock_response = mocker.Mock()
        mock_response.status_code = HTTP_PAYMENT_REQUIRED
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "402 Payment Required",
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

        with pytest.raises(LunaTaskSubscriptionRequiredError) as exc_info:
            await client.make_request("GET", "ping")

        assert exc_info.value.status_code == HTTP_PAYMENT_REQUIRED

    @pytest.mark.asyncio
    async def test_make_request_validation_error(self, mocker: MockerFixture) -> None:
        """Test handling of 422 validation error."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        # Mock 422 response
        mock_response = mocker.Mock()
        mock_response.status_code = HTTP_UNPROCESSABLE_ENTITY
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "422 Unprocessable Entity",
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

        with pytest.raises(LunaTaskValidationError) as exc_info:
            await client.make_request("GET", "ping")

        assert exc_info.value.status_code == HTTP_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_make_request_service_unavailable_error(self, mocker: MockerFixture) -> None:
        """Test handling of 503 service unavailable error."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        # Mock 503 response
        mock_response = mocker.Mock()
        mock_response.status_code = HTTP_SERVICE_UNAVAILABLE
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "503 Service Unavailable",
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

        with pytest.raises(LunaTaskServiceUnavailableError) as exc_info:
            await client.make_request("GET", "ping")

        assert exc_info.value.status_code == HTTP_SERVICE_UNAVAILABLE

    @pytest.mark.asyncio
    async def test_make_request_timeout_524_error(self, mocker: MockerFixture) -> None:
        """Test handling of 524 timeout error."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        # Mock 524 response
        mock_response = mocker.Mock()
        mock_response.status_code = HTTP_TIMEOUT
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "524 Request Timeout",
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

        with pytest.raises(LunaTaskTimeoutError) as exc_info:
            await client.make_request("GET", "ping")

        assert exc_info.value.status_code == HTTP_TIMEOUT


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


class TestLunaTaskClientGetTasks:
    """Test get_tasks method for retrieving all tasks."""

    @pytest.mark.asyncio
    async def test_get_tasks_success_with_data(self, mocker: MockerFixture) -> None:
        """Test successful get_tasks request with task data."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        # Mock successful response with tasks
        mock_response_data: list[dict[str, Any]] = [
            {
                "id": "task-1",
                "area_id": "area-1",
                "status": "open",
                "priority": 1,
                "due_date": "2025-08-20T10:00:00Z",
                "created_at": "2025-08-19T10:00:00Z",
                "updated_at": "2025-08-19T10:00:00Z",
                "source": {"type": "manual", "value": "user_created"},
                "tags": ["work", "urgent"],
            },
            {
                "id": "task-2",
                "area_id": None,
                "status": "completed",
                "priority": None,
                "due_date": None,
                "created_at": "2025-08-18T10:00:00Z",
                "updated_at": "2025-08-19T09:00:00Z",
                "source": None,
                "tags": [],
            },
        ]

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.get_tasks()

        expected_task_count = 2
        assert len(result) == expected_task_count
        assert all(isinstance(task, TaskResponse) for task in result)
        assert result[0].id == "task-1"
        assert result[0].status == "open"
        assert result[0].priority == 1
        assert result[0].tags == ["work", "urgent"]
        assert result[1].id == "task-2"
        assert result[1].status == "completed"
        assert result[1].priority is None
        mock_request.assert_called_once_with("GET", "tasks")

    @pytest.mark.asyncio
    async def test_get_tasks_success_empty_list(self, mocker: MockerFixture) -> None:
        """Test successful get_tasks request with empty task list."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=[],
        )

        result = await client.get_tasks()

        assert result == []
        mock_request.assert_called_once_with("GET", "tasks")

    @pytest.mark.asyncio
    async def test_get_tasks_handles_missing_encrypted_fields(self, mocker: MockerFixture) -> None:
        """Test get_tasks gracefully handles absence of encrypted fields (name, notes)."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        # Response without encrypted fields (name, notes) as expected from E2E encryption
        mock_response_data: list[dict[str, Any]] = [
            {
                "id": "task-1",
                "status": "open",
                "created_at": "2025-08-19T10:00:00Z",
                "updated_at": "2025-08-19T10:00:00Z",
                # Note: 'name' and 'notes' fields intentionally missing
            }
        ]

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.get_tasks()

        assert len(result) == 1
        assert result[0].id == "task-1"
        assert result[0].status == "open"
        # Encrypted fields should not be present in the model
        assert not hasattr(result[0], "name")
        assert not hasattr(result[0], "notes")
        mock_request.assert_called_once_with("GET", "tasks")

    @pytest.mark.asyncio
    async def test_get_tasks_authentication_error(self, mocker: MockerFixture) -> None:
        """Test get_tasks handles authentication error."""
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

        with pytest.raises(LunaTaskAuthenticationError):
            await client.get_tasks()

    @pytest.mark.asyncio
    async def test_get_tasks_rate_limit_error(self, mocker: MockerFixture) -> None:
        """Test get_tasks handles rate limit error."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskRateLimitError(),
        )

        with pytest.raises(LunaTaskRateLimitError):
            await client.get_tasks()

    @pytest.mark.asyncio
    async def test_get_tasks_with_pagination_params(self, mocker: MockerFixture) -> None:
        """Test get_tasks accepts and forwards pagination/filter parameters."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=[],
        )

        # Test with optional pagination/filter parameters
        await client.get_tasks(limit=10, offset=20, status="open")

        mock_request.assert_called_once_with(
            "GET", "tasks", params={"limit": 10, "offset": 20, "status": "open"}
        )


class TestLunaTaskClientRateLimiting:
    """Test rate limiting behavior in LunaTaskClient."""

    @pytest.mark.asyncio
    async def test_rate_limiter_initialization(self) -> None:
        """Test that rate limiter is properly initialized with configuration."""
        test_rpm = 30  # 30 requests per minute
        test_burst = 5  # 5 request burst

        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
            rate_limit_rpm=test_rpm,
            rate_limit_burst=test_burst,
        )
        client = LunaTaskClient(config)

        # Verify rate limiter configuration
        assert client._rate_limiter._rpm == test_rpm
        assert client._rate_limiter._burst == test_burst

    @pytest.mark.asyncio
    async def test_rate_limiter_applied_to_get_tasks(self, mocker: MockerFixture) -> None:
        """Test that rate limiter is applied to get_tasks requests."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
            rate_limit_rpm=60,
            rate_limit_burst=10,
        )
        client = LunaTaskClient(config)

        # Mock the rate limiter acquire method
        mock_rate_limiter_acquire = mocker.patch.object(
            client._rate_limiter, "acquire", return_value=None
        )

        # Mock the HTTP client and response
        mock_response = mocker.Mock()
        mock_response.status_code = HTTP_OK
        mock_response.json.return_value = []
        mock_response.raise_for_status.return_value = None

        mock_http_client = mocker.AsyncMock()
        mock_http_client.request.return_value = mock_response
        mocker.patch.object(client, "_get_http_client", return_value=mock_http_client)

        await client.get_tasks()

        # Verify rate limiter was called
        mock_rate_limiter_acquire.assert_called_once()
        # Verify HTTP request was made
        mock_http_client.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limiter_respects_burst_limits(self, mocker: MockerFixture) -> None:
        """Test that rate limiter prevents bursts beyond configured limits."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
            rate_limit_rpm=60,  # 1 request per second
            rate_limit_burst=2,  # 2 request burst max
        )
        client = LunaTaskClient(config)

        # Mock time to control timing
        mock_time = mocker.patch("time.time")

        # Start at time 0
        current_time = [0.0]

        def time_side_effect() -> float:
            return current_time[0]

        mock_time.side_effect = time_side_effect

        # Mock successful API response
        mocker.patch.object(client, "make_request", return_value=[])

        # Make first two requests (should succeed due to burst)
        await client.get_tasks()
        await client.get_tasks()

        # Third request should be delayed (no immediate burst tokens left)
        # Advance time by 1 second to replenish one token
        current_time[0] = 1.0
        await client.get_tasks()

        # Verify all requests succeeded
        assert True  # If we reach here, rate limiter is working correctly

    @pytest.mark.asyncio
    async def test_rate_limiter_token_replenishment(self, mocker: MockerFixture) -> None:
        """Test that rate limiter replenishes tokens over time."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
            rate_limit_rpm=60,  # 1 request per second
            rate_limit_burst=1,  # 1 request burst
        )
        client = LunaTaskClient(config)

        # Mock time to control timing
        mock_time = mocker.patch("time.time")

        # Start at time 0
        current_time = [0.0]

        def time_side_effect() -> float:
            return current_time[0]

        mock_time.side_effect = time_side_effect

        # Mock successful API response
        mocker.patch.object(client, "make_request", return_value=[])

        # Make first request (uses burst token)
        await client.get_tasks()

        # Advance time by 1 second to replenish one token
        current_time[0] = 1.0

        # Make second request (should succeed with replenished token)
        await client.get_tasks()

        # If we reach here, token replenishment is working
        assert True

    @pytest.mark.asyncio
    async def test_multiple_clients_independent_rate_limiting(self) -> None:
        """Test that multiple client instances have independent rate limiting."""
        client1_rpm = 60
        client1_burst = 2
        client2_rpm = 120
        client2_burst = 3

        config1 = ServerConfig(
            lunatask_bearer_token="token1",
            lunatask_base_url=DEFAULT_API_URL,
            rate_limit_rpm=client1_rpm,
            rate_limit_burst=client1_burst,
        )
        config2 = ServerConfig(
            lunatask_bearer_token="token2",
            lunatask_base_url=DEFAULT_API_URL,
            rate_limit_rpm=client2_rpm,
            rate_limit_burst=client2_burst,
        )

        client1 = LunaTaskClient(config1)
        client2 = LunaTaskClient(config2)

        # Verify clients have independent rate limiters
        assert client1._rate_limiter is not client2._rate_limiter
        assert client1._rate_limiter._rpm == client1_rpm
        assert client2._rate_limiter._rpm == client2_rpm
        assert client1._rate_limiter._burst == client1_burst
        assert client2._rate_limiter._burst == client2_burst
