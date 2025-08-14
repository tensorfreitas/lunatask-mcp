"""Pytest fixtures and configuration for the test suite."""

import pytest
from pydantic import HttpUrl

from lunatask_mcp.config import ServerConfig


@pytest.fixture
def default_config() -> ServerConfig:
    """Provide a default ServerConfig instance for testing.

    Returns:
        ServerConfig: A configured ServerConfig instance with test values.
    """
    return ServerConfig(
        lunatask_bearer_token="test_token_123",  # noqa: S106 - test token
        lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        port=8080,
        log_level="INFO",
        config_file=None,
    )
