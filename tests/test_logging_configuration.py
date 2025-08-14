"""Tests for logging configuration in CoreServer.

Tests verify that all logging is correctly directed to stderr with proper formatting
and that the context-scoped logging is configured to use stderr.
"""

import inspect
import logging
import re
import sys
from io import StringIO

from pytest_mock import MockerFixture

import lunatask_mcp.main
from lunatask_mcp.config import ServerConfig
from lunatask_mcp.main import CoreServer


class TestLoggingConfiguration:
    """Test cases for logging configuration."""

    def test_logging_configured_to_stderr(
        self,
        default_config: ServerConfig,
        mocker: MockerFixture,
    ) -> None:
        """Test that logging is configured to output to stderr."""
        # Clear any existing handlers to ensure clean test
        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers[:]
        root_logger.handlers.clear()

        try:
            # Capture stderr output
            captured_stderr = StringIO()

            mocker.patch.object(sys, "stderr", captured_stderr)
            # Create CoreServer instance which should configure logging
            CoreServer(default_config)

            # Get a logger and test it outputs to stderr
            logger = logging.getLogger("test_logger")
            logger.info("Test message")

            # Verify output went to stderr
            stderr_output = captured_stderr.getvalue()
            assert "Test message" in stderr_output
        finally:
            # Restore original handlers
            root_logger.handlers.clear()
            root_logger.handlers.extend(original_handlers)

    def test_logging_format_includes_timestamp_and_level(
        self,
        default_config: ServerConfig,
        mocker: MockerFixture,
    ) -> None:
        """Test that logging format includes timestamp and level."""
        # Clear any existing handlers to ensure clean test
        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers[:]
        root_logger.handlers.clear()

        try:
            captured_stderr = StringIO()

            mocker.patch.object(sys, "stderr", captured_stderr)
            # Create CoreServer instance
            CoreServer(default_config)

            # Log a test message
            logger = logging.getLogger("test_format")
            logger.warning("Format test message")

            # Verify format includes timestamp, level, and message
            stderr_output = captured_stderr.getvalue()
            assert "WARNING" in stderr_output
            assert "test_format" in stderr_output
            assert "Format test message" in stderr_output
            # Check for timestamp pattern (YYYY-MM-DD HH:MM:SS,mmm)
            timestamp_pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}"
            assert re.search(timestamp_pattern, stderr_output)
        finally:
            # Restore original handlers
            root_logger.handlers.clear()
            root_logger.handlers.extend(original_handlers)

    def test_no_print_statements_used(self) -> None:
        """Test that no print statements are used in the code."""
        # Read the main.py file and verify no print statements
        source = inspect.getsource(lunatask_mcp.main)

        # Check that print() is not used in the source
        assert "print(" not in source
        assert "print (" not in source

    def test_logging_level_set_to_info(
        self,
        default_config: ServerConfig,
        mocker: MockerFixture,
    ) -> None:
        """Test that logging level is set to INFO."""
        # Clear any existing handlers to ensure clean test
        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers[:]
        root_logger.handlers.clear()

        try:
            captured_stderr = StringIO()

            mocker.patch.object(sys, "stderr", captured_stderr)
            # Create CoreServer instance
            CoreServer(default_config)

            # Test that INFO level messages are captured
            logger = logging.getLogger("test_level")
            logger.info("Info level message")

            stderr_output = captured_stderr.getvalue()
            assert "Info level message" in stderr_output

            # Test that DEBUG messages are not captured (since level is INFO)
            captured_stderr.truncate(0)
            captured_stderr.seek(0)
            logger.debug("Debug level message")

            stderr_output = captured_stderr.getvalue()
            assert "Debug level message" not in stderr_output
        finally:
            # Restore original handlers
            root_logger.handlers.clear()
            root_logger.handlers.extend(original_handlers)

    def test_context_scoped_logging_uses_stderr(self, default_config: ServerConfig) -> None:
        """Test that context-scoped logging is configured to use stderr."""
        # Clear any existing handlers to ensure clean test
        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers[:]
        root_logger.handlers.clear()

        try:
            # Create CoreServer instance
            CoreServer(default_config)

            # Verify that when we configure logging, it affects the root logger
            # which will be used by FastMCP's context logging
            root_logger = logging.getLogger()

            # Check that root logger has our stderr handler
            handlers = root_logger.handlers
            assert len(handlers) > 0

            # Check that at least one handler writes to stderr
            stderr_handlers = [
                h
                for h in handlers
                if hasattr(h, "stream") and getattr(h, "stream", None) == sys.stderr
            ]
            assert len(stderr_handlers) > 0
        finally:
            # Restore original handlers
            root_logger.handlers.clear()
            root_logger.handlers.extend(original_handlers)

    def test_logging_preserves_stdout_purity(
        self,
        default_config: ServerConfig,
        mocker: MockerFixture,
    ) -> None:
        """Test that logging configuration preserves stdout purity."""
        # Clear any existing handlers to ensure clean test
        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers[:]
        root_logger.handlers.clear()

        try:
            captured_stdout = StringIO()
            captured_stderr = StringIO()

            mocker.patch.object(sys, "stdout", captured_stdout)
            mocker.patch.object(sys, "stderr", captured_stderr)
            # Create CoreServer instance
            CoreServer(default_config)

            # Log various messages
            logger = logging.getLogger("stdout_test")
            logger.info("This should go to stderr")
            logger.error("This error should go to stderr")
            logger.warning("This warning should go to stderr")

            # Verify stdout is empty (preserving purity for MCP protocol)
            stdout_output = captured_stdout.getvalue()
            assert stdout_output == ""

            # Verify stderr contains the messages
            stderr_output = captured_stderr.getvalue()
            assert "This should go to stderr" in stderr_output
            assert "This error should go to stderr" in stderr_output
            assert "This warning should go to stderr" in stderr_output
        finally:
            # Restore original handlers
            root_logger.handlers.clear()
            root_logger.handlers.extend(original_handlers)
