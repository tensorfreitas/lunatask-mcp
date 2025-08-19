"""Tests for configuration precedence (CLI > file > defaults)."""

import argparse
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from lunatask_mcp.config import ServerConfig
from lunatask_mcp.main import load_configuration

# ruff: noqa: PLR2004,S105 - Magic values and test tokens are acceptable in test files


class TestConfigurationPrecedence:
    """Test class for configuration precedence functionality."""

    def test_cli_overrides_file_values(self) -> None:
        """Test that CLI arguments override configuration file values."""
        # Create temporary config file with specific values
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            config_content = """
lunatask_bearer_token = "file_token"
port = 8888
log_level = "ERROR"
rate_limit_rpm = 120
rate_limit_burst = 20
http_retries = 5
http_backoff_start_seconds = 1.0
http_user_agent = "file-agent/1.0"
timeout_connect = 10.0
timeout_read = 60.0
"""
            f.write(config_content)
            config_file_path = f.name

        try:
            # Create args that override file values
            args = argparse.Namespace(
                config_file=config_file_path,
                port=9999,  # Override file value
                log_level="DEBUG",  # Override file value
            )

            config = load_configuration(args)

            # CLI values should override file values
            assert config.port == 9999
            assert config.log_level == "DEBUG"

            # File values should be used where CLI didn't override
            assert config.lunatask_bearer_token == "file_token"
            assert config.rate_limit_rpm == 120
            assert config.rate_limit_burst == 20
            assert config.http_retries == 5
            assert config.http_backoff_start_seconds == 1.0
            assert config.http_user_agent == "file-agent/1.0"
            assert config.timeout_connect == 10.0
            assert config.timeout_read == 60.0

        finally:
            Path(config_file_path).unlink()

    def test_file_overrides_defaults(self) -> None:
        """Test that configuration file values override defaults."""
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            config_content = """
lunatask_bearer_token = "file_token"
port = 7777
log_level = "WARNING"
rate_limit_rpm = 240
rate_limit_burst = 30
http_retries = 3
http_backoff_start_seconds = 0.5
http_user_agent = "custom-agent/2.0"
timeout_connect = 15.0
timeout_read = 90.0
"""
            f.write(config_content)
            config_file_path = f.name

        try:
            # Args with no overrides
            args = argparse.Namespace(
                config_file=config_file_path,
                port=None,
                log_level=None,
            )

            config = load_configuration(args)

            # File values should override defaults
            assert config.port == 7777  # Default: 8080
            assert config.log_level == "WARNING"  # Default: INFO
            assert config.rate_limit_rpm == 240  # Default: 60
            assert config.rate_limit_burst == 30  # Default: 10
            assert config.http_retries == 3  # Default: 2
            assert config.http_backoff_start_seconds == 0.5  # Default: 0.25
            assert config.http_user_agent == "custom-agent/2.0"  # Default: lunatask-mcp/0.1.0
            assert config.timeout_connect == 15.0  # Default: 5.0
            assert config.timeout_read == 90.0  # Default: 30.0

        finally:
            Path(config_file_path).unlink()

    def test_defaults_used_when_no_overrides(self) -> None:
        """Test that default values are used when no file or CLI overrides exist."""
        # Create minimal config file with only required token
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            config_content = """
lunatask_bearer_token = "test_token"
"""
            f.write(config_content)
            config_file_path = f.name

        try:
            args = argparse.Namespace(
                config_file=config_file_path,
                port=None,
                log_level=None,
            )

            config = load_configuration(args)

            # Should use default values for fields not specified in file or CLI
            assert config.port == 8080
            assert config.log_level == "INFO"
            assert config.rate_limit_rpm == 60
            assert config.rate_limit_burst == 10
            assert config.http_retries == 2
            assert config.http_backoff_start_seconds == 0.25
            assert config.http_user_agent == "lunatask-mcp/0.1.0"
            assert config.timeout_connect == 5.0
            assert config.timeout_read == 30.0

        finally:
            Path(config_file_path).unlink()

    def test_complex_precedence_scenario(self) -> None:
        """Test complex scenario with all three sources (CLI > file > defaults)."""
        # Create config file with some values
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            config_content = """
lunatask_bearer_token = "file_token"
port = 8888
rate_limit_rpm = 180
http_retries = 4
timeout_connect = 12.0
"""
            f.write(config_content)
            config_file_path = f.name

        try:
            # CLI overrides only some values
            args = argparse.Namespace(
                config_file=config_file_path,
                port=9999,  # CLI override
                log_level="DEBUG",  # CLI override (not in file)
            )

            config = load_configuration(args)

            # CLI overrides
            assert config.port == 9999
            assert config.log_level == "DEBUG"

            # File values (not overridden by CLI)
            assert config.lunatask_bearer_token == "file_token"
            assert config.rate_limit_rpm == 180
            assert config.http_retries == 4
            assert config.timeout_connect == 12.0

            # Defaults (not in CLI or file)
            assert config.rate_limit_burst == 10  # Default
            assert config.http_backoff_start_seconds == 0.25  # Default
            assert config.http_user_agent == "lunatask-mcp/0.1.0"  # Default
            assert config.timeout_read == 30.0  # Default

        finally:
            Path(config_file_path).unlink()

    def test_new_config_fields_validation(self) -> None:
        """Test that new configuration fields are properly validated."""
        # Test direct ServerConfig creation with new fields
        config = ServerConfig(
            lunatask_bearer_token="test_token",
            rate_limit_rpm=100,
            rate_limit_burst=15,
            http_retries=3,
            http_backoff_start_seconds=0.5,
            http_user_agent="test-agent/1.0",
            timeout_connect=8.0,
            timeout_read=45.0,
        )

        assert config.rate_limit_rpm == 100
        assert config.rate_limit_burst == 15
        assert config.http_retries == 3
        assert config.http_backoff_start_seconds == 0.5
        assert config.http_user_agent == "test-agent/1.0"
        assert config.timeout_connect == 8.0
        assert config.timeout_read == 45.0

    def test_config_field_validation_limits(self) -> None:
        """Test that configuration field validation enforces limits."""
        # Test http_retries bounds - use ValidationError from Pydantic v2
        with pytest.raises(ValidationError, match="Input should be greater than or equal to 0"):
            ServerConfig(
                lunatask_bearer_token="test_token",
                http_retries=-1,
            )

        with pytest.raises(ValidationError, match="Input should be less than or equal to 5"):
            ServerConfig(
                lunatask_bearer_token="test_token",
                http_retries=6,
            )

        # Test timeout bounds
        with pytest.raises(ValidationError):
            ServerConfig(
                lunatask_bearer_token="test_token",
                timeout_connect=0.5,  # Below minimum
            )

        with pytest.raises(ValidationError):
            ServerConfig(
                lunatask_bearer_token="test_token",
                timeout_read=150.0,  # Above maximum
            )
