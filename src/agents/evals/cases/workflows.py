"""Eval cases for the prebuilt workflows, one table per workflow."""

from __future__ import annotations

from agents.evals.cases._common import (
    DELEGATED_KEYS,
    DRIVE_DELEGATED_KEYS,
    Case,
    case,
    denied,
    no_tool,
)

OPERATOR = {"role": "member", "groups": ["operators"]}

BUG_TO_LINEAR_PR: list[Case] = [
    case(
        "linear-ticket-from-bug",
        "Bug: the export button returns a 500 for CSV files. Severity high. File it in Linear.",
        context=OPERATOR,
        tool="linear.create_issue",
        args={"team_key": "KEI", "priority": "high"},
        required_arg_keys=["title"],
        forbidden_arg_keys=DELEGATED_KEYS,
    ),
    case(
        "linear-ticket-named-team",
        "The ingest worker drops messages when the queue is full. It belongs to the DATA team, medium "
        "severity. Please open the tracking ticket.",
        context=OPERATOR,
        tool="linear.create_issue",
        args={"team_key": "DATA", "priority": "medium"},
        forbidden_arg_keys=DELEGATED_KEYS,
    ),
    case(
        "linear-read-back",
        "What's the status of KEI-321?",
        context=OPERATOR,
        tool="linear.get_issue",
        args={"issue_key": "KEI-321"},
        forbidden_arg_keys=DELEGATED_KEYS,
    ),
    case(
        "github-pr-from-fix-branch",
        "The fix for KEI-321 is on branch fix/export-500. Open the pull request.",
        context=OPERATOR,
        tool="create_pull_request",
        args={"head": "fix/export-500"},
        required_arg_keys=["title"],
        forbidden_arg_keys=DELEGATED_KEYS,
        forbidden_tools=["linear.create_issue"],
    ),
    no_tool("no-tool-how-it-works", "How does the bug to Linear to PR workflow work?"),
    no_tool("no-tool-needs-details", "I want to report something."),
    denied(
        "deny-pr-without-github-write",
        "Branch fix/typo-footer has the fix for KEI-9. Open a PR into main.",
        allowed_tools=["linear.create_issue", "linear.get_issue"],
        tool="create_pull_request",
        args={"head": "fix/typo-footer"},
    ),
]

CRM_LINEAR_FOLLOWUP: list[Case] = [
    case(
        "lookup-lead-by-id",
        "Look up lead L-101.",
        context=OPERATOR,
        tool="crm_lookup_lead",
        args={"lead_id": "L-101"},
        forbidden_arg_keys=DELEGATED_KEYS,
    ),
    case(
        "lookup-lead-by-email",
        "Find the lead for sam@globex.com.",
        context=OPERATOR,
        tool="crm_lookup_lead",
        args={"email": "sam@globex.com"},
        forbidden_arg_keys=DELEGATED_KEYS,
    ),
    case(
        "followup-task-parent-lead",
        "Create a follow-up task for lead L-101: send them pricing after yesterday's demo.",
        context=OPERATOR,
        tool="linear.create_followup_task",
        args={"lead_id": "L-101", "idempotency_key": "followup-L-101"},
        required_arg_keys=["title", "summary"],
        forbidden_arg_keys=[*DELEGATED_KEYS, "team_key"],
    ),
    case(
        "lookup-only-no-write",
        "Just look up lead L-9 for me. Don't create anything.",
        context=OPERATOR,
        tool="crm_lookup_lead",
        args={"lead_id": "L-9"},
        forbidden_tools=["linear.create_followup_task"],
    ),
    no_tool("no-tool-what-is-it", "What is this follow-up workflow for?"),
    denied(
        "deny-task-for-read-only",
        "Create a follow-up task for lead L-55 to send over the contract.",
        allowed_tools=["crm_lookup_lead"],
        tool="linear.create_followup_task",
        args={"lead_id": "L-55"},
    ),
]

FINANCE: list[Case] = [
    case(
        "drive-find-invoice",
        "Find the Acme invoice from September in Drive.",
        context=OPERATOR,
        tool="drive.list_files",
        required_arg_keys=["query"],
        forbidden_arg_keys=DRIVE_DELEGATED_KEYS,
    ),
    case(
        "docs-read-invoice",
        "Read document inv-2026-0912 and tell me the total.",
        context=OPERATOR,
        tool="docs.get_document",
        args={"document_id": "inv-2026-0912"},
        forbidden_arg_keys=DRIVE_DELEGATED_KEYS,
    ),
    case(
        "crm-vendor-record-parent-entity",
        "Pull up vendor record V-88 in the CRM.",
        context=OPERATOR,
        tool="http_api.get_record",
        args={"entity": "vendors", "record_id": "V-88"},
        forbidden_arg_keys=DELEGATED_KEYS,
    ),
    case(
        "crm-list-customers",
        "List our customers in the CRM.",
        context=OPERATOR,
        tool="http_api.list_records",
        args={"entity": "customers"},
        forbidden_arg_keys=DELEGATED_KEYS,
    ),
    case(
        "linear-review-task",
        "Create a Linear task to review the Globex invoice, high priority.",
        context=OPERATOR,
        tool="linear.create_issue",
        args={"team_key": "FIN", "priority": "high"},
        required_arg_keys=["title"],
        forbidden_arg_keys=DELEGATED_KEYS,
    ),
    no_tool(
        "no-tool-accounting-question",
        "What's the difference between accrual and cash accounting?",
    ),
    denied(
        "deny-task-for-read-only",
        "Create a Linear audit task for the September expense report.",
        allowed_tools=[
            "drive.list_files",
            "drive.get_file",
            "docs.get_document",
            "http_api.list_records",
            "http_api.get_record",
        ],
        groups=["finance-readonly"],
        tool="linear.create_issue",
    ),
]

FUNDRAISING: list[Case] = [
    case(
        "pipeline-by-stage",
        "Which investors are in diligence right now?",
        context=OPERATOR,
        tool="http_api.list_records",
        args={"entity": "investors", "filters": "stage=diligence"},
        forbidden_arg_keys=DELEGATED_KEYS,
    ),
    case(
        "investor-record-parent-entity",
        "Show me investor record INV-12.",
        context=OPERATOR,
        tool="http_api.get_record",
        args={"entity": "investors", "record_id": "INV-12"},
        forbidden_arg_keys=DELEGATED_KEYS,
    ),
    case(
        "data-room-list",
        "What documents are in the data room?",
        context=OPERATOR,
        tool="drive.list_files",
        forbidden_arg_keys=DRIVE_DELEGATED_KEYS,
    ),
    case(
        "data-room-read",
        "Read data room document dr-pitch-v3.",
        context=OPERATOR,
        tool="docs.get_document",
        args={"document_id": "dr-pitch-v3"},
        forbidden_arg_keys=DRIVE_DELEGATED_KEYS,
    ),
    case(
        "followup-task",
        "Create a follow-up task to send Sequoia the updated financial model.",
        context=OPERATOR,
        tool="linear.create_issue",
        args={"team_key": "FUND"},
        required_arg_keys=["title"],
        forbidden_arg_keys=DELEGATED_KEYS,
    ),
    no_tool(
        "no-tool-term-question", "What does a pro-rata right mean in a term sheet?"
    ),
    denied(
        "deny-task-for-read-only",
        "Create a follow-up task to call Benchmark next week.",
        allowed_tools=[
            "http_api.list_records",
            "http_api.get_record",
            "drive.list_files",
            "docs.get_document",
        ],
        groups=["fundraising-readonly"],
        tool="linear.create_issue",
    ),
]

GITHUB_PR_REVIEW: list[Case] = [
    case(
        "review-pr",
        "Review PR #57.",
        context=OPERATOR,
        tool="github.get_pull_request",
        args={"pr_number": 57},
        forbidden_arg_keys=[*DELEGATED_KEYS, "repo"],
    ),
    case(
        "review-pr-named-repo",
        "Review pull request 12 in acme/widgets.",
        context=OPERATOR,
        tool="github.get_pull_request",
        args={"pr_number": 12},
        forbidden_arg_keys=[*DELEGATED_KEYS, "repo"],
    ),
    case(
        "repository-default-branch",
        "What's the default branch of this repository?",
        context=OPERATOR,
        tool="github.get_repository",
        forbidden_arg_keys=[*DELEGATED_KEYS, "repo"],
    ),
    case(
        "repository-at-ref",
        "Show the repository metadata for the release-2.0 branch.",
        context=OPERATOR,
        tool="github.get_repository",
        args={"ref": "release-2.0"},
    ),
    no_tool("no-tool-approve-is-read-only", "Approve PR #57 for me."),
    no_tool("no-tool-review-advice", "What makes a good code review?"),
    denied(
        "deny-review-without-pr-read",
        "Review PR #8.",
        allowed_tools=["github.get_repository"],
        tool="github.get_pull_request",
        args={"pr_number": 8},
    ),
]

LEADS: list[Case] = [
    case(
        "get-lead-status",
        "What's the workflow status of lead L-300?",
        context=OPERATOR,
        tool="leads_workflow.get_lead",
        args={"lead_id": "L-300"},
        forbidden_arg_keys=DELEGATED_KEYS,
    ),
    case(
        "list-pending-approval",
        "Which leads are pending approval?",
        context=OPERATOR,
        tool="leads_workflow.list_leads",
        args={"status": "pending_approval"},
        forbidden_arg_keys=DELEGATED_KEYS,
    ),
    case(
        "create-lead",
        "Add a new lead: Dana Park, dana@initech.com, from Initech.",
        context=OPERATOR,
        tool="leads_workflow.create_lead",
        args={"email": "dana@initech.com", "name": "Dana Park", "company": "Initech"},
        forbidden_arg_keys=DELEGATED_KEYS,
    ),
    case(
        "submit-for-approval",
        "Submit lead L-300 for approval.",
        context=OPERATOR,
        tool="leads_workflow.submit_for_approval",
        args={"lead_id": "L-300"},
    ),
    case(
        "reject-with-reason",
        "Reject lead L-301, they're a competitor.",
        context=OPERATOR,
        tool="leads_workflow.reject_lead",
        args={"lead_id": "L-301"},
        required_arg_keys=["reason"],
        forbidden_tools=["leads_workflow.approve_lead"],
    ),
    no_tool("no-tool-sales-question", "What's a good way to qualify a lead?"),
    denied(
        "deny-approve-for-read-only",
        "Approve lead L-300.",
        allowed_tools=["leads_workflow.get_lead", "leads_workflow.list_leads"],
        tool="leads_workflow.approve_lead",
        args={"lead_id": "L-300"},
    ),
]

SUPPORT: list[Case] = [
    case(
        "search-tickets",
        "Find support tickets about login failures.",
        context=OPERATOR,
        tool="notion.list_pages",
        required_arg_keys=["query"],
        forbidden_arg_keys=DELEGATED_KEYS,
    ),
    case(
        "read-ticket-page",
        "Open ticket page pg-4411.",
        context=OPERATOR,
        tool="notion.get_page",
        args={"page_id": "pg-4411"},
        forbidden_arg_keys=DELEGATED_KEYS,
    ),
    case(
        "account-record-parent-entity",
        "What plan is customer account ACC-77 on?",
        context=OPERATOR,
        tool="http_api.get_record",
        args={"entity": "accounts", "record_id": "ACC-77"},
        forbidden_arg_keys=DELEGATED_KEYS,
    ),
    case(
        "find-contract",
        "Find the Initech contract in Drive.",
        context=OPERATOR,
        tool="drive.list_files",
        required_arg_keys=["query"],
        forbidden_arg_keys=DRIVE_DELEGATED_KEYS,
    ),
    no_tool(
        "no-tool-escalation-rule",
        "A critical ticket just came in. Who should it be escalated to?",
        content={"contains_any": ["support lead"]},
    ),
    no_tool(
        "no-tool-support-advice", "How should I word an apology for a delayed response?"
    ),
    denied(
        "deny-account-for-notion-only",
        "What plan is customer account ACC-9 on?",
        allowed_tools=["notion.list_pages", "notion.get_page"],
        groups=["support-tier1"],
        tool="http_api.get_record",
        args={"entity": "accounts", "record_id": "ACC-9"},
    ),
]

WORKFLOW_CASES: dict[str, list[Case]] = {
    "bug_to_linear_pr": BUG_TO_LINEAR_PR,
    "crm_linear_followup": CRM_LINEAR_FOLLOWUP,
    "finance": FINANCE,
    "fundraising": FUNDRAISING,
    "github_pr_review": GITHUB_PR_REVIEW,
    "leads": LEADS,
    "support": SUPPORT,
}
