"""Tests for Task 4: Configuration integration into CoreServer.

This module tests the integration of configuration into the CoreServer class
and verifies that configuration is properly used by the server components.
"""

import logging

import pytest
from pydantic import HttpUrl
from pytest_mock import MockerFixture

from lunatask_mcp.config import ServerConfig
from lunatask_mcp.main import CoreServer


class TestConfigurationIntegration:
    """Test class for configuration integration functionality."""

    def test_core_server_accepts_configuration(self, default_config: ServerConfig) -> None:
        """Test that CoreServer accepts a ServerConfig instance."""
        server = CoreServer(default_config)
        assert server.config is default_config

    def test_core_server_uses_log_level_from_config(self, mocker: MockerFixture) -> None:
        """Test that CoreServer uses log level from configuration."""
        # Create config with DEBUG log level
        config = ServerConfig(
            lunatask_bearer_token="test_token",  # noqa: S106 - test token
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
            log_level="DEBUG",
            port=9090,
        )

        mock_basic_config = mocker.patch("logging.basicConfig")

        CoreServer(config)

        # Verify that logging was configured with DEBUG level
        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args
        assert call_args[1]["level"] == logging.DEBUG

    def test_core_server_uses_log_level_from_config_warning(self, mocker: MockerFixture) -> None:
        """Test that CoreServer uses WARNING log level from configuration."""
        config = ServerConfig(
            lunatask_bearer_token="test_token",  # noqa: S106 - test token
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
            log_level="WARNING",
            port=8081,
        )

        mock_basic_config = mocker.patch("logging.basicConfig")

        CoreServer(config)

        # Verify that logging was configured with WARNING level
        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args
        assert call_args[1]["level"] == logging.WARNING

    def test_get_lunatask_config_returns_api_settings(self, default_config: ServerConfig) -> None:
        """Test that get_lunatask_config returns correct API settings."""
        server = CoreServer(default_config)
        api_config = server.get_lunatask_config()

        expected_config = {
            "bearer_token": default_config.lunatask_bearer_token,
            "base_url": str(default_config.lunatask_base_url),
        }

        assert api_config == expected_config

    def test_get_config_returns_server_config(self, default_config: ServerConfig) -> None:
        """Test that get_config returns the ServerConfig instance."""
        server = CoreServer(default_config)
        returned_config = server.get_config()

        assert returned_config is default_config

    def test_bearer_token_accessible_for_api_integration(self) -> None:
        """Test that bearer token is accessible for LunaTask API integration."""
        test_token = "test_bearer_token_12345"  # noqa: S105 - test token
        config = ServerConfig(
            lunatask_bearer_token=test_token,
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
        )

        server = CoreServer(config)
        api_config = server.get_lunatask_config()

        assert api_config["bearer_token"] == test_token

    def test_base_url_accessible_for_api_integration(self) -> None:
        """Test that base URL is accessible for LunaTask API integration."""
        test_url = "https://custom.lunatask.app/v2/"
        config = ServerConfig(
            lunatask_bearer_token="test_token",  # noqa: S106 - test token
            lunatask_base_url=HttpUrl(test_url),
        )

        server = CoreServer(config)
        api_config = server.get_lunatask_config()

        assert api_config["base_url"] == test_url

    @pytest.mark.asyncio
    async def test_server_initializes_with_custom_port_config(self) -> None:
        """Test that server initializes with custom port configuration."""
        config = ServerConfig(
            lunatask_bearer_token="test_token",  # noqa: S106 - test token
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
            port=9999,
        )

        server = CoreServer(config)

        # Verify that configuration is stored and accessible
        expected_port = 9999  # Test port value
        assert server.config.port == expected_port

        # Verify that the server can still be created successfully
        assert server.app is not None
