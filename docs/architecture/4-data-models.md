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

### `Source` (Nested Response Model)

```python
from pydantic import BaseModel, Field

class Source(BaseModel):
    """Source information for task origin."""
    type: str = Field(..., description="Type of source (e.g., 'email', 'web', 'manual')")
    value: str | None = Field(None, description="Source value or identifier")
```

### `TaskResponse` (Response Model)

**API Response Format**: The LunaTask API returns tasks in a wrapped format: `{"tasks": [...]}`

```python
from pydantic import BaseModel, Field
from datetime import date, datetime

class TaskResponse(BaseModel):
    """Response model for LunaTask task data.

    This model represents a task as returned by the LunaTask API in wrapped format.
    API returns tasks in: {"tasks": [TaskResponse, ...]}
    Note: Encrypted fields (name, note) are not included due to E2E encryption.
    """

    id: str = Field(description="The ID of the task (UUID)")
    area_id: str = Field(..., description="The ID of the area the task belongs in")
    status: TaskStatus = Field(description="Task status")
    priority: int = Field(..., ge=-2, le=2, description="Current priority")
    scheduled_on: date | None = Field(None, description="Date when task is scheduled")
    created_at: datetime = Field(description="Task creation timestamp")
    updated_at: datetime = Field(description="Task last update timestamp")
    source: Source | None = Field(None, description="Task source information")

    goal_id: str | None = Field(None, description="The ID of the goal the task belongs in")
    estimate: int | None = Field(None, description="Estimated duration in minutes")
    motivation: TaskMotivation = Field(default=TaskMotivation.UNKNOWN, description="Task motivation")
    eisenhower: int = Field(0, ge=0, le=4, description="Eisenhower matrix quadrant")
    previous_status: TaskStatus | None = Field(default=None, description="Previous task status")
    progress: int | None = Field(None, description="Task completion percentage")
    completed_at: datetime | None = Field(None, description="Task completion timestamp")
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
    """Shared request payload fields for task create/update.

    This base model centralizes field declarations and validation constraints
    common to both TaskCreate and TaskUpdate. Fields that need defaults
    for creation are overridden in TaskCreate with proper non-None defaults.
    """

    # Note: area_id is defined in subclasses (TaskCreate, TaskUpdate)
    goal_id: str | None = Field(default=None, description="Goal ID (optional)")
    status: TaskStatus = Field(default=TaskStatus.LATER, description="Task status")
    estimate: int | None = Field(default=None, description="Estimated duration in minutes")
    priority: int = Field(default=0, ge=-2, le=2, description="Priority level [-2, 2]")
    progress: int | None = Field(default=None, description="Task completion percentage")
    motivation: TaskMotivation | None = Field(default=None, description="Motivation level")
    eisenhower: int | None = Field(default=None, ge=0, le=4, description="Eisenhower quadrant [0, 4]")
    scheduled_on: date | None = Field(default=None, description="Scheduled date (YYYY-MM-DD)")
    source: Source | None = Field(default=None, description="Task source information")
    # Encrypted content fields
    name: str | None = Field(default=None, description="Task name (encrypted client-side)")
    note: str | None = Field(default=None, description="Task note (encrypted client-side)")
```

### `TaskCreate` (Request Model)

```python
class TaskCreate(TaskPayload):
    """Request model for creating new tasks in LunaTask.

    Inherits shared fields and validation from TaskPayload and applies
    create-time defaults and requirements.
    """

    area_id: str = Field(description="Area ID the task belongs to")
    # All other fields inherited from TaskPayload with their defaults
    # Defaults: status="later", priority=0, motivation=None
```

### `TaskUpdate` (Request Model)

```python
class TaskUpdate(TaskPayload):
    """Partial update payload for existing tasks.

    Inherits from TaskPayload to maintain field validation constraints.
    All fields are optional to support PATCH semantics. Outbound serialization
    uses model_dump(exclude_none=True) to send only changed fields.
    """
    id: str = Field(description="The ID of the task (UUID)")
    area_id: str | None = Field(default=None, description="Area ID the task belongs to")
    # All other fields inherited from TaskPayload as optional
```

## Habit Models

These models are based on the [Habits API Documentation](https://lunatask.app/api/habits-api/track-activity).

**Note**: Habit tracking is implemented through direct tool parameters rather than
dedicated request models. The `track_habit` tool accepts:
- `id`: string identifier for the habit (required)
- `date`: ISO-8601 formatted date string (YYYY-MM-DD) (required)

This approach keeps the implementation simple and follows the YAGNI principle.
Future enhancement could introduce a `HabitTrackRequest` model if additional
fields become necessary.
