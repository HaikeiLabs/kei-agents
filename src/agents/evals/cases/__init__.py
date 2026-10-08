"""Hand-written eval case tables, keyed by eval target name."""

from __future__ import annotations

from agents.evals.cases import pde_search_agent, pedro
from agents.evals.cases._common import Case
from agents.evals.cases.workflows import WORKFLOW_CASES

CASES: dict[str, list[Case]] = {
    "pedro": pedro.CASES,
    "pde_search_agent": pde_search_agent.CASES,
    **WORKFLOW_CASES,
}

__all__ = ["CASES", "Case"]
