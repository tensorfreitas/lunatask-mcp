# 4. Data Models

We will use `pydantic`'s `BaseModel` to define our data structures. These models provide runtime type checking and serialization and are critical for ensuring we communicate with the LunaTask API correctly. The models are separated into **Response Models** (data we receive) and **Request Models** (data we send).

## Enums and Constants

```python
from enum import StrEnum

class TaskStatus(StrEnum):
    """Status values accepted by LunaTask task creation/update."""
    LATER = "later"
    NEXT = "next"
    STARTED = "started"
    WAITING = "waiting"
    COMPLETED = "completed"

class TaskMotivation(StrEnum):
    """Motivation values accepted by LunaTask task creation/update."""
    MUST = "must"
    SHOULD = "should"
    WANT = "want"
    UNKNOWN = "unknown"

# Validation bounds
MIN_PRIORITY = -2
MAX_PRIORITY = 2
MIN_EISENHOWER = 0
MAX_EISENHOWER = 4
```

## Task Models

These models are based on the [Tasks API Documentation](https://lunatask.app/api/tasks-api/show).

### `LunataskSource` (Nested Response Model)

```python
from pydantic import BaseModel, Field, computed_field

class LunataskSource(BaseModel):
    """Source metadata entry associated with a task."""

    source: str | None = Field(
        default=None,
        description="System where the task originated (e.g., 'github', 'email')",
    )
    source_id: str | None = Field(
        default=None,
        description="Identifier of the task in the external system",
    )
```

### `TaskResponse` (Response Model)

**API Response Format**: The LunaTask API returns tasks in a wrapped format: `{"tasks": [...]}`

```python
from pydantic import BaseModel, Field
from datetime import date, datetime

class TaskResponse(BaseModel):
    """Response model for LunaTask task data.

    The API returns tasks in a wrapped format: {"tasks": [TaskResponse, ...]}.
    Encrypted fields (name, note) remain absent due to LunaTask's E2E encryption.
    """

    id: str = Field(description="The ID of the task (UUID)")
    area_id: str = Field(..., description="Area identifier")
    status: TaskStatus = Field(default=TaskStatus.LATER, description="Task status")
    priority: int = Field(..., ge=-2, le=2, description="Current priority")
    scheduled_on: date | None = Field(None, description="Scheduled date (YYYY-MM-DD)")
    created_at: datetime = Field(description="Created timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    goal_id: str | None = Field(None, description="Goal identifier, if present")
    estimate: int | None = Field(None, description="Estimated duration in minutes")
    motivation: TaskMotivation = Field(
        default=TaskMotivation.UNKNOWN, description="Motivation classification"
    )
    eisenhower: int = Field(0, ge=0, le=4, description="Eisenhower matrix quadrant")
    previous_status: TaskStatus | None = Field(default=None, description="Previous status")
    progress: int | None = Field(None, description="Completion percentage")
    completed_at: datetime | None = Field(None, description="Completion timestamp")
    sources: list[LunataskSource] = Field(
        default_factory=list,
        description="Collection of source metadata objects",
    )

    @computed_field
    def source(self) -> str | None:  # pragma: no cover - documented behaviour
        """Primary source accessor retained for backwards compatibility."""
        return self.sources[0].source if self.sources else None

    @computed_field
    def source_id(self) -> str | None:  # pragma: no cover - documented behaviour
        """Primary source ID accessor retained for backwards compatibility."""
        return self.sources[0].source_id if self.sources else None
```

**Example API Response:**
```json
{
  "tasks": [
    {
      "id": "task-123",
      "area_id": "area-456",
      "status": "later",
      "priority": 2,
      "scheduled_on": "2025-08-25",
      "created_at": "2025-08-20T10:00:00Z",
      "updated_at": "2025-08-20T10:30:00Z",
      "source": {"type": "manual", "value": "user_created"},
      "goal_id": "goal-789",
      "estimate": 60,
      "motivation": "must",
      "eisenhower": 2,
      "previous_status": "todo",
      "progress": 25,
      "scheduled_on": "2025-08-21",
      "completed_at": null
    }
  ]
}
```

### `TaskPayload` (Shared Request Base)

```python
from pydantic import BaseModel, Field
from datetime import date, datetime
from enum import StrEnum

class TaskPayload(BaseModel):
    """Shared request payload fields for task create/update operations.

    The shared payload keeps most attributes optional so that `TaskUpdate`
    can rely on Pydantic's `exclude_none` semantics to preserve PATCH behaviour.
    `TaskCreate` tightens defaults where necessary.
    """

    goal_id: str | None = Field(default=None, description="Optional goal identifier")
    status: TaskStatus | None = Field(default=None, description="Task status")
    estimate: int | None = Field(default=None, description="Estimated duration (minutes)")
    priority: int | None = Field(
        default=None, ge=-2, le=2, description="Priority value [-2, 2]"
    )
    progress: int | None = Field(default=None, description="Progress percentage")
    motivation: TaskMotivation | None = Field(
        default=None, description="Motivation classification"
    )
    eisenhower: int | None = Field(
        default=None, ge=0, le=4, description="Eisenhower quadrant [0, 4]"
    )
    scheduled_on: date | None = Field(
        default=None, description="Scheduled date (YYYY-MM-DD)"
    )
    name: str | None = Field(default=None, description="Task name (encrypted client-side)")
    note: str | None = Field(
        default=None, description="Task note in Markdown (encrypted client-side)"
    )
```

### `TaskCreate` (Request Model)

```python
class TaskCreate(TaskPayload):
    """Request model for creating new tasks in LunaTask."""

    area_id: str = Field(description="Area ID the task belongs to")
    source: str | None = Field(
        default=None,
        description="External system label (stored as first entry in sources)",
    )
    source_id: str | None = Field(
        default=None,
        description="External system identifier (stored as first entry in sources)",
    )
```

### `TaskUpdate` (Request Model)

```python
class TaskUpdate(TaskPayload):
    """Partial update payload for existing tasks."""

    id: str = Field(description="Task identifier (UUID)")
    area_id: str | None = Field(default=None, description="Updated area ID")
    priority: int | None = Field(
        default=None, ge=-2, le=2, description="Priority value [-2, 2]"
    )
```

## Note Models

The notes workflow mirrors tasks but operates on the [Notes API](https://lunatask.app/api/notes-api/create).
We reuse `LunataskSource` for note source metadata to keep a single normalized type.

### `NoteResponse` (Response Model)

```python
from datetime import date, datetime
from pydantic import BaseModel, Field, computed_field


class NoteResponse(BaseModel):
    """Response model for LunaTask notes."""

    id: str = Field(description="Unique note identifier (UUID)")
    notebook_id: str | None = Field(default=None, description="Notebook identifier")
    date_on: date | None = Field(default=None, description="Associated date for the note")
    sources: list[LunataskSource] = Field(
        default_factory=list,
        description="Collection of source metadata entries",
    )
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    deleted_at: datetime | None = Field(default=None, description="Soft-deletion timestamp")

    @computed_field
    def source(self) -> str | None:
        """Primary source accessor retained for backwards compatibility."""

        return self.sources[0].source if self.sources else None

    @computed_field
    def source_id(self) -> str | None:
        """Primary source ID accessor retained for backwards compatibility."""

        return self.sources[0].source_id if self.sources else None
```

### `NoteCreate` (Request Model)

```python
from datetime import date
from pydantic import BaseModel, Field


class NoteCreate(BaseModel):
    """Request payload for creating LunaTask notes."""

    notebook_id: str | None = Field(default=None, description="Notebook identifier")
    name: str | None = Field(default=None, description="Note title")
    content: str | None = Field(default=None, description="Markdown body")
    date_on: date | None = Field(default=None, description="ISO-8601 date associated with the note")
    source: str | None = Field(default=None, description="External system origin")
    source_id: str | None = Field(
        default=None, description="External identifier used for idempotent creates"
    )
```

# Journal Entry Models

Journal entries are lightweight diary records that mirror LunaTask's end-to-end encrypted
storage. The create endpoint accepts optional metadata, but responses only expose structural
fields. All request parameters are validated through Pydantic models in
`src/lunatask_mcp/api/models.py`.

### `JournalEntryCreate` (Request Model)

```python
from datetime import date
from pydantic import BaseModel, ConfigDict, Field


class JournalEntryCreate(BaseModel):
    """Request payload for creating LunaTask journal entries."""

    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    date_on: date = Field(description="Journal entry date (ISO-8601 date string)")
    name: str | None = Field(default=None, description="Optional journal entry title")
    content: str | None = Field(
        default=None,
        description="Markdown content body for the journal entry",
    )
```

### `JournalEntryResponse` (Response Model)

```python
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field


class JournalEntryResponse(BaseModel):
    """Response model for LunaTask journal entry data."""

    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    id: str = Field(description="Journal entry identifier (UUID)")
    date_on: date = Field(description="The date the journal entry belongs to")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
```

**Response Notes**:
- API responses omit `name` and `content` due to LunaTask's end-to-end encryption guarantees.
- The top-level payload is wrapped: `{ "journal_entry": { ... } }`. We unwrap that response in
  `LunaTaskClient.create_journal_entry()` before constructing `JournalEntryResponse`, keeping wrapper
  handling consistent with the notes client workflow and out of the Pydantic model itself.

## Habit Models

These models are based on the [Habits API Documentation](https://lunatask.app/api/habits-api/track-activity).

**Note**: Habit tracking is implemented through direct tool parameters rather than
dedicated request models. The `track_habit` tool accepts:
- `id`: string identifier for the habit (required)
- `date`: ISO-8601 formatted date string (YYYY-MM-DD) (required)

This approach keeps the implementation simple and follows the YAGNI principle.
Future enhancement could introduce a `HabitTrackRequest` model if additional
fields become necessary.
