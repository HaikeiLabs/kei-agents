"""Workflow specifications for Kei agents.

Workflows define typed, harness-neutral step DAGs that compose governed
connector capabilities (Drive, Linear, GitHub) into domain-specific processes
(bug to Linear PR, GitHub PR review, support).
Each step captures domain intent only; the harness resolves bindings,
enforces policy, and invokes provider adapters.
"""

from __future__ import annotations

from agents.workflows.bug_to_linear_pr import (
    BUG_TO_LINEAR_PR,
    WorkflowPrincipal,
    WorkflowSpec,
    WorkflowStep,
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

__all__ = [
    "BUG_TO_LINEAR_PR",
    "PR_REVIEW_TOOL_DEPENDENCIES",
    "WORKFLOW_DEFINITIONS",
    "PRReviewFinding",
    "PRReviewFindingSeverity",
    "PRReviewInput",
    "PRReviewOutput",
    "PRReviewStep",
    "PRReviewWorkflowSpec",
    "ReviewAction",
    "ReviewActionKind",
    "WorkflowPrincipal",
    "WorkflowSpec",
    "WorkflowStep",
]
