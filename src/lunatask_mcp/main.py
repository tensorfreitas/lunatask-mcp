"""Main application entry point for LunaTask MCP server.

This module contains the CoreServer class which serves as the main application runner
for the FastMCP server implementation.
"""

import argparse
import asyncio
import logging
import signal
import sys
import tomllib
from pathlib import Path
from typing import Any

from fastmcp import Context, FastMCP

from lunatask_mcp.config import ServerConfig


class CoreServer:
    """Main application runner responsible for initializing and managing the FastMCP server.

    This class handles FastMCP initialization, logging configuration to stderr,
    and server startup with stdio transport according to the MCP specification.
    """

    def __init__(self) -> None:
        """Initialize the CoreServer instance."""
        self._setup_logging()
        self.app = self._create_fastmcp_instance()
        self._register_tools()
        self._shutdown_requested = False
        self._setup_signal_handlers()

    def _setup_logging(self) -> None:
        """Configure logging to direct all output to stderr.

        This ensures that stdout remains clean for MCP JSON-RPC protocol communication
        while all logging output goes to stderr with proper formatting.
        """
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
            stream=sys.stderr,
        )

    def _create_fastmcp_instance(self) -> FastMCP:
        """Create and configure the FastMCP application instance.

        FastMCP automatically handles MCP protocol version negotiation,
        using the latest supported version (2025-06-18) by default.

        Returns:
            FastMCP: Configured FastMCP instance ready for stdio transport.
        """
        return FastMCP(
            name="lunatask-mcp",
            version="0.1.0",
        )

    def _register_tools(self) -> None:
        """Register all tools with the FastMCP instance."""
        self.app.tool(self.ping_tool, name="ping")

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown.

        Handles SIGINT and SIGTERM to ensure clean shutdown without stdout corruption.
        """

        def signal_handler(signum: int, _frame: object | None) -> None:
            """Handle shutdown signals by setting shutdown flag."""
            logger = logging.getLogger(__name__)
            signal_name = "SIGINT" if signum == signal.SIGINT else f"Signal {signum}"
            logger.info("Received %s, initiating graceful shutdown", signal_name)
            self._shutdown_requested = True

        # Set up signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def ping_tool(self, ctx: Context) -> str:
        """Ping health-check tool that returns a static 'pong' response.

        This tool serves as a basic health-check endpoint to verify that
        the MCP server is functioning correctly.

        Args:
            ctx: The execution context providing access to logging and other MCP capabilities.

        Returns:
            str: The 'pong' response text.

        Raises:
            asyncio.CancelledError: If the operation is cancelled during execution.
        """
        try:
            await ctx.info("Ping tool called, returning pong")
        except asyncio.CancelledError:
            await ctx.info("Ping tool execution cancelled")
            raise
        else:
            return "pong"

    def run(self) -> None:
        """Run the MCP server with stdio transport.

        This method starts the FastMCP server and handles the main event loop
        for processing MCP protocol messages over stdio with proper shutdown handling.
        """
        logger = logging.getLogger(__name__)
        logger.info("Starting LunaTask MCP server with stdio transport")

        try:
            # Run the FastMCP server with stdio transport
            self.app.run(transport="stdio")
        except KeyboardInterrupt:
            logger.info("Server shutdown requested via KeyboardInterrupt")
            raise
        except Exception:
            logger.exception("Unhandled exception in server run method")
            raise


def load_configuration(args: argparse.Namespace) -> ServerConfig:
    """Load configuration from defaults, file, and CLI arguments with proper precedence.

    Precedence order (CLI > file > defaults):
    1. Command-line arguments (highest priority)
    2. Configuration file values
    3. Default values (lowest priority)

    Args:
        args: Parsed command-line arguments.

    Returns:
        ServerConfig: Loaded and validated configuration.

    Raises:
        SystemExit: On configuration validation errors or file parsing errors.
    """
    config_data: dict[str, Any] = {}
    logger = logging.getLogger(__name__)

    # Determine config file path
    config_file = args.config_file or "./config.toml"
    config_path = Path(config_file)

    # Load from configuration file if it exists
    if config_path.exists():
        try:
            with config_path.open("rb") as f:
                file_config = tomllib.load(f)

            # Validate that all keys in the TOML file are known configuration fields
            known_fields = {
                "lunatask_bearer_token",
                "lunatask_base_url",
                "port",
                "log_level",
                "config_file",
            }
            unknown_keys = set(file_config.keys()) - known_fields
            if unknown_keys:
                logger.error(
                    "Unknown configuration keys in %s: %s",
                    config_path,
                    ", ".join(sorted(unknown_keys)),
                )
                sys.exit(1)

            config_data.update(file_config)
            logger.info("Loaded configuration from %s", config_path)
        except tomllib.TOMLDecodeError:
            logger.exception("Failed to parse TOML configuration file %s", config_path)
            sys.exit(1)
        except OSError:
            logger.exception("Failed to read configuration file %s", config_path)
            sys.exit(1)
    elif args.config_file:
        # Only error if config file was explicitly specified but doesn't exist
        logger.error("Configuration file not found: %s", config_file)
        sys.exit(1)

    # Override with CLI arguments (CLI takes precedence)
    if args.port is not None:
        config_data["port"] = args.port
    if args.log_level is not None:
        config_data["log_level"] = args.log_level

    # Add config_file to the data for the model
    config_data["config_file"] = config_file

    try:
        # Create and validate the configuration
        config = ServerConfig(**config_data)
    except Exception:
        logger.exception("Configuration validation failed")
        sys.exit(1)
    else:
        # Log effective configuration with secrets redacted
        logger.info("Effective configuration: %s", config.to_redacted_dict())
        return config


def parse_cli_args() -> argparse.Namespace:
    """Parse command-line arguments for server configuration.

    Returns:
        argparse.Namespace: Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="LunaTask MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--config-file",
        type=str,
        help="Path to configuration file (default: ./config.toml)",
    )

    parser.add_argument(
        "--port",
        type=int,
        help="Port number for future HTTP transport (1-65535)",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level",
    )

    return parser.parse_args()


def main() -> None:
    """Main entry point for the LunaTask MCP server.

    Creates a CoreServer instance and runs the server with proper exception handling
    to ensure stdout remains uncorrupted for MCP protocol communication.
    All logging is directed to stderr to maintain stdout purity.
    """
    logger = logging.getLogger(__name__)

    try:
        # Parse command-line arguments before server construction
        args = parse_cli_args()

        # Load and validate configuration
        _config = load_configuration(args)

        server = CoreServer()
        server.run()
    except KeyboardInterrupt:
        logger.info("Server shutdown requested via KeyboardInterrupt")
        # Clean exit for keyboard interrupt - don't call sys.exit()
    except Exception:
        logger.exception("Unhandled exception in server")
        # Exit with error code for unhandled exceptions
        sys.exit(1)
    finally:
        # Ensure any cleanup logging goes to stderr
        logger.info("Server shutdown complete")


if __name__ == "__main__":
    main()
