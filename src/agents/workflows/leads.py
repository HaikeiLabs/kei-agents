"""Harness-neutral leads-management workflow specification.

This module defines the workflow contract for leads management:
workflow state machine, duplicate-handling metadata, approval metadata,
and failure states.  All tools are
harness-neutral workflow metadata; runtime tool names are inferred by Kei.  Provider execution and customer data
retrieval are delegated to the tenant-side distributed proxy; this
module never carries provider clients, credentials, or secret material.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

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


__all__ = [
    "ApprovalInfo",
    "ApprovalStatus",
    "DuplicateAction",
    "DuplicateInfo",
    "FailureInfo",
    "FailureReason",
    "LeadWorkflowStatus",
]
