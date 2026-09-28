"""Workflow specifications for Kei agents.

Workflows define typed, harness-neutral step DAGs that compose governed
connector capabilities (Drive, CRM, Linear) into domain-specific processes
(finance, fundraising, GitHub PR review, leads).
Each step captures domain intent only; the harness resolves bindings,
enforces policy, and invokes provider adapters.
"""

from __future__ import annotations

from agents.workflows.finance import (
    FINANCE_WORKFLOW_SPECS,
    ApprovalGate,
    CRMLookup,
    CRMUpdate,
    DriveArchive,
    DriveRead,
    FinanceEntity,
    FinanceStepCategory,
    FinanceWorkflowSpec,
    FinanceWorkflowState,
    FinanceWorkflowStep,
    LinearTask,
    Notify,
    StepPayload,
    egress_steps,
    expense_report_workflow,
    invoice_processing_workflow,
    validate_read_first,
    vendor_onboarding_workflow,
)
from agents.workflows.fundraising import (
    FUNDRAISING_WORKFLOW_SPECS,
    DataRoomRead,
    DataRoomShare,
    FundraisingWorkflowSpec,
    FundraisingWorkflowStep,
    InvestorLookup,
    InvestorPipelineRead,
    InvestorStage,
    InvestorStageUpdate,
    data_room_share_workflow,
    fundraising_egress_steps,
    investor_decision_workflow,
    investor_outreach_workflow,
    is_valid_stage_transition,
    validate_fundraising_workflow,
)
from agents.workflows.github_pr_review import (
    PR_REVIEW_TOOL_DEPENDENCIES,
    PRReviewFinding,
    PRReviewFindingSeverity,
    PRReviewInput,
    PRReviewOutput,
    PRReviewStep,
    PRReviewWorkflowSpec,
    ReviewAction,
    ReviewActionKind,
)

WORKFLOW_DEFINITIONS: list[PRReviewWorkflowSpec] = [
    PRReviewWorkflowSpec(),
]

# Leads and CRM/Linear follow-up definitions import the canonical tool
# catalog, so expose them lazily to preserve the package's import order while
# keeping package-level workflow exports available to callers.
_LAZY_LEADS_EXPORTS = {
    "LEADS_WORKFLOW_TOOL_DEFINITIONS",
    "REGISTERED_LEADS_WORKFLOW_TOOL_DEFINITIONS",
    "QUARANTINED_LEADS_WORKFLOW_TOOL_DEFINITIONS",
    "ApprovalInfo",
    "ApprovalStatus",
    "DuplicateAction",
    "DuplicateInfo",
    "FailureInfo",
    "FailureReason",
    "LeadWorkflowStatus",
    "get_leads_workflow_tools",
}
_LAZY_CRM_LINEAR_EXPORTS = {
    "CRM_LINEAR_FOLLOWUP_TOOL_DEFINITIONS",
    "LINEAR_CREATE_FOLLOWUP_TOOL",
}


def __getattr__(name: str) -> object:
    if name in _LAZY_LEADS_EXPORTS:
        from agents.workflows import leads

        value = getattr(leads, name)
        globals()[name] = value
        return value
    if name in _LAZY_CRM_LINEAR_EXPORTS:
        from agents.workflows import crm_linear_followup

        value = getattr(crm_linear_followup, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "CRM_LINEAR_FOLLOWUP_TOOL_DEFINITIONS",
    "FINANCE_WORKFLOW_SPECS",
    "FUNDRAISING_WORKFLOW_SPECS",
    "LEADS_WORKFLOW_TOOL_DEFINITIONS",
    "LINEAR_CREATE_FOLLOWUP_TOOL",
    "PR_REVIEW_TOOL_DEPENDENCIES",
    "QUARANTINED_LEADS_WORKFLOW_TOOL_DEFINITIONS",
    "REGISTERED_LEADS_WORKFLOW_TOOL_DEFINITIONS",
    "WORKFLOW_DEFINITIONS",
    "ApprovalGate",
    "ApprovalInfo",
    "ApprovalStatus",
    "CRMLookup",
    "CRMUpdate",
    "DataRoomRead",
    "DataRoomShare",
    "DriveArchive",
    "DriveRead",
    "DuplicateAction",
    "DuplicateInfo",
    "FailureInfo",
    "FailureReason",
    "FinanceEntity",
    "FinanceStepCategory",
    "FinanceWorkflowSpec",
    "FinanceWorkflowState",
    "FinanceWorkflowStep",
    "FundraisingWorkflowSpec",
    "FundraisingWorkflowStep",
    "InvestorLookup",
    "InvestorPipelineRead",
    "InvestorStage",
    "InvestorStageUpdate",
    "LeadWorkflowStatus",
    "LinearTask",
    "Notify",
    "PRReviewFinding",
    "PRReviewFindingSeverity",
    "PRReviewInput",
    "PRReviewOutput",
    "PRReviewStep",
    "PRReviewWorkflowSpec",
    "ReviewAction",
    "ReviewActionKind",
    "StepPayload",
    "data_room_share_workflow",
    "egress_steps",
    "expense_report_workflow",
    "fundraising_egress_steps",
    "get_leads_workflow_tools",
    "investor_decision_workflow",
    "investor_outreach_workflow",
    "invoice_processing_workflow",
    "is_valid_stage_transition",
    "validate_fundraising_workflow",
    "validate_read_first",
    "vendor_onboarding_workflow",
]
