"""Harness-neutral GitHub PR review workflow.

This module defines a composable PR review workflow spec that any harness
(Discord, Agentware, CLI, etc.) can interpret and execute. It contains no
provider clients, no credential resolution, no Discord dependency, and no
org/workspace tool parameters (those are proxy-delegated context).

Semantic tool dependencies reference connector capabilities by name only;
the actual tool definitions live in ``agents.connectors.github``. The
workflow is read-only by default; optional approval-gated write actions
(post comment, approve, request changes) require an explicit policy gate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agents.permissions import Permission


class PRReviewStep(str, Enum):
    """Ordered steps in the PR review workflow.

    Each step corresponds to a logical phase that the harness executes
    using the declared tool dependencies.
    """

    FETCH_PR = "fetch_pr"
    FETCH_REPOSITORY = "fetch_repository"
    ANALYZE_CHANGES = "analyze_changes"
    PRODUCE_FINDINGS = "produce_findings"
    POST_REVIEW = "post_review"


class PRReviewFindingSeverity(str, Enum):
    """Severity of a structured review finding."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    QUESTION = "question"


class ReviewActionKind(str, Enum):
    """Kind of review action that can be taken on a PR."""

    COMMENT = "comment"
    APPROVE = "approve"
    REQUEST_CHANGES = "request_changes"


PR_REVIEW_TOOL_DEPENDENCIES: list[str] = [
    "github.get_pull_request",
    "github.get_repository",
]

PR_REVIEW_STEPS: list[PRReviewStep] = [
    PRReviewStep.FETCH_PR,
    PRReviewStep.FETCH_REPOSITORY,
    PRReviewStep.ANALYZE_CHANGES,
    PRReviewStep.PRODUCE_FINDINGS,
    PRReviewStep.POST_REVIEW,
]


@dataclass
class PRReviewInput:
    """Typed input parameters for the PR review workflow.

    All parameters are safe resource selectors. Org, workspace, and
    repository scope are resolved by the proxy from harness/runtime
    identity via delegated context, never supplied as tool parameters.
    """

    pr_number: int
    ref: str | None = None
    review_depth: str = "full"

    def validate(self) -> list[str]:
        violations: list[str] = []
        if self.pr_number < 1:
            violations.append("pr_number must be a positive integer")
        valid_depths = {"full", "surface", "security"}
        if self.review_depth not in valid_depths:
            violations.append(
                f"review_depth must be one of {sorted(valid_depths)}, "
                f"got {self.review_depth!r}"
            )
        return violations


@dataclass
class PRReviewFinding:
    """A single structured finding produced by the review workflow."""

    severity: PRReviewFindingSeverity
    message: str
    file_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    category: str | None = None
    suggestion: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReviewAction:
    """An optional approval-gated write action on a PR.

    Write actions are disallowed by default. The harness must obtain
    explicit policy approval (e.g. via ``Permission.GITHUB_WRITE``)
    before executing any action.
    """

    kind: ReviewActionKind
    body: str
    require_approval: bool = True
    approval_permission: Permission = Permission.GITHUB_WRITE


@dataclass
class PRReviewOutput:
    """Structured output of the PR review workflow."""

    pr_number: int
    summary: str
    findings: list[PRReviewFinding] = field(default_factory=list)
    actionable_findings: list[PRReviewFinding] = field(default_factory=list)
    suggested_actions: list[ReviewAction] = field(default_factory=list)
    completed_steps: list[PRReviewStep] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def finding_count(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for f in self.findings:
            counts[f.severity.value] = counts.get(f.severity.value, 0) + 1
        return counts

    @property
    def has_critical_findings(self) -> bool:
        return any(
            f.severity == PRReviewFindingSeverity.CRITICAL for f in self.findings
        )

    @property
    def approval_required(self) -> bool:
        return any(action.require_approval for action in self.suggested_actions)


@dataclass
class PRReviewWorkflowSpec:
    """Composable workflow specification for GitHub PR review.

    This is a spec, not a runtime. It declares:
    - ``name``: unique workflow identifier
    - ``description``: what the workflow does
    - ``version``: the workflow module version
    - ``steps``: ordered semantic steps
    - ``tool_dependencies``: connector capability names required
    - ``required_permission``: baseline permission gate
    - ``write_permission``: permission required for write actions
    - ``read_only_by_default``: whether write actions require opt-in
    - ``input_type``: reference to the input dataclass
    - ``output_type``: reference to the output dataclass

    A harness interprets this spec to determine which tools to load,
    which policy gates to enforce, and how to present results.
    """

    name: str = "github_pr_review"
    description: str = (
        "Review a GitHub pull request: fetch PR metadata and repository "
        "info, analyze changes, produce structured findings, and optionally "
        "post review comments or approve changes. Read-only by default; "
        "write actions require explicit approval policy gate."
    )
    version: str = "0.1.0"
    steps: list[PRReviewStep] = field(default_factory=lambda: PR_REVIEW_STEPS)
    tool_dependencies: list[str] = field(
        default_factory=lambda: PR_REVIEW_TOOL_DEPENDENCIES
    )
    required_permission: Permission = Permission.GITHUB_READ
    write_permission: Permission = Permission.GITHUB_WRITE
    read_only_by_default: bool = True
    input_type: type = field(default=PRReviewInput)
    output_type: type = field(default=PRReviewOutput)


__all__ = [
    "PR_REVIEW_STEPS",
    "PR_REVIEW_TOOL_DEPENDENCIES",
    "PRReviewFinding",
    "PRReviewFindingSeverity",
    "PRReviewInput",
    "PRReviewOutput",
    "PRReviewStep",
    "PRReviewWorkflowSpec",
    "ReviewAction",
    "ReviewActionKind",
]
