# 8. Source Tree

The project will be organized using a standard, installable Python package layout. The source code will reside within a `src` directory, which is a modern best practice that prevents many common packaging and import path issues. The package itself will be descriptively named `lunatask_mcp`.

```lunatask-mcp-server/
├── .git/
├── .gitignore
├── .pre-commit-config.yaml   # Configuration for pre-commit hooks
├── src/                      # Source code root
│   └── lunatask_mcp/         # Main application source code package
│       ├── __init__.py
│       ├── api/              # Component for LunaTask API client
│       │   ├── __init__.py
│       │   └── client.py     # Contains the LunaTaskClient class
│       ├── config.py         # Configuration loading (pydantic models)
│       ├── main.py           # Main application entry point (CoreServer)
│       ├── api/models.py     # Pydantic data models (tasks, habits)
│       └── tools/            # Components defining MCP tools
│           ├── __init__.py
│           ├── habits.py               # Habit tracking tools (track_habit tool)
│           ├── tasks.py                # TaskTools delegator/registration
│           ├── tasks_common.py         # Shared task helpers (serialization)
│           ├── tasks_resources.py      # Task list/single MCP resources
│           ├── tasks_create.py         # create_task MCP tool
│           ├── tasks_update.py         # update_task MCP tool
│           └── tasks_delete.py         # delete_task MCP tool
├── tests/                    # Tests for the application
│   ├── __init__.py
│   ├── conftest.py           # Pytest fixtures and hooks (function-scoped; avoid autouse)
│   ├── factories.py          # Simple builders to reduce duplication
│   ├── test_api_client_common.py           # Shared test helpers/constants (only for tests)
│   ├── test_api_client_init_and_http.py    # Client init and HTTP setup
│   ├── test_api_client_auth_and_connectivity.py
│   ├── test_api_client_security.py
│   ├── test_api_client_get_tasks.py
│   ├── test_api_client_rate_limiting.py
│   ├── test_api_client_get_task.py
│   ├── test_api_client_create_task.py
│   ├── test_api_client_update_task.py
│   ├── test_api_client_delete_task.py
│   ├── test_api_client_model_validation.py
│   ├── test_task_tools_init_and_registration.py
│   ├── test_task_tools_resource_list.py
│   ├── test_task_tools_resource_single.py
│   ├── test_task_tools_resource_e2e.py
│   ├── test_task_tools_create_tool.py
│   ├── test_task_tools_create_tool_e2e.py
│   ├── test_task_tools_pagination.py
│   ├── test_task_tools_update_tool.py
│   └── test_task_tools_delete_tool.py
├── pyproject.toml            # Project metadata and dependencies (for uv)
├── README.md                 # Project documentation
└── uv.lock                   # Pinned dependency versions
```

Notes:
- Tests are kept flat and split by concern. Large modules should be split well before 500 lines.
- Use [tests/factories.py](tests/factories.py) sparingly to remove duplication; prefer explicit construction.
- Prefer function-scoped fixtures in [tests/conftest.py](tests/conftest.py); avoid autouse fixtures unless essential.
- Use pytest markers to separate unit vs integration/E2E and register them in [pytest.ini](pytest.ini).

---
