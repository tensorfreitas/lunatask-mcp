"""Tests for LunaTaskClient.track_habit()."""
# pyright: reportPrivateUsage=false

from __future__ import annotations

from datetime import date

import pytest
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import (
    LunaTaskAuthenticationError,
    LunaTaskNetworkError,
    LunaTaskNotFoundError,
    LunaTaskRateLimitError,
    LunaTaskServerError,
    LunaTaskTimeoutError,
    LunaTaskValidationError,
)
from lunatask_mcp.config import ServerConfig
from tests.test_api_client_common import (
    DEFAULT_API_URL,
    INVALID_TOKEN,
    VALID_TOKEN,
)


class TestLunaTaskClientTrackHabit:
    """Test suite for LunaTaskClient.track_habit() method."""

    @pytest.mark.asyncio
    async def test_track_habit_success(self, mocker: MockerFixture) -> None:
        """Test successful habit tracking."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        habit_id = "habit-123"
        track_date = date(2025, 9, 6)

        # Mock the make_request method to return None (successful with no content)
        mock_make_request = mocker.patch.object(client, "make_request", return_value=None)

        # Call the method
        result = await client.track_habit(habit_id, track_date)

        # Verify the method returns None for successful tracking
        assert result is None

        # Verify make_request was called with correct parameters
        mock_make_request.assert_called_once_with(
            "POST", f"habits/{habit_id}/track", data={"performed_on": "2025-09-06"}
        )

    @pytest.mark.asyncio
    async def test_track_habit_authentication_error(self, mocker: MockerFixture) -> None:
        """Test habit tracking with authentication error (401)."""
        config = ServerConfig(
            lunatask_bearer_token=INVALID_TOKEN, lunatask_base_url=DEFAULT_API_URL
        )
        client = LunaTaskClient(config)

        habit_id = "habit-123"
        track_date = date(2025, 9, 6)

        # Mock make_request to raise authentication error
        mock_make_request = mocker.patch.object(
            client, "make_request", side_effect=LunaTaskAuthenticationError("Invalid token")
        )

        # Expect the exception to be raised
        with pytest.raises(LunaTaskAuthenticationError, match="Invalid token"):
            await client.track_habit(habit_id, track_date)

        # Verify make_request was called
        mock_make_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_track_habit_not_found_error(self, mocker: MockerFixture) -> None:
        """Test habit tracking with habit not found error (404)."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        habit_id = "nonexistent-habit"
        track_date = date(2025, 9, 6)

        # Mock make_request to raise not found error
        mock_make_request = mocker.patch.object(
            client, "make_request", side_effect=LunaTaskNotFoundError("Habit not found")
        )

        # Expect the exception to be raised
        with pytest.raises(LunaTaskNotFoundError, match="Habit not found"):
            await client.track_habit(habit_id, track_date)

        # Verify make_request was called
        mock_make_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_track_habit_validation_error(self, mocker: MockerFixture) -> None:
        """Test habit tracking with validation error (422)."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        habit_id = "habit-123"
        track_date = date(2025, 9, 6)

        # Mock make_request to raise validation error
        mock_make_request = mocker.patch.object(
            client, "make_request", side_effect=LunaTaskValidationError("Invalid date format")
        )

        # Expect the exception to be raised
        with pytest.raises(LunaTaskValidationError, match="Invalid date format"):
            await client.track_habit(habit_id, track_date)

        # Verify make_request was called
        mock_make_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_track_habit_rate_limit_error(self, mocker: MockerFixture) -> None:
        """Test habit tracking with rate limit error (429)."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        habit_id = "habit-123"
        track_date = date(2025, 9, 6)

        # Mock make_request to raise rate limit error
        mock_make_request = mocker.patch.object(
            client, "make_request", side_effect=LunaTaskRateLimitError("Rate limit exceeded")
        )

        # Expect the exception to be raised
        with pytest.raises(LunaTaskRateLimitError, match="Rate limit exceeded"):
            await client.track_habit(habit_id, track_date)

        # Verify make_request was called
        mock_make_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_track_habit_server_error(self, mocker: MockerFixture) -> None:
        """Test habit tracking with server error (5xx)."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        habit_id = "habit-123"
        track_date = date(2025, 9, 6)

        # Mock make_request to raise server error
        mock_make_request = mocker.patch.object(
            client, "make_request", side_effect=LunaTaskServerError("Internal server error")
        )

        # Expect the exception to be raised
        with pytest.raises(LunaTaskServerError, match="Internal server error"):
            await client.track_habit(habit_id, track_date)

        # Verify make_request was called
        mock_make_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_track_habit_timeout_error(self, mocker: MockerFixture) -> None:
        """Test habit tracking with timeout error."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        habit_id = "habit-123"
        track_date = date(2025, 9, 6)

        # Mock make_request to raise timeout error
        mock_make_request = mocker.patch.object(
            client, "make_request", side_effect=LunaTaskTimeoutError("Request timeout")
        )

        # Expect the exception to be raised
        with pytest.raises(LunaTaskTimeoutError, match="Request timeout"):
            await client.track_habit(habit_id, track_date)

        # Verify make_request was called
        mock_make_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_track_habit_network_error(self, mocker: MockerFixture) -> None:
        """Test habit tracking with network error."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        habit_id = "habit-123"
        track_date = date(2025, 9, 6)

        # Mock make_request to raise network error
        mock_make_request = mocker.patch.object(
            client, "make_request", side_effect=LunaTaskNetworkError("Network connection failed")
        )

        # Expect the exception to be raised
        with pytest.raises(LunaTaskNetworkError, match="Network connection failed"):
            await client.track_habit(habit_id, track_date)

        # Verify make_request was called
        mock_make_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_track_habit_rate_limiter_invoked(self, mocker: MockerFixture) -> None:
        """Test that rate limiter is invoked before request (integration via make_request)."""
        config = ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)
        client = LunaTaskClient(config)

        habit_id = "habit-123"
        track_date = date(2025, 9, 6)

        # Mock make_request to verify it's called (rate limiter is inside make_request)
        mock_make_request = mocker.patch.object(client, "make_request", return_value=None)

        # Call the method
        await client.track_habit(habit_id, track_date)

        # Verify make_request was called (which includes rate limiter logic)
        mock_make_request.assert_called_once_with(
            "POST", f"habits/{habit_id}/track", data={"performed_on": "2025-09-06"}
        )
