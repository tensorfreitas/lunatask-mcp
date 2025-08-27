# 11. Coding Standards

## Design Principles

*   **KISS (Keep It Simple, Stupid)**: Simplicity is a key design goal. Straightforward solutions are always preferred over complex ones.
*   **YAGNI (You Aren't Gonna Need It)**: Do not build functionality on speculation. Implement features only when required by the current stories.
*   **Single Responsibility**: Each function, class, and module must have one clear, well-defined purpose.
*   **Open/Closed Principle**: Software entities should be open for extension but closed for modification.
*   **Dependency Inversion**: High-level modules shall not depend on low-level modules; both should depend on abstractions.
*   **Fail Fast**: Check for potential errors as early as possible and raise exceptions immediately when issues occur.

## Core Standards

*   **Languages & Runtimes**: All Python code **must** be compatible with **Python 3.12**.
*   **Style & Linting**: Code style will be enforced by **`ruff`**.
*   **Type Checking**: All new code **must** include type hints, enforced by **`pyright`** in its strict mode.
*   **Test Organization**: Tests will be located in the top-level `tests/` directory. Test filenames **must** follow the `test_*.py` pattern.
*   **Docstrings**: All modules, classes, and functions **MUST** have docstrings that follow the **Google Python Style Guide format**.

## Code Structure & Modularity

*   **File and Function Limits**: No file should exceed 500 lines of code. If approaching this limit, refactor into smaller, focused modules. This limit applies to both source files and test files. Test modules should be split by concern well before the limit.
*   **Line Length**: The maximum line length is **100 characters**, as enforced by `ruff`.
*   **Modularity**: Code must be organized into clearly separated modules, grouped by feature or responsibility as defined in the project's source tree.

## Naming Conventions

| Element | Convention | Example |
| :--- | :--- | :--- |
| Packages/Modules | `snake_case` | `lunatask_mcp` |
| Classes | `PascalCase` | `LunaTaskClient` |
| Functions/Methods | `snake_case` | `create_task` |
| Variables/Constants| `snake_case` | `bearer_token` |
| Custom Exceptions | `PascalCase` ending in `Error` | `TaskNotFoundError` |

## Testing Strategy

**Test-Driven Development (TDD) is the required methodology for this project.** The development cycle is as follows:
1.  **Write the test first**: Define the expected behavior before writing the implementation.
2.  **Watch it fail**: Run the test to confirm it fails as expected.
3.  **Write minimal code**: Write only the code necessary to make the test pass.
4.  **Refactor**: Improve the implementation while ensuring all tests remain green.
5.  **Repeat**: Continue this cycle for all new functionality.

### Test Organization and Conventions
- Tests live in the top-level `tests/` directory and follow the `test_*.py` naming.
- Prefer function-scoped fixtures; avoid `autouse` fixtures unless essential.
- Use `pytest` markers to separate unit vs integration/E2E tests (e.g., `@pytest.mark.integration`); register markers in `pytest.ini` to avoid unknown-marker warnings.
- Keep tests flat by concern; split large modules before reaching 500 lines and favor explicit construction. Use `tests/factories.py` only to reduce duplication. Each test file should remain under 500 lines.
- Ensure logging assertions attach to `stderr` only (never `stdout`).
- CI must run `ruff` and `pyright` against `tests/`, and maintain or improve the current coverage baseline.

## Critical Rules for AI Agents

1.  **Log to `stderr` Only**: All logging operations **must** be directed to `sys.stderr`.
2.  **No `print()` Statements**: `print()` is forbidden. Use the configured logger.
3.  **Use Custom Exceptions**: Always raise specific custom exceptions from `api/exceptions.py`.
4.  **Secure Token Handling**: The LunaTask bearer token must never be included in logs or exceptions.
5.  **Use `async/await`**: All I/O operations **must** use `async/await`.
6.  **Type Everything**: All function signatures must have explicit type hints.

## Development Workflow
*   **Pre-commit Hooks**: The `.pre-commit-config.yaml` file will run `ruff` and `pyright` before each commit across `src/` and `tests/`. Commits that fail these checks will be rejected.