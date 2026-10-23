"""Tests for the harness-neutral leads-management workflow specification."""

from __future__ import annotations

import datetime

from agents.workflows.leads import (
    ApprovalInfo,
    ApprovalStatus,
    DuplicateAction,
    DuplicateInfo,
    FailureInfo,
    FailureReason,
    LeadWorkflowStatus,
)

# ── Type tests ──────────────────────────────────────────────────────


class TestLeadWorkflowStatus:
    def test_enum_values(self):
        assert LeadWorkflowStatus.DRAFT.value == "draft"
        assert LeadWorkflowStatus.SUBMITTED.value == "submitted"
        assert LeadWorkflowStatus.DUPLICATE_REVIEW.value == "duplicate_review"
        assert LeadWorkflowStatus.PENDING_APPROVAL.value == "pending_approval"
        assert LeadWorkflowStatus.APPROVED.value == "approved"
        assert LeadWorkflowStatus.REJECTED.value == "rejected"
        assert LeadWorkflowStatus.FAILED.value == "failed"
        assert LeadWorkflowStatus.COMPLETED.value == "completed"

    def test_all_states_distinct(self):
        values = [s.value for s in LeadWorkflowStatus]
        assert len(values) == len(set(values))


class TestDuplicateTypes:
    def test_duplicate_action_enum(self):
        assert DuplicateAction.MERGE.value == "merge"
        assert DuplicateAction.DISMISS_NEW.value == "dismiss_new"
        assert DuplicateAction.DISMISS_EXISTING.value == "dismiss_existing"
        assert DuplicateAction.REVIEW_MANUALLY.value == "review_manually"

    def test_duplicate_info_defaults(self):
        info = DuplicateInfo(matched_lead_id="lead_1", match_reason="email match")
        assert info.matched_lead_id == "lead_1"
        assert info.match_reason == "email match"
        assert info.match_score == 0.0
        assert info.resolved is False
        assert info.resolution_action is None
        assert info.resolved_by is None
        assert info.resolved_at is None

    def test_duplicate_info_resolved(self):
        now = datetime.datetime.now(datetime.UTC)
        info = DuplicateInfo(
            matched_lead_id="lead_2",
            match_reason="name+company match",
            match_score=0.95,
            resolved=True,
            resolution_action=DuplicateAction.MERGE,
            resolved_by="agent_1",
            resolved_at=now,
        )
        assert info.resolved is True
        assert info.resolution_action == DuplicateAction.MERGE
        assert info.resolved_by == "agent_1"
        assert info.resolved_at == now


class TestApprovalTypes:
    def test_approval_status_enum(self):
        assert ApprovalStatus.NOT_REQUIRED.value == "not_required"
        assert ApprovalStatus.PENDING.value == "pending"
        assert ApprovalStatus.APPROVED.value == "approved"
        assert ApprovalStatus.REJECTED.value == "rejected"

    def test_approval_info_defaults(self):
        info = ApprovalInfo()
        assert info.status == ApprovalStatus.NOT_REQUIRED
        assert info.approved_by is None
        assert info.required_approvers == 1

    def test_approval_info_approved(self):
        now = datetime.datetime.now(datetime.UTC)
        info = ApprovalInfo(
            status=ApprovalStatus.APPROVED,
            approved_by="reviewer_1",
            approved_at=now,
        )
        assert info.status == ApprovalStatus.APPROVED
        assert info.approved_by == "reviewer_1"
        assert info.approved_at == now


class TestFailureTypes:
    def test_failure_reason_enum(self):
        assert FailureReason.VALIDATION_ERROR.value == "validation_error"
        assert FailureReason.DUPLICATE_DETECTED.value == "duplicate_detected"
        assert FailureReason.APPROVAL_DENIED.value == "approval_denied"
        assert FailureReason.PROVIDER_ERROR.value == "provider_error"
        assert FailureReason.TIMEOUT.value == "timeout"
        assert FailureReason.INTERNAL_ERROR.value == "internal_error"

    def test_failure_info_defaults(self):
        info = FailureInfo(
            reason=FailureReason.VALIDATION_ERROR,
            message="Invalid email format",
            failed_step="create_lead",
        )
        assert info.reason == FailureReason.VALIDATION_ERROR
        assert info.message == "Invalid email format"
        assert info.failed_step == "create_lead"
        assert info.error_code == ""
        assert info.retry_allowed is False
        assert info.retry_count == 0

    def test_failure_info_with_details(self):
        info = FailureInfo(
            reason=FailureReason.PROVIDER_ERROR,
            message="CRM API unavailable",
            failed_step="submit_for_approval",
            error_code="CRM_503",
            retry_allowed=True,
            retry_count=2,
            details={"http_status": 503, "retry_after": 30},
        )
        assert info.retry_allowed is True
        assert info.retry_count == 2
        assert info.details["http_status"] == 503


# ── Tool definition tests ───────────────────────────────────────────
