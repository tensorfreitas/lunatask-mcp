# 6. External APIs

This project has one critical external dependency: the LunaTask API. All core functionality is contingent upon the availability and stability of this API.

## LunaTask API

*   **Purpose**: To provide programmatic access to a user's LunaTask data for creating, retrieving, updating, and deleting entities like tasks and habits.
*   **Documentation**:
    *   **Tasks API**: [https://lunatask.app/api/tasks-api/entity](https://lunatask.app/api/tasks-api/entity)
    *   **Notes API**: [https://lunatask.app/api/notes-api/create](https://lunatask.app/api/notes-api/create)
    *   **Journal Entries API**: [https://lunatask.app/api/journal-api/create](https://lunatask.app/api/journal-api/create)
    *   **Habits API**: [https://lunatask.app/api/habits-api/track-activity](https://lunatask.app/api/habits-api/track-activity)
*   **Base URL**: `https://api.lunatask.app/v1/`
*   **Authentication**: Bearer Token sent in the `Authorization` header.
*   **Rate Limits**: Undocumented. Our server must implement a conservative, configurable rate limiter to act as a good citizen.
*   **Integration Notes**: The API enforces end-to-end encryption, meaning response payloads for `GET` requests will not contain sensitive, encrypted fields like `name` or `note`. Our `TaskResponse` model is designed to handle this.

## API Endpoint Coverage

### Tasks API

#### Implemented Endpoints

1. **GET /v1/tasks** - Retrieve All Tasks
   - **Purpose**: Get a list of all tasks for the authenticated user
   - **Implementation**: `LunaTaskClient.get_tasks()` method
   - **MCP Resource Discovery**: `lunatask://tasks` (returns discovery document)
   - **MCP Resource Access**: Via alias resources (area/global families)
   - **Response Model**: Array of `TaskResponse` objects
   - **Features**: Supports pagination and filtering parameters
   - **Alias Resources**:
     - Area family: `lunatask://area/{area_id}/now`, `lunatask://area/{area_id}/today`, `lunatask://area/{area_id}/overdue`, `lunatask://area/{area_id}/next-7-days`, `lunatask://area/{area_id}/high-priority`, `lunatask://area/{area_id}/recent-completions`
     - Global family: `lunatask://global/now`, `lunatask://global/today`, `lunatask://global/overdue`, `lunatask://global/next-7-days`, `lunatask://global/high-priority`, `lunatask://global/recent-completions`

2. **GET /v1/tasks/{id}** - Retrieve Single Task
   - **Purpose**: Get details of a specific task by its unique ID  
   - **Implementation**: `LunaTaskClient.get_task(task_id: str)` method; MCP resource handler in `tools/tasks_resources.py:get_task_resource`
   - **MCP Resource**: `lunatask://tasks/{task_id}` (URI template)
   - **Response Model**: Single `TaskResponse` object
   - **Error Handling**: Returns `TaskNotFoundError` for non-existent tasks (404)

3. **POST /v1/tasks** - Create Task
   - **Purpose**: Create a new task with specified parameters
   - **Implementation**: `LunaTaskClient.create_task(task: TaskCreate)` method
   - **MCP Tool**: `create_task` tool (handler in `tools/tasks_create.py`)
   - **Request Model**: `TaskCreate` (subclasses `TaskPayload`) with create-time defaults
   - **Response Model**: Task creation result with new task ID
   - **Features**: Supports E2E encryption for `name` and `note` fields
   - **Error Handling**: Validation errors (422), subscription limits (402), auth errors (401)

4. **PATCH /v1/tasks/{id}** - Update Task
   - **Purpose**: Update an existing task with partial field updates
   - **Implementation**: `LunaTaskClient.update_task(task_id: str, update: TaskUpdate)` method
   - **MCP Tool**: `update_task` tool (handler in `tools/tasks_update.py`)
   - **Request Model**: `TaskUpdate` (subclasses `TaskPayload`) with all optional fields
   - **Response Model**: `TaskResponse` object with updated task data
   - **Features**: Supports partial updates (only provided fields are modified)
   - **Error Handling**: Task not found (404), validation errors (400), auth errors (401)
   - **Date Handling**: Date string parsing and validation for `scheduled_on` field (YYYY-MM-DD format)

5. **DELETE /v1/tasks/{id}** - Delete Task
   - **Purpose**: Delete a task by ID
   - **Implementation**: `LunaTaskClient.delete_task(task_id: str)` and `delete_task` MCP tool
     (handler in `tools/tasks_delete.py`)
   - **Response**: 204 No Content on success, 404 if not found
   - **Client Handling**: The client treats any 2xx status as a successful deletion to accommodate
     provider variations (e.g., some deployments may return 200 OK with a JSON body). The MCP tool
     reports success when no exception is raised by the client.
   - **Behavior**: Non-idempotent (repeated deletion returns 404)

### Habits API

#### Implemented Endpoints

1. **POST /v1/habits/{id}/track** - Track Habit Activity
   - **Purpose**: Track an activity for a specific habit on a given date
   - **Implementation**: `LunaTaskClient.track_habit(habit_id: str, track_date: date)` method
   - **MCP Tool**: `track_habit` tool (handler in `tools/habits.py`)
   - **Request Body**: JSON with `performed_on` field in ISO-8601 format (`YYYY-MM-DD`)
   - **Response**: Success returns 204 No Content or similar success status
   - **Error Handling**: Habit not found (404), validation errors (422), auth errors (401)
   - **Rate Limiting**: Applied via `TokenBucketLimiter` in `make_request`

### Notes API

#### Implemented Endpoints

1. **POST /v1/notes** - Create Note
   - **Purpose**: Create a note with optional metadata and duplicate detection
   - **Implementation**: `LunaTaskClient.create_note(note: NoteCreate)` method
   - **MCP Tool**: `create_note` tool (handler in `tools/notes.py`)
   - **Request Model**: `NoteCreate` with optional `notebook_id`, `name`, `content`, `date_on`, `source`, `source_id`
   - **Response Model**: `NoteResponse` when the API returns a new note payload
   - **Duplicate Handling**: The LunaTask API returns `204 No Content` when a note with the same
     `notebook_id`/`source`/`source_id` already exists. The client surfaces this as `None` so the
     MCP tool can return `{ "duplicate": true }` without erroring.
   - **Error Handling**: Validation errors (422), subscription limits (402), auth errors (401),
     rate limiting (429), transient errors (timeout/network), and server errors (5xx/503) mapped to
     structured tool responses.

### Journal Entries API

#### Implemented Endpoints

1. **POST /v1/journal_entries** - Create Journal Entry
   - **Purpose**: Persist a daily journal entry for the authenticated user
   - **Implementation**: `LunaTaskClient.create_journal_entry(entry_data: JournalEntryCreate)`
   - **MCP Tool**: `create_journal_entry` (handler in `tools/journal.py`)
   - **Request Model**: `JournalEntryCreate` with required `date_on` and optional `name`/`content`
   - **Response Model**: `JournalEntryResponse` parsed from wrapped `{ "journal_entry": { ... } }`
   - **Encryption Note**: Response omits `name` and `content` because of E2E encryption in LunaTask
   - **Error Handling**: Mirrors note creation, mapping validation (422), auth (401), subscription
     (402), rate limit (429), timeout/network, server (5xx), and service unavailable (503) errors to
     structured MCP tool responses. Missing wrap keys raise
     `LunaTaskAPIError.create_parse_error("journal_entries", ...)`.

### Response Format Notes

All implemented endpoints respect LunaTask's E2E encryption constraints:
- Sensitive fields (`name`, `note`) are absent from all responses
- Sensitive fields (`name`, `note`, note `content`) are absent from all responses
- Only structural and metadata fields are available
- Error responses are properly translated to MCP error format
- Rate limiting is applied to all requests via `TokenBucketLimiter`; an additional
  `http_min_mutation_interval_seconds` configuration option can enforce a fixed
  delay before mutating requests when the API requires extra pacing.

## Alias Resource Semantics and Deterministic Sorting

### Alias Definitions

Each alias applies specific filters and client-side heuristics:

- **`now`**: Client-side only filter for unscheduled tasks that meet urgency criteria:
  - Tasks with `status == "started"` (in progress)
  - Tasks with `priority == 2` (highest priority)
  - Tasks with `motivation == "must"` (must-do tasks)
  - Tasks with `eisenhower == 1` (urgent and important)
  - Default limit: 25 items

- **`today`**: Tasks scheduled for today (UTC timezone)
  - Filter: `scheduled_on == today's date`
  - Default limit: 50 items

- **`overdue`**: Tasks scheduled before today
  - Filter: `scheduled_on < today's date`
  - Default limit: 50 items

- **`next-7-days`**: Tasks scheduled within the next 7 days (excluding today)
  - Filter: `today < scheduled_on <= today + 7 days`
  - Default limit: 50 items

- **`high-priority`**: Tasks with high priority values
  - Filter: `priority >= 1` (priority 1 or 2)
  - Default limit: 50 items

- **`recent-completions`**: Recently completed tasks
  - Filter: `completed_at` within last 72 hours
  - Default limit: 50 items

### Deterministic Sorting

Each alias applies consistent sorting to ensure deterministic results:

- **Default sorting**: `priority.desc,scheduled_on.asc,id.asc`
  - Primary: Higher priority first
  - Secondary: Earlier scheduled date first
  - Tertiary: Lexicographic ID order

- **`overdue` sorting**: `scheduled_on.asc,priority.desc,id.asc`
  - Primary: Earliest overdue date first
  - Secondary: Higher priority first
  - Tertiary: Lexicographic ID order

- **`recent-completions` sorting**: `completed_at.desc,id.asc`
  - Primary: Most recently completed first
  - Secondary: Lexicographic ID order

### Response Format

All alias resources return:
- Array of serialized `TaskResponse` objects
- Each item includes a `detail_uri` field for single-task access
- Consistent field projection across all aliases
- Client-side filtering applied where necessary for accuracy

### Discovery Document Structure

The discovery resource (`lunatask://tasks`) returns a comprehensive document describing list resource capabilities:

```json
{
  "resource_type": "lunatask_tasks_discovery",
  "params": {
    "area_id": "string",
    "scope": "global",
    "window": "today|overdue|next_7_days|now",
    "status": "later|next|started|waiting|completed|open",
    "min_priority": "low|medium|high",
    "priority": ["low", "medium", "high"],
    "completed_since": "-72h|ISO8601",
    "tz": "UTC",
    "q": "string",
    "limit": 50,
    "cursor": "opaque",
    "sort": "priority.desc,scheduled_on.asc,id.asc"
  },
  "defaults": {
    "status": "open",
    "limit": 50,
    "sort": "priority.desc,scheduled_on.asc,id.asc",
    "tz": "UTC"
  },
  "limits": {
    "max_limit": 50,
    "dense_cap": 25
  },
  "projection": [
    "id", "scheduled_on", "priority", "status", "area_id", "detail_uri"
  ],
  "sorts": {
    "default": "priority.desc,scheduled_on.asc,id.asc",
    "overdue": "scheduled_on.asc,priority.desc,id.asc",
    "recent_completions": "completed_at.desc,id.asc"
  },
  "aliases": [
    {
      "family": "area",
      "name": "now",
      "uri": "lunatask://area/{area_id}/now",
      "canonical": "lunatask://tasks?area_id={area_id}&limit=25&status=open"
    },
    {
      "family": "global",
      "name": "overdue",
      "uri": "lunatask://global/overdue",
      "canonical": "lunatask://tasks?limit=50&scope=global&sort=scheduled_on.asc,priority.desc,id.asc&status=open&window=overdue"
    }
  ],
  "guardrails": {
    "unscoped_error_code": "LUNA_TASKS/UNSCOPED_LIST",
    "message": "Provide area_id or scope=global for list views.",
    "examples": [
      "lunatask://area/AREA123/today",
      "lunatask://global/next-7-days"
    ]
  }
}
```

**Key Fields:**
- `params`: Supported query parameters with types/constraints
- `defaults`: Default values applied when parameters are omitted
- `limits`: Pagination and result set constraints
- `projection`: Fields included in each task object
- `sorts`: Available sorting options by alias type
- `aliases`: Complete list of available alias URIs with canonical mappings
- `guardrails`: Error handling and usage guidance

### Status Parameter: Composite "open" Filter

The `status` parameter supports both individual LunaTask statuses and a special composite value:

**Individual Statuses (sent to upstream API):**
- `later` - Tasks in "Later" status
- `next` - Tasks in "Next" status
- `started` - Tasks in "Started" status
- `waiting` - Tasks in "Waiting" status
- `completed` - Completed tasks

**Composite Filter (client-side only):**
- `open` - **Not sent upstream**. Applied client-side to include all non-completed tasks (`later|next|started|waiting`). This is the default filter when no status is specified.

**Implementation Note:** When `status=open` is requested, the MCP server fetches all tasks from the upstream API and applies the composite filter locally, excluding only tasks with `status=completed`.

---
