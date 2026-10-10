"""What each eval suite exercises: a system prompt and the tools it may call.

Agent suites take both from the :class:`~agents.agent_definitions.AgentDefinition`.
Workflow suites name a prompt under ``prompts/workflows/`` and the catalog
tools that carry out the workflow's steps. A workflow step with no catalog
tool yet (Drive archive, CRM update, data-room share, notifications) is done
by the harness after review, so it has no tool here and the prompt says so.
"""

from __future__ import annotations

from dataclasses import dataclass

from agents.agent_definitions import (
    PDE_SEARCH_AGENT,
    PEDRO_AGENT,
    AgentDefinition,
)
from agents.workflows.bug_to_linear_pr import BUG_TO_LINEAR_PR
from agents.workflows.github_pr_review import PR_REVIEW_TOOL_DEPENDENCIES
from agents.workflows.leads import REGISTERED_LEADS_WORKFLOW_TOOL_DEFINITIONS

SUITE_PREFIX = "kei-agents"


@dataclass(frozen=True)
class EvalTarget:
    """One suite's subject.

    Attributes:
        name: Agent or workflow name; the suite id is ``kei-agents.<name>``.
        prompt_file: System prompt path relative to the ``agents`` package.
        tools: Catalog tool names rendered into the suite, in order.
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
    return EvalTarget(agent.name, agent.system_prompt_file, agent.tools)


def _workflow(name: str, *tools: str) -> EvalTarget:
    return EvalTarget(name, f"prompts/workflows/{name}.md", tools)


AGENT_TARGETS: tuple[EvalTarget, ...] = (
    _agent_target(PEDRO_AGENT),
    _agent_target(PDE_SEARCH_AGENT),
)

WORKFLOW_TARGETS: tuple[EvalTarget, ...] = (
    _workflow(
        "bug_to_linear_pr",
        *(
            ref.name
            for step in BUG_TO_LINEAR_PR.steps
            for ref in step.connector_dependencies
        ),
    ),
    _workflow("crm_linear_followup", "crm_lookup_lead", "linear.create_followup_task"),
    # DriveRead, CRMLookup (customers/vendors as http_api records), LinearTask.
    _workflow(
        "finance",
        "drive.list_files",
        "drive.get_file",
        "docs.get_document",
        "http_api.list_records",
        "http_api.get_record",
        "linear.create_issue",
    ),
    # InvestorLookup/InvestorPipelineRead (investors as http_api records),
    # DataRoomRead, LinearTask.
    _workflow(
        "fundraising",
        "http_api.list_records",
        "http_api.get_record",
        "drive.list_files",
        "docs.get_document",
        "linear.create_issue",
    ),
    _workflow("github_pr_review", *PR_REVIEW_TOOL_DEPENDENCIES),
    _workflow("leads", *(t.name for t in REGISTERED_LEADS_WORKFLOW_TOOL_DEFINITIONS)),
    # The support spec's read steps that exist in the catalog; notion.list_pages
    # stands in for notion.query_database until that read schema exists.
    _workflow(
        "support",
        "notion.list_pages",
        "notion.get_page",
        "drive.list_files",
        "docs.get_document",
        "http_api.get_record",
    ),
    # Harness-side Drive doc writes (confirm-required) plus the reads used to
    # find a doc before updating it.
    _workflow(
        "drive_publish",
        "drive_create_doc",
        "drive_update_doc",
        "drive.list_files",
        "docs.get_document",
    ),
)

EVAL_TARGETS: tuple[EvalTarget, ...] = AGENT_TARGETS + WORKFLOW_TARGETS

__all__ = [
    "AGENT_TARGETS",
    "EVAL_TARGETS",
    "SUITE_PREFIX",
    "WORKFLOW_TARGETS",
    "EvalTarget",
]
