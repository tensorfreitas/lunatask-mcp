"""Tests for the main entry point module."""

import pytest
from pytest_mock import MockerFixture

from lunatask_mcp.config import ServerConfig
from lunatask_mcp.main import CoreServer, main


def test_core_server_class_exists() -> None:
    """Test that CoreServer class is defined."""
    assert CoreServer is not None
    assert callable(CoreServer)


def test_main_function_exists() -> None:
    """Test that main function is defined and callable."""
    assert main is not None
    assert callable(main)


@pytest.mark.asyncio
async def test_core_server_initialization(default_config: ServerConfig) -> None:
    """Test CoreServer can be instantiated."""
    server = CoreServer(default_config)
    assert server is not None


def test_main_configures_logging_to_stderr(mocker: MockerFixture) -> None:
    """Test that main function configures logging to stderr."""
    mocker.patch("sys.stderr")
    # This test will be implemented after we create the main module


def test_main_does_not_print_to_stdout() -> None:
    """Test that main function doesn't output to stdout (MCP protocol requirement)."""
    # This test will validate stdout purity
