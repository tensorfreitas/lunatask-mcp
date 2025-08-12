# 2. Requirements

## Functional

1.  **FR1**: The server shall be capable of operating in two communication modes: via standard input/output (stdio) for subprocess control, and via Server-Sent Events (SSE) for HTTP-based clients.
2.  **FR2**: The server shall correctly parse and handle valid Model Context Protocol (MCP) requests for discovering and calling `tool` functions.
3.  **FR3**: The server shall authenticate with the LunaTask REST API by including a user-provided bearer token in its outgoing requests.
4.  **FR4**: The server shall provide MCP tools to create and update tasks by making the appropriate calls to the LunaTask Tasks API.
5.  **FR5**: The server shall provide MCP tools to create and update habits by making the appropriate calls to the LunaTask Habits API.
6.  **FR6**: The server shall implement an in-memory rate limiter to control the frequency of requests sent to the LunaTask API.
7.  **FR7**: The server's core settings (e.g., communication mode, port, rate limit parameters) shall be configurable through both command-line arguments and a dedicated configuration file.
8.  **FR8**: The server shall return structured MCP-compliant error responses when it fails to process a request, encounters an API error, or receives an invalid request.

## Non-Functional

1.  **NFR1**: **Performance**: The server must be lightweight, with a low memory footprint and fast startup time, making it suitable to run as a local background subprocess.
2.  **NFR2**: **Security**: The user's LunaTask bearer token must be handled securely in memory and must never be written to logs or exposed in error messages.
3.  **NFR3**: **Compatibility**: The server must be a cross-platform Python application, capable of running on Windows, macOS, and Linux.
4.  **NFR4**: **Reliability**: The server must be designed as a long-running process. All diagnostic and informational logging must be directed to `stderr` to avoid interfering with the `stdio` communication channel.
5.  **NFR5**: **Good Citizenship**: As the LunaTask API does not publish official rate limits, the server's own rate limiter must be enabled by default with a *conservative* and reasonable setting (e.g., 60 requests per minute) to avoid overwhelming the upstream service.
