"""HAI-384: the agent package carries no CRM code, permissions, or workflows."""

from importlib.util import find_spec
from pathlib import Path

from agents import HARNESS_AGENT_DEFINITIONS, Permission
from agents.evals.cases import WORKFLOW_CASES

_REMOVED_WORKFLOWS = ("crm_linear_followup", "leads", "fundraising", "finance")
_SRC = Path(__file__).parents[1] / "src" / "agents"


def test_no_crm_modules_or_workflows():
    assert find_spec("agents.crm") is None
    for name in ("finance", "fundraising", "leads"):
        assert find_spec(f"agents.workflows.{name}") is None
    for name in _REMOVED_WORKFLOWS:
        assert not (_SRC / "prompts" / "workflows" / f"{name}.md").exists()
        assert name not in WORKFLOW_CASES


def test_no_crm_permissions():
    names = {p.name for p in Permission}
    assert not names & {"CRM_READ", "CRM_WRITE", "FINANCE_READ", "FINANCE_WRITE", "FUNDRAISING_READ", "FUNDRAISING_WRITE"}
    for agent in HARNESS_AGENT_DEFINITIONS:
        assert not {p.name for p in agent.permissions} & {"CRM_READ", "CRM_WRITE"}


def test_no_crm_tools_in_prompts():
    for prompt in (_SRC / "prompts").rglob("*.md"):
        text = prompt.read_text()
        assert "crm_" not in text, prompt
        assert "linear.create_followup_task" not in text, prompt
        assert "leads_workflow" not in text, prompt
