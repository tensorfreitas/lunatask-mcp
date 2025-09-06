# 9. Infrastructure and Deployment

## Infrastructure as Code

This project will not utilize traditional Infrastructure as Code (IaC) tools like Terraform or CloudFormation, as it is not deployed to a cloud provider. The "infrastructure" is the user's local machine, and the "code" to manage it is the project's setup and installation scripts using `uv`.

## Deployment Strategy

*   **Strategy**: The primary deployment strategy is **uv**. This allows users to install the server easily and reliably on any platform using a standard command.
*   **CI/CD Platform**: **GitHub Actions** will be used to automate testing, linting, and the package deployment process.
*   **Pipeline Configuration**: The CI/CD workflow will be defined in `.github/workflows/ci.yaml`. This pipeline will:
    1.  Run `pre-commit` checks on every push to the `main` branch.
    2.  Execute the `pytest` test suite.

## Environments

The concept of "environments" is simplified for this local application:

*   **Development**: The user's local machine, running the code directly from the source within a `uv`-managed virtual environment.
*   **Production**: The user's local machine, but running the stable version of the server installed into a dedicated `uv` environment. Users will install it via:
    ```bash
    uv pip install lunatask-mcp
    ```

## Rollback Strategy

*   **Primary Method**: Rollback is managed by the user through package versioning with `uv`. If a new version introduces a bug, the user can downgrade to a previous, stable version using a single command:
    ```bash
    uv pip install lunatask-mcp==1.0.0
    ```
*   **Trigger Conditions**: A rollback would be triggered by a user discovering a critical bug in a newly released version.

---