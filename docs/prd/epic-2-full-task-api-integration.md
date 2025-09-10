# Epic 2: Full Task API Integration

**Expanded Goal**: The objective of this epic is to implement the complete set of supported operations for the LunaTask Tasks API, exposing them as MCP tools and resources. This includes retrieving, creating, updating, and deleting tasks, while fully respecting LunaTask's end-to-end encryption constraints. This epic also includes implementing the core rate-limiting and error-handling features.

## **Story 2.1: Area‑Scoped & Global Task List Resources (Filtered & Paginated)**
**As a** user, **I want** curated, paginated task lists as MCP resources (area‑scoped and all‑areas), **so that** my AI tools get small, relevant context slices.
### Acceptance Criteria
1. Scope rule: list views require exactly one scope — `area_id` OR `scope=global`; unscoped attempts return a structured, actionable error with examples for both families.
2. Aliases: provide canonical presets for both families with deterministic sorting and caps:
   - Area: `lunatask://area/{area_id}/now|today|overdue|next-7-days|high-priority|recent-completions`.
   - Global: `lunatask://global/now|today|overdue|next-7-days|high-priority|recent-completions`.
   - Now semantics: client-side only; includes UNDated tasks matching ANY of {status=started, priority=2,
     motivation=must, eisenhower=1}; completed tasks excluded.
3. Defaults and caps: `status=open`, minimal projection (`id,scheduled_on,priority,status,area_id,list_id,detail_uri`), deterministic sort (`priority.desc,scheduled_on.asc,id.asc`), `limit<=50` (default 25 for `now`), and `tz=UTC` by default.
4. Sorting variants: Overdue uses `scheduled_on.asc,priority.desc,id.asc`; Recent completions uses `completed_at.desc,id.asc`; null `scheduled_on` placed last for non‑overdue; null priority treated as lowest.
5. Discovery: `lunatask://tasks` becomes discovery‑only and returns params, defaults (including `tz`), limits, canonical examples for both families, sorts, projection, and guardrails.
6. Backwards compatibility: `lunatask://tasks/{id}` unchanged; creation/update/delete tools unchanged; multi‑area CSV is not supported.

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
## Story 2.7: Enforce and Validate Task Attribute Domains

As a developer, I want strict request-side validation and sensible defaults for core task attributes, so that our MCP tools only send valid states to LunaTask while remaining compatible with upstream responses.

### Acceptance Criteria
1. Request-side validation for TaskCreate and TaskUpdate:
   - status: must be one of {"later", "next", "started", "waiting", "completed"}; default "later" on create.
   - priority: integer in [-2, -1, 0, 1, 2]; default 0 on create.
   - motivation: one of {"must", "should", "want", "unknown"}; default "unknown" on create.
   - eisenhower: integer in [0, 1, 2, 3, 4] (0 = Uncategorized).
2. TaskCreate and TaskUpdate include optional motivation and eisenhower fields (validated when present); MCP tools accept and forward these fields.
3. Response handling is compatibility-first (permissive): TaskResponse accepts upstream values without normalization or rejection (e.g., "open" is passed through).
4. create_task and update_task return structured MCP errors on validation failures that clearly indicate the invalid field and allowed values.
5. Attribute evaluation tests cover presence/optionality and types for:
   - id, area_id, goal_id, status, previous_status, estimate, priority, progress, motivation, eisenhower, source, scheduled_on, completed_at, created_at, updated_at.
6. Boundary tests:
   - priority accepts -2 and 2; rejects &lt; -2 or &gt; 2 on requests.
   - eisenhower accepts 0 and 4; rejects &lt; 0 or &gt; 4 on requests.
   - status accepts only the 5 allowed values; motivation accepts only the 4 allowed values.
7. No cross-field invariants (e.g., completed ⇒ completed_at) are enforced in this story.
8. No changes to rate limiting or encryption handling.

### Development Approach (TDD)
- Write tests first (failing), then implement minimal code, then refactor when all tests pass:
  - tests/test_api_client.py: request model validation and defaults for TaskCreate/TaskUpdate (status/priority/motivation/eisenhower), boundary and rejection cases.
  - tests/test_task_tools.py: tool-level behavior for create_task and update_task returning structured errors on invalid inputs; success on valid boundary inputs; schema exposes new optional fields.
  - tests/test_task_tools.py: response attribute coverage for TaskResponse fields listed above (permissive handling, no normalization).
- Implement:
  - Add/augment request-side validation and defaults in Pydantic models in src/lunatask_mcp/api/models.py for TaskCreate and TaskUpdate.
  - Extend MCP tools parameter schemas in src/lunatask_mcp/tools/tasks.py to accept motivation and eisenhower; forward validated values to the client.
  - Keep TaskResponse permissive; do not map values like "open" → "later".
- Refactor:
  - Ensure consistent structured MCP error formatting across tools; keep logs secure and tokens redacted.
