# Epic 2: Full Task API Integration

**Expanded Goal**: The objective of this epic is to implement the complete set of supported operations for the LunaTask Tasks API, exposing them as MCP tools and resources. This includes retrieving, creating, updating, and deleting tasks, while fully respecting LunaTask's end-to-end encryption constraints. This epic also includes implementing the core rate-limiting and error-handling features.

## **Story 2.1: Retrieve All Tasks Resource**
**As a** user, **I want** to retrieve a list of all my tasks via an MCP resource, **so that** my AI tools can have context on my existing to-dos.
### Acceptance Criteria
1. An MCP `resource` is implemented that corresponds to the `GET /v1/tasks` endpoint.
2. When accessed, the resource makes an authenticated `GET` request to the LunaTask API.
3. A successful response returns a list of task objects.
4. **Crucially**, the returned data respects LunaTask's E2E encryption: fields like `name` and `note` will not be present in the response, and the implementation must handle their absence gracefully.
5. An error response from the LunaTask API results in a structured MCP error.

## **Story 2.2: Retrieve a Single Task Resource**
**As a** user, **I want** to retrieve the details of a single task by its ID, **so that** my AI tools can get information about a specific to-do item.
### Acceptance Criteria
1. An MCP `resource` is implemented that corresponds to the `GET /v1/tasks/<id>` endpoint.
2. The resource accepts a task `id` as a parameter.
3. A successful response returns the specific task object.
4. The implementation correctly handles the absence of encrypted fields (`name`, `note`, etc.) in the API response.
5. If the task is not found, a specific MCP error is returned.

## **Story 2.3: Create Task Tool**
**As a** user, **I want** to create a new task in LunaTask using an MCP tool, **so that** I can add to-dos from my integrated AI applications.
### Acceptance Criteria
1. An MCP `tool` named `create_task` is implemented, corresponding to `POST /v1/tasks`.
2. The tool accepts all necessary parameters to create a LunaTask task (e.g., `listId`, `name`, `note`).
3. A successful API call results in an MCP response containing the ID of the newly created task.

## **Story 2.4: Update Task Tool**
**As a** user, **I want** to update an existing task in LunaTask using an MCP tool, **so that** I can modify to-dos from my integrated AI applications.
### Acceptance Criteria
1. An MCP `tool` named `update_task` is implemented, corresponding to `PATCH /v1/tasks/<id>`.
2. The tool accepts the `id` of the task to update, along with any modifiable fields.
3. A successful API call results in a successful MCP response.

## **Story 2.5: Delete Task Tool**
**As a** user, **I want** to delete a task by its ID using an MCP tool, **so that** I can clean up completed or unnecessary to-dos.
### Acceptance Criteria
1. An MCP `tool` named `delete_task` is implemented, corresponding to `DELETE /v1/tasks/<id>`.
2. The tool accepts the `id` of the task to delete.
3. A successful deletion (e.g., a 204 No Content response) results in a successful MCP response.
4. An error is returned if the task ID does not exist.

## **Story 2.6: Implement Rate Limiter**
**As a** developer, **I want** all outgoing requests to the LunaTask API to be managed by a configurable rate limiter, **so that** the server operates reliably without being blocked.
### Acceptance Criteria
1. A configurable, in-memory rate-limiting mechanism is implemented.
2. All five MCP resources/tools created in this epic use the rate limiter before making an external API call.
3. When a request is rate-limited, the server returns a specific, structured MCP error to the client.

---