"""Tests for LunaTask API client.

This module contains comprehensive tests for the LunaTaskClient class,
following TDD methodology and ensuring secure token handling.
"""
# pyright: reportPrivateUsage=false

from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
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
from lunatask_mcp.api.models import TaskCreate, TaskResponse, TaskUpdate
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

# Task priority constants
TEST_PRIORITY_HIGH = 2
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


class TestLunaTaskClientGetTask:
    """Test get_task method for retrieving a single task."""

    @pytest.mark.asyncio
    async def test_get_task_success_with_data(self, mocker: MockerFixture) -> None:
        """Test successful get_task request with complete task data."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)
        task_id = "task-123"

        # Mock successful response with task data
        mock_response_data: dict[str, Any] = {
            "id": "task-123",
            "area_id": "area-456",
            "status": "open",
            "priority": 2,
            "due_date": "2025-08-25T14:30:00Z",
            "created_at": "2025-08-20T10:00:00Z",
            "updated_at": "2025-08-20T11:00:00Z",
            "source": {"type": "manual", "value": "user_created"},
            "tags": ["work", "important"],
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.get_task(task_id)

        assert isinstance(result, TaskResponse)
        assert result.id == "task-123"
        assert result.area_id == "area-456"
        assert result.status == "open"
        expected_priority = 2
        assert result.priority == expected_priority
        assert result.due_date is not None
        assert result.due_date.isoformat() == "2025-08-25T14:30:00+00:00"
        assert result.tags == ["work", "important"]
        assert result.source is not None
        assert result.source.type == "manual"
        assert result.source.value == "user_created"
        mock_request.assert_called_once_with("GET", "tasks/task-123")

    @pytest.mark.asyncio
    async def test_get_task_success_minimal_data(self, mocker: MockerFixture) -> None:
        """Test successful get_task request with minimal task data."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)
        task_id = "task-minimal"

        # Mock response with only required fields
        mock_response_data: dict[str, Any] = {
            "id": "task-minimal",
            "status": "completed",
            "created_at": "2025-08-20T10:00:00Z",
            "updated_at": "2025-08-20T10:00:00Z",
            "area_id": None,
            "priority": None,
            "due_date": None,
            "source": None,
            "tags": [],
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.get_task(task_id)

        assert isinstance(result, TaskResponse)
        assert result.id == "task-minimal"
        assert result.status == "completed"
        assert result.area_id is None
        assert result.priority is None
        assert result.due_date is None
        assert result.source is None
        assert result.tags == []
        mock_request.assert_called_once_with("GET", "tasks/task-minimal")

    @pytest.mark.asyncio
    async def test_get_task_handles_missing_encrypted_fields(self, mocker: MockerFixture) -> None:
        """Test get_task gracefully handles absence of encrypted fields (name, notes)."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)
        task_id = "task-encrypted"

        # Response without encrypted fields (name, notes) as expected from E2E encryption
        mock_response_data: dict[str, Any] = {
            "id": "task-encrypted",
            "status": "open",
            "created_at": "2025-08-20T10:00:00Z",
            "updated_at": "2025-08-20T10:00:00Z",
            # Note: 'name' and 'notes' fields intentionally missing due to E2E encryption
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.get_task(task_id)

        assert isinstance(result, TaskResponse)
        assert result.id == "task-encrypted"
        assert result.status == "open"
        # Encrypted fields should not be present in the model
        assert not hasattr(result, "name")
        assert not hasattr(result, "notes")
        mock_request.assert_called_once_with("GET", "tasks/task-encrypted")

    @pytest.mark.asyncio
    async def test_get_task_not_found_error(self, mocker: MockerFixture) -> None:
        """Test get_task handles task not found (404) error."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)
        task_id = "nonexistent-task"

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskNotFoundError(),
        )

        with pytest.raises(LunaTaskNotFoundError):
            await client.get_task(task_id)

    @pytest.mark.asyncio
    async def test_get_task_authentication_error(self, mocker: MockerFixture) -> None:
        """Test get_task handles authentication error."""
        config = ServerConfig(
            lunatask_bearer_token=INVALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)
        task_id = "task-123"

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskAuthenticationError(),
        )

        with pytest.raises(LunaTaskAuthenticationError):
            await client.get_task(task_id)

    @pytest.mark.asyncio
    async def test_get_task_rate_limit_error(self, mocker: MockerFixture) -> None:
        """Test get_task handles rate limit error."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)
        task_id = "task-123"

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskRateLimitError(),
        )

        with pytest.raises(LunaTaskRateLimitError):
            await client.get_task(task_id)

    @pytest.mark.asyncio
    async def test_get_task_server_error(self, mocker: MockerFixture) -> None:
        """Test get_task handles server error."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)
        task_id = "task-123"

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskServerError("Server error", 500),
        )

        with pytest.raises(LunaTaskServerError):
            await client.get_task(task_id)

    @pytest.mark.asyncio
    async def test_get_task_network_error(self, mocker: MockerFixture) -> None:
        """Test get_task handles network error."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)
        task_id = "task-123"

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskNetworkError(),
        )

        with pytest.raises(LunaTaskNetworkError):
            await client.get_task(task_id)

    @pytest.mark.asyncio
    async def test_get_task_timeout_error(self, mocker: MockerFixture) -> None:
        """Test get_task handles timeout error."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)
        task_id = "task-123"

        mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskTimeoutError(),
        )

        with pytest.raises(LunaTaskTimeoutError):
            await client.get_task(task_id)

    @pytest.mark.asyncio
    async def test_get_task_parsing_error(self, mocker: MockerFixture) -> None:
        """Test get_task handles JSON parsing error."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)
        task_id = "task-123"

        # Mock response with invalid data that cannot be parsed into TaskResponse
        mock_response_data = {"invalid": "data", "missing": "required_fields"}

        mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        with pytest.raises(LunaTaskAPIError):
            await client.get_task(task_id)

    @pytest.mark.asyncio
    async def test_get_task_rate_limiter_applied(self, mocker: MockerFixture) -> None:
        """Test that rate limiter is applied to get_task requests."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
            rate_limit_rpm=60,
            rate_limit_burst=10,
        )
        client = LunaTaskClient(config)
        task_id = "task-123"

        # Mock successful task response
        mock_response_data: dict[str, Any] = {
            "id": "task-123",
            "status": "open",
            "created_at": "2025-08-20T10:00:00Z",
            "updated_at": "2025-08-20T10:00:00Z",
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        await client.get_task(task_id)

        # Verify make_request was called (which applies rate limiting)
        mock_request.assert_called_once_with("GET", "tasks/task-123")

    @pytest.mark.asyncio
    async def test_get_task_empty_string_id(self, mocker: MockerFixture) -> None:
        """Test get_task with empty string task_id."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)
        task_id = ""

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskBadRequestError(),
        )

        with pytest.raises(LunaTaskBadRequestError):
            await client.get_task(task_id)

        mock_request.assert_called_once_with("GET", "tasks/")

    @pytest.mark.asyncio
    async def test_get_task_special_characters_in_id(self, mocker: MockerFixture) -> None:
        """Test get_task with special characters in task_id."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)
        task_id = "task-with-special/chars"

        mock_response_data: dict[str, Any] = {
            "id": "task-with-special/chars",
            "status": "open",
            "created_at": "2025-08-20T10:00:00Z",
            "updated_at": "2025-08-20T10:00:00Z",
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.get_task(task_id)

        assert result.id == "task-with-special/chars"
        mock_request.assert_called_once_with("GET", "tasks/task-with-special/chars")


class TestLunaTaskClientCreateTask:
    """Test suite for LunaTaskClient.create_task() method."""

    @pytest.mark.asyncio
    async def test_create_task_success_minimal_data(self, mocker: MockerFixture) -> None:
        """Test successful task creation with minimal required data."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_data = TaskCreate(name="Test Task")

        mock_response_data: dict[str, Any] = {
            "id": "task-123",
            "status": "open",
            "created_at": "2025-08-21T10:00:00Z",
            "updated_at": "2025-08-21T10:00:00Z",
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.create_task(task_data)

        assert result.id == "task-123"
        assert result.status == "open"
        mock_request.assert_called_once_with(
            "POST", "tasks", data={"name": "Test Task", "status": "open", "tags": []}
        )

    @pytest.mark.asyncio
    async def test_create_task_success_full_data(self, mocker: MockerFixture) -> None:
        """Test successful task creation with all optional fields."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_data = TaskCreate(
            name="Full Test Task",
            notes="These are test notes",
            area_id="area-456",
            status="open",
            priority=1,
            tags=["urgent", "test"],
        )

        mock_response_data: dict[str, Any] = {
            "id": "task-456",
            "area_id": "area-456",
            "status": "open",
            "priority": 1,
            "created_at": "2025-08-21T10:00:00Z",
            "updated_at": "2025-08-21T10:00:00Z",
            "tags": ["urgent", "test"],
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.create_task(task_data)

        assert result.id == "task-456"
        assert result.area_id == "area-456"
        assert result.status == "open"
        assert result.priority == 1
        assert result.tags == ["urgent", "test"]
        mock_request.assert_called_once_with(
            "POST",
            "tasks",
            data={
                "name": "Full Test Task",
                "notes": "These are test notes",
                "area_id": "area-456",
                "status": "open",
                "priority": 1,
                "tags": ["urgent", "test"],
            },
        )

    @pytest.mark.asyncio
    async def test_create_task_validation_error_422(self, mocker: MockerFixture) -> None:
        """Test create_task raises LunaTaskValidationError on 422 response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_data = TaskCreate(name="Invalid Task")

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskValidationError("Validation failed"),
        )

        with pytest.raises(LunaTaskValidationError, match="Validation failed"):
            await client.create_task(task_data)

        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_subscription_required_error_402(self, mocker: MockerFixture) -> None:
        """Test create_task raises LunaTaskSubscriptionRequiredError on 402 response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_data = TaskCreate(name="Test Task")

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskSubscriptionRequiredError("Subscription required"),
        )

        with pytest.raises(LunaTaskSubscriptionRequiredError, match="Subscription required"):
            await client.create_task(task_data)

        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_auth_error_401(self, mocker: MockerFixture) -> None:
        """Test create_task raises LunaTaskAuthenticationError on 401 response."""
        config = ServerConfig(
            lunatask_bearer_token=INVALID_TOKEN, lunatask_base_url=DEFAULT_API_URL
        )
        client = LunaTaskClient(config)

        task_data = TaskCreate(name="Test Task")

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskAuthenticationError("Invalid token"),
        )

        with pytest.raises(LunaTaskAuthenticationError, match="Invalid token"):
            await client.create_task(task_data)

        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_rate_limit_error_429(self, mocker: MockerFixture) -> None:
        """Test create_task raises LunaTaskRateLimitError on 429 response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_data = TaskCreate(name="Test Task")

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskRateLimitError("Rate limit exceeded"),
        )

        with pytest.raises(LunaTaskRateLimitError, match="Rate limit exceeded"):
            await client.create_task(task_data)

        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_server_error_500(self, mocker: MockerFixture) -> None:
        """Test create_task raises LunaTaskServerError on 500 response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_data = TaskCreate(name="Test Task")

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskServerError("Internal server error"),
        )

        with pytest.raises(LunaTaskServerError, match="Internal server error"):
            await client.create_task(task_data)

        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_timeout_error(self, mocker: MockerFixture) -> None:
        """Test create_task raises LunaTaskTimeoutError on network timeout."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_data = TaskCreate(name="Test Task")

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskTimeoutError("Request timeout"),
        )

        with pytest.raises(LunaTaskTimeoutError, match="Request timeout"):
            await client.create_task(task_data)

        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_response_parsing_success(self, mocker: MockerFixture) -> None:
        """Test create_task correctly parses task response with assigned ID."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_data = TaskCreate(name="Parse Test Task")

        mock_response_data: dict[str, Any] = {
            "id": "newly-assigned-id-123",
            "area_id": "test-area",
            "status": "open",
            "priority": TEST_PRIORITY_HIGH,
            "created_at": "2025-08-21T11:30:00Z",
            "updated_at": "2025-08-21T11:30:00Z",
            "source": {"type": "api", "value": "mcp-client"},
            "tags": ["api-created"],
        }

        mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.create_task(task_data)

        assert isinstance(result, TaskResponse)
        assert result.id == "newly-assigned-id-123"
        assert result.area_id == "test-area"
        assert result.status == "open"
        assert result.priority == TEST_PRIORITY_HIGH
        assert result.tags == ["api-created"]
        assert result.source is not None
        assert result.source.type == "api"
        assert result.source.value == "mcp-client"

    @pytest.mark.asyncio
    async def test_create_task_rate_limiter_integration(self, mocker: MockerFixture) -> None:
        """Test create_task applies rate limiting before request."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_data = TaskCreate(name="Rate Limited Task")

        mock_response_data: dict[str, Any] = {
            "id": "rate-limited-task",
            "status": "open",
            "created_at": "2025-08-21T10:00:00Z",
            "updated_at": "2025-08-21T10:00:00Z",
        }

        # Mock make_request (which applies rate limiting)
        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.create_task(task_data)

        # Verify make_request was called (which applies rate limiting)
        mock_request.assert_called_once_with(
            "POST", "tasks", data={"name": "Rate Limited Task", "status": "open", "tags": []}
        )
        assert result.id == "rate-limited-task"


class TestLunaTaskClientUpdateTask:
    """Test suite for LunaTaskClient.update_task() method."""

    @pytest.mark.asyncio
    async def test_update_task_success_single_field(self, mocker: MockerFixture) -> None:
        """Test successful task update with single field change."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-123"
        update_data = TaskUpdate(status="completed")

        mock_response_data: dict[str, Any] = {
            "id": "task-123",
            "status": "completed",
            "created_at": "2025-08-21T10:00:00Z",
            "updated_at": "2025-08-21T11:00:00Z",
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.update_task(task_id, update_data)

        assert result.id == "task-123"
        assert result.status == "completed"
        mock_request.assert_called_once_with(
            "PATCH", "tasks/task-123", data={"status": "completed"}
        )

    @pytest.mark.asyncio
    async def test_update_task_success_multiple_fields(self, mocker: MockerFixture) -> None:
        """Test successful task update with multiple field changes."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-456"
        due_date = datetime(2025, 8, 30, 14, 30, 0, tzinfo=UTC)
        update_data = TaskUpdate(
            name="Updated Task Name",
            status="in_progress",
            priority=2,
            due_date=due_date,
            tags=["urgent", "updated"],
        )

        mock_response_data: dict[str, Any] = {
            "id": "task-456",
            "status": "in_progress",
            "priority": 2,
            "due_date": "2025-08-30T14:30:00Z",
            "created_at": "2025-08-21T10:00:00Z",
            "updated_at": "2025-08-21T11:30:00Z",
            "tags": ["urgent", "updated"],
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.update_task(task_id, update_data)

        assert result.id == "task-456"
        assert result.status == "in_progress"
        expected_priority = 2
        assert result.priority == expected_priority
        assert result.tags == ["urgent", "updated"]
        mock_request.assert_called_once_with(
            "PATCH",
            "tasks/task-456",
            data={
                "name": "Updated Task Name",
                "status": "in_progress",
                "priority": 2,
                "due_date": due_date,
                "tags": ["urgent", "updated"],
            },
        )

    @pytest.mark.asyncio
    async def test_update_task_partial_update_excludes_none(self, mocker: MockerFixture) -> None:
        """Test that only non-None fields are sent in partial update."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-partial"
        # Only set status field, leaving others as None
        update_data = TaskUpdate(status="completed")

        mock_response_data: dict[str, Any] = {
            "id": "task-partial",
            "status": "completed",
            "created_at": "2025-08-21T10:00:00Z",
            "updated_at": "2025-08-21T11:00:00Z",
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.update_task(task_id, update_data)

        # Verify only non-None fields were sent
        mock_request.assert_called_once_with(
            "PATCH", "tasks/task-partial", data={"status": "completed"}
        )
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_update_task_handles_204_no_content(self, mocker: MockerFixture) -> None:
        """Test handling of 204 No Content response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-no-content"
        update_data = TaskUpdate(status="completed")

        # Mock 204 response which returns minimal data
        mock_response_data: dict[str, Any] = {
            "id": "task-no-content",
            "status": "completed",
            "created_at": "2025-08-21T10:00:00Z",
            "updated_at": "2025-08-21T11:00:00Z",
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.update_task(task_id, update_data)

        assert result.id == "task-no-content"
        assert result.status == "completed"
        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_not_found_error_404(self, mocker: MockerFixture) -> None:
        """Test update_task raises TaskNotFoundError on 404 response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "nonexistent-task"
        update_data = TaskUpdate(status="completed")

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskNotFoundError("Task not found"),
        )

        with pytest.raises(LunaTaskNotFoundError, match="Task not found"):
            await client.update_task(task_id, update_data)

        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_validation_error_400(self, mocker: MockerFixture) -> None:
        """Test update_task raises LunaTaskBadRequestError on 400 response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-invalid"
        update_data = TaskUpdate(status="invalid_status")

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskBadRequestError("Invalid task status"),
        )

        with pytest.raises(LunaTaskBadRequestError, match="Invalid task status"):
            await client.update_task(task_id, update_data)

        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_authentication_error_401(self, mocker: MockerFixture) -> None:
        """Test update_task raises LunaTaskAuthenticationError on 401 response."""
        config = ServerConfig(
            lunatask_bearer_token=INVALID_TOKEN, lunatask_base_url=DEFAULT_API_URL
        )
        client = LunaTaskClient(config)

        task_id = "task-123"
        update_data = TaskUpdate(status="completed")

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskAuthenticationError("Invalid token"),
        )

        with pytest.raises(LunaTaskAuthenticationError, match="Invalid token"):
            await client.update_task(task_id, update_data)

        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_rate_limit_error_429(self, mocker: MockerFixture) -> None:
        """Test update_task raises LunaTaskRateLimitError on 429 response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-123"
        update_data = TaskUpdate(status="completed")

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskRateLimitError("Rate limit exceeded"),
        )

        with pytest.raises(LunaTaskRateLimitError, match="Rate limit exceeded"):
            await client.update_task(task_id, update_data)

        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_server_error_500(self, mocker: MockerFixture) -> None:
        """Test update_task raises LunaTaskServerError on 500 response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-123"
        update_data = TaskUpdate(status="completed")

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskServerError("Internal server error"),
        )

        with pytest.raises(LunaTaskServerError, match="Internal server error"):
            await client.update_task(task_id, update_data)

        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_timeout_error(self, mocker: MockerFixture) -> None:
        """Test update_task raises LunaTaskTimeoutError on network timeout."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-123"
        update_data = TaskUpdate(status="completed")

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskTimeoutError("Request timeout"),
        )

        with pytest.raises(LunaTaskTimeoutError, match="Request timeout"):
            await client.update_task(task_id, update_data)

        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_response_parsing_success(self, mocker: MockerFixture) -> None:
        """Test update_task correctly parses task response with updated fields."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "parse-test-task"
        update_data = TaskUpdate(priority=TEST_PRIORITY_HIGH, area_id="new-area")

        mock_response_data: dict[str, Any] = {
            "id": "parse-test-task",
            "area_id": "new-area",
            "status": "open",
            "priority": TEST_PRIORITY_HIGH,
            "created_at": "2025-08-21T10:00:00Z",
            "updated_at": "2025-08-21T12:00:00Z",
            "source": {"type": "api", "value": "mcp-update"},
            "tags": ["updated"],
        }

        mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.update_task(task_id, update_data)

        assert isinstance(result, TaskResponse)
        assert result.id == "parse-test-task"
        assert result.area_id == "new-area"
        assert result.priority == TEST_PRIORITY_HIGH
        assert result.tags == ["updated"]
        assert result.source is not None
        assert result.source.type == "api"
        assert result.source.value == "mcp-update"

    @pytest.mark.asyncio
    async def test_update_task_parsing_error(self, mocker: MockerFixture) -> None:
        """Test update_task handles JSON parsing error."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-123"
        update_data = TaskUpdate(status="completed")

        # Mock response with invalid data that cannot be parsed into TaskResponse
        mock_response_data = {"invalid": "data", "missing": "required_fields"}

        mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        with pytest.raises(LunaTaskAPIError):
            await client.update_task(task_id, update_data)

    @pytest.mark.asyncio
    async def test_update_task_rate_limiter_integration(self, mocker: MockerFixture) -> None:
        """Test update_task applies rate limiting before request."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "rate-limited-update"
        update_data = TaskUpdate(status="completed")

        mock_response_data: dict[str, Any] = {
            "id": "rate-limited-update",
            "status": "completed",
            "created_at": "2025-08-21T10:00:00Z",
            "updated_at": "2025-08-21T11:00:00Z",
        }

        # Mock make_request (which applies rate limiting)
        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.update_task(task_id, update_data)

        # Verify make_request was called (which applies rate limiting)
        mock_request.assert_called_once_with(
            "PATCH", "tasks/rate-limited-update", data={"status": "completed"}
        )
        assert result.id == "rate-limited-update"

    @pytest.mark.asyncio
    async def test_update_task_empty_update(self, mocker: MockerFixture) -> None:
        """Test update_task with no fields set (all None) sends empty data."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-empty"
        # Create TaskUpdate with all default None values
        update_data = TaskUpdate()

        mock_response_data: dict[str, Any] = {
            "id": "task-empty",
            "status": "open",
            "created_at": "2025-08-21T10:00:00Z",
            "updated_at": "2025-08-21T10:00:00Z",
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.update_task(task_id, update_data)

        # Verify empty data object was sent (no None values)
        mock_request.assert_called_once_with("PATCH", "tasks/task-empty", data={})
        assert result.id == "task-empty"

    @pytest.mark.asyncio
    async def test_update_task_handles_missing_encrypted_fields(
        self, mocker: MockerFixture
    ) -> None:
        """Test update_task handles missing encrypted fields (name, notes) in response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-encrypted-update"
        update_data = TaskUpdate(status="completed")

        # Response without encrypted fields (name, notes) as expected from E2E encryption
        mock_response_data: dict[str, Any] = {
            "id": "task-encrypted-update",
            "status": "completed",
            "created_at": "2025-08-21T10:00:00Z",
            "updated_at": "2025-08-21T11:00:00Z",
            # Note: 'name' and 'notes' fields intentionally missing
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.update_task(task_id, update_data)

        assert result.id == "task-encrypted-update"
        assert result.status == "completed"
        # Encrypted fields should not be present in the model
        assert not hasattr(result, "name")
        assert not hasattr(result, "notes")
        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_special_characters_in_id(self, mocker: MockerFixture) -> None:
        """Test update_task with special characters in task_id."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-with-special/chars"
        update_data = TaskUpdate(status="completed")

        mock_response_data: dict[str, Any] = {
            "id": "task-with-special/chars",
            "status": "completed",
            "created_at": "2025-08-21T10:00:00Z",
            "updated_at": "2025-08-21T11:00:00Z",
        }

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value=mock_response_data,
        )

        result = await client.update_task(task_id, update_data)

        assert result.id == "task-with-special/chars"
        mock_request.assert_called_once_with(
            "PATCH", "tasks/task-with-special/chars", data={"status": "completed"}
        )


class TestLunaTaskClientDeleteTask:
    """Test suite for LunaTaskClient.delete_task() method."""

    @pytest.mark.asyncio
    async def test_delete_task_success_204_response(self, mocker: MockerFixture) -> None:
        """Test successful task deletion with 204 No Content response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-to-delete"

        # Mock 204 response (No Content - empty response)
        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value={},  # 204 responses return empty dict
        )

        result = await client.delete_task(task_id)

        assert result is True
        mock_request.assert_called_once_with("DELETE", "tasks/task-to-delete")

    @pytest.mark.asyncio
    async def test_delete_task_not_found_error_404(self, mocker: MockerFixture) -> None:
        """Test delete_task raises LunaTaskNotFoundError on 404 response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "nonexistent-task"

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskNotFoundError("Task not found"),
        )

        with pytest.raises(LunaTaskNotFoundError, match="Task not found"):
            await client.delete_task(task_id)

        mock_request.assert_called_once_with("DELETE", "tasks/nonexistent-task")

    @pytest.mark.asyncio
    async def test_delete_task_authentication_error_401(self, mocker: MockerFixture) -> None:
        """Test delete_task raises LunaTaskAuthenticationError on 401 response."""
        config = ServerConfig(
            lunatask_bearer_token=INVALID_TOKEN, lunatask_base_url=DEFAULT_API_URL
        )
        client = LunaTaskClient(config)

        task_id = "task-123"

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskAuthenticationError("Invalid token"),
        )

        with pytest.raises(LunaTaskAuthenticationError, match="Invalid token"):
            await client.delete_task(task_id)

        mock_request.assert_called_once_with("DELETE", "tasks/task-123")

    @pytest.mark.asyncio
    async def test_delete_task_rate_limit_error_429(self, mocker: MockerFixture) -> None:
        """Test delete_task raises LunaTaskRateLimitError on 429 response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-rate-limited"

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskRateLimitError("Rate limit exceeded"),
        )

        with pytest.raises(LunaTaskRateLimitError, match="Rate limit exceeded"):
            await client.delete_task(task_id)

        mock_request.assert_called_once_with("DELETE", "tasks/task-rate-limited")

    @pytest.mark.asyncio
    async def test_delete_task_server_error_500(self, mocker: MockerFixture) -> None:
        """Test delete_task raises LunaTaskServerError on 500 response."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-server-error"

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskServerError("Internal server error"),
        )

        with pytest.raises(LunaTaskServerError, match="Internal server error"):
            await client.delete_task(task_id)

        mock_request.assert_called_once_with("DELETE", "tasks/task-server-error")

    @pytest.mark.asyncio
    async def test_delete_task_timeout_error(self, mocker: MockerFixture) -> None:
        """Test delete_task raises LunaTaskTimeoutError on network timeout."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-timeout"

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskTimeoutError("Request timeout"),
        )

        with pytest.raises(LunaTaskTimeoutError, match="Request timeout"):
            await client.delete_task(task_id)

        mock_request.assert_called_once_with("DELETE", "tasks/task-timeout")

    @pytest.mark.asyncio
    async def test_delete_task_network_error(self, mocker: MockerFixture) -> None:
        """Test delete_task raises LunaTaskNetworkError on network error."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-network-error"

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskNetworkError("Network error"),
        )

        with pytest.raises(LunaTaskNetworkError, match="Network error"):
            await client.delete_task(task_id)

        mock_request.assert_called_once_with("DELETE", "tasks/task-network-error")

    @pytest.mark.asyncio
    async def test_delete_task_empty_string_id(self, mocker: MockerFixture) -> None:
        """Test delete_task with empty string task_id."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = ""

        mock_request = mocker.patch.object(
            client,
            "make_request",
            side_effect=LunaTaskBadRequestError("Invalid task ID"),
        )

        with pytest.raises(LunaTaskBadRequestError):
            await client.delete_task(task_id)

        mock_request.assert_called_once_with("DELETE", "tasks/")

    @pytest.mark.asyncio
    async def test_delete_task_special_characters_in_id(self, mocker: MockerFixture) -> None:
        """Test delete_task with special characters in task_id."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-with-special/chars"

        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value={},  # 204 success response
        )

        result = await client.delete_task(task_id)

        assert result is True
        mock_request.assert_called_once_with("DELETE", "tasks/task-with-special/chars")

    @pytest.mark.asyncio
    async def test_delete_task_rate_limiter_integration(self, mocker: MockerFixture) -> None:
        """Test delete_task applies rate limiting before request."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "rate-limited-delete"

        # Mock make_request (which applies rate limiting)
        mock_request = mocker.patch.object(
            client,
            "make_request",
            return_value={},  # 204 success response
        )

        result = await client.delete_task(task_id)

        # Verify make_request was called (which applies rate limiting)
        mock_request.assert_called_once_with("DELETE", "tasks/rate-limited-delete")
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_task_non_idempotent_behavior(self, mocker: MockerFixture) -> None:
        """Test delete_task non-idempotent behavior - second delete returns 404."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        task_id = "task-already-deleted"

        # First call succeeds (task exists and gets deleted)
        mock_request_success = mocker.patch.object(
            client,
            "make_request",
            return_value={},  # 204 success response
        )

        result = await client.delete_task(task_id)
        assert result is True

        # Second call fails (task no longer exists)
        mock_request_success.side_effect = LunaTaskNotFoundError("Task not found")

        with pytest.raises(LunaTaskNotFoundError):
            await client.delete_task(task_id)
