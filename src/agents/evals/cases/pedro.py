"""Eval cases for Pedro, the Discord agent.

The Discord ``default`` group may use only ``file_bug``, ``search_wiki``, and
``web_search``; every data tool is admin-only. Admin cases leave
``allowed_tools`` unset, so every tool is allowed.
"""

from __future__ import annotations

from agents.agent_definitions import PEDRO_DEFAULT_GROUP_TOOLS
from agents.evals.cases._common import (
    DELEGATED_KEYS,
    DRIVE_DELEGATED_KEYS,
    Case,
    case,
    denied,
    no_tool,
)

ADMIN = {"role": "admin", "groups": ["admin"]}
MEMBER = {
    "role": "member",
    "groups": ["default"],
    "allowed_tools": list(PEDRO_DEFAULT_GROUP_TOOLS),
}
_DEFAULT_TOOLS = list(PEDRO_DEFAULT_GROUP_TOOLS)

CASES: list[Case] = [
    # file_bug: the bug_to_linear_pr entry point, open to every group.
    case(
        "file-bug-basic",
        "The login page crashes with a 500 error when I click 'Sign in with Google'. Can you file a bug?",
        context=MEMBER,
        tool="file_bug",
        args={"team_key": "KEI"},
        required_arg_keys=["title", "description", "severity"],
        forbidden_arg_keys=DELEGATED_KEYS,
    ),
    case(
        "file-bug-named-team-critical",
        "File a bug for the OPS team: the nightly database backup job has been failing silently since "
        "Monday, so we may have lost data.",
        context=MEMBER,
        tool="file_bug",
        args={"team_key": "OPS", "severity": "critical"},
        forbidden_arg_keys=DELEGATED_KEYS,
    ),
    case(
        "file-bug-cosmetic-low",
        "Tiny thing: the footer logo on the pricing page is a few pixels off-center. Please report it.",
        context=MEMBER,
        tool="file_bug",
        args={"team_key": "KEI", "severity": "low"},
    ),
    case(
        "file-bug-not-github-issue",
        "The Slack integration stopped posting messages after yesterday's deploy. Report this bug please.",
        context=ADMIN,
        tool="file_bug",
        args={"team_key": "KEI"},
        forbidden_tools=["create_issue", "linear.create_followup_task"],
    ),
    # search_wiki / web_search: open to every group.
    case(
        "search-wiki-past-decision",
        "What did we decide last week about the pricing tiers?",
        context=MEMBER,
        tool="search_wiki",
        required_arg_keys=["query"],
    ),
    case(
        "search-wiki-what-did-i-ask",
        "What did I ask you yesterday about the deploy?",
        context=MEMBER,
        tool="search_wiki",
        required_arg_keys=["query"],
    ),
    case(
        "web-search-weather",
        "What's the weather in Salt Lake City today?",
        context=MEMBER,
        tool="web_search",
        required_arg_keys=["query"],
    ),
    case(
        "web-search-news",
        "Any news today about the Kubernetes 2.0 release?",
        context=MEMBER,
        tool="web_search",
        required_arg_keys=["query"],
        forbidden_tools=["search_wiki"],
    ),
    # No tool.
    no_tool("no-tool-thanks", "hey pedro, thanks for the help earlier!"),
    no_tool("no-tool-capabilities", "What kinds of things can you help me with?"),
    no_tool(
        "no-tool-general-knowledge",
        "Explain the difference between git merge and git rebase in two sentences.",
    ),
    # Admin data tools: argument semantics and delegated scoping.
    case(
        "admin-list-prs",
        "Show me the open pull requests.",
        context=ADMIN,
        tool="list_prs",
        forbidden_arg_keys=DELEGATED_KEYS,
    ),
    case(
        "admin-get-pr-by-number",
        "What's in PR #42?",
        context=ADMIN,
        tool="github.get_pull_request",
        args={"pr_number": 42},
        forbidden_arg_keys=DELEGATED_KEYS,
    ),
    case(
        "admin-get-pr-other-repo",
        "Pull up pull request 7 in the soypete/kei-website repo.",
        context=ADMIN,
        tool="github.get_pull_request",
        args={"pr_number": 7},
        forbidden_arg_keys=[*DELEGATED_KEYS, "repo"],
    ),
    case(
        "admin-get-github-issue",
        "Pull up GitHub issue 17 for me.",
        context=ADMIN,
        tool="github.get_issue",
        args={"issue_number": 17},
        forbidden_arg_keys=DELEGATED_KEYS,
    ),
    case(
        "admin-ci-status",
        "Is the deploy workflow passing in CI right now?",
        context=ADMIN,
        tool="get_workflow_status",
        required_arg_keys=["workflow_name"],
    ),
    case(
        "admin-linear-issue-key",
        "What's the status of KEI-123?",
        context=ADMIN,
        tool="linear.get_issue",
        args={"issue_key": "KEI-123"},
        forbidden_arg_keys=DELEGATED_KEYS,
    ),
    case(
        "admin-linear-urgent",
        "List the urgent Linear issues.",
        context=ADMIN,
        tool="linear.list_issues",
        args={"priority": "urgent"},
        forbidden_arg_keys=DELEGATED_KEYS,
    ),
    case(
        "admin-drive-search",
        "Find the Q3 board deck in our Drive.",
        context=ADMIN,
        tool="drive.list_files",
        required_arg_keys=["query"],
        forbidden_arg_keys=DRIVE_DELEGATED_KEYS,
    ),
    case(
        "admin-crm-lookup-email",
        "Look up the lead with email jane@acme.io in the CRM.",
        context=ADMIN,
        tool="crm_lookup_lead",
        args={"email": "jane@acme.io"},
        forbidden_arg_keys=DELEGATED_KEYS,
    ),
    case(
        "admin-crm-list-qualified",
        "List all qualified leads in the CRM.",
        context=ADMIN,
        tool="crm_list_leads",
        args={"status": "qualified"},
    ),
    case(
        "admin-followup-task-parent-lead",
        "Create a Linear follow-up task for lead L-204 to schedule a product demo.",
        context=ADMIN,
        tool="linear.create_followup_task",
        args={"lead_id": "L-204"},
        required_arg_keys=["title", "summary", "idempotency_key"],
        forbidden_arg_keys=DELEGATED_KEYS,
    ),
    case(
        "admin-approve-lead",
        "Approve lead L-77 in the leads workflow.",
        context=ADMIN,
        tool="leads_workflow.approve_lead",
        args={"lead_id": "L-77"},
    ),
    # Default group asking for admin-only data tools: the policy denies.
    denied(
        "deny-member-list-leads",
        "List all the leads in the CRM.",
        allowed_tools=_DEFAULT_TOOLS,
    ),
    denied(
        "deny-member-open-pr",
        "Open a pull request from branch fix/login-crash into main.",
        allowed_tools=_DEFAULT_TOOLS,
        tool="create_pull_request",
        args={"head": "fix/login-crash"},
        forbidden_arg_keys=DELEGATED_KEYS,
    ),
    denied(
        "deny-member-drive",
        "Find the payroll spreadsheet in Drive.",
        allowed_tools=_DEFAULT_TOOLS,
        tool="drive.list_files",
        content={"not_contains": ["payroll.xlsx"]},
    ),
    denied(
        "deny-member-linear-read",
        "What's the status of Linear issue KEI-88?",
        allowed_tools=_DEFAULT_TOOLS,
        tool="linear.get_issue",
        args={"issue_key": "KEI-88"},
    ),
]
