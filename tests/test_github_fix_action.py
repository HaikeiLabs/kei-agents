from __future__ import annotations

from agents import (
    ALL_TOOL_DEFINITIONS,
    GITHUB_FIX_ACTION_TOOL,
    GITHUB_FIX_ACTION_TOOL_DEFINITIONS,
    TOOL_DEFINITIONS,
    ModelFormat,
    Permission,
    ToolCategory,
    render_tools,
    validate_tool_definitions,
)
from agents.github.tools import GITHUB_TOOL_DEFINITIONS


def test_fix_action_has_scoped_github_write_schema() -> None:
    tool = GITHUB_FIX_ACTION_TOOL
    assert tool.name == "github.create_fix_pr"
    assert tool in GITHUB_FIX_ACTION_TOOL_DEFINITIONS
    assert tool.permission == Permission.GITHUB_WRITE
    assert tool.category == ToolCategory.GITHUB
    assert tool.service == "github"
    assert tool.binding is None
    assert tool.handler is None
    assert validate_tool_definitions(GITHUB_FIX_ACTION_TOOL_DEFINITIONS) == []

    rendered = render_tools(GITHUB_FIX_ACTION_TOOL_DEFINITIONS, ModelFormat.OPENAI)
    schema = rendered[0]["function"]["parameters"]
    assert set(schema["properties"]) == {"title", "body", "unified_diff"}
    assert schema["required"] == ["title", "body", "unified_diff"]
    assert schema["properties"]["unified_diff"]["type"] == "string"
    assert "32 KiB" in schema["properties"]["unified_diff"]["description"]


def test_fix_action_is_opt_in_and_not_exposed_by_default_tools() -> None:
    fix_name = GITHUB_FIX_ACTION_TOOL.name
    for tools in (TOOL_DEFINITIONS, ALL_TOOL_DEFINITIONS, GITHUB_TOOL_DEFINITIONS):
        assert fix_name not in {tool.name for tool in tools}

    parameters = GITHUB_FIX_ACTION_TOOL.parameters
    assert isinstance(parameters, list)
    names = {parameter.name for parameter in parameters}
    assert names.isdisjoint(
        {
            "owner",
            "repo",
            "repository",
            "branch",
            "base",
            "draft",
            "shell",
            "credentials",
            "token",
        }
    )
