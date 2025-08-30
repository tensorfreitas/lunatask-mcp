"""Authenticated request and connectivity tests for LunaTaskClient."""
# pyright: reportPrivateUsage=false

from __future__ import annotations

import httpx
import pytest
from pytest_mock import MockerFixture

from lunatask_mcp.api import client as api_client
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
from lunatask_mcp.config import ServerConfig
from tests.test_api_client_common import (
    DEFAULT_API_URL,
    HTTP_BAD_GATEWAY,
    HTTP_BAD_REQUEST,
    HTTP_INTERNAL_SERVER_ERROR,
    HTTP_NOT_FOUND,
    HTTP_OK,
    HTTP_PAYMENT_REQUIRED,
    HTTP_SERVICE_UNAVAILABLE,
    HTTP_TIMEOUT,
    HTTP_TOO_MANY_REQUESTS,
    HTTP_UNAUTHORIZED,
    HTTP_UNPROCESSABLE_ENTITY,
    INVALID_TOKEN,
    VALID_TOKEN,
)


def test_http_bad_gateway_constant_value() -> None:
    """Ensure BAD_GATEWAY constant matches HTTP 502."""
    assert api_client._HTTP_BAD_GATEWAY == HTTP_BAD_GATEWAY  # pyright: ignore[reportPrivateUsage]


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
    async def test_make_request_bad_gateway_error(self, mocker: MockerFixture) -> None:
        """Test handling of 502 Bad Gateway server error."""
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        mock_response = mocker.Mock()
        mock_response.status_code = HTTP_BAD_GATEWAY
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "502 Bad Gateway",
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

        assert exc_info.value.status_code == HTTP_BAD_GATEWAY

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
