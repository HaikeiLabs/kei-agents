"""Typed finance/bookkeeping workflow specification.

Semantic step definitions for governed finance workflows that compose
Drive (documents), CRM (customers/vendors), and Linear (tasks/approvals)
operations. Every workflow follows a read-first discipline: mutations are
always preceded by a read step and gated behind an explicit approval.

This is a harness-neutral data specification. Each step defines domain
intent only; the consuming harness resolves connector bindings, enforces
policy, and invokes provider adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from agents.tool_definitions import Permission


class FinanceEntity(str, Enum):
    """Entities in the finance/bookkeeping domain."""

    INVOICE = "invoice"
    RECEIPT = "receipt"
    STATEMENT = "statement"
    PAYMENT = "payment"
    EXPENSE = "expense"
    QUOTE = "quote"
    PURCHASE_ORDER = "purchase_order"
    CREDIT_NOTE = "credit_note"
    VENDOR = "vendor"
    CUSTOMER = "customer"


class FinanceWorkflowState(str, Enum):
    """Lifecycle state of a finance workflow instance."""

    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ESCALATED = "escalated"


class FinanceStepCategory(str, Enum):
    """Category of a workflow step."""

    DRIVE_READ = "drive_read"
    CRM_READ = "crm_read"
    CRM_WRITE = "crm_write"
    LINEAR_TASK = "linear_task"
    APPROVAL = "approval"
    NOTIFICATION = "notification"


# ---------------------------------------------------------------------------
# Step payloads — each dataclass captures the domain intent of one step.
# Payloads contain no provider clients, credentials, or execution logic.
# ---------------------------------------------------------------------------


@dataclass
class DriveRead:
    """Read a finance document from the governed Drive.

    One of *query* or *document_id* should be set.  *query* searches the
    governed Drive; *document_id* fetches a specific file.
    """

    entity: FinanceEntity
    query: str | None = None
    document_id: str | None = None
    mime_type: str | None = None


@dataclass
class DriveArchive:
    """Move a finance document to the archive folder in the governed Drive."""

    entity: FinanceEntity
    document_id: str
    target_folder: str = "archived"


@dataclass
class CRMLookup:
    """Look up a customer or vendor record in the CRM."""

    entity_type: Literal["customer", "vendor"]
    lookup_by: Literal["id", "email", "name"]
    lookup_value: str


@dataclass
class CRMUpdate:
    """Update a CRM record with finance-related information."""

    entity_type: Literal["customer", "vendor"]
    record_id: str
    updates: dict[str, str]


@dataclass
class LinearTask:
    """Create or update a task in the governed Linear workspace."""

    title: str
    description: str | None = None
    assignee: str | None = None
    labels: list[str] = field(default_factory=list)
    priority: str = "medium"
    state: str = "backlog"


@dataclass
class ApprovalGate:
    """An explicit approval gate that blocks mutation steps until resolved."""

    required_role: str = "finance_approver"
    reason: str = ""
    timeout_hours: int = 72
    escalation_role: str | None = None


@dataclass
class Notify:
    """Send a notification about workflow progress."""

    channel: Literal["email", "slack", "linear_comment"]
    recipient: str
    message: str
    entity: FinanceEntity | None = None


# ---------------------------------------------------------------------------
# Composite types
# ---------------------------------------------------------------------------

StepPayload = (
    DriveRead
    | DriveArchive
    | CRMLookup
    | CRMUpdate
    | LinearTask
    | ApprovalGate
    | Notify
)


@dataclass
class FinanceWorkflowStep:
    """A single step in a finance workflow DAG.

    Each step carries a domain-intent payload and metadata for dependency
    ordering and permission gating.  Steps are read-first: mutation payloads
    (CRMUpdate, DriveArchive) **must** be preceded by a corresponding read
    step and gated by an ApprovalGate.
    """

    step_id: str
    description: str
    payload: StepPayload
    depends_on: list[str] = field(default_factory=list)
    permission: Permission = Permission.FINANCE_READ


@dataclass
class FinanceWorkflowSpec:
    """A complete finance workflow specification.

    A DAG of semantic steps that a harness interprets and executes against
    the governed Drive, CRM, and Linear connectors.  The spec is pure data:
    it carries no provider clients, credentials, or execution logic.
    """

    workflow_id: str
    name: str
    description: str
    steps: list[FinanceWorkflowStep]
    tags: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Read-first validation
# ---------------------------------------------------------------------------

_MUTATION_PAYLOAD_TYPES = (CRMUpdate, DriveArchive)

# Steps whose execution leaves the governed boundary: LinearTask puts text in a
# ticket, Notify sends it to a mailbox or a chat channel. They are named here
# so a harness can classify a step, and so :func:`egress_steps` can report them
# to whatever presents a workflow for review.
#
# They are deliberately NOT gated by this function. Whether a given subject may
# cause a given egress is an authorization question, and per ADR-011 the live
# allow/deny decision belongs to ABAC and the tenant-side proxy PEP, not to a
# static property of the spec. Encoding it here would recreate the dormant
# connector-side policy the governance pivot moved out: unenforceable, and
# silently divergent from the policy that actually runs.
_EGRESS_PAYLOAD_TYPES = (LinearTask, Notify)

_READ_PAYLOAD_TYPES = (DriveRead, CRMLookup)


def _is_mutation(payload: StepPayload) -> bool:
    return isinstance(payload, _MUTATION_PAYLOAD_TYPES)


def _is_egress(payload: StepPayload) -> bool:
    return isinstance(payload, _EGRESS_PAYLOAD_TYPES)


def _is_read(payload: StepPayload) -> bool:
    return isinstance(payload, _READ_PAYLOAD_TYPES)


def egress_steps(spec: FinanceWorkflowSpec) -> list[FinanceWorkflowStep]:
    """Return the steps whose execution leaves the governed boundary.

    This is a classification helper, not a gate: it tells a harness which
    steps to submit to ABAC as egress-class requests, and lets a reviewer see
    a workflow's egress surface at a glance. The decision itself stays with
    the policy decision point.
    """
    return [step for step in spec.steps if _is_egress(step.payload)]


def _find_cycle(spec: FinanceWorkflowSpec) -> list[str] | None:
    """Return one dependency cycle as a list of step ids, or None if acyclic.

    A spec is a DAG by contract. Nothing enforced that, so a cycle would reach
    a harness interpreter and hang it rather than being rejected here.
    """
    dependencies = {
        step.step_id: [d for d in step.depends_on if d != step.step_id]
        for step in spec.steps
    }
    # Self-dependency is a cycle of length one; report it directly since the
    # traversal below skips it to keep the walk simple.
    for step in spec.steps:
        if step.step_id in step.depends_on:
            return [step.step_id, step.step_id]

    WHITE, GREY, BLACK = 0, 1, 2
    colour = dict.fromkeys(dependencies, WHITE)

    def walk(node: str, path: list[str]) -> list[str] | None:
        colour[node] = GREY
        path.append(node)
        for dep in dependencies.get(node, ()):
            if dep not in colour:
                continue  # unknown dep: reported separately as a dangling edge
            if colour[dep] == GREY:
                return path[path.index(dep) :] + [dep]
            if colour[dep] == WHITE:
                found = walk(dep, path)
                if found is not None:
                    return found
        path.pop()
        colour[node] = BLACK
        return None

    for node in dependencies:
        if colour[node] == WHITE:
            cycle = walk(node, [])
            if cycle is not None:
                return cycle
    return None


def _gated_by_approval(
    step: FinanceWorkflowStep, by_id: dict[str, FinanceWorkflowStep]
) -> bool:
    """Report whether an ApprovalGate is reachable from *step*'s dependencies.

    The gate may be any ancestor, not only a direct dependency. Requiring a
    direct edge would mean a step that legitimately depends on an intermediate
    read could not be gated without also naming the gate, which authors get
    wrong in the direction of removing the intermediate step rather than adding
    the edge. Reachability keeps the guarantee -- the gate is still upstream of
    the step, so it still blocks -- while allowing the natural shape.
    """
    seen: set[str] = set()
    frontier = list(step.depends_on)
    while frontier:
        current = frontier.pop()
        if current in seen:
            continue
        seen.add(current)
        dependency = by_id.get(current)
        if dependency is None:
            continue
        if isinstance(dependency.payload, ApprovalGate):
            return True
        frontier.extend(dependency.depends_on)
    return False


def _depends_on_read(
    step: FinanceWorkflowStep, by_id: dict[str, FinanceWorkflowStep]
) -> bool:
    """Report whether a read step is reachable from *step*'s dependencies."""
    seen: set[str] = set()
    frontier = list(step.depends_on)
    while frontier:
        current = frontier.pop()
        if current in seen:
            continue
        seen.add(current)
        dependency = by_id.get(current)
        if dependency is None:
            continue
        if _is_read(dependency.payload):
            return True
        frontier.extend(dependency.depends_on)
    return False


def validate_read_first(spec: FinanceWorkflowSpec) -> list[str]:
    """Validate a finance workflow's read-first and approval invariants.

    Checks, in order: the step graph is well formed (unique ids, resolvable
    dependencies, no cycles); every mutation depends on a read and is gated by
    an approval; and approval gates carry the approval permission.

    Dependency checks are by reachability, so a gate or read may be any
    ancestor rather than a direct dependency.

    This validates the *structure* of a spec -- properties that are true of
    the graph itself, independent of who runs it. It is not an authorization
    check. Whether a particular subject may perform a step, and whether an
    egress needs an approval in a given tenant, is decided at invocation time
    by ABAC and the tenant-side proxy PEP (ADR-011). A spec that passes here
    is well formed, not permitted.

    Returns a list of violations; an empty list means the spec is valid.
    """
    violations: list[str] = []
    by_id: dict[str, FinanceWorkflowStep] = {}

    for step in spec.steps:
        if step.step_id in by_id:
            violations.append(f"{step.step_id}: duplicate step_id")
        by_id[step.step_id] = step

    for step in spec.steps:
        for dep in step.depends_on:
            if dep not in by_id:
                violations.append(
                    f"{step.step_id}: depends_on {dep!r} not found in steps"
                )

    cycle = _find_cycle(spec)
    if cycle is not None:
        violations.append(f"dependency cycle: {' -> '.join(cycle)}")
        # Reachability checks below assume an acyclic graph is meaningful to
        # traverse. The traversals terminate regardless, but reporting
        # gate/read findings from inside a cycle would be noise on top of the
        # real defect, so stop here.
        return violations

    for step in spec.steps:
        # Permission is a str enum, so a bare "finance_write" compares equal to
        # Permission.FINANCE_WRITE; check the type so typos and untyped values
        # cannot slip past the policy engine.
        if not isinstance(step.permission, Permission):
            violations.append(
                f"{step.step_id}: permission must be a Permission member, "
                f"got bare {step.permission!r}"
            )
            continue
        if _is_mutation(step.payload):
            if step.permission not in (
                Permission.FINANCE_WRITE,
                Permission.FINANCE_APPROVE,
            ):
                violations.append(
                    f"{step.step_id}: mutation step requires "
                    "finance_write or finance_approve permission, "
                    f"got {step.permission.value!r}"
                )
            if not _depends_on_read(step, by_id):
                violations.append(
                    f"{step.step_id}: mutation step must depend on a read step"
                )
            if not _gated_by_approval(step, by_id):
                violations.append(
                    f"{step.step_id}: mutation step must depend on an approval gate"
                )

        if (
            isinstance(step.payload, ApprovalGate)
            and step.permission is not Permission.FINANCE_APPROVE
        ):
            violations.append(
                f"{step.step_id}: approval gate requires "
                f"finance_approve permission, got {step.permission.value!r}"
            )

    return violations


# ---------------------------------------------------------------------------
# Pre-built workflow specs
# ---------------------------------------------------------------------------


def invoice_processing_workflow() -> FinanceWorkflowSpec:
    """Standard invoice processing workflow.

    Read-first discipline:
      1. Read invoice from Drive
      2. Look up customer in CRM
      3. Create Linear review task
      4. Approval gate
      5. Update CRM with payment status (mutation)
      6. Archive invoice in Drive (mutation)
      7. Notify customer
    """
    return FinanceWorkflowSpec(
        workflow_id="finance.invoice_processing",
        name="Invoice Processing",
        description=(
            "Process an invoice from receipt through approval and payment recording"
        ),
        tags=["finance", "invoice", "approval"],
        steps=[
            FinanceWorkflowStep(
                step_id="read_invoice",
                description="Read the invoice document from the governed Drive",
                payload=DriveRead(entity=FinanceEntity.INVOICE),
            ),
            FinanceWorkflowStep(
                step_id="lookup_customer",
                description="Look up the customer in CRM",
                payload=CRMLookup(
                    entity_type="customer", lookup_by="name", lookup_value=""
                ),
                depends_on=["read_invoice"],
            ),
            FinanceWorkflowStep(
                step_id="create_review_task",
                description="Create a Linear task for invoice review",
                payload=LinearTask(
                    title="Review invoice",
                    labels=["finance", "invoice"],
                    priority="high",
                ),
                depends_on=["read_invoice", "lookup_customer"],
            ),
            FinanceWorkflowStep(
                step_id="approval",
                description="Finance team approval of the invoice",
                payload=ApprovalGate(
                    required_role="finance_approver",
                    reason="Invoice requires financial approval before payment",
                ),
                permission=Permission.FINANCE_APPROVE,
                depends_on=["create_review_task"],
            ),
            FinanceWorkflowStep(
                step_id="update_crm",
                description="Update CRM with payment status",
                payload=CRMUpdate(
                    entity_type="customer",
                    record_id="",
                    updates={"payment_status": "paid"},
                ),
                permission=Permission.FINANCE_WRITE,
                depends_on=["approval", "lookup_customer"],
            ),
            FinanceWorkflowStep(
                step_id="archive_invoice",
                description="Archive the invoice in Drive",
                payload=DriveArchive(
                    entity=FinanceEntity.INVOICE,
                    document_id="",
                ),
                permission=Permission.FINANCE_WRITE,
                depends_on=["approval", "read_invoice"],
            ),
            FinanceWorkflowStep(
                step_id="notify_customer",
                description="Notify customer of payment completion",
                payload=Notify(
                    channel="email",
                    recipient="",
                    message="Your invoice has been processed and payment completed.",
                    entity=FinanceEntity.INVOICE,
                ),
                depends_on=["update_crm"],
            ),
        ],
    )


def expense_report_workflow() -> FinanceWorkflowSpec:
    """Expense report submission and approval workflow.

    Read-first discipline:
      1. Read receipt documents from Drive
      2. Look up vendor in CRM
      3. Create Linear audit task
      4. Approval gate
      5. Archive receipts (mutation)
      6. Notify submitter
    """
    return FinanceWorkflowSpec(
        workflow_id="finance.expense_report",
        name="Expense Report Processing",
        description=("Process an expense report from submission through approval"),
        tags=["finance", "expense", "approval"],
        steps=[
            FinanceWorkflowStep(
                step_id="read_receipts",
                description="Read receipt documents from Drive",
                payload=DriveRead(entity=FinanceEntity.RECEIPT),
            ),
            FinanceWorkflowStep(
                step_id="lookup_vendor",
                description="Look up vendor in CRM",
                payload=CRMLookup(
                    entity_type="vendor", lookup_by="name", lookup_value=""
                ),
                depends_on=["read_receipts"],
            ),
            FinanceWorkflowStep(
                step_id="create_audit_task",
                description="Create Linear task for expense audit",
                payload=LinearTask(
                    title="Audit expense report",
                    labels=["finance", "expense", "audit"],
                    priority="medium",
                ),
                depends_on=["read_receipts", "lookup_vendor"],
            ),
            FinanceWorkflowStep(
                step_id="approval",
                description="Manager approval of the expense report",
                payload=ApprovalGate(
                    required_role="expense_approver",
                    reason="Expense report requires manager approval",
                    timeout_hours=48,
                ),
                permission=Permission.FINANCE_APPROVE,
                depends_on=["create_audit_task"],
            ),
            FinanceWorkflowStep(
                step_id="archive_receipts",
                description="Archive receipts in Drive",
                payload=DriveArchive(
                    entity=FinanceEntity.RECEIPT,
                    document_id="",
                ),
                permission=Permission.FINANCE_WRITE,
                depends_on=["approval", "read_receipts"],
            ),
            FinanceWorkflowStep(
                step_id="notify_submitter",
                description="Notify the expense submitter of completion",
                payload=Notify(
                    channel="email",
                    recipient="",
                    message="Your expense report has been approved and processed.",
                    entity=FinanceEntity.EXPENSE,
                ),
                depends_on=["archive_receipts"],
            ),
        ],
    )


def vendor_onboarding_workflow() -> FinanceWorkflowSpec:
    """New vendor onboarding with document verification.

    Read-first discipline:
      1. Read vendor registration documents from Drive
      2. Look up potential vendor in CRM
      3. Create Linear onboarding task
      4. Approval gate
      5. Update vendor status in CRM (mutation)
      6. Archive vendor documents (mutation)
      7. Notify vendor
    """
    return FinanceWorkflowSpec(
        workflow_id="finance.vendor_onboarding",
        name="Vendor Onboarding",
        description=("Onboard a new vendor with document collection and verification"),
        tags=["finance", "vendor", "onboarding"],
        steps=[
            FinanceWorkflowStep(
                step_id="read_vendor_docs",
                description="Read vendor registration documents from Drive",
                payload=DriveRead(entity=FinanceEntity.VENDOR),
            ),
            FinanceWorkflowStep(
                step_id="create_vendor_record",
                description="Look up vendor record in CRM",
                payload=CRMLookup(
                    entity_type="vendor",
                    lookup_by="name",
                    lookup_value="",
                ),
                depends_on=["read_vendor_docs"],
            ),
            FinanceWorkflowStep(
                step_id="create_onboarding_task",
                description="Create Linear task for vendor onboarding review",
                payload=LinearTask(
                    title="Review vendor onboarding",
                    labels=["finance", "vendor", "onboarding"],
                    priority="medium",
                ),
                depends_on=["read_vendor_docs", "create_vendor_record"],
            ),
            FinanceWorkflowStep(
                step_id="approval",
                description="Finance team approval of the vendor",
                payload=ApprovalGate(
                    required_role="finance_approver",
                    reason="New vendor requires financial approval",
                    escalation_role="finance_manager",
                ),
                permission=Permission.FINANCE_APPROVE,
                depends_on=["create_onboarding_task"],
            ),
            FinanceWorkflowStep(
                step_id="update_vendor_status",
                description="Update vendor status to approved in CRM",
                payload=CRMUpdate(
                    entity_type="vendor",
                    record_id="",
                    updates={"status": "approved"},
                ),
                permission=Permission.FINANCE_WRITE,
                depends_on=["approval", "create_vendor_record"],
            ),
            FinanceWorkflowStep(
                step_id="archive_docs",
                description="Archive vendor documents in Drive",
                payload=DriveArchive(
                    entity=FinanceEntity.VENDOR,
                    document_id="",
                ),
                permission=Permission.FINANCE_WRITE,
                depends_on=["approval", "read_vendor_docs"],
            ),
            FinanceWorkflowStep(
                step_id="notify_vendor",
                description="Notify vendor of successful onboarding",
                payload=Notify(
                    channel="email",
                    recipient="",
                    message="Your vendor registration has been approved.",
                    entity=FinanceEntity.VENDOR,
                ),
                depends_on=["update_vendor_status"],
            ),
        ],
    )


FINANCE_WORKFLOW_SPECS: dict[str, FinanceWorkflowSpec] = {
    "finance.invoice_processing": invoice_processing_workflow(),
    "finance.expense_report": expense_report_workflow(),
    "finance.vendor_onboarding": vendor_onboarding_workflow(),
}


__all__ = [
    "FINANCE_WORKFLOW_SPECS",
    "ApprovalGate",
    "CRMLookup",
    "CRMUpdate",
    "DriveArchive",
    "DriveRead",
    "FinanceEntity",
    "FinanceStepCategory",
    "FinanceWorkflowSpec",
    "FinanceWorkflowState",
    "FinanceWorkflowStep",
    "LinearTask",
    "Notify",
    "StepPayload",
    "egress_steps",
    "expense_report_workflow",
    "invoice_processing_workflow",
    "validate_read_first",
    "vendor_onboarding_workflow",
]
