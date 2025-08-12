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
│       ├── models/           # Pydantic data models
│       │   ├── __init__.py
│       │   ├── habit.py      # Habit related models
│       │   └── task.py       # Task related models
│       └── tools/            # Components defining MCP tools
│           ├── __init__.py
│           ├── habits.py     # Defines the HabitTools
│           └── tasks.py      # Defines the TaskTools
├── tests/                    # Tests for the application
│   ├── __init__.py
│   ├── conftest.py           # Pytest fixtures and hooks
│   └── test_tasks.py         # Tests for the task tools
├── pyproject.toml            # Project metadata and dependencies (for uv)
├── README.md                 # Project documentation
└── uv.lock                   # Pinned dependency versions
```

---