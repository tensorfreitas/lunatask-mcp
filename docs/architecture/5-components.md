# 5. Components

The application will be structured around a few key logical components, each with a clear responsibility. This separation of concerns will make the codebase easier to understand, test, and maintain.

## 1. `LunaTaskClient` (Service Component)

**Responsibility**: This component is solely responsible for all communication with the external LunaTask REST API. It will encapsulate the `httpx` client, handle authentication by adding the bearer token to outgoing requests, and perform basic error handling and response parsing. It will use the `pydantic` models we defined to structure its requests and parse responses.

**Key Interfaces / Methods**:

*   `async def get_tasks() -> List[TaskResponse]`
*   `async def get_task(task_id: str) -> TaskResponse`
*   `async def create_task(task_data: TaskCreate) -> TaskResponse`
*   `async def update_task(task_id: str, task_data: TaskUpdate) -> TaskResponse`
*   `async def delete_task(task_id: str) -> None`
*   `async def track_habit(habit_id: str, track_data: HabitTrackRequest) -> None`

**Dependencies**: `httpx`, `pydantic` models.

## 2. `TaskTools` (MCP Interface Component)

**Responsibility**: This component will expose the Task-related functionality to clients by defining MCP **`resources`** for read operations and **`tools`** for write operations.
*   The `get_tasks` and `get_task` methods will be exposed as `resources` with URI templates like `lunatask://tasks` and `lunatask://tasks/{task_id}`.
*   The `create_task`, `update_task`, and `delete_task` methods will be exposed as `tools`.
This component will use the `LunaTaskClient` to perform the actual API calls and will translate the results and errors into MCP-compliant responses.

**Dependencies**: `LunaTaskClient`, `fastmcp`.

## 3. `HabitTools` (MCP Interface Component)

**Responsibility**: Similar to `TaskTools`, this component will define the MCP tool for tracking habits.

**Key Interfaces (as MCP Tools)**:

*   **Tool**: `track_habit(...)` (Calls `LunaTaskClient.track_habit`)

**Dependencies**: `LunaTaskClient`, `fastmcp`.

## 4. `CoreServer` (Application Runner)

**Responsibility**: This is the main application entry point (`server.py`). It will be responsible for:
*   Initializing the `FastMCP` application.
*   Handling configuration loading (from files and command-line arguments).
*   Setting up logging to `stderr`.
*   Initializing the `LunaTaskClient` and making it available to the tool components (e.g., via dependency injection).
*   Registering the `TaskTools` and `HabitTools` with the FastMCP instance.
*   Starting the server with the `stdio` transport.

**Dependencies**: All other components.

---