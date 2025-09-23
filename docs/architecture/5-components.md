# 5. Components

The application will be structured around a few key logical components, each with a clear responsibility. This separation of concerns will make the codebase easier to understand, test, and maintain.

## 1. `LunaTaskClient` (Service Component)

**Responsibility**: This component is solely responsible for all communication with the external LunaTask REST API. It encapsulates HTTP infrastructure, authentication, error handling, and response parsing while maintaining a clean separation between core HTTP concerns and feature-specific functionality.

**Modular Architecture**: The client uses a composition-based design that separates concerns:

- **`BaseClient`** (`client_base.py`): Core HTTP infrastructure including:
  - `httpx` client lifecycle management
  - Bearer token authentication and secure header handling
  - Retry logic with exponential backoff for transient failures
  - Centralized rate limiting and mutation delay enforcement
  - HTTP status code mapping to custom exceptions
  - Connectivity testing

- **Feature Mixins**: Focused functionality classes that compose with the base:
  - **`TasksClientMixin`** (`client_tasks.py`): Task CRUD operations and query parameter handling
  - **`NotesClientMixin`** (`client_notes.py`): Note creation with 204 No Content handling
  - **`JournalClientMixin`** (`client_journal.py`): Journal entry creation
  - **`HabitsClientMixin`** (`client_habits.py`): Habit tracking functionality

- **`BaseClientProtocol`** (`protocols.py`): Typing protocol enabling mixins to reference base client methods without circular imports, supporting strict pyright type checking

- **Final Composition** (`client.py`): The `LunaTaskClient` class inherits from `BaseClient` and all mixins via multiple inheritance, providing a unified interface while keeping each file under the 500-line limit.

**Key Interfaces / Methods**:

*   `async def get_tasks() -> List[TaskResponse]`
*   `async def get_task(task_id: str) -> TaskResponse`
*   `async def create_task(task_data: TaskCreate) -> TaskResponse`
*   `async def update_task(task_id: str, task_data: TaskUpdate) -> TaskResponse`
*   `async def delete_task(task_id: str) -> bool`
*   `async def create_note(note_data: NoteCreate) -> NoteResponse | None`
*   `async def create_journal_entry(entry_data: JournalEntryCreate) -> JournalEntryResponse`
*   `async def track_habit(habit_id: str, track_date: date) -> None`
*   `async def test_connectivity() -> bool`

**Dependencies**: `httpx`, `pydantic` models, custom exceptions.

## 2. `TaskTools` (MCP Interface Component)

**Responsibility**: This component exposes Task functionality to clients by defining MCP **resources** for reads and **tools** for writes.
- Resources:
  - Discovery: `lunatask://tasks`, `lunatask://tasks/discovery`
  - Single task: `lunatask://tasks/{task_id}`
  - Area aliases: `lunatask://area/{area_id}/now`, `lunatask://area/{area_id}/today`, `lunatask://area/{area_id}/overdue`, `lunatask://area/{area_id}/next-7-days`, `lunatask://area/{area_id}/high-priority`, `lunatask://area/{area_id}/recent-completions`
  - Global aliases: `lunatask://global/now`, `lunatask://global/today`, `lunatask://global/overdue`, `lunatask://global/next-7-days`, `lunatask://global/high-priority`, `lunatask://global/recent-completions`
- Tools: `create_task`, `update_task`, `delete_task`.

**Implementation Layout**:
- `src/lunatask_mcp/tools/tasks.py`: TaskTools class and FastMCP registration (delegator).
- `src/lunatask_mcp/tools/tasks_resources.py`: `get_tasks_resource`, `get_task_resource` handlers.
- `src/lunatask_mcp/tools/tasks_create.py`: `create_task` tool handler.
- `src/lunatask_mcp/tools/tasks_update.py`: `update_task` tool handler.
- `src/lunatask_mcp/tools/tasks_delete.py`: `delete_task` tool handler.

**Architecture Pattern**: This component implements a **delegation pattern with dependency injection** to achieve modular separation of concerns:

1. **Delegator Role** (`tasks.py`): The `TaskTools` class acts as a delegator that:
   - Registers MCP resources and tools with the FastMCP instance
   - Holds a reference to the `LunaTaskClient` instance
   - Creates wrapper functions that inject the client into standalone handlers
   - Maintains public API methods for backward compatibility with existing tests

2. **Standalone Handler Functions**: Each handler file contains pure functions that:
   - Accept `LunaTaskClient` as their first parameter (dependency injection)
   - Perform specific business logic (create, update, delete, resource access)
   - Have no dependencies on class instances or global state
   - Are easily testable in isolation

3. **Dependency Flow**: 
   ```
   FastMCP → TaskTools(lunatask_client) → Wrapper Functions → Handler Functions(lunatask_client, ...)
   ```

This architecture aligns with the stated dependency injection and repository patterns, ensuring clean separation between MCP protocol handling and LunaTask API communication.

**Dependencies**: `LunaTaskClient`, `fastmcp`.

## 3. `HabitTools` (MCP Interface Component)

**Responsibility**: Similar to `TaskTools`, this component will define the MCP tool for tracking habits.

**Key Interfaces (as MCP Tools)**:

*   **Tool**: `track_habit(id: str, date: str)` (Calls `LunaTaskClient.track_habit`)

**Dependencies**: `LunaTaskClient`, `fastmcp`.

## 4. `CoreServer` (Application Runner)

**Responsibility**: This is the main application entry point (`main.py`). It will be responsible for:
*   Initializing the `FastMCP` application.
*   Handling configuration loading (from files and command-line arguments).
*   Setting up logging to `stderr`.
*   Initializing the `LunaTaskClient` and making it available to the tool components (e.g., via dependency injection).
*   Registering the `TaskTools`, `HabitTools`, and a built-in `ping` health-check tool with the FastMCP instance.
*   Starting the server with the `stdio` transport.

**Dependencies**: All other components.

---
