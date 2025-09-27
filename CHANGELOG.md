# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-01-XX

### Added
- **Notes Management**: New `create_note` tool for creating notes in LunaTask notebooks
  - Supports `notebook_id`, `name`, optional `content`, `date_on`, and source metadata
  - Handles duplicate detection with 204 No Content responses
  - Returns `{"success": true, "note_id": "..."}` on creation
- **Journal Entries**: New `create_journal_entry` tool for daily journal management
  - Requires `date_on` in YYYY-MM-DD format
  - Supports optional `name` and `content` (Markdown)
  - Returns `{"success": true, "journal_entry_id": "..."}` on creation
- **People/Contact Management**: Comprehensive people management capabilities
  - `create_person` tool for creating contacts with relationship tracking
  - `create_person_timeline_note` tool for adding timeline notes to existing people
  - `delete_person` tool for removing contacts (non-idempotent)
  - Support for relationship strength levels (family, friends, business contacts, etc.)
  - Custom fields support for email, birthday, and phone (requires LunaTask app configuration)
  - Duplicate handling and proper error responses
- **MCP Client Compatibility**: Added comprehensive documentation for MCP client support
  - Resource support matrix for popular MCP clients
  - Setup instructions for Claude Code, Claude Desktop, Codex, and other clients
  - Known limitations and workarounds for clients with partial MCP support

### Changed
- **Architecture**: Modularized LunaTask API client to enforce 500-line file limit
  - Split client functionality into focused mixins by domain
  - Improved maintainability and testability
  - Better separation of concerns across API endpoints

### Fixed
- **Security**: Removed accidentally tracked configuration files with sensitive data
- **Configuration**: Replaced committed tokens with placeholder values

### Documentation
- Updated README.md with all new tools and capabilities
- Enhanced server capabilities section to reflect people management features
- Updated architecture documentation to reflect new client structure
- Added comprehensive tool descriptions with parameters and response formats
- Marked completed features in "To Be Implemented" section

### Internal
- Extensive test coverage for all new functionality following TDD methodology
- Maintained 95%+ test coverage requirement
- All new code follows established coding standards and patterns
- Proper error handling and logging for all new tools

## [0.1.0] - 2024-XX-XX

### Added
- Initial release of LunaTask MCP Server
- Task management tools (create, update, delete)
- Habit tracking functionality
- MCP resource support for task discovery and listing
- Rate limiting and authentication
- Comprehensive configuration system
- FastMCP-based architecture with stdio transport

[0.2.0]: https://github.com/tensorfreitas/lunatask-mcp/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/tensorfreitas/lunatask-mcp/releases/tag/v0.1.0