import agents
from agents import GITHUB_FIX_ACTION_TOOL, HARNESS_AGENT_DEFINITIONS, Permission
from agents.policy import AuthorizationResult, PermissionContext, PolicyEngine


def test_fix_action_matches_original_contract_and_stays_opt_in() -> None:
    tool = GITHUB_FIX_ACTION_TOOL
    assert tool["name"] == "github.create_fix_pr"
    assert tool["description"] == (
        "Propose a pull-request fix for the server-selected repository and branch. "
        "Provide a concise title, a PR description, and a unified diff of at most "
        "32 KiB. The server controls the target repository, branch, and draft status."
    )
    assert tool["permission"] is Permission.GITHUB_WRITE
    schema = tool["parameters"]
    assert set(schema["properties"]) == {"title", "body", "unified_diff"}
    assert schema["required"] == ["title", "body", "unified_diff"]
    assert schema["additionalProperties"] is False
    assert "32 KiB" in schema["properties"]["unified_diff"]["description"]
    assert not hasattr(agents, "TOOL_DEFINITIONS")
    assert not hasattr(agents, "ALL_TOOL_DEFINITIONS")
    assert all(not hasattr(agent, "tools") for agent in HARNESS_AGENT_DEFINITIONS)
    engine = PolicyEngine()
    denied = engine.evaluate(
        GITHUB_FIX_ACTION_TOOL["name"],
        GITHUB_FIX_ACTION_TOOL["permission"],
        PermissionContext(user_id="u1"),
    )
    allowed = engine.evaluate(
        GITHUB_FIX_ACTION_TOOL["name"],
        GITHUB_FIX_ACTION_TOOL["permission"],
        PermissionContext(user_id="u1", permissions={Permission.GITHUB_WRITE}),
    )
    assert denied.result is AuthorizationResult.DENY
    assert allowed.result is AuthorizationResult.ALLOW
