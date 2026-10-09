"""Provider-neutral read tool schemas for the governed Linear connector.

Read capabilities are scoped to the Linear workspace bound in the governed
connection preset (delegated context); agents can never target arbitrary
workspaces or supply URLs/credentials. Execution is delegated to the
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

LINEAR_READ_TOOL_DEFINITIONS: list[ToolDefinition] = [
    ToolDefinition(
        name="linear.list_issues",
        description="List issues in the governed Linear workspace",
        parameters=[
            ToolParameter(
                name="state",
                description="Filter by workflow state",
                required=False,
                enum=["backlog", "unstarted", "started", "done", "canceled"],
            ),
            ToolParameter(
                name="priority",
                description="Filter by priority",
                required=False,
                enum=["urgent", "high", "medium", "low", "none"],
            ),
            ToolParameter(
                name="assignee",
                description="Filter by assignee display name",
                required=False,
            ),
            ToolParameter(
                name="limit",
                description="Maximum number of issues to return",
                type="integer",
                required=False,
                default=50,
            ),
        ],
        permission=Permission.LINEAR_READ,
        category=ToolCategory.LINEAR,
        service="linear",
        tags=["linear-read", "governed-connector"],
        binding=ToolBinding(
            connector_id="conn_linear_1",
            config={"resource": "issues"},
            delegated_context=["tenant_id", "workspace"],
        ),
    ),
    ToolDefinition(
        name="linear.get_issue",
        description=(
            "Read a single issue by its key in the governed Linear workspace."
            " Use it when the user asks about an issue (status, details); do not"
            " call it just because a request mentions an issue key"
        ),
        parameters=[
            ToolParameter(
                name="issue_key",
                description="Issue key, e.g. ENG-123",
                required=True,
            ),
        ],
        permission=Permission.LINEAR_READ,
        category=ToolCategory.LINEAR,
        service="linear",
        tags=["linear-read", "governed-connector"],
        binding=ToolBinding(
            connector_id="conn_linear_1",
            config={"resource": "issues"},
            delegated_context=["tenant_id", "workspace"],
        ),
    ),
    ToolDefinition(
        name="linear.list_projects",
        description="List projects in the governed Linear workspace",
        parameters=[
            ToolParameter(
                name="state",
                description="Filter by project state",
                required=False,
                enum=[
                    "backlog",
                    "planned",
                    "started",
                    "paused",
                    "completed",
                    "canceled",
                ],
            ),
            ToolParameter(
                name="limit",
                description="Maximum number of projects to return",
                type="integer",
                required=False,
                default=50,
            ),
        ],
        permission=Permission.LINEAR_READ,
        category=ToolCategory.LINEAR,
        service="linear",
        tags=["linear-read", "governed-connector"],
        binding=ToolBinding(
            connector_id="conn_linear_1",
            config={"resource": "projects"},
            delegated_context=["tenant_id", "workspace"],
        ),
    ),
]

__all__ = ["LINEAR_READ_TOOL_DEFINITIONS"]
