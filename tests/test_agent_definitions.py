"""Tests for the harness permission set and harness agent definitions (HAI-205)."""

from __future__ import annotations

import pytest

from agents import (
    ALL_TOOL_DEFINITIONS,
    HARNESS_AGENT_DEFINITIONS,
    PDE_SEARCH_AGENT,
    PEDRO_AGENT,
    PEDRO_DEFAULT_GROUP_TOOLS,
    AgentDefinition,
    Harness,
    Permission,
    get_agent_tools,
    load_system_prompt,
    validate_agent_definitions,
    validate_tool_definitions,
)

P = Permission


class TestPermissionSet:
    @pytest.mark.parametrize(
        ("member", "value"),
        [
            ("GMAIL_READ", "gmail_read"),
            ("TITO_READ", "tito_read"),
            ("FINANCE_READ", "finance_read"),
            ("FINANCE_WRITE", "finance_write"),
            ("FUNDRAISING_READ", "fundraising_read"),
            ("FUNDRAISING_WRITE", "fundraising_write"),
            ("PROJECT_HOURS_READ", "project_hours_read"),
            ("SEMANTIC_MODEL_READ", "semantic_model_read"),
        ],
    )
    def test_new_members(self, member: str, value: str) -> None:
        assert Permission[member].value == value

    def test_values_are_unique(self) -> None:
        values = [p.value for p in Permission]
        assert len(values) == len(set(values))


class TestHarnessAgents:
    def test_two_harness_agents(self) -> None:
        assert [a.name for a in HARNESS_AGENT_DEFINITIONS] == [
            "pde_search_agent",
            "pedro",
        ]
        assert {a.harness for a in HARNESS_AGENT_DEFINITIONS} == {
            Harness.PDE,
            Harness.DISCORD,
        }

    def test_definitions_validate(self) -> None:
        assert validate_agent_definitions(HARNESS_AGENT_DEFINITIONS) == []

    def test_agent_tools_validate(self) -> None:
        for agent in HARNESS_AGENT_DEFINITIONS:
            assert validate_tool_definitions(get_agent_tools(agent)) == []

    def test_pde_permissions(self) -> None:
        assert PDE_SEARCH_AGENT.permissions == frozenset(
            {P.DRIVE_READ, P.NOTION_READ, P.GMAIL_READ, P.TITO_READ}
        )

    def test_pde_is_read_only(self) -> None:
        for tool in get_agent_tools(PDE_SEARCH_AGENT):
            assert tool.permission.value.endswith("_read")

    def test_pedro_permissions(self) -> None:
        assert PEDRO_AGENT.permissions == frozenset(
            {
                P.GITHUB_READ,
                P.GITHUB_WRITE,
                P.CRM_READ,
                P.CRM_WRITE,
                P.LINEAR_READ,
                P.LINEAR_WRITE,
                P.DRIVE_READ,
                P.FUNDRAISING_READ,
                P.FUNDRAISING_WRITE,
                P.FINANCE_READ,
                P.FINANCE_WRITE,
                P.SEARCH_WIKI,
                P.WEB_SEARCH,
            }
        )

    def test_pedro_has_linear_followup_action(self) -> None:
        assert "linear.create_followup_task" in PEDRO_AGENT.tools

    def test_pedro_default_group_tools_come_first(self) -> None:
        assert PEDRO_DEFAULT_GROUP_TOOLS == ("file_bug", "search_wiki", "web_search")
        assert PEDRO_AGENT.tools[:3] == PEDRO_DEFAULT_GROUP_TOOLS

    def test_pedro_files_bugs_through_the_workflow_entry(self) -> None:
        # linear.create_issue is the workflow's own step, not a Pedro tool.
        assert "linear.create_issue" not in PEDRO_AGENT.tools
        assert len(set(PEDRO_AGENT.tools)) == len(PEDRO_AGENT.tools)

    def test_get_agent_tools_uses_catalog(self) -> None:
        tools = get_agent_tools(PEDRO_AGENT)
        assert [t.name for t in tools] == list(PEDRO_AGENT.tools)
        assert all(t in ALL_TOOL_DEFINITIONS for t in tools)


def _agent(**overrides: object) -> AgentDefinition:
    fields: dict[str, object] = {
        "name": "probe",
        "harness": Harness.PDE,
        "description": "probe agent",
        "permissions": frozenset({P.DRIVE_READ}),
        "tools": ("drive.list_files",),
    }
    fields.update(overrides)
    return AgentDefinition(**fields)  # type: ignore[arg-type]


class TestValidateAgentDefinitions:
    def test_valid_probe(self) -> None:
        assert validate_agent_definitions([_agent()]) == []

    def test_invalid_name(self) -> None:
        assert any(
            "invalid name" in v
            for v in validate_agent_definitions([_agent(name="Bad-Name")])
        )

    def test_duplicate_name(self) -> None:
        assert any(
            "duplicate" in v for v in validate_agent_definitions([_agent(), _agent()])
        )

    def test_empty_description(self) -> None:
        assert any(
            "description" in v
            for v in validate_agent_definitions([_agent(description="")])
        )

    def test_bare_string_permission_rejected(self) -> None:
        bad = _agent(permissions=frozenset({P.DRIVE_READ, "drive_write"}))
        assert any("invalid permission" in v for v in validate_agent_definitions([bad]))

    def test_bare_string_harness_rejected(self) -> None:
        assert any(
            "invalid harness" in v
            for v in validate_agent_definitions([_agent(harness="pde")])
        )

    def test_unknown_tool_rejected(self) -> None:
        bad = _agent(tools=("drive.list_files", "drive.delete_file"))
        assert any("unknown tool" in v for v in validate_agent_definitions([bad]))

    def test_tool_permission_not_granted_rejected(self) -> None:
        bad = _agent(tools=("drive.list_files", "gmail.get_message"))
        assert any("not granted" in v for v in validate_agent_definitions([bad]))

    def test_duplicate_tool_rejected(self) -> None:
        bad = _agent(tools=("drive.list_files", "drive.list_files"))
        assert any("duplicate tool" in v for v in validate_agent_definitions([bad]))


class TestSystemPrompt:
    def test_prompt_fields_default_to_none(self) -> None:
        # Back-compatible: definitions written before the fields existed.
        agent = _agent()
        assert agent.system_prompt is None
        assert agent.system_prompt_file is None
        assert load_system_prompt(agent) is None
        assert validate_agent_definitions([agent]) == []

    def test_positional_construction_still_works(self) -> None:
        agent = AgentDefinition(
            "probe",
            Harness.PDE,
            "probe agent",
            frozenset({P.DRIVE_READ}),
            ("drive.list_files",),
        )
        assert load_system_prompt(agent) is None

    def test_inline_prompt(self) -> None:
        agent = _agent(system_prompt="You are a probe.")
        assert load_system_prompt(agent) == "You are a probe."
        assert validate_agent_definitions([agent]) == []

    def test_prompt_file_is_packaged(self) -> None:
        for agent in HARNESS_AGENT_DEFINITIONS:
            prompt = load_system_prompt(agent)
            assert prompt is not None and prompt.strip()

    def test_both_sources_rejected(self) -> None:
        agent = _agent(system_prompt="x", system_prompt_file="prompts/pedro.md")
        assert any("not both" in v for v in validate_agent_definitions([agent]))

    @pytest.mark.parametrize(
        "path", ["prompts/missing.md", "../pyproject.toml", "/etc/hosts"]
    )
    def test_bad_prompt_file_rejected(self, path: str) -> None:
        agent = _agent(system_prompt_file=path)
        assert any(
            "system_prompt_file" in v for v in validate_agent_definitions([agent])
        )
        with pytest.raises(ValueError):
            load_system_prompt(agent)
