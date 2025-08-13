"""Main application entry point for LunaTask MCP server.

This module contains the CoreServer class which serves as the main application runner
for the FastMCP server implementation.
"""

import logging
import sys

from fastmcp import FastMCP


class CoreServer:
    """Main application runner responsible for initializing and managing the FastMCP server.

    This class handles FastMCP initialization, logging configuration to stderr,
    and server startup with stdio transport according to the MCP specification.
    """

    def __init__(self) -> None:
        """Initialize the CoreServer instance."""
        self._setup_logging()
        self.app = self._create_fastmcp_instance()

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

    def run(self) -> None:
        """Run the MCP server with stdio transport.

        This method starts the FastMCP server and handles the main event loop
        for processing MCP protocol messages over stdio.
        """
        logger = logging.getLogger(__name__)
        logger.info("Starting LunaTask MCP server with stdio transport")

        # Run the FastMCP server with stdio transport
        self.app.run(transport="stdio")


def main() -> None:
    """Main entry point for the LunaTask MCP server.

    Creates a CoreServer instance and runs the server.
    All logging is directed to stderr to maintain stdout purity for MCP protocol.
    """
    server = CoreServer()

    # Run the server
    try:
        server.run()
    except KeyboardInterrupt:
        logger = logging.getLogger(__name__)
        logger.info("Server shutdown requested via KeyboardInterrupt")
    except Exception:
        logger = logging.getLogger(__name__)
        logger.exception("Unhandled exception in server")
        sys.exit(1)


if __name__ == "__main__":
    main()
