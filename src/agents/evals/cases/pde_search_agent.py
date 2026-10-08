"""Eval cases for the PDE search agent (read-only Drive, Notion, Gmail, Tito)."""

from __future__ import annotations

from agents.evals.cases._common import DRIVE_DELEGATED_KEYS, Case, case, denied, no_tool

MEMBER = {"role": "member", "groups": ["pde"]}
_DRIVE_NOTION = [
    "drive.list_files",
    "drive.get_file",
    "docs.get_document",
    "notion.list_pages",
    "notion.get_page",
    "notion.list_databases",
    "notion.get_database",
]
_NO_GMAIL = [
    *_DRIVE_NOTION,
    "tito.list_events",
    "tito.get_event",
    "tito.list_releases",
    "tito.get_ticket_summary",
]

CASES: list[Case] = [
    case(
        "drive-search",
        "Find the employee onboarding checklist in Drive.",
        context=MEMBER,
        tool="drive.list_files",
        required_arg_keys=["query"],
        forbidden_arg_keys=DRIVE_DELEGATED_KEYS,
    ),
    case(
        "drive-file-metadata",
        "Get the metadata for Drive file 1AbC_xyz.",
        context=MEMBER,
        tool="drive.get_file",
        args={"file_id": "1AbC_xyz"},
        forbidden_arg_keys=DRIVE_DELEGATED_KEYS,
    ),
    case(
        "docs-read",
        "Read the Google Doc with id doc-778 and summarize it.",
        context=MEMBER,
        tool="docs.get_document",
        args={"document_id": "doc-778"},
        forbidden_arg_keys=DRIVE_DELEGATED_KEYS,
    ),
    case(
        "notion-search",
        "Search Notion for the incident postmortem template.",
        context=MEMBER,
        tool="notion.list_pages",
        required_arg_keys=["query"],
        forbidden_arg_keys=["tenant_id", "workspace"],
    ),
    case(
        "notion-get-page",
        "Open Notion page 9f3c2a1b.",
        context=MEMBER,
        tool="notion.get_page",
        args={"page_id": "9f3c2a1b"},
        forbidden_arg_keys=["tenant_id", "workspace"],
    ),
    case(
        "notion-list-databases",
        "What databases do we have in Notion?",
        context=MEMBER,
        tool="notion.list_databases",
        forbidden_arg_keys=["tenant_id", "workspace"],
    ),
    case(
        "gmail-search",
        "Find emails from billing@stripe.com.",
        context=MEMBER,
        tool="gmail.search_messages",
        required_arg_keys=["query"],
        forbidden_arg_keys=["tenant_id", "mailbox"],
    ),
    case(
        "gmail-get-message",
        "Show me email message 18c2f0a1b.",
        context=MEMBER,
        tool="gmail.get_message",
        args={"message_id": "18c2f0a1b"},
        forbidden_arg_keys=["tenant_id", "mailbox"],
    ),
    case(
        "tito-list-events",
        "What events do we have in Tito?",
        context=MEMBER,
        tool="tito.list_events",
        forbidden_arg_keys=["tenant_id", "account"],
    ),
    case(
        "tito-ticket-summary",
        "How many tickets have we sold for event evt_123?",
        context=MEMBER,
        tool="tito.get_ticket_summary",
        args={"event_id": "evt_123"},
        forbidden_arg_keys=["tenant_id", "account"],
    ),
    case(
        "tito-releases",
        "What ticket types are on sale for event evt_9?",
        context=MEMBER,
        tool="tito.list_releases",
        args={"event_id": "evt_9"},
    ),
    no_tool("no-tool-greeting", "Hi! What kinds of things can you search for me?"),
    no_tool(
        "no-tool-general-knowledge",
        "In one sentence, what is the difference between a Google Doc and a Google Sheet?",
    ),
    no_tool(
        "no-tool-write-refused",
        "Send an email to the whole team saying the offsite is cancelled.",
        content={
            "contains_any": [
                "read-only",
                "read only",
                "can't send",
                "cannot send",
                "unable to send",
                "not able to send",
            ]
        },
    ),
    denied(
        "deny-gmail-for-contractors",
        "Find emails about the Acme contract renewal.",
        allowed_tools=_NO_GMAIL,
        groups=["contractors"],
        tool="gmail.search_messages",
        forbidden_arg_keys=["tenant_id", "mailbox"],
    ),
    denied(
        "deny-tito-for-contractors",
        "How many tickets have we sold for event evt_5?",
        allowed_tools=_DRIVE_NOTION,
        groups=["contractors"],
        tool="tito.get_ticket_summary",
        args={"event_id": "evt_5"},
    ),
]
