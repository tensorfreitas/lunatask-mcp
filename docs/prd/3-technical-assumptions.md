# 3. Technical Assumptions

These assumptions are foundational for the architecture and implementation of the server. They are derived from the technical research and project goals.

## Repository Structure: Polyrepo

A single repository (`polyrepo`) is sufficient and appropriate for this self-contained application.

## Service Architecture

The project will be a single, monolithic application. The architecture will be built on Python's `asyncio` to handle I/O-bound operations efficiently, aligning with the pattern used by the chosen FastMCP framework.

## Testing Requirements

The project will require a comprehensive suite of automated tests. This includes:
*   **Unit Tests**: For individual functions and classes.
*   **Integration Tests**: To validate the integration between the server's MCP tools and the live LunaTask API (or a mocked version of it).
The overall quality will be measured by the percentage of code covered by these tests.

## Additional Technical Assumptions and Requests

*   **Framework**: The server **must** be built using the **FastMCP framework** from the official `mcp` Python SDK. This is a non-negotiable architectural constraint.
*   **Logging**: All application logging **must** be directed to `stderr` to avoid conflicts with the `stdio` communication protocol which uses `stdout`.
*   **Package Management**: The project will use **`uv`** for dependency and virtual environment management, as it offers superior performance.
*   **Communication Transports**: The MVP will exclusively implement the **stdio transport**. The **Streamable HTTP transport** is planned for a post-MVP release and the architecture should accommodate its future addition.
*   **Rate Limit Uncertainty**: It is a known constraint that the LunaTask API does not provide documented rate limits. The Architect must design the server's internal rate limiter to be easily configurable, allowing users to adjust it if they encounter throttling. The default value should be conservative.
