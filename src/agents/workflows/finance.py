"""Typed finance/bookkeeping workflow specification.

Semantic step definitions for governed finance workflows that compose
Drive (documents), CRM (customers/vendors), and Linear (tasks/notifications)
operations. Every workflow follows a read-first discipline: mutations are
always preceded by a read step.

This is a harness-neutral data specification. Each step defines domain
intent only; the consuming harness resolves connector bindings, enforces
policy, and invokes provider adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from agents.tool_definitions import Permission
from agents.workflows.step_graph import validate_step_graph


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
class Notify:
    """Send a notification about workflow progress."""

    channel: Literal["email", "slack", "linear_comment"]
    recipient: str
    message: str
    entity: FinanceEntity | None = None


# ---------------------------------------------------------------------------
# Composite types
# ---------------------------------------------------------------------------

StepPayload = DriveRead | DriveArchive | CRMLookup | CRMUpdate | LinearTask | Notify


@dataclass
class FinanceWorkflowStep:
    """A single step in a finance workflow DAG.

    Each step carries a domain-intent payload and metadata for dependency
    ordering and permission gating.  Steps are read-first: mutation payloads
    (CRMUpdate, DriveArchive) **must** be preceded by a corresponding read
    step.
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


def _is_egress(payload: StepPayload) -> bool:
    return isinstance(payload, _EGRESS_PAYLOAD_TYPES)


def egress_steps(spec: FinanceWorkflowSpec) -> list[FinanceWorkflowStep]:
    """Return the steps whose execution leaves the governed boundary.

    This is a classification helper, not a gate: it tells a harness which
    steps to submit to ABAC as egress-class requests, and lets a reviewer see
    a workflow's egress surface at a glance. The decision itself stays with
    the policy decision point.
    """
    return [step for step in spec.steps if _is_egress(step.payload)]


def validate_read_first(spec: FinanceWorkflowSpec) -> list[str]:
    """Validate a finance workflow's read-first invariants.

    Checks, in order: the step graph is well formed (unique ids, resolvable
    dependencies, no cycles); every mutation depends on a read step.

    Dependency checks are by reachability, so a read may be any ancestor
    rather than a direct dependency.

    This validates the *structure* of a spec — properties that are true of
    the graph itself, independent of who runs it. It is not an authorization
    check. Whether a particular subject may perform a step is decided at
    invocation time by ABAC and the tenant-side proxy PEP (ADR-011). A spec
    that passes here is well formed, not permitted.

    Returns a list of violations; an empty list means the spec is valid.
    """
    return validate_step_graph(
        spec.steps,
        read_types=_READ_PAYLOAD_TYPES,
        mutation_types=_MUTATION_PAYLOAD_TYPES,
        mutation_permissions=(Permission.FINANCE_WRITE,),
    )


# ---------------------------------------------------------------------------
# Pre-built workflow specs
# ---------------------------------------------------------------------------


def invoice_processing_workflow() -> FinanceWorkflowSpec:
    """Standard invoice processing workflow.

    Read-first discipline:
      1. Read invoice from Drive
      2. Look up customer in CRM
      3. Create Linear review task
      4. Update CRM with payment status (mutation)
      5. Archive invoice in Drive (mutation)
      6. Notify customer
    """
    return FinanceWorkflowSpec(
        workflow_id="finance.invoice_processing",
        name="Invoice Processing",
        description=(
            "Process an invoice from receipt through approval and payment recording"
        ),
        tags=["finance", "invoice"],
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
                step_id="update_crm",
                description="Update CRM with payment status",
                payload=CRMUpdate(
                    entity_type="customer",
                    record_id="",
                    updates={"payment_status": "paid"},
                ),
                permission=Permission.FINANCE_WRITE,
                depends_on=["create_review_task", "lookup_customer"],
            ),
            FinanceWorkflowStep(
                step_id="archive_invoice",
                description="Archive the invoice in Drive",
                payload=DriveArchive(
                    entity=FinanceEntity.INVOICE,
                    document_id="",
                ),
                permission=Permission.FINANCE_WRITE,
                depends_on=["create_review_task", "read_invoice"],
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
    """Expense report submission and processing workflow.

    Read-first discipline:
      1. Read receipt documents from Drive
      2. Look up vendor in CRM
      3. Create Linear audit task
      4. Archive receipts (mutation)
      5. Notify submitter
    """
    return FinanceWorkflowSpec(
        workflow_id="finance.expense_report",
        name="Expense Report Processing",
        description=("Process an expense report from submission through approval"),
        tags=["finance", "expense"],
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
                step_id="archive_receipts",
                description="Archive receipts in Drive",
                payload=DriveArchive(
                    entity=FinanceEntity.RECEIPT,
                    document_id="",
                ),
                permission=Permission.FINANCE_WRITE,
                depends_on=["create_audit_task", "read_receipts"],
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
      4. Update vendor status in CRM (mutation)
      5. Archive vendor documents (mutation)
      6. Notify vendor
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
                step_id="update_vendor_status",
                description="Update vendor status to approved in CRM",
                payload=CRMUpdate(
                    entity_type="vendor",
                    record_id="",
                    updates={"status": "approved"},
                ),
                permission=Permission.FINANCE_WRITE,
                depends_on=["create_onboarding_task", "create_vendor_record"],
            ),
            FinanceWorkflowStep(
                step_id="archive_docs",
                description="Archive vendor documents in Drive",
                payload=DriveArchive(
                    entity=FinanceEntity.VENDOR,
                    document_id="",
                ),
                permission=Permission.FINANCE_WRITE,
                depends_on=["create_onboarding_task", "read_vendor_docs"],
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
