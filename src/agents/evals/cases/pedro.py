"""Eval cases for Pedro that are independent of tool availability."""

from __future__ import annotations

from agents.evals.cases._common import Case, no_tool

CASES: list[Case] = [
    no_tool("no-tool-thanks", "hey pedro, thanks for the help earlier!"),
    no_tool("no-tool-capabilities", "What kinds of things can you help me with?"),
    no_tool(
        "no-tool-general-knowledge",
        "Explain the difference between git merge and git rebase in two sentences.",
    ),
]
