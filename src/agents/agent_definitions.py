"""Harness agent identity, permission, and prompt metadata.

An :class:`AgentDefinition` is pure data describing one harness agent's grant
surface: the permissions it may exercise. Harnesses (PDE,
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

from agents.permissions import Permission


class Harness(str, Enum):
    """Product harnesses that host a Kei agent."""

    PDE = "pde"
    DISCORD = "discord"


@dataclass(frozen=True)
class AgentDefinition:
    """One harness agent's permissions, approval requirements, and prompts.

    Attributes:
        name: Unique agent id, ``^[a-z0-9_]+$``.
        harness: The harness that hosts the agent.
        description: What the agent is for.
        permissions: Permissions the agent may exercise.
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
) -> list[str]:
    """Validate agent identity, permission, and prompt metadata.

    Checks name format/uniqueness, a description, typed harness and
    permissions (bare strings are rejected), no ``*_approve`` permission
    (reserved), and that at most one system prompt source is set and a prompt
    file resolves inside the package. Returns a
    list of violations; empty means valid.
    """
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
    return violations



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
    system_prompt_file="prompts/pde_search_agent.md",
)

BUG_REPORT_TRIAGE_AGENT = AgentDefinition(
    name="bug_report_triage",
    harness=Harness.DISCORD,
    description=(
        "Read-only diagnosis of sanitized BugBot reports using provided "
        "diagnostics and current source evidence"
    ),
    permissions=frozenset({Permission.GITHUB_READ}),
    system_prompt_file="prompts/bug_report_triage.md",
)

FIX_PROPOSAL_AGENT = AgentDefinition(
    name="fix_proposal",
    harness=Harness.DISCORD,
    description=(
        "Propose a bounded draft fix for an explicitly requested BugBot "
        "report through the scoped create_fix_pr harness action"
    ),
    permissions=frozenset({Permission.GITHUB_READ, Permission.GITHUB_WRITE}),
    system_prompt_file="prompts/fix_proposal.md",
)

ONBOARDING_E2E_TRIAGE_AGENT = AgentDefinition(
    name="onboarding_e2e_triage",
    harness=Harness.DISCORD,
    description=(
        "Read-only analysis of first-account onboarding E2E failures using "
        "the failed workflow run and source on current main"
    ),
    permissions=frozenset({Permission.GITHUB_READ}),
    system_prompt_file="prompts/onboarding_e2e_triage.md",
)

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
    system_prompt_file="prompts/pedro.md",
)

HARNESS_AGENT_DEFINITIONS: list[AgentDefinition] = [
    PDE_SEARCH_AGENT,
    PEDRO_AGENT,
    ONBOARDING_E2E_TRIAGE_AGENT,
    BUG_REPORT_TRIAGE_AGENT,
    FIX_PROPOSAL_AGENT,
]

__all__ = [
    "BUG_REPORT_TRIAGE_AGENT",
    "FIX_PROPOSAL_AGENT",
    "HARNESS_AGENT_DEFINITIONS",
    "ONBOARDING_E2E_TRIAGE_AGENT",
    "PDE_SEARCH_AGENT",
    "PEDRO_AGENT",
    "AgentDefinition",
    "Harness",
    "load_system_prompt",
    "validate_agent_definitions",
]
