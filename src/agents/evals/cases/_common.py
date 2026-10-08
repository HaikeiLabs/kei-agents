"""Shared building blocks for eval case tables."""

from __future__ import annotations

from typing import Any

Case = dict[str, Any]

# Proxy-delegated scoping (EV-C1 §6): never a tool argument.
DELEGATED_KEYS = ["tenant_id", "org_id", "workspace", "workspace_id", "repository", "owner"]
DRIVE_DELEGATED_KEYS = ["tenant_id", "drive_id"]

# A denied reply says so; any one of these is enough.
DENIAL_WORDS = [
    "denied",
    "not allowed",
    "permission",
    "access",
    "admin",
    "not authorized",
    "unauthorized",
    "unable",
    "can't",
    "cannot",
    "can not",
    "couldn't",
    "could not",
]


def case(
    case_id: str, prompt: str, *, context: dict[str, Any] | None = None, **expect: Any
) -> Case:
    """Build one case; keyword arguments become ``expect`` fields."""
    result: Case = {"id": case_id, "prompt": prompt}
    if context is not None:
        result["context"] = context
    result["expect"] = expect
    return result


def no_tool(case_id: str, prompt: str, **expect: Any) -> Case:
    """A case the agent must answer without calling any tool."""
    return case(case_id, prompt, tool=None, **expect)


def denied(
    case_id: str,
    prompt: str,
    *,
    allowed_tools: list[str],
    role: str = "member",
    groups: list[str] | None = None,
    **expect: Any,
) -> Case:
    """A case the policy must deny; the reply must say so, not claim success."""
    content = expect.pop("content", {})
    content.setdefault("contains_any", DENIAL_WORDS)
    context = {
        "role": role,
        "groups": groups or ["default"],
        "allowed_tools": allowed_tools,
    }
    return case(case_id, prompt, context=context, deny=True, content=content, **expect)
