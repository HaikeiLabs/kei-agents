"""Release-gate tests for PR #18 tool registration and quarantine."""

from agents import ALL_TOOL_DEFINITIONS, ToolDefinition, validate_tool_definitions
from agents.workflows.crm_linear_followup import LINEAR_CREATE_FOLLOWUP_TOOL
from agents.workflows.leads import (
    LEADS_WORKFLOW_TOOL_DEFINITIONS,
    QUARANTINED_LEADS_WORKFLOW_TOOL_DEFINITIONS,
    REGISTERED_LEADS_WORKFLOW_TOOL_DEFINITIONS,
)


def _names(tools: list[ToolDefinition]) -> set[str]:
    return {tool.name for tool in tools}


def test_pr18_tools_are_registered_or_quarantined() -> None:
    all_pr18 = _names(LEADS_WORKFLOW_TOOL_DEFINITIONS)
    registered = _names(REGISTERED_LEADS_WORKFLOW_TOOL_DEFINITIONS)
    quarantined = _names(QUARANTINED_LEADS_WORKFLOW_TOOL_DEFINITIONS)
    assert registered.isdisjoint(quarantined)
    assert registered | quarantined == all_pr18
    assert registered <= _names(ALL_TOOL_DEFINITIONS)
    assert quarantined.isdisjoint(_names(ALL_TOOL_DEFINITIONS))


def test_registered_pr18_tools_are_handlerless_and_valid() -> None:
    assert validate_tool_definitions(REGISTERED_LEADS_WORKFLOW_TOOL_DEFINITIONS) == []
    assert all(tool.handler is None for tool in REGISTERED_LEADS_WORKFLOW_TOOL_DEFINITIONS)
    assert validate_tool_definitions([LINEAR_CREATE_FOLLOWUP_TOOL]) == []


def test_pr18_tools_do_not_accept_delegated_scope() -> None:
    forbidden = {"tenant_id", "workspace", "workspace_id", "org_id", "organization_id"}
    for tool in LEADS_WORKFLOW_TOOL_DEFINITIONS + [LINEAR_CREATE_FOLLOWUP_TOOL]:
        params = tool.parameters if isinstance(tool.parameters, list) else []
        assert forbidden.isdisjoint({param.name for param in params})
