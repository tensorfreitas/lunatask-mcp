"""Tests for shutdown and exception handling in main application.

These tests verify that the server handles cancellation, shutdown, and unhandled
exceptions properly without corrupting the stdout MCP protocol channel.
"""

import asyncio
import logging
import signal
import sys
import threading
from typing import Never
from unittest.mock import MagicMock, patch

import pytest
from _pytest.capture import CaptureFixture
from _pytest.logging import LogCaptureFixture

from lunatask_mcp.main import CoreServer, main


class TestShutdownHandling:
    """Test cases for shutdown and exception handling."""

    def test_keyboard_interrupt_handling(self, caplog: LogCaptureFixture) -> None:
        """Test that KeyboardInterrupt is handled gracefully and logs to stderr."""
        # Ensure logging capture is working for the right logger
        caplog.set_level(logging.INFO, logger="lunatask_mcp.main")

        # Mock the CoreServer.run method to raise KeyboardInterrupt
        with (
            patch.object(CoreServer, "run", side_effect=KeyboardInterrupt),
            patch("sys.exit") as mock_exit,
        ):
            main()
            # Should not call sys.exit for KeyboardInterrupt
            mock_exit.assert_not_called()

        # Check that the shutdown messages were logged
        log_messages = [record.message for record in caplog.records]
        assert any("Server shutdown requested via KeyboardInterrupt" in msg for msg in log_messages)
        assert any("Server shutdown complete" in msg for msg in log_messages)

    def test_unhandled_exception_handling(self, caplog: LogCaptureFixture) -> None:
        """Test that unhandled exceptions are logged to stderr and sys.exit(1) is called."""
        # Ensure logging capture is working for the right logger
        caplog.set_level(logging.INFO, logger="lunatask_mcp.main")

        test_exception = RuntimeError("Test exception")

        # Mock the CoreServer.run method to raise an unhandled exception
        with (
            patch.object(CoreServer, "run", side_effect=test_exception),
            patch("sys.exit") as mock_exit,
        ):
            main()
            # Should call sys.exit(1) for unhandled exceptions
            mock_exit.assert_called_once_with(1)

        # Check that the exception was logged with full traceback
        log_messages = [record.message for record in caplog.records]
        assert any("Unhandled exception in server" in msg for msg in log_messages)
        # Note: sys.exit(1) prevents finally block from executing,
        # so "shutdown complete" won't appear

        # Check for exception in log records
        error_records = [record for record in caplog.records if record.levelname == "ERROR"]
        assert len(error_records) > 0

    def test_signal_handling_sigterm(self) -> None:
        """Test that SIGTERM signal is handled gracefully."""
        # This test verifies that the server sets up SIGTERM signal handlers
        with patch("signal.signal") as mock_signal:
            server = CoreServer()
            # Verify that signal handlers were set up
            assert server is not None
            # Should call signal.signal twice: once for SIGINT, once for SIGTERM
            expected_signal_count = 2
            assert mock_signal.call_count == expected_signal_count

            # Check the calls - should be SIGINT and SIGTERM
            calls = mock_signal.call_args_list
            signal_numbers = [call[0][0] for call in calls]
            assert signal.SIGINT in signal_numbers
            assert signal.SIGTERM in signal_numbers

    def test_signal_handling_sigint(self) -> None:
        """Test that SIGINT signal is handled gracefully."""
        # This test verifies that the server can handle SIGINT signals
        # SIGINT is typically handled by Python as KeyboardInterrupt
        with (
            patch.object(CoreServer, "run", side_effect=KeyboardInterrupt),
            patch("sys.exit") as mock_exit,
        ):
            main()
            mock_exit.assert_not_called()

    def test_stdout_purity_during_exception(self, capfd: CaptureFixture[str]) -> None:
        """Test that stdout remains clean even when exceptions occur."""
        # Test various exception scenarios to ensure stdout is never corrupted
        test_exceptions = [
            KeyboardInterrupt(),
            RuntimeError("Runtime error"),
            ValueError("Value error"),
            OSError("OS error"),
        ]

        for exception in test_exceptions:
            with (
                patch.object(CoreServer, "run", side_effect=exception),
                patch("sys.exit"),
            ):
                main()

            # Verify stdout remains clean
            captured = capfd.readouterr()
            assert captured.out == "", f"Stdout was corrupted during {type(exception).__name__}"

    def test_concurrent_exception_handling(self, capfd: CaptureFixture[str]) -> None:
        """Test that exceptions in concurrent operations don't corrupt stdout."""

        # Simulate concurrent operations that might fail
        exception_captured = threading.Event()

        def failing_operation() -> None:
            def _do_fail() -> None:
                raise RuntimeError

            try:
                _do_fail()
            except RuntimeError:
                # Capture the exception to prevent it from being unhandled
                exception_captured.set()

        # Mock CoreServer.run to simulate concurrent operations
        def mock_run_with_concurrent_exception(_self: object) -> Never:
            # Start a background task that will fail
            thread = threading.Thread(target=failing_operation)
            thread.start()
            # Wait for the thread to handle its exception
            thread.join(timeout=1.0)
            # Verify the exception was captured
            assert exception_captured.is_set()
            raise KeyboardInterrupt  # Then simulate shutdown

        with (
            patch.object(CoreServer, "run", mock_run_with_concurrent_exception),
            patch("sys.exit"),
        ):
            main()

        # Verify stdout remains clean despite concurrent exceptions
        captured = capfd.readouterr()
        assert captured.out == ""

    def test_logging_configuration_during_shutdown(self) -> None:
        """Test that logging configuration is set up correctly."""
        # Test that basicConfig is called with correct parameters
        with patch("logging.basicConfig") as mock_basic_config:
            CoreServer()

            # Verify basicConfig was called with stderr stream
            mock_basic_config.assert_called_once()
            call_args = mock_basic_config.call_args
            assert call_args[1]["stream"] == sys.stderr
            assert call_args[1]["level"] == logging.INFO
            assert "%(asctime)s" in call_args[1]["format"]
            assert "%(levelname)s" in call_args[1]["format"]
            assert "%(name)s" in call_args[1]["format"]
            assert "%(message)s" in call_args[1]["format"]


class TestAsyncShutdownHandling:
    """Test cases for async shutdown handling scenarios."""

    @pytest.mark.asyncio
    async def test_async_cancellation_propagation(self) -> None:
        """Test that asyncio cancellation is properly propagated to tool implementations."""
        server = CoreServer()

        # Create a mock context
        mock_ctx = MagicMock()
        mock_ctx.info = MagicMock(return_value=asyncio.create_task(asyncio.sleep(0)))

        # Test that the ping tool can be cancelled
        task = asyncio.create_task(server.ping_tool(mock_ctx))

        # Cancel the task
        task.cancel()

        # Verify the task was cancelled
        with pytest.raises(asyncio.CancelledError):
            await task

    @pytest.mark.asyncio
    async def test_context_cancellation_handling(self) -> None:
        """Test that context cancellation is handled properly in tools."""
        server = CoreServer()

        # Create a cancelled context
        mock_ctx = MagicMock()
        mock_ctx.info = MagicMock(side_effect=asyncio.CancelledError())

        # The tool should propagate the cancellation
        with pytest.raises(asyncio.CancelledError):
            await server.ping_tool(mock_ctx)


if __name__ == "__main__":
    pytest.main([__file__])
