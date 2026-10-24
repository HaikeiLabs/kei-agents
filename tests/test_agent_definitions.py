from __future__ import annotations

from agents import (
    BUG_REPORT_TRIAGE_AGENT,
    FIX_PROPOSAL_AGENT,
    HARNESS_AGENT_DEFINITIONS,
    ONBOARDING_E2E_TRIAGE_AGENT,
    PDE_SEARCH_AGENT,
    PEDRO_AGENT,
    AgentDefinition,
    Harness,
    Permission,
    load_system_prompt,
    validate_agent_definitions,
)

P = Permission


def _agent(**overrides: object) -> AgentDefinition:
    fields: dict[str, object] = {
        "name": "probe", "harness": Harness.PDE, "description": "probe agent",
        "permissions": frozenset({P.DRIVE_READ}),
    }
    fields.update(overrides)
    return AgentDefinition(**fields)  # type: ignore[arg-type]


def test_permission_values_are_unique() -> None:
    values = [p.value for p in Permission]
    assert len(values) == len(set(values))


def test_harness_agents_validate() -> None:
    assert [a.name for a in HARNESS_AGENT_DEFINITIONS] == [
        "pde_search_agent", "pedro", "onboarding_e2e_triage",
        "bug_report_triage", "fix_proposal"
    ]
    assert validate_agent_definitions(HARNESS_AGENT_DEFINITIONS) == []


def test_agent_permissions_remain_metadata() -> None:
    assert PDE_SEARCH_AGENT.permissions == frozenset(
        {P.DRIVE_READ, P.NOTION_READ, P.GMAIL_READ, P.TITO_READ}
    )
    assert P.GITHUB_WRITE in PEDRO_AGENT.permissions
    assert ONBOARDING_E2E_TRIAGE_AGENT.permissions == frozenset({P.GITHUB_READ})


def test_agent_definition_has_no_tool_name_catalog() -> None:
    assert not hasattr(PEDRO_AGENT, "tools")


def test_validator_checks_names_permissions_and_prompts() -> None:
    assert validate_agent_definitions([_agent()]) == []
    assert any("invalid name" in v for v in validate_agent_definitions([_agent(name="Bad-Name")]))
    assert any("duplicate" in v for v in validate_agent_definitions([_agent(), _agent()]))
    assert any("invalid permission" in v for v in validate_agent_definitions([_agent(permissions=frozenset({"drive_read"}))]))


def test_prompts_load() -> None:
    for agent in HARNESS_AGENT_DEFINITIONS:
        assert load_system_prompt(agent)


def test_both_prompt_sources_are_rejected() -> None:
    agent = _agent(system_prompt="x", system_prompt_file="prompts/pedro.md")
    assert any("not both" in v for v in validate_agent_definitions([agent]))


def test_bug_report_triage_agent_is_read_only_and_uses_its_prompt() -> None:
    assert BUG_REPORT_TRIAGE_AGENT.harness is Harness.DISCORD
    assert BUG_REPORT_TRIAGE_AGENT.permissions == frozenset({P.GITHUB_READ})
    prompt = load_system_prompt(BUG_REPORT_TRIAGE_AGENT)
    assert prompt is not None
    for required in ("sanitized report", "untrusted evidence", "**Likely cause**", "**Verification**"):
        assert required in prompt


def test_fix_proposal_agent_keeps_scoped_write_permission_and_prompt() -> None:
    assert FIX_PROPOSAL_AGENT.harness is Harness.DISCORD
    assert FIX_PROPOSAL_AGENT.permissions == frozenset({P.GITHUB_READ, P.GITHUB_WRITE})
    prompt = load_system_prompt(FIX_PROPOSAL_AGENT)
    assert prompt is not None
    for required in ("create_fix_pr", "unified diff", "Never use a shell", "do not grant extra permissions"):
        assert required in prompt
