from agents.permissions import Permission
from agents.policy import (
    AuthorizationResult,
    PermissionContext,
    PolicyDecision,
    PolicyEngine,
    filter_accessible_tools,
)


def test_policy_evaluates_runtime_tool_name_and_permission():
    engine = PolicyEngine()
    context = PermissionContext(user_id="u1", permissions={Permission.DRIVE_READ})

    assert (
        engine.evaluate("drive.list_files", Permission.DRIVE_READ, context).result
        is AuthorizationResult.ALLOW
    )
    denied = engine.evaluate("drive.delete_file", Permission.DRIVE_WRITE, context)
    assert denied.result is AuthorizationResult.DENY
    assert denied.required_permission is Permission.DRIVE_WRITE


def test_filter_accessible_tools_keeps_permitted_runtime_names():
    tools = {
        "drive.list_files": Permission.DRIVE_READ,
        "drive.create_file": Permission.DRIVE_WRITE,
    }
    context = PermissionContext(user_id="u1", permissions={Permission.DRIVE_READ})

    assert filter_accessible_tools(tools, context) == {
        "drive.list_files": Permission.DRIVE_READ
    }


def test_policy_callbacks_receive_permission_metadata():
    engine = PolicyEngine()
    engine.register_policy(
        "special.tool",
        lambda permission, _: PolicyDecision(
            result=AuthorizationResult.ALLOW,
            required_permission=permission,
        ),
    )

    decision = engine.evaluate(
        "special.tool", Permission.DRIVE_READ, PermissionContext(user_id="u1")
    )
    assert decision.result is AuthorizationResult.ALLOW
    assert decision.required_permission is Permission.DRIVE_READ
