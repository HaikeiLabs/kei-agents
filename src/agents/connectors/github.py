"""Provider-neutral read tool schemas for the governed GitHub connector.

Read capabilities are scoped to the repository bound in the governed
connection preset (delegated context); agents can never target arbitrary
repositories or supply URLs/credentials. Execution is delegated to the
tenant-side distributed proxy - these schemas declare no handlers.
"""

from __future__ import annotations

from agents.tool_definitions import (
    Permission,
    ToolBinding,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
)

GITHUB_READ_TOOL_DEFINITIONS: list[ToolDefinition] = [
    ToolDefinition(
        name="github.get_repository",
        description=(
            "Read metadata (default branch, description) for the governed"
            " repository at a given ref. Use it for questions about the repository"
            " itself; it is not a step before reading a pull request"
        ),
        parameters=[
            ToolParameter(
                name="ref",
                description="Branch or tag to inspect; defaults to the default branch",
                required=False,
                default="main",
            ),
        ],
        permission=Permission.GITHUB_READ,
        category=ToolCategory.GITHUB,
        service="github",
        tags=["github-read", "governed-connector"],
        binding=ToolBinding(
            connector_id="conn_github_1",
            config={"resource": "repository", "default_branch": "main"},
            delegated_context=["tenant_id", "repository"],
        ),
    ),
    ToolDefinition(
        name="github.get_issue",
        description="Read a single issue in the governed repository",
        parameters=[
            ToolParameter(
                name="issue_number",
                description="Issue number within the governed repository",
                type="integer",
                required=True,
            ),
        ],
        permission=Permission.GITHUB_READ,
        category=ToolCategory.GITHUB,
        service="github",
        tags=["github-read", "governed-connector"],
        binding=ToolBinding(
            connector_id="conn_github_1",
            config={"resource": "issues"},
            delegated_context=["tenant_id", "repository"],
        ),
    ),
    ToolDefinition(
        name="github.get_pull_request",
        description=(
            "Read a single pull request in the governed repository to review or"
            " inspect it. Read-only: do not call it for requests to approve,"
            " comment on, merge, or close a pull request"
        ),
        parameters=[
            ToolParameter(
                name="pr_number",
                description="Pull request number within the governed repository",
                type="integer",
                required=True,
            ),
        ],
        permission=Permission.GITHUB_READ,
        category=ToolCategory.GITHUB,
        service="github",
        tags=["github-read", "governed-connector"],
        binding=ToolBinding(
            connector_id="conn_github_1",
            config={"resource": "pull_requests"},
            delegated_context=["tenant_id", "repository"],
        ),
    ),
]

__all__ = ["GITHUB_READ_TOOL_DEFINITIONS"]
