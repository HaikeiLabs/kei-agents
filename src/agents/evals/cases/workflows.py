"""Eval cases for the prebuilt workflows, one table per workflow."""

from __future__ import annotations

from agents.evals.cases._common import Case, no_tool

BUG_TO_LINEAR_PR: list[Case] = [
    no_tool("no-tool-how-it-works", "How does the bug to Linear to PR workflow work?"),
    no_tool("no-tool-needs-details", "I want to report something."),
]
GITHUB_PR_REVIEW: list[Case] = [
    no_tool("no-tool-approve-is-read-only", "Approve PR #57 for me."),
    no_tool("no-tool-review-advice", "What makes a good code review?"),
]
SUPPORT: list[Case] = [
    no_tool(
        "no-tool-escalation-rule",
        "A critical ticket just came in. Who should it be escalated to?",
        content={"contains_any": ["support lead"]},
    ),
    no_tool(
        "no-tool-support-advice", "How should I word an apology for a delayed response?"
    ),
]
DRIVE_PUBLISH: list[Case] = [
    no_tool(
        "no-tool-how-publishing-works",
        "How does publishing a doc to Drive work here? Does it write right away?",
        content={"contains_any": ["confirm", "preview"]},
    )
]
WORKFLOW_CASES: dict[str, list[Case]] = {
    "bug_to_linear_pr": BUG_TO_LINEAR_PR,
    "drive_publish": DRIVE_PUBLISH,
    "github_pr_review": GITHUB_PR_REVIEW,
    "support": SUPPORT,
}
