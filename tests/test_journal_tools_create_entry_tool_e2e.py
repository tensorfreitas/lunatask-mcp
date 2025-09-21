"""End-to-end tests for JournalTools.create_journal_entry tool."""

from __future__ import annotations

import inspect
from datetime import date
from unittest.mock import AsyncMock

import pytest
from fastmcp import FastMCP
from fastmcp.server.context import Context as ServerContext
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import (
    LunaTaskAPIError,
    LunaTaskAuthenticationError,
    LunaTaskNetworkError,
    LunaTaskRateLimitError,
    LunaTaskServerError,
    LunaTaskServiceUnavailableError,
    LunaTaskSubscriptionRequiredError,
    LunaTaskTimeoutError,
    LunaTaskValidationError,
)
from lunatask_mcp.api.models import JournalEntryCreate
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.journal import JournalTools
from tests.factories import create_journal_entry_response


class TestCreateJournalEntryToolEndToEnd:
    """End-to-end validation for create_journal_entry MCP tool."""

    def _build_tools(self) -> tuple[FastMCP, LunaTaskClient, JournalTools]:
        """Create configured MCP, client, and tool instances for tests."""

        mcp = FastMCP("test-server")
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )
        client = LunaTaskClient(config)
        tools = JournalTools(mcp, client)
        return mcp, client, tools

    def test_create_journal_entry_tool_registration(self) -> None:
        """Tool should register with FastMCP and expose expected schema."""

        mcp, _client, _tools = self._build_tools()

        tool_manager = mcp._tool_manager  # type: ignore[attr-defined]
        registered_tools = tool_manager._tools.values()  # type: ignore[attr-defined]

        tool_names = [tool.name for tool in registered_tools]
        assert "create_journal_entry" in tool_names

        create_entry_tool = next(
            tool for tool in registered_tools if tool.name == "create_journal_entry"
        )
        assert create_entry_tool.description is not None
        assert "Create a journal entry" in create_entry_tool.description

        try:
            if hasattr(create_entry_tool, "input_schema"):
                schema = getattr(create_entry_tool, "input_schema", None)
                if isinstance(schema, dict) and "properties" in schema:
                    properties = schema["properties"]  # type: ignore[index]
                    for param in ["date_on", "name", "content"]:
                        assert param in properties
        except (AttributeError, KeyError, TypeError):
            pass

    @pytest.mark.asyncio
    async def test_create_journal_entry_tool_success(self, mocker: MockerFixture) -> None:
        """Tool should execute and return structured success payload."""

        _mcp, client, tools = self._build_tools()
        mock_ctx = mocker.AsyncMock(spec=ServerContext)

        journal_entry = create_journal_entry_response(entry_id="journal-abc")

        create_entry_mock: AsyncMock = mocker.AsyncMock(return_value=journal_entry)
        mocker.patch.object(client, "create_journal_entry", create_entry_mock)
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await tools.create_journal_entry_tool(
            ctx=mock_ctx,
            date_on="2025-09-20",
            name="Daily reflection",
            content="Today was productive.",
        )

        assert result["success"] is True
        assert result["journal_entry_id"] == "journal-abc"
        assert result["message"] == "Journal entry created successfully"

        create_entry_mock.assert_awaited_once()
        await_args = create_entry_mock.await_args
        assert await_args is not None
        payload = await_args.args[0]
        assert isinstance(payload, JournalEntryCreate)
        assert payload.date_on == date.fromisoformat("2025-09-20")
        assert payload.name == "Daily reflection"
        assert payload.content == "Today was productive."

        mock_ctx.info.assert_any_call("Creating journal entry")
        mock_ctx.info.assert_any_call("Successfully created journal entry journal-abc")

    @pytest.mark.asyncio
    async def test_create_journal_entry_tool_invalid_date(self, mocker: MockerFixture) -> None:
        """Invalid ISO dates should produce validation error payloads."""

        _mcp, client, tools = self._build_tools()
        mock_ctx = mocker.AsyncMock(spec=ServerContext)

        mock_create = mocker.patch.object(client, "create_journal_entry", mocker.AsyncMock())

        result = await tools.create_journal_entry_tool(
            ctx=mock_ctx,
            date_on="20-09-2025",
        )

        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "Invalid date_on format" in result["message"]

        mock_ctx.error.assert_called_once()
        assert mock_create.await_count == 0

    @pytest.mark.asyncio
    async def test_create_journal_entry_tool_validation_error(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Tool should surface API validation errors in structured format."""

        _mcp, client, tools = self._build_tools()
        mock_ctx = mocker.AsyncMock(spec=ServerContext)

        mocker.patch.object(
            client,
            "create_journal_entry",
            side_effect=LunaTaskValidationError("Payload invalid"),
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await tools.create_journal_entry_tool(
            ctx=mock_ctx,
            date_on="2025-09-20",
        )

        assert result["success"] is False
        assert result["error"] == "validation_error"
        assert "Payload invalid" in result["message"]
        mock_ctx.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_journal_entry_tool_subscription_required(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Tool should map subscription errors to subscription_required."""

        _mcp, client, tools = self._build_tools()
        mock_ctx = mocker.AsyncMock(spec=ServerContext)

        mocker.patch.object(
            client,
            "create_journal_entry",
            side_effect=LunaTaskSubscriptionRequiredError("Upgrade required"),
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await tools.create_journal_entry_tool(
            ctx=mock_ctx,
            date_on="2025-09-20",
        )

        assert result["success"] is False
        assert result["error"] == "subscription_required"
        assert "Upgrade required" in result["message"]
        mock_ctx.error.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("exception", "error_key"),
        [
            (LunaTaskAuthenticationError("Invalid token"), "authentication_error"),
            (LunaTaskRateLimitError("Too many requests"), "rate_limit_error"),
            (LunaTaskServerError("Internal error"), "server_error"),
            (LunaTaskServiceUnavailableError("Maintenance"), "server_error"),
            (LunaTaskTimeoutError("Request timed out"), "timeout_error"),
            (LunaTaskNetworkError("Network unreachable"), "network_error"),
            (LunaTaskAPIError("API failure"), "api_error"),
        ],
    )
    async def test_create_journal_entry_tool_maps_additional_errors(
        self,
        mocker: MockerFixture,
        exception: Exception,
        error_key: str,
    ) -> None:
        """Tool should map remaining LunaTask errors to structured responses."""

        _mcp, client, tools = self._build_tools()
        mock_ctx = mocker.AsyncMock(spec=ServerContext)

        mocker.patch.object(
            client,
            "create_journal_entry",
            mocker.AsyncMock(side_effect=exception),
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await tools.create_journal_entry_tool(
            ctx=mock_ctx,
            date_on="2025-09-20",
        )

        assert result["success"] is False
        assert result["error"] == error_key
        assert str(exception) in result["message"]
        mock_ctx.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_registered_journal_tool_delegates(self, mocker: MockerFixture) -> None:
        """Registered FastMCP tool should delegate to create_journal_entry_tool."""

        mcp, client, _tools = self._build_tools()
        mock_ctx = mocker.AsyncMock(spec=ServerContext)

        journal_entry = create_journal_entry_response(entry_id="journal-wrapper")

        mocker.patch.object(
            client,
            "create_journal_entry",
            mocker.AsyncMock(return_value=journal_entry),
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        tool_manager = mcp._tool_manager  # type: ignore[attr-defined]
        registered_tool = next(
            tool
            for tool in tool_manager._tools.values()  # type: ignore[attr-defined]
            if tool.name == "create_journal_entry"
        )

        result = await registered_tool.fn(  # type: ignore[call-arg]
            ctx=mock_ctx,
            date_on="2025-09-21",
            name="Wrapper",
            content="Delegated call",
        )

        assert result["success"] is True
        assert result["journal_entry_id"] == "journal-wrapper"
        mock_ctx.info.assert_any_call("Successfully created journal entry journal-wrapper")

    @pytest.mark.asyncio
    async def test_create_journal_entry_tool_unexpected_error(self, mocker: MockerFixture) -> None:
        """Unexpected exceptions should map to unexpected_error payloads."""

        _mcp, client, tools = self._build_tools()
        mock_ctx = mocker.AsyncMock(spec=ServerContext)

        mock_logger = mocker.patch("lunatask_mcp.tools.journal.logger")

        mocker.patch.object(
            client,
            "create_journal_entry",
            mocker.AsyncMock(side_effect=RuntimeError("Disk failure")),
        )
        mocker.patch.object(client, "__aenter__", return_value=client)
        mocker.patch.object(client, "__aexit__", return_value=None)

        result = await tools.create_journal_entry_tool(
            ctx=mock_ctx,
            date_on="2025-09-20",
        )

        assert result["success"] is False
        assert result["error"] == "unexpected_error"
        assert "Unexpected error creating journal entry" in result["message"]
        assert "Disk failure" in result["message"]

        mock_ctx.error.assert_called_once()
        mock_logger.exception.assert_called_once_with(
            "Unexpected error during journal entry creation"
        )

    def test_create_journal_entry_tool_signature(self) -> None:
        """Tool signature should expose context-first parameters."""

        _mcp, _client, tools = self._build_tools()
        signature = inspect.signature(tools.create_journal_entry_tool)
        params = list(signature.parameters.keys())

        assert params[0] == "ctx"
        assert "date_on" in params
        assert "name" in params
        assert "content" in params
