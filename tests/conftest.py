"""Pytest fixtures and configuration for the test suite."""

import tempfile
from collections.abc import Generator, Sequence
from pathlib import Path
from typing import cast

import pytest
from fastmcp import FastMCP
from pydantic import HttpUrl
from pytest_mock import AsyncMockType, MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.tools.tasks import TaskTools


@pytest.fixture
def default_config() -> ServerConfig:
    """Provide a default ServerConfig instance for testing.

    Returns:
        ServerConfig: A configured ServerConfig instance with test values.
    """
    return ServerConfig(
        lunatask_bearer_token="test_token_123",
        lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        port=8080,
        log_level="INFO",
        config_file=None,
    )


@pytest.fixture
def mcp() -> FastMCP:
    """Provide a FastMCP instance for testing.

    Returns:
        FastMCP: A FastMCP instance with a test server name.
    """
    return FastMCP("test-server")


@pytest.fixture
def config() -> ServerConfig:
    """Provide a ServerConfig instance for testing.

    Returns:
        ServerConfig: A ServerConfig instance with test values.
    """
    return ServerConfig(
        lunatask_bearer_token="test_token",
        lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
    )


@pytest.fixture
def client(config: ServerConfig) -> LunaTaskClient:
    """Provide a LunaTaskClient instance for testing.

    Args:
        config: A ServerConfig fixture.

    Returns:
        LunaTaskClient: A LunaTaskClient instance.
    """
    return LunaTaskClient(config)


@pytest.fixture
def task_tools(mcp: FastMCP, client: LunaTaskClient) -> TaskTools:
    """Provide a TaskTools instance for testing.

    Args:
        mcp: A FastMCP fixture.
        client: A LunaTaskClient fixture.

    Returns:
        TaskTools: A TaskTools instance.
    """
    return TaskTools(mcp, client)


@pytest.fixture
def async_ctx(mocker: MockerFixture) -> AsyncMockType:
    """Provide an async context mock for testing.

    Args:
        mocker: Pytest mocker fixture.

    Returns:
        AsyncMock: An async context mock with a test session ID.
    """
    mock_ctx = mocker.AsyncMock()
    mock_ctx.session_id = "test-session-123"
    return mock_ctx


@pytest.fixture
def temp_config_file() -> Generator[str, None, None]:
    """Create a temporary config file for integration tests.

    Yields:
        str: Path to a temporary TOML config file used by stdio integration tests.
    """
    config_content = """
lunatask_bearer_token = "test_integration_token"
port = 8080
log_level = "INFO"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(config_content)
        temp_path = f.name

    try:
        yield temp_path
    finally:
        Path(temp_path).unlink(missing_ok=True)


def extract_tool_response_text(result: object) -> str | None:
    """Extract text content from a FastMCP tool call result.

    Uses duck typing to avoid depending on internal FastMCP classes.

    Args:
        result: The FastMCP tool call result object.

    Returns:
        str | None: The extracted text content, or None if extraction fails.
    """

    try:
        contents = getattr(result, "content", None)
        if contents:
            for content_item in contents:
                text = getattr(content_item, "text", None)
                if text is not None:
                    return str(text)
            try:
                seq = cast(Sequence[object], contents)
                return str(seq[0])
            except Exception:
                return str(contents)
        return str(result)
    except Exception:
        return None
