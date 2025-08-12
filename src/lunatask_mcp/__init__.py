"""LunaTask MCP - Model Context Protocol integration for LunaTask."""

import logging

__version__ = "0.1.0"

logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point for the LunaTask MCP server."""
    logging.basicConfig(level=logging.INFO)
    logger.info("LunaTask MCP server starting...")
    # TODO: Implement MCP server initialization


if __name__ == "__main__":
    main()
