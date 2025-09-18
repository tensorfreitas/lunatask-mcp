# 8. Source Tree

The project will be organized using a standard, installable Python package layout. The source code will reside within a `src` directory, which is a modern best practice that prevents many common packaging and import path issues. The package itself will be descriptively named `lunatask_mcp`.

```text
lunatask-mcp/
├── src/
│   └── lunatask_mcp/
│       ├── __init__.py
│       ├── api/
│       │   ├── __init__.py
│       │   ├── client.py              # LunaTaskClient + request orchestration
│       │   └── models.py              # Pydantic enums/models with TaskSource support
│       ├── config.py                  # ServerConfig settings + validation
│       ├── main.py                    # CoreServer bootstrap & cli parsing
│       ├── rate_limiter.py            # TokenBucketLimiter used by client
│       └── tools/
│           ├── __init__.py
│           ├── habits.py              # HabitTools + track_habit registration
│           ├── tasks.py               # TaskTools delegator and MCP bindings
│           ├── tasks_common.py        # Shared serialization helpers
│           ├── tasks_create.py        # create_task handler (coercion & validation)
│           ├── tasks_update.py        # update_task handler (partial updates)
│           ├── tasks_delete.py        # delete_task handler
│           └── tasks_resources.py     # Discovery, list, alias & single task resources
├── tests/
│   ├── conftest.py, factories.py      # Function-scoped fixtures and builders
│   ├── api client suite               # init/auth/connectivity/rate limiting/model validation
│   ├── task tool suite                # registration, CRUD tools, alias resources, pagination
│   ├── habit tool & stdio suites      # habit tracking, protocol metadata, stdio integration
│   └── configuration/error suites     # config precedence, logging, shutdown handling
├── docs/                              # Architecture + PRD documentation
├── pyproject.toml / uv.lock           # Project metadata (managed by uv)
└── README.md                          # Primary onboarding guide
```

Notes:
- Tests remain flat and are grouped by concern (API client, tools, stdio, configuration).
- Use [tests/factories.py](tests/factories.py) sparingly to remove duplication; prefer explicit construction.
- Prefer function-scoped fixtures in [tests/conftest.py](tests/conftest.py); avoid autouse fixtures unless essential.
- Use pytest markers to separate unit vs integration/E2E and register them in [pytest.ini](pytest.ini).

---
