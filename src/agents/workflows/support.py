"""Harness-neutral support-management workflow specification (WORKFLOW-4).

A typed, composable specification for a support-management workflow that
reads from Notion, Drive, and custom API (http_api) connectors. This module
is a **specification only**: it declares the workflow's structure, resource
mappings, escalation rules, redaction rules, and failure states. It never
contains provider clients, credential resolution, or secret material.
Provider execution and customer data retrieval happen in the tenant-side
distributed proxy.

The workflow is harness-neutral: it references connector tool names as
strings and declares semantic mappings, not execution logic. It has no
Discord dependency, no org/workspace tool parameters, and no provider
clients.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Spec types
# ---------------------------------------------------------------------------

# Allowed step kinds.
_READ = "read"
_WRITE = "write"
_STEP_KINDS = frozenset({_READ, _WRITE})

# Allowed failure-handling strategies.
_ABORT = "abort"
_SKIP = "skip"
_RETRY = "retry"
_FALLBACK = "fallback"
_FAILURE_STRATEGIES = frozenset({_ABORT, _SKIP, _RETRY, _FALLBACK})

# Connectors this workflow composes.
_NOTION = "notion"
_DRIVE = "drive"
_HTTP_API = "http_api"
_CONNECTORS = frozenset({_NOTION, _DRIVE, _HTTP_API})

# Tool-name pattern: ``^[a-z0-9_]+(\.[a-z0-9_]+)*$``
_TOOL_NAME_RE = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)*$")


@dataclass(frozen=True)
class ResourceMapping:
    """Maps a governed connector resource to a workflow entity.

    Attributes:
        connector: Connector identifier (``notion``, ``drive``, ``http_api``).
        tool_name: The governed read tool that supplies the resource.
        resource: The connector resource type (e.g. ``databases``, ``files``).
        entity: The workflow entity the resource maps to (e.g. ``ticket``).
        description: Human-readable mapping description.
    """

    connector: str
    tool_name: str
    resource: str
    entity: str
    description: str


@dataclass(frozen=True)
class EscalationRule:
    """Defines a condition under which the workflow escalates.

    Attributes:
        condition: A semantic condition expression (e.g. ``severity == critical``).
        action: The escalation action to take (e.g. ``notify_lead``).
        target_tool: The tool that executes the escalation.
        description: Human-readable rule description.
    """

    condition: str
    action: str
    target_tool: str
    description: str


@dataclass(frozen=True)
class RedactionRule:
    """Defines a field pattern to redact before data leaves the workflow.

    Attributes:
        field_pattern: A regex or exact field name to match.
        scope: The data scope to apply the rule to (e.g. ``ticket_body``).
        replacement: The replacement string (e.g. ``[REDACTED]``).
        description: Human-readable rule description.
    """

    field_pattern: str
    scope: str
    replacement: str
    description: str


@dataclass(frozen=True)
class FailureState:
    """Defines failure handling for a workflow step.

    Attributes:
        step_name: The workflow step this state applies to.
        on_failure: The strategy (``abort``, ``skip``, ``retry``, ``fallback``).
        max_retries: Maximum retry attempts (0 if strategy is not ``retry``).
        fallback_step: Name of the fallback step (required if strategy is
            ``fallback``, optional otherwise).
        description: Human-readable state description.
    """

    step_name: str
    on_failure: str
    max_retries: int = 0
    fallback_step: str | None = None
    description: str = ""


@dataclass(frozen=True)
class WorkflowStep:
    """A single step in the support-management workflow.

    Attributes:
        name: Unique step identifier within the workflow.
        kind: Step kind (``read`` or ``write``).
        tool_name: The governed tool that executes this step.
        connector: The connector the tool belongs to.
        description: Human-readable step description.
        param_hints: Non-secret parameter names the step accepts (values are
            resolved by the tenant-side proxy, never embedded here).
        failure_state: Optional failure-handling state for this step.
    """

    name: str
    kind: str
    tool_name: str
    connector: str
    description: str
    param_hints: tuple[str, ...] = ()
    failure_state: FailureState | None = None


@dataclass(frozen=True)
class SupportWorkflow:
    """The top-level support-management workflow specification.

    Attributes:
        name: Workflow identifier.
        version: Specification version.
        description: Human-readable workflow description.
        steps: Ordered workflow steps.
        resource_mappings: Connector-resource-to-entity mappings.
        escalation_rules: Escalation conditions and actions.
        redaction_rules: PII/sensitive-field redaction rules.
        failure_states: Failure-handling definitions.
    """

    name: str
    version: str
    description: str
    steps: tuple[WorkflowStep, ...]
    resource_mappings: tuple[ResourceMapping, ...]
    escalation_rules: tuple[EscalationRule, ...]
    redaction_rules: tuple[RedactionRule, ...]
    failure_states: tuple[FailureState, ...]


# ---------------------------------------------------------------------------
# WORKFLOW-4: support-management specification
# ---------------------------------------------------------------------------

SUPPORT_WORKFLOW = SupportWorkflow(
    name="support-management",
    version="1.0.0",
    description=(
        "Harness-neutral support-management workflow that composes semantic "
        "reads from Notion (ticket store), Drive (customer documents), and "
        "custom API (CRM/account records), applies escalation and redaction "
        "rules, and executes writes. Provider execution is delegated to the "
        "tenant-side distributed proxy."
    ),
    resource_mappings=(
        ResourceMapping(
            connector=_NOTION,
            tool_name="notion.query_database",
            resource="databases",
            entity="support_ticket",
            description=(
                "Notion database rows map to support tickets. The governed "
                "connection preset binds the workspace; the agent supplies "
                "only the database_id and filter."
            ),
        ),
        ResourceMapping(
            connector=_NOTION,
            tool_name="notion.get_page",
            resource="pages",
            entity="ticket_detail",
            description=(
                "Notion page content maps to ticket detail (body, "
                "attachments metadata, linked records)."
            ),
        ),
        ResourceMapping(
            connector=_DRIVE,
            tool_name="drive.list_files",
            resource="files",
            entity="customer_document",
            description=(
                "Drive files in the governed drive map to customer "
                "documents (contracts, onboarding artifacts)."
            ),
        ),
        ResourceMapping(
            connector=_DRIVE,
            tool_name="docs.get_document",
            resource="documents",
            entity="customer_document_content",
            description=(
                "Docs document content maps to customer document content "
                "for context retrieval."
            ),
        ),
        ResourceMapping(
            connector=_HTTP_API,
            tool_name="http_api.get_record",
            resource="records",
            entity="customer_account",
            description=(
                "CRM record maps to the customer account (billing tier, "
                "plan, contact metadata). The governed connection preset "
                "binds the endpoint and entity."
            ),
        ),
    ),
    steps=(
        WorkflowStep(
            name="fetch_tickets",
            kind=_READ,
            tool_name="notion.query_database",
            connector=_NOTION,
            description=(
                "Query the governed Notion ticket database for open support "
                "tickets matching the requested filters."
            ),
            param_hints=("database_id", "filter_json", "limit"),
            failure_state=FailureState(
                step_name="fetch_tickets",
                on_failure=_RETRY,
                max_retries=3,
                description=(
                    "Retry up to 3 times on transient Notion read failures "
                    "before aborting the workflow."
                ),
            ),
        ),
        WorkflowStep(
            name="fetch_ticket_detail",
            kind=_READ,
            tool_name="notion.get_page",
            connector=_NOTION,
            description=(
                "Read the full ticket page for each ticket returned by "
                "fetch_tickets to obtain body, linked records, and "
                "attachment metadata."
            ),
            param_hints=("page_id",),
            failure_state=FailureState(
                step_name="fetch_ticket_detail",
                on_failure=_SKIP,
                description=(
                    "Skip individual ticket detail reads that fail; the "
                    "workflow continues with the tickets that were "
                    "successfully fetched."
                ),
            ),
        ),
        WorkflowStep(
            name="fetch_customer_documents",
            kind=_READ,
            tool_name="drive.list_files",
            connector=_DRIVE,
            description=(
                "List customer documents in the governed Drive for the "
                "accounts referenced by the fetched tickets."
            ),
            param_hints=("query", "mime_type", "limit"),
            failure_state=FailureState(
                step_name="fetch_customer_documents",
                on_failure=_SKIP,
                description=(
                    "Skip Drive reads that fail; the workflow continues "
                    "without customer document context."
                ),
            ),
        ),
        WorkflowStep(
            name="fetch_customer_account",
            kind=_READ,
            tool_name="http_api.get_record",
            connector=_HTTP_API,
            description=(
                "Read the customer account record from the governed "
                "http_api/CRM connection for billing tier, plan, and "
                "contact metadata."
            ),
            param_hints=("entity", "record_id"),
            failure_state=FailureState(
                step_name="fetch_customer_account",
                on_failure=_FALLBACK,
                fallback_step="fetch_tickets",
                description=(
                    "If the CRM read fails, fall back to the ticket data "
                    "already fetched from Notion; the workflow continues "
                    "with reduced account context."
                ),
            ),
        ),
        WorkflowStep(
            name="update_ticket_status",
            kind=_WRITE,
            tool_name="notion.update_page",
            connector=_NOTION,
            description=(
                "Update the ticket status and add a resolution note in the "
                "governed Notion workspace."
            ),
            param_hints=("page_id", "properties_json"),
            failure_state=FailureState(
                step_name="update_ticket_status",
                on_failure=_ABORT,
                description=(
                    "Abort the workflow if the ticket update "
                    "fails; a partial write is not acceptable."
                ),
            ),
        ),
        WorkflowStep(
            name="log_resolution",
            kind=_WRITE,
            tool_name="http_api.create_record",
            connector=_HTTP_API,
            description=(
                "Create a resolution log record in the governed "
                "http_api/CRM connection."
            ),
            param_hints=("entity", "record_json"),
            failure_state=FailureState(
                step_name="log_resolution",
                on_failure=_SKIP,
                description=(
                    "Skip the resolution log write if it fails; the "
                    "primary ticket update has already been committed."
                ),
            ),
        ),
    ),
    escalation_rules=(
        EscalationRule(
            condition="ticket.severity == 'critical'",
            action="notify_support_lead",
            target_tool="notion.create_page",
            description=(
                "Critical-severity tickets trigger an immediate "
                "escalation page in the governed Notion workspace for "
                "the support lead."
            ),
        ),
        EscalationRule(
            condition="ticket.sla_breach_minutes > 30",
            action="escalate_to_engineering",
            target_tool="http_api.create_record",
            description=(
                "Tickets that breach the SLA by more than 30 minutes "
                "are escalated to the engineering queue via the "
                "governed http_api connection."
            ),
        ),
        EscalationRule(
            condition="ticket.customer_tier == 'enterprise' and ticket.status == 'open'",
            action="assign_dedicated_engineer",
            target_tool="notion.update_page",
            description=(
                "Open enterprise-tier tickets are escalated for "
                "dedicated engineer assignment."
            ),
        ),
    ),
    redaction_rules=(
        RedactionRule(
            field_pattern=r"\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b",
            scope="ticket_body",
            replacement="[EMAIL_REDACTED]",
            description=(
                "Redact email addresses in ticket body content before "
                "the data is shared outside the tenant boundary."
            ),
        ),
        RedactionRule(
            field_pattern=r"\\b\\d{3}[-.]?\\d{3}[-.]?\\d{4}\\b",
            scope="ticket_body",
            replacement="[PHONE_REDACTED]",
            description=(
                "Redact phone numbers in ticket body content before "
                "the data is shared outside the tenant boundary."
            ),
        ),
        RedactionRule(
            field_pattern="ssn",
            scope="customer_account",
            replacement="[SSN_REDACTED]",
            description=(
                "Redact the SSN field from customer account records "
                "before the data is shared outside the tenant boundary."
            ),
        ),
        RedactionRule(
            field_pattern="credit_card",
            scope="customer_account",
            replacement="[CARD_REDACTED]",
            description=(
                "Redact credit card fields from customer account records "
                "before the data is shared outside the tenant boundary."
            ),
        ),
    ),
    failure_states=(
        FailureState(
            step_name="fetch_tickets",
            on_failure=_RETRY,
            max_retries=3,
            description=(
                "Retry up to 3 times on transient Notion read failures "
                "before aborting the workflow."
            ),
        ),
        FailureState(
            step_name="fetch_ticket_detail",
            on_failure=_SKIP,
            description=(
                "Skip individual ticket detail reads that fail; the "
                "workflow continues with the tickets that were "
                "successfully fetched."
            ),
        ),
        FailureState(
            step_name="fetch_customer_documents",
            on_failure=_SKIP,
            description=(
                "Skip Drive reads that fail; the workflow continues "
                "without customer document context."
            ),
        ),
        FailureState(
            step_name="fetch_customer_account",
            on_failure=_FALLBACK,
            fallback_step="fetch_tickets",
            description=(
                "If the CRM read fails, fall back to the ticket data "
                "already fetched from Notion; the workflow continues "
                "with reduced account context."
            ),
        ),
        FailureState(
            step_name="update_ticket_status",
            on_failure=_ABORT,
            description=(
                "Abort the workflow if the approved ticket update "
                "fails; a partial write is not acceptable."
            ),
        ),
        FailureState(
            step_name="log_resolution",
            on_failure=_SKIP,
            description=(
                "Skip the resolution log write if it fails; the "
                "primary ticket update has already been committed."
            ),
        ),
    ),
)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_SECRET_KEY_HINTS = (
    "token",
    "secret",
    "password",
    "passwd",
    "apikey",
    "api_key",
    "key",
    "credential",
    "auth",
    "bearer",
)

_URL_VALUE_RE = re.compile(r"://")

_TENANT_IDENTIFIER_HINTS = (
    "tenant_id",
    "tenant",
    "account_id",
    "customer_id",
    "organization_id",
    "org_id",
)


def validate_support_workflow(workflow: SupportWorkflow) -> list[str]:
    """Validate a support-management workflow specification.

    Checks that:
    - All step names are unique and well-formed.
    - All step kinds are valid (``read`` or ``write``).
    - All tool names are well-formed.
    - All connectors are in the allowed set.
    - Failure states reference valid step names.
    - Fallback steps reference valid step names.
    - No parameter hints look like secrets, URLs, or tenant identifiers.
    - No resource mapping references an unknown connector.
    - No escalation rule references an unknown tool name pattern.
    - No redaction rule has an empty pattern.

    Returns a list of violations; an empty list means the spec is valid.
    """
    violations: list[str] = []
    step_names: set[str] = set()

    for step in workflow.steps:
        if not step.name:
            violations.append("step has an empty name")
            continue
        if not _TOOL_NAME_RE.fullmatch(step.name):
            violations.append(
                f"invalid step name {step.name!r}: must match {_TOOL_NAME_RE.pattern}"
            )
        if step.name in step_names:
            violations.append(f"duplicate step name: {step.name!r}")
        step_names.add(step.name)

        if step.kind not in _STEP_KINDS:
            violations.append(
                f"step {step.name!r}: invalid kind {step.kind!r}; "
                f"must be one of {sorted(_STEP_KINDS)}"
            )
        if not _TOOL_NAME_RE.fullmatch(step.tool_name):
            violations.append(
                f"step {step.name!r}: invalid tool name {step.tool_name!r}"
            )
        if step.connector not in _CONNECTORS:
            violations.append(
                f"step {step.name!r}: connector {step.connector!r} is not "
                f"in the allowed set {sorted(_CONNECTORS)}"
            )
        if not step.description:
            violations.append(f"step {step.name!r}: description is required")

        for hint in step.param_hints:
            lower = hint.lower()
            if any(h in lower for h in _SECRET_KEY_HINTS):
                violations.append(
                    f"step {step.name!r}: param hint {hint!r} looks like "
                    "a secret; param hints must be non-secret"
                )
            if _URL_VALUE_RE.search(hint):
                violations.append(
                    f"step {step.name!r}: param hint {hint!r} looks like "
                    "a URL; endpoints are resolved from the governed "
                    "connection preset"
                )
            if hint in _TENANT_IDENTIFIER_HINTS:
                violations.append(
                    f"step {step.name!r}: param hint {hint!r} looks like "
                    "a tenant identifier; tenant context is delegated, "
                    "never agent-chosen"
                )

        if step.failure_state is not None:
            fs = step.failure_state
            if fs.step_name != step.name:
                violations.append(
                    f"step {step.name!r}: failure_state.step_name "
                    f"{fs.step_name!r} does not match"
                )
            if fs.on_failure not in _FAILURE_STRATEGIES:
                violations.append(
                    f"step {step.name!r}: invalid failure strategy "
                    f"{fs.on_failure!r}; must be one of "
                    f"{sorted(_FAILURE_STRATEGIES)}"
                )
            if fs.on_failure == _RETRY and fs.max_retries < 1:
                violations.append(
                    f"step {step.name!r}: retry strategy requires max_retries >= 1"
                )
            if fs.on_failure == _FALLBACK and not fs.fallback_step:
                violations.append(
                    f"step {step.name!r}: fallback strategy requires a fallback_step"
                )

    for fs in workflow.failure_states:
        if fs.step_name not in step_names:
            violations.append(f"failure_state references unknown step {fs.step_name!r}")
        if fs.on_failure not in _FAILURE_STRATEGIES:
            violations.append(
                f"failure_state for {fs.step_name!r}: invalid strategy "
                f"{fs.on_failure!r}"
            )
        if (
            fs.on_failure == _FALLBACK
            and fs.fallback_step
            and fs.fallback_step not in step_names
        ):
            violations.append(
                f"failure_state for {fs.step_name!r}: fallback_step "
                f"{fs.fallback_step!r} is not a known step"
            )

    for rm in workflow.resource_mappings:
        if rm.connector not in _CONNECTORS:
            violations.append(
                f"resource_mapping: connector {rm.connector!r} is not "
                f"in the allowed set {sorted(_CONNECTORS)}"
            )
        if not _TOOL_NAME_RE.fullmatch(rm.tool_name):
            violations.append(f"resource_mapping: invalid tool name {rm.tool_name!r}")
        if not rm.entity:
            violations.append("resource_mapping: entity is required")

    for rule in workflow.redaction_rules:
        if not rule.field_pattern:
            violations.append("redaction_rule: field_pattern is required")
        if not rule.scope:
            violations.append("redaction_rule: scope is required")

    for esc_rule in workflow.escalation_rules:
        if not esc_rule.condition:
            violations.append("escalation_rule: condition is required")
        if not _TOOL_NAME_RE.fullmatch(esc_rule.target_tool):
            violations.append(
                f"escalation_rule: invalid target_tool {esc_rule.target_tool!r}"
            )

    return violations


__all__ = [
    "SUPPORT_WORKFLOW",
    "EscalationRule",
    "FailureState",
    "RedactionRule",
    "ResourceMapping",
    "SupportWorkflow",
    "WorkflowStep",
    "validate_support_workflow",
]
