"""Tests for HabitTools.track_habit_tool()."""
# pyright: reportPrivateUsage=false

from __future__ import annotations

from datetime import date

import pytest
from fastmcp.server.context import Context as ServerContext
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
from lunatask_mcp.tools.habits import HabitTools
from tests.test_api_client_common import DEFAULT_API_URL, VALID_TOKEN


class TestHabitToolsTrackTool:
    """Test suite for HabitTools.track_habit_tool() method."""

    @pytest.fixture
    def mock_context(self, mocker: MockerFixture) -> ServerContext:
        """Create a mock server context."""
        mock_ctx = mocker.MagicMock(spec=ServerContext)
        mock_logger = mocker.MagicMock()
        mock_ctx.logger = mock_logger
        return mock_ctx

    @pytest.fixture
    def client_config(self) -> ServerConfig:
        """Create a client configuration for testing."""
        return ServerConfig(lunatask_bearer_token=VALID_TOKEN, lunatask_base_url=DEFAULT_API_URL)

    @pytest.fixture
    def lunatask_client(self, client_config: ServerConfig) -> LunaTaskClient:
        """Create a LunaTaskClient for testing."""
        return LunaTaskClient(client_config)

    @pytest.fixture
    def habit_tools(self, lunatask_client: LunaTaskClient, mocker: MockerFixture) -> HabitTools:
        """Create HabitTools instance for testing."""
        mock_mcp = mocker.MagicMock()
        return HabitTools(mock_mcp, lunatask_client)

    @pytest.mark.asyncio
    async def test_track_habit_tool_success(
        self, habit_tools: HabitTools, mock_context: ServerContext, mocker: MockerFixture
    ) -> None:
        """Test successful habit tracking via MCP tool."""
        habit_id = "habit-123"
        date_str = "2025-09-06"

        # Mock the client method
        mock_track_habit = mocker.patch.object(
            habit_tools.lunatask_client, "track_habit", return_value=None
        )

        # Call the MCP tool method
        result = await habit_tools.track_habit_tool(mock_context, habit_id, date_str)

        # Verify the result
        expected_result = {
            "ok": True,
            "message": f"Successfully tracked habit {habit_id} on {date_str}",
        }
        assert result == expected_result

        # Verify the client method was called with correct parameters
        mock_track_habit.assert_called_once_with(habit_id, date(2025, 9, 6))

    @pytest.mark.asyncio
    async def test_track_habit_tool_authentication_error(
        self, habit_tools: HabitTools, mock_context: ServerContext, mocker: MockerFixture
    ) -> None:
        """Test habit tracking tool with authentication error."""
        habit_id = "habit-123"
        date_str = "2025-09-06"

        # Mock the client method to raise authentication error
        mock_track_habit = mocker.patch.object(
            habit_tools.lunatask_client,
            "track_habit",
            side_effect=LunaTaskAuthenticationError("Invalid token"),
        )

        # Expect the exception to be raised (tools should not catch API errors)
        with pytest.raises(LunaTaskAuthenticationError, match="Invalid token"):
            await habit_tools.track_habit_tool(mock_context, habit_id, date_str)

        # Verify the client method was called
        mock_track_habit.assert_called_once()

    @pytest.mark.asyncio
    async def test_track_habit_tool_not_found_error(
        self, habit_tools: HabitTools, mock_context: ServerContext, mocker: MockerFixture
    ) -> None:
        """Test habit tracking tool with habit not found error."""
        habit_id = "nonexistent-habit"
        date_str = "2025-09-06"

        # Mock the client method to raise not found error
        mock_track_habit = mocker.patch.object(
            habit_tools.lunatask_client,
            "track_habit",
            side_effect=LunaTaskNotFoundError("Habit not found"),
        )

        # Expect the exception to be raised
        with pytest.raises(LunaTaskNotFoundError, match="Habit not found"):
            await habit_tools.track_habit_tool(mock_context, habit_id, date_str)

        # Verify the client method was called
        mock_track_habit.assert_called_once()

    @pytest.mark.asyncio
    async def test_track_habit_tool_validation_error(
        self, habit_tools: HabitTools, mock_context: ServerContext, mocker: MockerFixture
    ) -> None:
        """Test habit tracking tool with validation error."""
        habit_id = "habit-123"
        date_str = "2025-09-06"

        # Mock the client method to raise validation error
        mock_track_habit = mocker.patch.object(
            habit_tools.lunatask_client,
            "track_habit",
            side_effect=LunaTaskValidationError("Invalid date format"),
        )

        # Expect the exception to be raised
        with pytest.raises(LunaTaskValidationError, match="Invalid date format"):
            await habit_tools.track_habit_tool(mock_context, habit_id, date_str)

        # Verify the client method was called
        mock_track_habit.assert_called_once()

    @pytest.mark.asyncio
    async def test_track_habit_tool_invalid_date_format(
        self, habit_tools: HabitTools, mock_context: ServerContext
    ) -> None:
        """Test habit tracking tool with invalid date format."""
        habit_id = "habit-123"
        invalid_date_str = "invalid-date"

        # Don't mock the client - expect ValueError to be raised by date parsing
        with pytest.raises(ValueError, match="Invalid date format"):
            await habit_tools.track_habit_tool(mock_context, habit_id, invalid_date_str)

    @pytest.mark.asyncio
    async def test_track_habit_tool_rate_limit_error(
        self, habit_tools: HabitTools, mock_context: ServerContext, mocker: MockerFixture
    ) -> None:
        """Test habit tracking tool with rate limit error."""
        habit_id = "habit-123"
        date_str = "2025-09-06"

        # Mock the client method to raise rate limit error
        mock_track_habit = mocker.patch.object(
            habit_tools.lunatask_client,
            "track_habit",
            side_effect=LunaTaskRateLimitError("Rate limit exceeded"),
        )

        # Expect the exception to be raised
        with pytest.raises(LunaTaskRateLimitError, match="Rate limit exceeded"):
            await habit_tools.track_habit_tool(mock_context, habit_id, date_str)

        # Verify the client method was called
        mock_track_habit.assert_called_once()

    @pytest.mark.asyncio
    async def test_track_habit_tool_server_error(
        self, habit_tools: HabitTools, mock_context: ServerContext, mocker: MockerFixture
    ) -> None:
        """Test habit tracking tool with server error."""
        habit_id = "habit-123"
        date_str = "2025-09-06"

        # Mock the client method to raise server error
        mock_track_habit = mocker.patch.object(
            habit_tools.lunatask_client,
            "track_habit",
            side_effect=LunaTaskServerError("Internal server error"),
        )

        # Expect the exception to be raised
        with pytest.raises(LunaTaskServerError, match="Internal server error"):
            await habit_tools.track_habit_tool(mock_context, habit_id, date_str)

        # Verify the client method was called
        mock_track_habit.assert_called_once()

    @pytest.mark.asyncio
    async def test_track_habit_tool_timeout_error(
        self, habit_tools: HabitTools, mock_context: ServerContext, mocker: MockerFixture
    ) -> None:
        """Test habit tracking tool with timeout error."""
        habit_id = "habit-123"
        date_str = "2025-09-06"

        # Mock the client method to raise timeout error
        mock_track_habit = mocker.patch.object(
            habit_tools.lunatask_client,
            "track_habit",
            side_effect=LunaTaskTimeoutError("Request timeout"),
        )

        # Expect the exception to be raised
        with pytest.raises(LunaTaskTimeoutError, match="Request timeout"):
            await habit_tools.track_habit_tool(mock_context, habit_id, date_str)

        # Verify the client method was called
        mock_track_habit.assert_called_once()

    @pytest.mark.asyncio
    async def test_track_habit_tool_network_error(
        self, habit_tools: HabitTools, mock_context: ServerContext, mocker: MockerFixture
    ) -> None:
        """Test habit tracking tool with network error."""
        habit_id = "habit-123"
        date_str = "2025-09-06"

        # Mock the client method to raise network error
        mock_track_habit = mocker.patch.object(
            habit_tools.lunatask_client,
            "track_habit",
            side_effect=LunaTaskNetworkError("Network connection failed"),
        )

        # Expect the exception to be raised
        with pytest.raises(LunaTaskNetworkError, match="Network connection failed"):
            await habit_tools.track_habit_tool(mock_context, habit_id, date_str)

        # Verify the client method was called
        mock_track_habit.assert_called_once()

    @pytest.mark.asyncio
    async def test_habit_tools_registration(
        self, mocker: MockerFixture, client_config: ServerConfig
    ) -> None:
        """Test that HabitTools properly registers the track_habit tool."""
        # Create mocks
        mock_mcp = mocker.MagicMock()
        lunatask_client = LunaTaskClient(client_config)

        # Create HabitTools instance (should register tools)
        habit_tools = HabitTools(mock_mcp, lunatask_client)

        # Verify _register_tools was called during initialization
        assert hasattr(habit_tools, "mcp")
        assert hasattr(habit_tools, "lunatask_client")
        assert habit_tools.mcp is mock_mcp
        assert habit_tools.lunatask_client is lunatask_client
