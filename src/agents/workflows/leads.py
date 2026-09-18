"""Harness-neutral leads-management workflow specification.

This module defines the workflow contract for leads management:
semantic tool schemas, workflow state machine, duplicate-handling
metadata, approval metadata, and failure states.  All tools are
harness-neutral (no handlers) and use ToolBinding + delegated_context
for tenant resource mapping.  Provider execution and customer data
retrieval are delegated to the tenant-side distributed proxy; this
module never carries provider clients, credentials, or secret material.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agents.tool_definitions import (
    Permission,
    ToolBinding,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
)

# ── Workflow state machine ──────────────────────────────────────────


class LeadWorkflowStatus(str, Enum):
    """State-machine values for a lead progressing through the workflow."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    DUPLICATE_REVIEW = "duplicate_review"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"
    COMPLETED = "completed"


# ── Duplicate-handling metadata ─────────────────────────────────────


class DuplicateAction(str, Enum):
    """Resolution action taken on a detected duplicate pair."""

    MERGE = "merge"
    DISMISS_NEW = "dismiss_new"
    DISMISS_EXISTING = "dismiss_existing"
    REVIEW_MANUALLY = "review_manually"


@dataclass
class DuplicateInfo:
    """Describes a duplicate-detection result and its resolution."""

    matched_lead_id: str
    match_reason: str
    match_score: float = 0.0
    resolved: bool = False
    resolution_action: DuplicateAction | None = None
    resolved_by: str | None = None
    resolved_at: datetime.datetime | None = None


# ── Approval metadata ───────────────────────────────────────────────


class ApprovalStatus(str, Enum):
    """Status of an approval gate within the workflow."""

    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class ApprovalInfo:
    """Metadata tracking approval of a workflow step."""

    status: ApprovalStatus = ApprovalStatus.NOT_REQUIRED
    approved_by: str | None = None
    approved_at: datetime.datetime | None = None
    rejection_reason: str | None = None
    required_approvers: int = 1


# ── Failure states ──────────────────────────────────────────────────


class FailureReason(str, Enum):
    """Categorised reasons a workflow step may fail."""

    VALIDATION_ERROR = "validation_error"
    DUPLICATE_DETECTED = "duplicate_detected"
    APPROVAL_DENIED = "approval_denied"
    PROVIDER_ERROR = "provider_error"
    TIMEOUT = "timeout"
    INTERNAL_ERROR = "internal_error"


@dataclass
class FailureInfo:
    """Describes a terminal or non-terminal failure in the workflow."""

    reason: FailureReason
    message: str
    failed_step: str
    error_code: str = ""
    retry_allowed: bool = False
    retry_count: int = 0
    details: dict[str, Any] = field(default_factory=dict)


# ── Semantic tool schemas (harness-neutral, no handlers) ────────────

_WORKFLOW_CONNECTOR = ToolBinding(
    connector_id="conn_crm_workflow_1",
    config={"resource": "leads_workflow", "api": "crm"},
    delegated_context=["tenant_id"],
)

_READ_COMMON: dict[str, Any] = {
    "permission": Permission.CRM_READ,
    "category": ToolCategory.CRM,
    "service": "crm",
    "tags": ["crm-read", "workflow-spec", "harness-neutral"],
    "binding": _WORKFLOW_CONNECTOR,
}

_WRITE_COMMON: dict[str, Any] = {
    "permission": Permission.CRM_WRITE,
    "category": ToolCategory.CRM,
    "service": "crm",
    "tags": ["crm-write", "workflow-spec", "harness-neutral"],
    "binding": _WORKFLOW_CONNECTOR,
}


LEADS_WORKFLOW_TOOL_DEFINITIONS: list[ToolDefinition] = [
    # ── Read operations ──
    ToolDefinition(
        name="leads_workflow.get_lead",
        description="Get a single lead with its current workflow status and metadata",
        parameters=[
            ToolParameter(
                name="lead_id",
                description="Lead identifier within the governed CRM connection",
                required=True,
            ),
            ToolParameter(
                name="include_approval",
                description="Include approval metadata in the response",
                required=False,
            ),
            ToolParameter(
                name="include_duplicates",
                description="Include duplicate-detection information",
                required=False,
            ),
        ],
        **_READ_COMMON,
    ),
    ToolDefinition(
        name="leads_workflow.list_leads",
        description="List leads with optional workflow-status filter",
        parameters=[
            ToolParameter(
                name="status",
                description="Filter by workflow status",
                required=False,
                enum=[s.value for s in LeadWorkflowStatus],
            ),
            ToolParameter(
                name="limit",
                description="Maximum number of leads to return",
                type="integer",
                required=False,
                default=100,
            ),
            ToolParameter(
                name="offset",
                description="Number of leads to skip",
                type="integer",
                required=False,
                default=0,
            ),
        ],
        **_READ_COMMON,
    ),
    # ── Create / update ──
    ToolDefinition(
        name="leads_workflow.create_lead",
        description="Initiate a new lead through the governed CRM workflow",
        parameters=[
            ToolParameter(
                name="email",
                description="Email address of the lead",
                required=True,
            ),
            ToolParameter(
                name="name",
                description="Full name of the lead",
                required=True,
            ),
            ToolParameter(
                name="company",
                description="Company name",
                required=False,
            ),
            ToolParameter(
                name="phone",
                description="Phone number",
                required=False,
            ),
            ToolParameter(
                name="notes",
                description="Additional notes about the lead",
                required=False,
            ),
        ],
        **_WRITE_COMMON,
    ),
    ToolDefinition(
        name="leads_workflow.update_lead",
        description="Update lead fields within the governed CRM workflow",
        parameters=[
            ToolParameter(
                name="lead_id",
                description="Lead identifier to update",
                required=True,
            ),
            ToolParameter(
                name="email",
                description="New email address",
                required=False,
            ),
            ToolParameter(
                name="name",
                description="New full name",
                required=False,
            ),
            ToolParameter(
                name="company",
                description="New company name",
                required=False,
            ),
            ToolParameter(
                name="phone",
                description="New phone number",
                required=False,
            ),
            ToolParameter(
                name="notes",
                description="Updated notes",
                required=False,
            ),
        ],
        **_WRITE_COMMON,
    ),
    # ── Workflow transition operations ──
    ToolDefinition(
        name="leads_workflow.submit_for_approval",
        description="Submit a lead for approval review",
        parameters=[
            ToolParameter(
                name="lead_id",
                description="Lead identifier to submit for approval",
                required=True,
            ),
            ToolParameter(
                name="notes",
                description="Context or justification for the approval request",
                required=False,
            ),
        ],
        **_WRITE_COMMON,
    ),
    ToolDefinition(
        name="leads_workflow.approve_lead",
        description="Approve a lead that is pending approval",
        parameters=[
            ToolParameter(
                name="lead_id",
                description="Lead identifier to approve",
                required=True,
            ),
            ToolParameter(
                name="approval_note",
                description="Optional note attached to the approval",
                required=False,
            ),
        ],
        **_WRITE_COMMON,
    ),
    ToolDefinition(
        name="leads_workflow.reject_lead",
        description="Reject a lead that is pending approval",
        parameters=[
            ToolParameter(
                name="lead_id",
                description="Lead identifier to reject",
                required=True,
            ),
            ToolParameter(
                name="reason",
                description="Reason for rejection",
                required=True,
            ),
        ],
        **_WRITE_COMMON,
    ),
    ToolDefinition(
        name="leads_workflow.resolve_duplicate",
        description="Resolve a duplicate-detection alert for a lead",
        parameters=[
            ToolParameter(
                name="lead_id",
                description="Lead identifier with the duplicate alert",
                required=True,
            ),
            ToolParameter(
                name="action",
                description="Resolution action to apply",
                required=True,
                enum=[a.value for a in DuplicateAction],
            ),
            ToolParameter(
                name="target_lead_id",
                description="Identifier of the existing lead to merge/dismiss against",
                required=False,
            ),
        ],
        **_WRITE_COMMON,
    ),
]


# The duplicate-resolution action remains visible for review but is not part
# of the governed catalog until its provider contract is registered.
QUARANTINED_LEADS_WORKFLOW_TOOL_DEFINITIONS: list[ToolDefinition] = [
    LEADS_WORKFLOW_TOOL_DEFINITIONS[-1]
]
REGISTERED_LEADS_WORKFLOW_TOOL_DEFINITIONS: list[ToolDefinition] = (
    LEADS_WORKFLOW_TOOL_DEFINITIONS[:-1]
)


def get_leads_workflow_tools() -> list[ToolDefinition]:
    """Return the harness-neutral leads-workflow tool definitions.

    This is the canonical accessor so that package-level exports can
    be added later without changing the internal module shape.
    """
    return list(LEADS_WORKFLOW_TOOL_DEFINITIONS)


__all__ = [
    "LEADS_WORKFLOW_TOOL_DEFINITIONS",
    "QUARANTINED_LEADS_WORKFLOW_TOOL_DEFINITIONS",
    "REGISTERED_LEADS_WORKFLOW_TOOL_DEFINITIONS",
    "ApprovalInfo",
    "ApprovalStatus",
    "DuplicateAction",
    "DuplicateInfo",
    "FailureInfo",
    "FailureReason",
    "LeadWorkflowStatus",
    "get_leads_workflow_tools",
]
