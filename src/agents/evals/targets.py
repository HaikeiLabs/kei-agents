"""Eval suite prompts. Runtime tools are inferred by Kei at call time."""

from __future__ import annotations

from dataclasses import dataclass

from agents.agent_definitions import PDE_SEARCH_AGENT, PEDRO_AGENT, AgentDefinition

SUITE_PREFIX = "kei-agents"


@dataclass(frozen=True)
class EvalTarget:
    """One suite's subject.

    Attributes:
        name: Agent or workflow name; the suite id is ``kei-agents.<name>``.
        prompt_file: System prompt path relative to the ``agents`` package.
        tools: Empty because Kei infers available tools at call time.
    """

    name: str
    prompt_file: str
    tools: tuple[str, ...]

    @property
    def suite(self) -> str:
        return f"{SUITE_PREFIX}.{self.name}"


def _agent_target(agent: AgentDefinition) -> EvalTarget:
    if agent.system_prompt_file is None:
        raise ValueError(f"{agent.name}: an eval target needs a system_prompt_file")
    return EvalTarget(agent.name, agent.system_prompt_file, ())


def _workflow(name: str, *tools: str) -> EvalTarget:
    return EvalTarget(name, f"prompts/workflows/{name}.md", tools)


AGENT_TARGETS: tuple[EvalTarget, ...] = (
    _agent_target(PEDRO_AGENT),
    _agent_target(PDE_SEARCH_AGENT),
)

WORKFLOW_TARGETS: tuple[EvalTarget, ...] = tuple(
    _workflow(name)
    for name in (
        "bug_to_linear_pr",
        "github_pr_review",
        "support",
        "drive_publish",
    )
)

EVAL_TARGETS: tuple[EvalTarget, ...] = AGENT_TARGETS + WORKFLOW_TARGETS

__all__ = [
    "AGENT_TARGETS",
    "EVAL_TARGETS",
    "SUITE_PREFIX",
    "WORKFLOW_TARGETS",
    "EvalTarget",
]
