"""Bug-to-Linear-PR workflow specification.

A typed, harness-neutral three-stage workflow:

1. **Bug intake** — accept and validate a bug report from any channel (web
   form, chat, API).  No Discord/provider client is embedded; the intake
   source is an orthogonal routing concern.
2. **Linear ticket creation** — create a tracking issue in the governed Linear
   workspace via a semantic connector reference (``linear.create_issue``).
3. **GitHub PR creation** — create a pull request in the governed GitHub
   repository via the existing ``create_pull_request`` action tool.

The spec references connectors **semantically** (by tool name string) so that
any harness can resolve them against its own ``ToolDefinition`` catalog.  No
provider clients, credentials, or org/workspace arguments appear here —
routing context is supplied by the governed connector bindings at execution
time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

# ── Step data types ──────────────────────────────────────────────────────────


@dataclass
class BugReport:
    """Normalised bug report after intake and validation."""

    title: str
    description: str
    severity: str
    affected_feature: str
    environment: str = ""
    steps_to_reproduce: str = ""
    expected_behaviour: str = ""
    actual_behaviour: str = ""
    reporter: str = ""
    labels: list[str] = field(default_factory=lambda: ["bug"])


class Severity(str, Enum):
    """Bug severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class LinearTicketRef:
    """Reference to a created Linear issue."""

    issue_key: str
    url: str = ""


@dataclass
class PRSpec:
    """GitHub pull-request specification."""

    title: str
    body: str
    head_branch: str
    base_branch: str = "main"


@dataclass
class PRResult:
    """Created pull-request result."""

    pr_url: str
    pr_number: int


# ── Connector & step metadata ────────────────────────────────────────────────


@dataclass
class ConnectorRef:
    """Semantic reference to a connector tool required by a workflow step.

    The harness resolves ``name`` against its ``ToolDefinition`` catalog to
    obtain the actual permission gate, binding, and handler.  This indirection
    keeps the workflow spec provider- and credential-free.
    """

    name: str
    description: str
    required_permission: str


@dataclass
class WorkflowStep:
    """A single typed step in a workflow definition.

    Steps declare their input/output schemas (as dataclass types), the
    connector tools they depend on, required permissions, and valid
    transitions to subsequent steps.
    """

    name: str
    description: str
    input_type: type
    output_type: type
    connector_dependencies: list[ConnectorRef] = field(default_factory=list)
    required_permissions: list[str] = field(default_factory=list)
    next_steps: list[str | None] = field(default_factory=list)
    timeout_seconds: int = 300


@dataclass
class WorkflowSpec:
    """Complete workflow specification.

    A ``WorkflowSpec`` is a static definition only — it carries no runtime
    state, engine binding, or harness configuration.
    """

    name: str
    description: str
    version: str = "0.1.0"
    entry_step: str = ""
    steps: list[WorkflowStep] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


# ── Workflow steps ───────────────────────────────────────────────────────────


_STEP_BUG_INTAKE = WorkflowStep(
    name="bug_intake",
    description=(
        "Accept and validate a bug report.  The intake channel (web form, chat,"
        " API) is an orthogonal routing concern — no provider client is embedded."
    ),
    input_type=BugReport,
    output_type=BugReport,
    required_permissions=[],
    next_steps=["linear_ticket"],
)

_STEP_LINEAR_TICKET = WorkflowStep(
    name="linear_ticket",
    description=(
        "Create a tracking issue in the governed Linear workspace.  The harness"
        " resolves the 'linear.create_issue' connector ref against its tool"
        " catalog."
    ),
    input_type=BugReport,
    output_type=LinearTicketRef,
    connector_dependencies=[
        ConnectorRef(
            name="linear.create_issue",
            description="Create a Linear issue for bug tracking",
            required_permission="linear_write",
        ),
        ConnectorRef(
            name="linear.get_issue",
            description="Read back the created issue to confirm",
            required_permission="linear_read",
        ),
    ],
    required_permissions=["linear_write", "linear_read"],
    next_steps=["github_pr"],
)

_STEP_GITHUB_PR = WorkflowStep(
    name="github_pr",
    description=(
        "Create a pull request in the governed GitHub repository via the"
        " 'create_pull_request' action tool."
    ),
    input_type=PRSpec,
    output_type=PRResult,
    connector_dependencies=[
        ConnectorRef(
            name="create_pull_request",
            description="Create a GitHub pull request with the fix",
            required_permission="github_write",
        ),
    ],
    required_permissions=["github_write"],
    next_steps=[],  # terminal step
)


# ── Public workflow constant ─────────────────────────────────────────────────


BUG_TO_LINEAR_PR = WorkflowSpec(
    name="bug_to_linear_pr",
    description=(
        "Intake a bug report, create a Linear tracking ticket, then create a"
        " GitHub pull request.  Suitable for any harness that can resolve the"
        " referenced connector tools."
    ),
    version="0.1.0",
    entry_step="bug_intake",
    steps=[
        _STEP_BUG_INTAKE,
        _STEP_LINEAR_TICKET,
        _STEP_GITHUB_PR,
    ],
    tags=["bug", "linear", "github"],
)


def get_step(spec: WorkflowSpec, step_name: str) -> WorkflowStep | None:
    """Look up a step by name within a workflow spec."""
    return next((s for s in spec.steps if s.name == step_name), None)


def validate_workflow(spec: WorkflowSpec, connector_names: set[str]) -> list[str]:
    """Validate a workflow spec against a set of available connector tool names.

    Returns a list of violation strings (empty = valid).
    """
    violations: list[str] = []

    if not spec.name:
        violations.append("workflow name is required")
    if not spec.entry_step:
        violations.append("entry_step is required")

    step_names = {s.name for s in spec.steps}

    if spec.entry_step and spec.entry_step not in step_names:
        violations.append(f"entry_step {spec.entry_step!r} not found in steps")

    for step in spec.steps:
        if not step.name:
            violations.append("step has an empty name")
            continue
        if not step.description:
            violations.append(f"{step.name}: description is required")
        if step.next_steps:
            for next_name in step.next_steps:
                if next_name is not None and next_name not in step_names:
                    violations.append(f"{step.name}: unknown next_step {next_name!r}")
        for ref in step.connector_dependencies:
            if ref.name not in connector_names:
                violations.append(f"{step.name}: unresolved connector ref {ref.name!r}")

    # Check that every step except terminal ones is reachable.
    reachable = _reachable_steps(spec)
    for step in spec.steps:
        if step.name not in reachable:
            violations.append(f"{step.name}: unreachable step")

    return violations


def _reachable_steps(spec: WorkflowSpec) -> set[str]:
    """Compute the set of step names reachable from the entry step."""
    step_map = {s.name: s for s in spec.steps}
    visited: set[str] = set()
    stack = [spec.entry_step] if spec.entry_step else []
    while stack:
        name = stack.pop()
        if name in visited:
            continue
        visited.add(name)
        step = step_map.get(name)
        if step:
            for next_name in step.next_steps:
                if next_name is not None:
                    stack.append(next_name)
    return visited


__all__ = [
    "BUG_TO_LINEAR_PR",
    "BugReport",
    "ConnectorRef",
    "LinearTicketRef",
    "PRResult",
    "PRSpec",
    "Severity",
    "WorkflowSpec",
    "WorkflowStep",
    "get_step",
    "validate_workflow",
]
