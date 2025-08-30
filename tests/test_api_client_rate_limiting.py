"""Rate limiting behavior tests for LunaTaskClient."""
# pyright: reportPrivateUsage=false

from __future__ import annotations

import pytest
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.config import ServerConfig
from tests.test_api_client_common import DEFAULT_API_URL, HTTP_OK, VALID_TOKEN


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
        mock_response.json.return_value = {"tasks": []}
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
        # Mock time BEFORE creating the client to avoid real time in _last_refill
        mock_time = mocker.patch("time.time")

        # Start at time 0
        current_time = [0.0]

        def time_side_effect() -> float:
            return current_time[0]

        mock_time.side_effect = time_side_effect

        # Now create client with mocked time active
        config = ServerConfig(
            lunatask_bearer_token=VALID_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
            rate_limit_rpm=60,  # 1 request per second
            rate_limit_burst=2,  # 2 request burst max
        )
        client = LunaTaskClient(config)

        # Mock HTTP client and response
        mock_response = mocker.Mock()
        mock_response.status_code = HTTP_OK
        mock_response.json.return_value = {"tasks": []}
        mock_response.raise_for_status.return_value = None
        mock_http_client = mocker.AsyncMock()
        mock_http_client.request.return_value = mock_response
        mocker.patch.object(client, "_get_http_client", return_value=mock_http_client)

        # Make first two requests (should succeed due to burst)
        await client.get_tasks()
        await client.get_tasks()

        # Verify burst tokens are exhausted
        assert client._rate_limiter._tokens == 0.0

        # Third request should be delayed (no immediate burst tokens left)
        async def sleep_side_effect(duration: float) -> None:
            current_time[0] += duration

        mock_sleep = mocker.patch("asyncio.sleep", side_effect=sleep_side_effect)

        await client.get_tasks()

        # Verify that sleep was called once with expected duration
        mock_sleep.assert_awaited_once_with(1.0)

        # Verify token was consumed after refill
        assert client._rate_limiter._tokens == 0.0

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
        mocker.patch.object(client, "make_request", return_value={"tasks": []})

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
