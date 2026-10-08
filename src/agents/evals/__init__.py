"""Eval suites for the prebuilt agents and workflows (EV-C1 ``agentware.eval-suite.v1``).

Suites are data: :mod:`agents.evals.export` renders each target's system
prompt, its tools (OpenAI format), and its hand-written cases into one JSON
file. The Agentware runner executes them; nothing here calls a model.
"""

from __future__ import annotations

from agents.evals.schema import SCHEMA_ID, validate_suite
from agents.evals.targets import EVAL_TARGETS, EvalTarget

__all__ = [
    "EVAL_TARGETS",
    "SCHEMA_ID",
    "EvalTarget",
    "validate_suite",
]
