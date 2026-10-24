"""Eval cases for the PDE search agent (read-only Drive, Notion, Gmail, Tito)."""

from __future__ import annotations

from agents.evals.cases._common import Case, no_tool

CASES: list[Case] = [
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
]
