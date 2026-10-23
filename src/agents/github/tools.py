"""Opt-in GitHub write action metadata."""

from typing import Any, TypedDict

from agents.permissions import Permission


class GitHubFixAction(TypedDict):
    name: str
    description: str
    parameters: dict[str, Any]
    permission: Permission


GITHUB_FIX_ACTION_TOOL: GitHubFixAction = {
    "name": "github.create_fix_pr",
    "description": (
        "Propose a pull-request fix for the server-selected repository and branch. "
        "Provide a concise title, a PR description, and a unified diff of at most "
        "32 KiB. The server controls the target repository, branch, and draft status."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Pull request title"},
            "body": {"type": "string", "description": "Pull request description"},
            "unified_diff": {
                "type": "string",
                "description": "Unified diff to apply (maximum 32 KiB)",
            },
        },
        "required": ["title", "body", "unified_diff"],
        "additionalProperties": False,
    },
    "permission": Permission.GITHUB_WRITE,
}

__all__ = ["GITHUB_FIX_ACTION_TOOL"]
