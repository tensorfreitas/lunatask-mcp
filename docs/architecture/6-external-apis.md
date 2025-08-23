# 6. External APIs

This project has one critical external dependency: the LunaTask API. All core functionality is contingent upon the availability and stability of this API.

## LunaTask API

*   **Purpose**: To provide programmatic access to a user's LunaTask data for creating, retrieving, updating, and deleting entities like tasks and habits.
*   **Documentation**:
    *   **Tasks API**: [https://lunatask.app/api/tasks-api/entity](https://lunatask.app/api/tasks-api/entity)
    *   **Habits API**: [https://lunatask.app/api/habits-api/track-activity](https://lunatask.app/api/habits-api/track-activity)
*   **Base URL**: `https://api.lunatask.app/v1/`
*   **Authentication**: Bearer Token sent in the `Authorization` header.
*   **Rate Limits**: Undocumented. Our server must implement a conservative, configurable rate limiter to act as a good citizen.
*   **Integration Notes**: The API enforces end-to-end encryption, meaning response payloads for `GET` requests will not contain sensitive, encrypted fields like `name` or `notes`. Our `TaskResponse` model is designed to handle this.

## API Endpoint Coverage

### Tasks API

#### Implemented Endpoints

1. **GET /v1/tasks** - Retrieve All Tasks
   - **Purpose**: Get a list of all tasks for the authenticated user
   - **Implementation**: `LunaTaskClient.get_tasks()` method
   - **MCP Resource**: `lunatask://tasks`
   - **Response Model**: Array of `TaskResponse` objects
   - **Features**: Supports pagination and filtering parameters
   - **Status**: ✅ Implemented (Story 2.1)

2. **GET /v1/tasks/{id}** - Retrieve Single Task
   - **Purpose**: Get details of a specific task by its unique ID  
   - **Implementation**: `LunaTaskClient.get_task(task_id: str)` method
   - **MCP Resource**: `lunatask://tasks/{task_id}` (URI template)
   - **Response Model**: Single `TaskResponse` object
   - **Error Handling**: Returns `TaskNotFoundError` for non-existent tasks (404)
   - **Status**: ✅ Implemented (Story 2.2)

3. **POST /v1/tasks** - Create Task
   - **Purpose**: Create a new task with specified parameters
   - **Implementation**: `LunaTaskClient.create_task(task: TaskCreate)` method
   - **MCP Tool**: `create_task` tool
   - **Request Model**: `TaskCreate` object with required/optional fields
   - **Response Model**: Task creation result with new task ID
   - **Features**: Supports E2E encryption for `name` and `notes` fields
   - **Error Handling**: Validation errors (422), subscription limits (402), auth errors (401)
   - **Status**: ✅ Implemented (Story 2.3)

4. **PATCH /v1/tasks/{id}** - Update Task
   - **Purpose**: Update an existing task with partial field updates
   - **Implementation**: `LunaTaskClient.update_task(task_id: str, update: TaskUpdate)` method
   - **MCP Tool**: `update_task` tool
   - **Request Model**: `TaskUpdate` object with all optional fields (partial updates)
   - **Response Model**: `TaskResponse` object with updated task data
   - **Features**: Supports partial updates (only provided fields are modified)
   - **Error Handling**: Task not found (404), validation errors (400), auth errors (401)
   - **Date Handling**: ISO 8601 string parsing and validation for `due_date` field
   - **Status**: ✅ Implemented (Story 2.4)

#### Not Yet Implemented

5. **DELETE /v1/tasks/{id}** - Delete Task
   - **Purpose**: Delete a task by ID
   - **Planned Implementation**: `delete_task` MCP tool
   - **Status**: 📋 Planned (Story 2.5)

### Response Format Notes

All implemented endpoints respect LunaTask's E2E encryption constraints:
- Sensitive fields (`name`, `notes`) are absent from all responses
- Only structural and metadata fields are available
- Error responses are properly translated to MCP error format
- Rate limiting is applied to all requests via `TokenBucketLimiter`

---