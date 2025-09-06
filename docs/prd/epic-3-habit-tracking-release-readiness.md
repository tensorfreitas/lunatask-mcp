# Epic 3: Habit Tracking & Release Readiness

**Expanded Goal**: The goal of this final epic is to implement the specific habit-tracking functionality and to perform all the necessary final steps to prepare the project for a high-quality, public release on PyPI.

## **Story 3.1: Track Habit Tool**
**As a** user, **I want** to track an activity for a specific habit on a given date using an MCP tool, **so that** I can log my habit progress from my AI tools.
### Acceptance Criteria
1. An MCP `tool` named `track_habit` is implemented.
2. The tool accepts a habit `id` and a `date` as parameters.
3. When called, the tool makes an authenticated `POST` request to the `https://api.lunatask.app/v1/habits/<id>/track` endpoint.
4. The body of the POST request includes the `date`.
5. A successful API call results in a successful MCP response.
6. The tool handles error responses correctly (e.g., habit not found).
7. The rate limiter from Epic 2 is applied to this tool.

## **Story 3.2: Finalize Documentation**
**As a** new user, **I want** clear, comprehensive documentation in the `README.md` file, **so that** I can quickly understand how to install, configure, and run the server.
### Acceptance Criteria
1. The `README.md` is updated with complete installation instructions using `uv` and `pip`.
2. Configuration instructions are provided, explaining all options for the config file and command-line arguments.
3. A "Getting Started" or "Usage" section is added, showing a clear example of how to run the server and call a tool.
4. All available MCP tools and resources are documented.
