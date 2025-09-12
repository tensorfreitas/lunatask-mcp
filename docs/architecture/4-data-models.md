# 4. Data Models

We will use `pydantic`'s `BaseModel` to define our data structures. These models provide runtime type checking and serialization and are critical for ensuring we communicate with the LunaTask API correctly. The models are separated into **Response Models** (data we receive) and **Request Models** (data we send).

## Task Models

These models are based on the [Tasks API Documentation](https://lunatask.app/api/tasks-api/show).

### `Source` (Nested Response Model)

```python
from pydantic import BaseModel
from typing import Optional

class Source(BaseModel):
    """Nested model representing the source/origin of a task."""
    type: str
    value: Optional[str] = None
```

### `TaskResponse` (Response Model)

**API Response Format**: The LunaTask API returns tasks in a wrapped format: `{"tasks": [...]}`

```python
from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional

class TaskResponse(BaseModel):
    """Response model for task data received from LunaTask API.

    Note: Encrypted fields like 'name' and 'note' are absent in GET responses
    due to end-to-end encryption. This model is intentionally permissive to
    accommodate upstream values (e.g., status like "open").
    """

    id: str
    area_id: Optional[str] = None
    status: str  # permissive: accepts upstream strings
    priority: Optional[int] = 0  # permissive: no bounds enforced in response
    scheduled_on: Optional[date] = None
    created_at: datetime
    updated_at: datetime
    source: Optional[Source] = None

    goal_id: Optional[str] = None
    estimate: Optional[int] = None
    motivation: Optional[str] = None
    eisenhower: Optional[int] = None
    previous_status: Optional[str] = None
    progress: Optional[int] = None
    completed_at: Optional[datetime] = None
```

**Example API Response:**
```json
{
  "tasks": [
    {
      "id": "task-123",
      "area_id": "area-456",
      "status": "open",
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
from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional

class TaskPayload(BaseModel):
    """Shared fields and constraints for create/update requests."""
    area_id: Optional[str] = None
    goal_id: Optional[str] = None
    name: Optional[str] = None
    note: Optional[str] = None
    status: Optional[str] = None  # strict in requests; validated against enum in code
    motivation: Optional[str] = None  # strict in requests
    eisenhower: Optional[int] = None  # strict bounds in requests (0..4)
    priority: Optional[int] = None    # strict bounds in requests (-2..2)
    scheduled_on: Optional[date] = None
    completed_at: Optional[datetime] = None
    source: Optional[Source] = None
```

### `TaskCreate` (Request Model)

```python
class TaskCreate(TaskPayload):
    """Create new tasks; applies create-time defaults and requirements."""
    estimate: Optional[int] = None
    # Defaults applied: status="later", priority=0, motivation="unknown"; name required.
```

### `TaskUpdate` (Request Model)

```python
class TaskUpdate(TaskPayload):
    """Partial updates; all fields optional. Used with PATCH."""
```

## Habit Models

These models are based on the [Habits API Documentation](https://lunatask.app/api/habits-api/track-activity).

### `HabitTrackRequest` (Request Model)

```python
from pydantic import BaseModel
from datetime import date
from typing import Optional

class HabitTrackRequest(BaseModel):
    """Request model for tracking habit activities via LunaTask API."""
    habit_id: str
    date: date
    value: Optional[float] = None  # For quantified habits (e.g., glasses of water)
    completed: bool = True  # For simple completion tracking
```
