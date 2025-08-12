# 4. Data Models

We will use `pydantic`'s `BaseModel` to define our data structures. These models provide runtime type checking and serialization and are critical for ensuring we communicate with the LunaTask API correctly. The models are separated into **Response Models** (data we receive) and **Request Models** (data we send).

## Task Models

These models are based on the [Tasks API Documentation](https://lunatask.app/api/tasks-api/show).

### `Source` (Nested Response Model)

```python