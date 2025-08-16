# ruff: noqa: S105, PLR2004
"""Tests for the configuration module.

This module contains comprehensive tests for the ServerConfig Pydantic model
and configuration loading functionality following TDD methodology.
"""

import argparse
import tempfile
from pathlib import Path

import pytest
from pydantic import HttpUrl, ValidationError
from pytest_mock import MockerFixture

from lunatask_mcp.config import ServerConfig
from lunatask_mcp.main import load_configuration


class TestServerConfigModel:
    """Test suite for the ServerConfig Pydantic model."""

    def test_server_config_default_values(self) -> None:
        """Test that ServerConfig initializes with correct default values."""
        config = ServerConfig(lunatask_bearer_token="test_token")

        assert str(config.lunatask_base_url) == "https://api.lunatask.app/v1/"
        assert config.port == 8080
        assert config.log_level == "INFO"
        assert config.config_file is None

    def test_server_config_required_bearer_token(self) -> None:
        """Test that lunatask_bearer_token is required and raises ValidationError when missing."""
        with pytest.raises(ValidationError) as exc_info:
            ServerConfig()  # type: ignore[call-arg] - testing missing required parameter

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "missing"
        assert "lunatask_bearer_token" in str(errors[0]["loc"])

    def test_server_config_with_valid_token(self) -> None:
        """Test that ServerConfig accepts valid bearer token."""
        config = ServerConfig(lunatask_bearer_token="test_token_123")

        assert config.lunatask_bearer_token == "test_token_123"
        assert str(config.lunatask_base_url) == "https://api.lunatask.app/v1/"
        assert config.port == 8080
        assert config.log_level == "INFO"

    def test_server_config_port_validation_valid_range(self) -> None:
        """Test that port accepts values in valid range [1, 65535]."""
        # Test minimum valid port
        config1 = ServerConfig(lunatask_bearer_token="token", port=1)
        assert config1.port == 1

        # Test maximum valid port
        config2 = ServerConfig(lunatask_bearer_token="token", port=65535)
        assert config2.port == 65535

        # Test typical port
        config3 = ServerConfig(lunatask_bearer_token="token", port=8080)
        assert config3.port == 8080

    def test_server_config_port_validation_invalid_range(self) -> None:
        """Test that port rejects values outside range [1, 65535]."""
        # Test port 0 (too low)
        with pytest.raises(ValidationError) as exc_info:
            ServerConfig(lunatask_bearer_token="token", port=0)
        errors = exc_info.value.errors()
        assert any("greater_than_equal" in str(error) for error in errors)

        # Test port 65536 (too high)
        with pytest.raises(ValidationError) as exc_info:
            ServerConfig(lunatask_bearer_token="token", port=65536)
        errors = exc_info.value.errors()
        assert any("less_than_equal" in str(error) for error in errors)

        # Test negative port
        with pytest.raises(ValidationError) as exc_info:
            ServerConfig(lunatask_bearer_token="token", port=-1)
        errors = exc_info.value.errors()
        assert any("greater_than_equal" in str(error) for error in errors)

    def test_server_config_base_url_validation_https_only(self) -> None:
        """Test that lunatask_base_url must be an absolute HTTPS URL."""
        # Valid HTTPS URL
        config = ServerConfig(
            lunatask_bearer_token="token",
            lunatask_base_url=HttpUrl("https://api.example.com/v1/"),
        )
        assert str(config.lunatask_base_url) == "https://api.example.com/v1/"

        # Invalid: HTTP URL
        with pytest.raises(ValidationError):
            ServerConfig(
                lunatask_bearer_token="token",
                lunatask_base_url="http://api.example.com/v1/",  # type: ignore[arg-type] - testing invalid HTTP URL
            )

        # Invalid: relative URL
        with pytest.raises(ValidationError):
            ServerConfig(
                lunatask_bearer_token="token",
                lunatask_base_url="/api/v1/",  # type: ignore[arg-type] - testing invalid relative URL
            )

        # Invalid: no protocol
        with pytest.raises(ValidationError):
            ServerConfig(
                lunatask_bearer_token="token",
                lunatask_base_url="api.example.com",  # type: ignore[arg-type] - testing invalid URL without protocol
            )

    def test_server_config_log_level_validation(self) -> None:
        """Test that log_level accepts only valid logging levels."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in valid_levels:
            config = ServerConfig(lunatask_bearer_token="token", log_level=level)  # type: ignore[arg-type] - loop variable type issue
            assert config.log_level == level

        # Invalid log level
        with pytest.raises(ValidationError) as exc_info:
            ServerConfig(lunatask_bearer_token="token", log_level="INVALID")  # type: ignore[arg-type] - testing invalid log level
        errors = exc_info.value.errors()
        assert any("literal_error" in str(error) or "enum" in str(error) for error in errors)

    def test_server_config_to_redacted_dict(self) -> None:
        """Test that to_redacted_dict() properly redacts sensitive information."""
        config = ServerConfig(
            lunatask_bearer_token="secret_token_123",
            lunatask_base_url=HttpUrl("https://api.lunatask.app/v1/"),
            port=9000,
            log_level="DEBUG",
            config_file="./custom.toml",
        )

        redacted = config.to_redacted_dict()

        assert redacted["lunatask_bearer_token"] == "***redacted***"
        assert redacted["lunatask_base_url"] == "https://api.lunatask.app/v1/"
        assert redacted["port"] == 9000
        assert redacted["log_level"] == "DEBUG"
        assert redacted["config_file"] == "./custom.toml"

    def test_server_config_to_redacted_dict_none_values(self) -> None:
        """Test that to_redacted_dict() handles None values correctly."""
        config = ServerConfig(lunatask_bearer_token="secret_token")
        redacted = config.to_redacted_dict()

        assert redacted["lunatask_bearer_token"] == "***redacted***"
        assert redacted["config_file"] is None


class TestConfigurationLoading:
    """Test suite for configuration file loading functionality (Task 3)."""

    def test_load_configuration_defaults_only(self, mocker: MockerFixture) -> None:
        """Test loading configuration with defaults only (no file, no CLI args)."""
        # When no config file and no CLI args, should fail due to missing bearer token
        args = argparse.Namespace(config_file=None, port=None, log_level=None)

        mocker.patch("pathlib.Path.exists", return_value=False)

        with pytest.raises(SystemExit) as exc_info:
            load_configuration(args)

        assert exc_info.value.code == 1

    def test_load_configuration_missing_file_explicit_path(self, mocker: MockerFixture) -> None:
        """Test that explicitly specified missing config file causes exit."""

        args = argparse.Namespace(config_file="./nonexistent.toml", port=None, log_level=None)

        mocker.patch("pathlib.Path.exists", return_value=False)

        with pytest.raises(SystemExit) as exc_info:
            load_configuration(args)

        assert exc_info.value.code == 1

    def test_load_configuration_valid_toml_file(self) -> None:
        """Test loading configuration from valid TOML file."""

        # Create temporary TOML file
        toml_content = """
lunatask_bearer_token = "file_token"
port = 9000
log_level = "DEBUG"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = f.name

        try:
            args = argparse.Namespace(config_file=temp_path, port=None, log_level=None)

            config = load_configuration(args)

            # Should include file values and config_file path
            assert config.lunatask_bearer_token == "file_token"
            assert config.port == 9000
            assert config.log_level == "DEBUG"
            assert config.config_file == temp_path
        finally:
            Path(temp_path).unlink()

    def test_load_configuration_cli_overrides_file(self) -> None:
        """Test that CLI arguments override file values (precedence)."""

        # Create temporary TOML file with different values
        toml_content = """
lunatask_bearer_token = "file_token"
port = 9000
log_level = "DEBUG"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = f.name

        try:
            # CLI args override file values
            args = argparse.Namespace(config_file=temp_path, port=8080, log_level="INFO")

            config = load_configuration(args)

            # CLI should override file: port=8080, log_level="INFO"
            assert config.lunatask_bearer_token == "file_token"  # from file
            assert config.port == 8080  # CLI override
            assert config.log_level == "INFO"  # CLI override
            assert config.config_file == temp_path
        finally:
            Path(temp_path).unlink()

    def test_load_configuration_unknown_keys_rejection(self) -> None:
        """Test that unknown keys in TOML file cause exit with error."""

        # Create TOML file with unknown key
        toml_content = """
lunatask_bearer_token = "token"
unknown_key = "value"
another_unknown = 123
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = f.name

        try:
            args = argparse.Namespace(config_file=temp_path, port=None, log_level=None)

            with pytest.raises(SystemExit) as exc_info:
                load_configuration(args)

            assert exc_info.value.code == 1
        finally:
            Path(temp_path).unlink()

    def test_load_configuration_invalid_toml_format(self) -> None:
        """Test that invalid TOML format causes exit with error."""

        # Create invalid TOML file
        invalid_toml = """
        lunatask_bearer_token = "token"
        port = [invalid toml syntax
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(invalid_toml)
            temp_path = f.name

        try:
            args = argparse.Namespace(config_file=temp_path, port=None, log_level=None)

            with pytest.raises(SystemExit) as exc_info:
                load_configuration(args)

            assert exc_info.value.code == 1
        finally:
            Path(temp_path).unlink()

    def test_load_configuration_default_toml_discovery(self) -> None:
        """Test that ./config.toml is discovered when --config-file not provided."""
        # Create actual temporary TOML file for this test
        toml_content = """
lunatask_bearer_token = "default_token"
port = 9000
"""

        args = argparse.Namespace(config_file=None, port=None, log_level=None)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = f.name

        # Rename to ./config.toml for discovery test
        config_toml_path = Path("./config.toml")
        try:
            Path(temp_path).rename(config_toml_path)

            config = load_configuration(args)

            # Should discover and load ./config.toml
            assert config.lunatask_bearer_token == "default_token"
            assert config.port == 9000
            assert config.config_file == "./config.toml"
        finally:
            if config_toml_path.exists():
                config_toml_path.unlink()

    def test_load_configuration_validation_failure_exit(self) -> None:
        """Test that ServerConfig validation errors cause exit."""
        # Create TOML with invalid port to trigger validation error
        toml_content = """
lunatask_bearer_token = "token"
port = 99999  # Invalid port > 65535
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = f.name

        try:
            args = argparse.Namespace(config_file=temp_path, port=None, log_level=None)

            with pytest.raises(SystemExit) as exc_info:
                load_configuration(args)

            assert exc_info.value.code == 1
        finally:
            Path(temp_path).unlink()

    def test_load_configuration_effective_config_logging(self, mocker: MockerFixture) -> None:
        """Test that effective configuration is logged with redaction."""
        # Create valid TOML file to test logging
        toml_content = """
lunatask_bearer_token = "secret_token_123"
port = 9000
log_level = "DEBUG"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = f.name

        try:
            args = argparse.Namespace(config_file=temp_path, port=None, log_level=None)

            mock_logger = mocker.Mock()
            mocker.patch("logging.getLogger", return_value=mock_logger)

            config = load_configuration(args)

            # Should log effective configuration with redaction
            mock_logger.info.assert_called_with(
                "Effective configuration: %s",
                config.to_redacted_dict(),
            )
            # Verify redaction worked
            redacted = config.to_redacted_dict()
            assert redacted["lunatask_bearer_token"] == "***redacted***"
            assert redacted["port"] == 9000
        finally:
            Path(temp_path).unlink()
