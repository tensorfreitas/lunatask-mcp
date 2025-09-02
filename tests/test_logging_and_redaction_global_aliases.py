"""Logging and token redaction tests for global alias resources.

Validates that:
- Logging goes to stderr (stdout remains clean for MCP JSON-RPC)
- Bearer tokens never appear in logs when invoking global alias resources

These tests exercise the LunaTaskClient.make_request() debug logging
via the global alias resource handler to ensure redaction occurs.
"""

from __future__ import annotations

import logging
import sys
from io import StringIO
from typing import Any, cast

import pytest
from fastmcp import Context, FastMCP
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.main import CoreServer
from lunatask_mcp.tools.tasks import TaskTools


@pytest.mark.asyncio
async def test_global_alias_logging_goes_to_stderr_and_not_stdout(
    mocker: MockerFixture,
) -> None:
    """Ensure logs during global alias resolution go to stderr only.

    Sets up logging via CoreServer (INFO by default), forces DEBUG on logger
    to capture client debug output, and verifies stdout purity.
    """

    # Capture stdout/stderr
    captured_stdout = StringIO()
    captured_stderr = StringIO()
    mocker.patch.object(sys, "stdout", captured_stdout)
    mocker.patch.object(sys, "stderr", captured_stderr)

    # Configure logging to stderr using CoreServer
    config = ServerConfig(
        lunatask_bearer_token="test_secret_token",
        lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        log_level="DEBUG",  # ensure debug logs are emitted
    )
    CoreServer(config)  # sets up logging.basicConfig(stream=sys.stderr)

    # Build TaskTools with a real client; we'll stub HTTP
    mcp = FastMCP("test-server")
    client = LunaTaskClient(config)
    TaskTools(mcp, client)

    # Patch client's HTTP request to avoid real network
    # We want make_request() to run so it logs redacted headers at DEBUG
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"tasks": []}

    mock_http = mocker.AsyncMock()
    mock_http.request.return_value = mock_response
    mocker.patch.object(client, "_get_http_client", return_value=mock_http)

    # Grab the global/today handler
    registry: dict[str, Any] = {}

    def capture(uri: str) -> object:
        def deco(fn: object) -> object:
            registry[uri] = fn
            return fn

        return deco

    mocker.patch.object(mcp, "resource", side_effect=capture)
    # Re-register to populate registry
    TaskTools(mcp, client)

    fn = registry["lunatask://global/today"]  # (ctx)

    class Ctx:
        async def info(self, _: str) -> None:  # Google-style: returns None
            return

    await fn(cast(Context, Ctx()))

    # stdout must remain pure (no logging)
    assert captured_stdout.getvalue() == ""
    # stderr should contain some log lines (while stdout stays empty)
    assert captured_stderr.getvalue() != ""


@pytest.mark.asyncio
async def test_global_alias_logs_do_not_leak_bearer_token(
    mocker: MockerFixture, caplog: pytest.LogCaptureFixture
) -> None:
    """Ensure bearer token never appears in stderr logs for global alias operations."""

    captured_stderr = StringIO()
    mocker.patch.object(sys, "stderr", captured_stderr)

    # Configure DEBUG to capture client debug with redacted headers
    secret = "super_duper_secret_token_ABC123"  # noqa: S105 - test token fixture
    config = ServerConfig(
        lunatask_bearer_token=secret,
        lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        log_level="DEBUG",
    )
    CoreServer(config)

    # Ensure root level is DEBUG for this test regardless of environment
    logging.getLogger().setLevel(logging.DEBUG)
    caplog.set_level(logging.DEBUG)

    # Setup TaskTools and client with mocked HTTP
    mcp = FastMCP("test-server")
    client = LunaTaskClient(config)
    TaskTools(mcp, client)

    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"tasks": []}

    mock_http = mocker.AsyncMock()
    mock_http.request.return_value = mock_response
    mocker.patch.object(client, "_get_http_client", return_value=mock_http)

    # Call through a global alias to trigger make_request logging
    registry: dict[str, Any] = {}

    def capture(uri: str) -> object:
        def deco(fn: object) -> object:
            registry[uri] = fn
            return fn

        return deco

    mocker.patch.object(mcp, "resource", side_effect=capture)
    TaskTools(mcp, client)

    fn = registry["lunatask://global/now"]  # (ctx)

    class Ctx:
        async def info(self, _: str) -> None:
            return

    await fn(cast(Context, Ctx()))

    # Validate using pytest's logging capture to ensure we see debug logs
    log_text = caplog.text
    # Token must never appear in logs
    assert secret not in log_text
    # Redacted marker should appear in logs where headers are emitted
    assert "Bearer ***redacted***" in log_text
