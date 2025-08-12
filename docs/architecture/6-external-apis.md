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

---