"""Harness agent definitions: which permissions and tools each agent holds.

An :class:`AgentDefinition` is pure data describing one harness agent's grant
surface: the typed :class:`~agents.tool_definitions.Permission` members it may
exercise and the catalog tool names it exposes to its model. Harnesses (PDE,
Discord) consume these; they never carry provider clients, credentials, or
org/workspace identifiers. A definition that passes
:func:`validate_agent_definitions` is well formed, not permitted — the live
allow/deny decision stays with ABAC and the tenant-side proxy PEP.

No agent holds an ``*_approve`` permission: those permissions are reserved
and not granted to agents.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from importlib import resources
from pathlib import PurePosixPath

from agents.tool_definitions import (
    ALL_TOOL_DEFINITIONS,
    Permission,
    ToolDefinition,
)


class Harness(str, Enum):
    """Product harnesses that host a Kei agent."""

    PDE = "pde"
    DISCORD = "discord"


@dataclass(frozen=True)
class AgentDefinition:
    """One harness agent's permissions, approval requirements, and tools.

    Attributes:
        name: Unique agent id, ``^[a-z0-9_]+$``.
        harness: The harness that hosts the agent.
        description: What the agent is for.
        permissions: Permissions the agent may exercise.
        tools: Names of catalog tools the agent exposes to its model. Every
            tool's permission must be in ``permissions``. May be a subset of
            what ``permissions`` allows, and empty for tools defined outside
            this catalog.
        system_prompt: Inline system prompt. Optional; at most one of
            ``system_prompt`` and ``system_prompt_file`` may be set.
        system_prompt_file: Path of a system prompt file relative to the
            ``agents`` package (e.g. ``prompts/pedro.md``), so prompts ship as
            data with the package. Read it with :func:`load_system_prompt`.
    """

    name: str
    harness: Harness
    description: str
    permissions: frozenset[Permission]
    tools: tuple[str, ...] = ()
    system_prompt: str | None = None
    system_prompt_file: str | None = None


_NAME_RE = re.compile(r"^[a-z0-9_]+$")
_APPROVE_SUFFIX = "_approve"


def _prompt_file_violation(path: str) -> str | None:
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts:
        return f"system_prompt_file {path!r} must be relative to the agents package"
    if not resources.files("agents").joinpath(path).is_file():
        return f"system_prompt_file {path!r} not found in the agents package"
    return None


def load_system_prompt(agent: AgentDefinition) -> str | None:
    """Return the agent's system prompt, reading its prompt file if it has one.

    Returns ``None`` for an agent that declares no prompt.
    """
    if agent.system_prompt_file is not None:
        violation = _prompt_file_violation(agent.system_prompt_file)
        if violation is not None:
            raise ValueError(f"{agent.name}: {violation}")
        return (
            resources.files("agents")
            .joinpath(agent.system_prompt_file)
            .read_text(encoding="utf-8")
        )
    return agent.system_prompt


def validate_agent_definitions(
    agents: list[AgentDefinition],
    tools: list[ToolDefinition] | None = None,
) -> list[str]:
    """Validate agent definitions against the tool catalog.

    Checks name format/uniqueness, a description, typed harness and
    permissions (bare strings are rejected), no ``*_approve`` permission
    (reserved), that every tool exists in *tools* (default: the full
    catalog) with its permission granted, and that at most one system prompt
    source is set and a prompt file resolves inside the package. Returns a
    list of violations; empty means valid.
    """
    catalog = {t.name: t for t in (ALL_TOOL_DEFINITIONS if tools is None else tools)}
    violations: list[str] = []
    seen: set[str] = set()
    for agent in agents:
        name = agent.name
        if not _NAME_RE.fullmatch(name):
            violations.append(f"invalid name {name!r}: must match {_NAME_RE.pattern}")
        if name in seen:
            violations.append(f"duplicate agent name: {name!r}")
        seen.add(name)
        if not agent.description:
            violations.append(f"{name}: description is required")
        if not isinstance(agent.harness, Harness):
            violations.append(f"{name}: invalid harness {agent.harness!r}")
        for permission in agent.permissions:
            if not isinstance(permission, Permission):
                violations.append(f"{name}: invalid permission {permission!r}")
            elif permission.value.endswith(_APPROVE_SUFFIX):
                violations.append(
                    f"{name}: holds {permission.value!r}; "
                    "_approve permissions are reserved and not granted to agents"
                )
        if agent.system_prompt is not None and agent.system_prompt_file is not None:
            violations.append(
                f"{name}: set system_prompt or system_prompt_file, not both"
            )
        if agent.system_prompt_file is not None:
            violation = _prompt_file_violation(agent.system_prompt_file)
            if violation is not None:
                violations.append(f"{name}: {violation}")
        tool_names: set[str] = set()
        for tool_name in agent.tools:
            if tool_name in tool_names:
                violations.append(f"{name}: duplicate tool {tool_name!r}")
            tool_names.add(tool_name)
            tool = catalog.get(tool_name)
            if tool is None:
                violations.append(f"{name}: unknown tool {tool_name!r}")
            elif tool.permission not in agent.permissions:
                violations.append(
                    f"{name}: tool {tool_name!r} needs permission "
                    f"{tool.permission.value!r}, which is not granted"
                )
    return violations


def get_agent_tools(
    agent: AgentDefinition, tools: list[ToolDefinition] | None = None
) -> list[ToolDefinition]:
    """Resolve an agent's tool names to catalog definitions, in order."""
    catalog = {t.name: t for t in (ALL_TOOL_DEFINITIONS if tools is None else tools)}
    return [catalog[name] for name in agent.tools if name in catalog]


def _tool_names(*permissions: Permission) -> tuple[str, ...]:
    return tuple(t.name for t in ALL_TOOL_DEFINITIONS if t.permission in permissions)


_PDE_PERMISSIONS = (
    Permission.DRIVE_READ,
    Permission.NOTION_READ,
    Permission.GMAIL_READ,
    Permission.TITO_READ,
)

PDE_SEARCH_AGENT = AgentDefinition(
    name="pde_search_agent",
    harness=Harness.PDE,
    description=(
        "PDE search agent: read-only search across the governed Drive, "
        "Notion, Gmail, and Tito connectors"
    ),
    permissions=frozenset(_PDE_PERMISSIONS),
    tools=_tool_names(*_PDE_PERMISSIONS),
    system_prompt_file="prompts/pde_search_agent.md",
)

# Pedro's everyday tools, open to the Discord default group. Every other
# Pedro tool reads or writes governed data and is for admins; the group split
# is enforced by ABAC policy, not by this definition.
PEDRO_DEFAULT_GROUP_TOOLS: tuple[str, ...] = ("file_bug", "search_wiki", "web_search")
_PEDRO_DATA_PERMISSIONS = (
    Permission.GITHUB_READ,
    Permission.GITHUB_WRITE,
    Permission.CRM_READ,
    Permission.CRM_WRITE,
    Permission.LINEAR_READ,
    Permission.LINEAR_WRITE,
    Permission.DRIVE_READ,
)
# linear.create_issue is the bug_to_linear_pr workflow's own step; Pedro
# reaches it through file_bug.
_PEDRO_EXCLUDED_TOOLS = frozenset({*PEDRO_DEFAULT_GROUP_TOOLS, "linear.create_issue"})

PEDRO_AGENT = AgentDefinition(
    name="pedro",
    harness=Harness.DISCORD,
    description=(
        "Pedro, the Discord agent: bug filing, wiki and web search, GitHub, "
        "CRM/leads, Linear follow-ups, and the finance and fundraising workflows"
    ),
    permissions=frozenset(
        {
            Permission.GITHUB_READ,
            Permission.GITHUB_WRITE,
            Permission.CRM_READ,
            Permission.CRM_WRITE,
            Permission.LINEAR_READ,
            Permission.LINEAR_WRITE,
            # The finance and fundraising workflows read documents and the
            # fundraising data room through the governed Drive.
            Permission.DRIVE_READ,
            Permission.FUNDRAISING_READ,
            Permission.FUNDRAISING_WRITE,
            Permission.FINANCE_READ,
            Permission.FINANCE_WRITE,
            Permission.SEARCH_WIKI,
            Permission.WEB_SEARCH,
        }
    ),
    tools=PEDRO_DEFAULT_GROUP_TOOLS
    + tuple(
        name
        for name in _tool_names(*_PEDRO_DATA_PERMISSIONS)
        if name not in _PEDRO_EXCLUDED_TOOLS
    ),
    system_prompt_file="prompts/pedro.md",
)

HARNESS_AGENT_DEFINITIONS: list[AgentDefinition] = [
    PDE_SEARCH_AGENT,
    PEDRO_AGENT,
]

__all__ = [
    "HARNESS_AGENT_DEFINITIONS",
    "PDE_SEARCH_AGENT",
    "PEDRO_AGENT",
    "PEDRO_DEFAULT_GROUP_TOOLS",
    "AgentDefinition",
    "Harness",
    "get_agent_tools",
    "load_system_prompt",
    "validate_agent_definitions",
]
