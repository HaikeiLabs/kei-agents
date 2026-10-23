"""GitHub tool definitions for agent integration.

This module provides tool definitions for GitHub operations.
"""

from __future__ import annotations

from agents.github import (
    github_create_issue,
    github_get_workflow_status,
    github_list_issues,
    github_list_prs,
)
from agents.tool_definitions import (
    Permission,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
)

GITHUB_FIX_ACTION_TOOL = ToolDefinition(
    name="github.create_fix_pull_request",
    description=(
        "Propose a pull-request fix for the server-selected repository and branch. "
        "Provide a concise title, a PR description, and a unified diff of at most "
        "32 KiB. The server controls the target repository, branch, and draft status."
    ),
    parameters=[
        ToolParameter(name="title", description="Pull request title", required=True),
        ToolParameter(name="body", description="Pull request description", required=True),
        ToolParameter(
            name="unified_diff",
            description="Unified diff to apply (maximum 32 KiB)",
            required=True,
        ),
    ],
    permission=Permission.GITHUB_WRITE,
    category=ToolCategory.GITHUB,
    service="github",
    tags=["github-write", "fix-action"],
)

# Opt-in only: this action is intentionally absent from GITHUB_TOOL_DEFINITIONS,
# TOOL_DEFINITIONS, and ALL_TOOL_DEFINITIONS. Fix agents must select it directly.
GITHUB_FIX_ACTION_TOOL_DEFINITIONS: list[ToolDefinition] = [GITHUB_FIX_ACTION_TOOL]

GITHUB_TOOL_DEFINITIONS: list[ToolDefinition] = [
    ToolDefinition(
        name="list_issues",
        description="List GitHub issues with optional filtering",
        parameters=[
            ToolParameter(
                name="state",
                description="Filter by issue state",
                required=False,
                enum=["open", "closed", "all"],
                default="open",
            ),
            ToolParameter(
                name="labels",
                description="Comma-separated list of labels to filter by",
                required=False,
            ),
            ToolParameter(
                name="limit",
                description="Maximum number of issues to return",
                type="integer",
                required=False,
                default=30,
            ),
        ],
        permission=Permission.GITHUB_READ,
        category=ToolCategory.GITHUB,
        handler=github_list_issues,
    ),
    ToolDefinition(
        name="create_issue",
        description="Create a new GitHub issue with governance workflow",
        parameters=[
            ToolParameter(
                name="title",
                description="Issue title (required)",
                required=True,
            ),
            ToolParameter(
                name="body",
                description="Issue body/description",
                required=False,
            ),
            ToolParameter(
                name="labels",
                description="Comma-separated list of labels",
                required=False,
            ),
            ToolParameter(
                name="assignee",
                description="Username to assign the issue to",
                required=False,
            ),
            ToolParameter(
                name="auto_approve",
                description="Skip approval for governance (use with caution)",
                required=False,
            ),
        ],
        permission=Permission.GITHUB_WRITE,
        category=ToolCategory.GITHUB,
        handler=github_create_issue,
    ),
    ToolDefinition(
        name="get_workflow_status",
        description="Get CI/CD workflow status",
        parameters=[
            ToolParameter(
                name="workflow_name",
                description="Name of the workflow",
                required=True,
            ),
        ],
        permission=Permission.GITHUB_READ,
        category=ToolCategory.GITHUB,
        handler=github_get_workflow_status,
    ),
    ToolDefinition(
        name="list_prs",
        description="List GitHub pull requests",
        parameters=[
            ToolParameter(
                name="state",
                description="Filter by PR state",
                required=False,
                enum=["open", "closed", "all"],
                default="open",
            ),
            ToolParameter(
                name="limit",
                description="Maximum number of PRs to return",
                type="integer",
                required=False,
                default=30,
            ),
        ],
        permission=Permission.GITHUB_READ,
        category=ToolCategory.GITHUB,
        handler=github_list_prs,
    ),
]


__all__ = [
    "GITHUB_FIX_ACTION_TOOL",
    "GITHUB_FIX_ACTION_TOOL_DEFINITIONS",
    "GITHUB_TOOL_DEFINITIONS",
    "github_create_issue",
    "github_get_workflow_status",
    "github_list_issues",
    "github_list_prs",
]
