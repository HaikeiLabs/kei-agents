"""Harness agent definitions: which permissions and tools each agent holds.

An :class:`AgentDefinition` is pure data describing one harness agent's grant
surface: the typed :class:`~agents.tool_definitions.Permission` members it may
exercise, the subset whose calls need a human approval, and the catalog tool
names it exposes to its model. Harnesses (PDE, Discord, DVL Assistant) consume
these; they never carry provider clients, credentials, or org/workspace
identifiers. A definition that passes :func:`validate_agent_definitions` is
well formed, not permitted - the live allow/deny decision stays with ABAC and
the tenant-side proxy PEP.

No agent holds an ``*_approve`` permission: approval gates are resolved by a
human approver, and an agent that held the approve permission could approve
its own writes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from agents.tool_definitions import (
    ALL_TOOL_DEFINITIONS,
    Permission,
    ToolDefinition,
)


class Harness(str, Enum):
    """Product harnesses that host a Kei agent."""

    PDE = "pde"
    DISCORD = "discord"
    ASSISTANT = "assistant"


@dataclass(frozen=True)
class AgentDefinition:
    """One harness agent's permissions, approval requirements, and tools.

    Attributes:
        name: Unique agent id, ``^[a-z0-9_]+$``.
        harness: The harness that hosts the agent.
        description: What the agent is for.
        permissions: Permissions the agent may exercise.
        approval_required: Subset of ``permissions`` whose calls need a human
            approval before the harness executes them.
        tools: Names of catalog tools the agent exposes to its model. Every
            tool's permission must be in ``permissions``. May be a subset of
            what ``permissions`` allows, and empty for tools defined outside
            this catalog (e.g. the DVL Assistant's TypeScript lanes).
    """

    name: str
    harness: Harness
    description: str
    permissions: frozenset[Permission]
    approval_required: frozenset[Permission] = field(default_factory=frozenset)
    tools: tuple[str, ...] = ()


_NAME_RE = re.compile(r"^[a-z0-9_]+$")
_APPROVE_SUFFIX = "_approve"


def validate_agent_definitions(
    agents: list[AgentDefinition],
    tools: list[ToolDefinition] | None = None,
) -> list[str]:
    """Validate agent definitions against the tool catalog.

    Checks name format/uniqueness, a description, typed harness and
    permissions (bare strings are rejected), ``approval_required`` being a
    subset of ``permissions``, no ``*_approve`` permission (no self-approval),
    and that every tool exists in *tools* (default: the full catalog) with its
    permission granted. Returns a list of violations; empty means valid.
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
        for permission in agent.permissions | agent.approval_required:
            if not isinstance(permission, Permission):
                violations.append(f"{name}: invalid permission {permission!r}")
            elif permission.value.endswith(_APPROVE_SUFFIX):
                violations.append(
                    f"{name}: holds {permission.value!r}; approvals are resolved "
                    "by a human approver, never the agent (no self-approval)"
                )
        for permission in agent.approval_required - agent.permissions:
            violations.append(
                f"{name}: approval_required permission {permission!r} is not granted"
            )
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
)

PEDRO_AGENT = AgentDefinition(
    name="pedro",
    harness=Harness.DISCORD,
    description=(
        "Pedro, the Discord agent: GitHub, CRM/leads, Linear follow-ups, and "
        "the finance and fundraising workflows"
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
        }
    ),
    approval_required=frozenset(
        {
            Permission.LINEAR_WRITE,
            Permission.FUNDRAISING_WRITE,
            Permission.FINANCE_WRITE,
        }
    ),
    tools=_tool_names(
        Permission.GITHUB_READ,
        Permission.GITHUB_WRITE,
        Permission.CRM_READ,
        Permission.CRM_WRITE,
        Permission.LINEAR_READ,
        Permission.LINEAR_WRITE,
        Permission.DRIVE_READ,
    ),
)

# DVL Assistant lane permissions, keyed by the lane registry ``tool_id``
# (assistant/deployment/governor/registry/tool-lane-registry.v1.yaml; mapping
# in assistant/docs/kei-permission-vocabulary.md). Kei service/operation:
# project-hours/read (timesheet), semantic-model/read (dataset). The public
# wiki and internet search lanes map to the existing SEARCH_WIKI and
# WEB_SEARCH permissions. The dark proof-lane tools are deliberately absent.
ASSISTANT_LANE_PERMISSIONS: dict[str, Permission] = {
    "my-project-hours": Permission.PROJECT_HOURS_READ,
    "semantic-model-query": Permission.SEMANTIC_MODEL_READ,
}

DVL_ASSISTANT_AGENT = AgentDefinition(
    name="dvl_assistant",
    harness=Harness.ASSISTANT,
    description=(
        "DVL Assistant: user-scoped project hours and semantic model reads, "
        "plus public wiki and internet search"
    ),
    permissions=frozenset(
        {
            Permission.SEARCH_WIKI,
            Permission.WEB_SEARCH,
            *ASSISTANT_LANE_PERMISSIONS.values(),
        }
    ),
    tools=("search_wiki", "web_search"),
)

HARNESS_AGENT_DEFINITIONS: list[AgentDefinition] = [
    PDE_SEARCH_AGENT,
    PEDRO_AGENT,
    DVL_ASSISTANT_AGENT,
]

__all__ = [
    "ASSISTANT_LANE_PERMISSIONS",
    "DVL_ASSISTANT_AGENT",
    "HARNESS_AGENT_DEFINITIONS",
    "PDE_SEARCH_AGENT",
    "PEDRO_AGENT",
    "AgentDefinition",
    "Harness",
    "get_agent_tools",
    "validate_agent_definitions",
]
