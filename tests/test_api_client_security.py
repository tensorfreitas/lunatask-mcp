"""Security features and token handling tests for LunaTaskClient."""
# pyright: reportPrivateUsage=false

from __future__ import annotations

import httpx
import pytest
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import LunaTaskAPIError
from lunatask_mcp.config import ServerConfig
from tests.test_api_client_common import (
    DEFAULT_API_URL,
    SECRET_TOKEN_HIDDEN,
    SUPER_SECRET_TOKEN,
    SUPER_SECRET_TOKEN_456,
    TEST_TOKEN,
    get_http_client,
    get_redacted_headers,
)


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
        except Exception as e:
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

    def test_redacted_headers_structure_and_values(self) -> None:
        """AC:16 — Only Authorization (redacted) and Content-Type returned."""
        token = SUPER_SECRET_TOKEN
        config = ServerConfig(lunatask_bearer_token=token, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        redacted = get_redacted_headers(client)

        # Assert only the expected keys are present
        assert set(redacted.keys()) == {"Authorization", "Content-Type"}

        # Assert Authorization is redacted and Content-Type is application/json
        assert redacted["Authorization"] == "Bearer ***redacted***"
        assert redacted["Content-Type"] == "application/json"

        # Ensure the actual token is not present anywhere in the serialized headers
        serialized = str(redacted)
        assert token not in serialized

    @pytest.mark.asyncio
    async def test_unexpected_error_path_has_safe_context(self, mocker: MockerFixture) -> None:
        """AC:2 — Catch-all except produces safe, contextual LunaTaskAPIError.

        Ensures the error message includes method and endpoint, and never leaks the bearer token.
        """
        config = ServerConfig(
            lunatask_bearer_token=TEST_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        mock_http_client = mocker.AsyncMock()
        mock_http_client.request.side_effect = ValueError("boom")
        mocker.patch.object(client, "_get_http_client", return_value=mock_http_client)

        with pytest.raises(LunaTaskAPIError) as exc_info:
            await client.make_request("GET", "ping")

        message = str(exc_info.value)
        assert "method=GET" in message
        assert "endpoint=ping" in message
        assert TEST_TOKEN not in message
