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

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class TaskResponse(BaseModel):
    """Response model for task data received from LunaTask API.
    
    Note: Encrypted fields like 'name' and 'notes' are absent in GET responses
    due to end-to-end encryption.
    """
    id: str
    area_id: Optional[str] = None
    status: str  # e.g., "open", "completed", "canceled"
    priority: Optional[int] = None
    due_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    source: Optional[Source] = None
    tags: List[str] = []
    # Note: 'name' and 'notes' fields are encrypted and not returned in responses
```

### `TaskCreate` (Request Model)

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class TaskCreate(BaseModel):
    """Request model for creating new tasks via LunaTask API."""
    name: str
    notes: Optional[str] = None
    area_id: Optional[str] = None
    status: str = "open"
    priority: Optional[int] = None
    due_date: Optional[datetime] = None
    tags: List[str] = []
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
    notes: Optional[str] = None
    area_id: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[int] = None
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = None
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
    notes: Optional[str] = None
```