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
    type: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None
```

### `TaskResponse` (Response Model)

**API Response Format**: The LunaTask API returns tasks in a wrapped format: `{"tasks": [...]}`

```python
from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, List

class TaskResponse(BaseModel):
    """Response model for task data received from LunaTask API.
    
    Note: Encrypted fields like 'name' and 'note' are absent in GET responses
    due to end-to-end encryption.
    """
    # Core fields
    id: str
    area_id: Optional[str] = None
    status: str  # e.g., "open", "completed", "canceled"
    priority: Optional[int] = None
    due_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    source: Optional[Source] = None
    
    # Additional fields from LunaTask API
    goal_id: Optional[str] = None  # Goal ID the task belongs to
    estimate: Optional[int] = None  # Estimated duration in minutes
    motivation: Optional[str] = None  # Task motivation: "must", "should", "want", "unknown"
    eisenhower: Optional[int] = None  # Eisenhower matrix quadrant (0-4)
    previous_status: Optional[str] = None  # Previous task status
    progress: Optional[int] = None  # Task completion percentage (0-100)
    scheduled_on: Optional[date] = None  # Date when task is scheduled
    completed_at: Optional[datetime] = None  # Task completion timestamp
    
    # Note: 'name' and 'note' fields are encrypted and not returned in responses
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
      "due_date": "2025-08-25T18:00:00Z",
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

### `TaskCreate` (Request Model)

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class TaskCreate(BaseModel):
    """Request model for creating new tasks via LunaTask API."""
    name: str
    note: Optional[str] = None
    area_id: Optional[str] = None
    status: str = "open"
    priority: Optional[int] = None
    due_date: Optional[datetime] = None
    source: Optional[dict] = None
```

### `TaskUpdate` (Request Model)

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class TaskUpdate(BaseModel):
    """Request model for updating existing tasks via LunaTask API.
    
    All fields are optional to support partial updates.
    """
    name: Optional[str] = None
    note: Optional[str] = None
    area_id: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[int] = None
    due_date: Optional[datetime] = None
    source: Optional[dict] = None
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
    note: Optional[str] = None
```