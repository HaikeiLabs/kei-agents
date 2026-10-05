from agents import (
    ConnectorOperationDescriptor,
    HarnessExecutorRegistration,
    ResourceTypeDescriptor,
    ToolBinding,
    ToolDefinition,
    render_tool_manifest,
)


def test_v3_manifest_emits_exactly_one_typed_route_branch() -> None:
    connector = ToolDefinition(
        name="github.get_issue",
        description="Read issue",
        service="github",
        source="github",
        operation_class="read",
        binding=ToolBinding(
            connector_id="binding-1",
            operation=ConnectorOperationDescriptor(
                required_capabilities=("issue.read",),
                resource_types=(ResourceTypeDescriptor("issue", "repository"),),
                operation_class="read",
            ),
        ),
        # Binding must win even if a harness handler/registration also exists.
        handler=lambda: None,
        harness_registration=HarnessExecutorRegistration("codex", "codex.shell"),
    )
    native = ToolDefinition(
        name="codex.shell",
        description="Run shell",
        source="codex",
        operation_class="write",
        harness_registration=HarnessExecutorRegistration("codex", "codex.shell"),
    )
    manifest = render_tool_manifest([connector, native])
    assert manifest["schema"] == "kei.tool-manifest/v3"
    assert manifest["tools"][0] == {
        "name": "github.get_issue",
        "source": "github",
        "operation_class": "read",
        "description": "Read issue",
        "route": {"connector_binding": {"connector_id": "binding-1"}},
        "required_capabilities": ["issue.read"],
        "resource_types": [{"type": "issue", "parent_type": "repository"}],
    }
    assert manifest["tools"][1] == {
        "name": "codex.shell",
        "source": "codex",
        "operation_class": "write",
        "description": "Run shell",
        "route": {"harness_executor": {"executor": "codex", "registration": "codex.shell"}},
    }


def test_resource_less_connector_descriptor_omits_resource_types() -> None:
    tool = ToolDefinition(
        name="http_api.health",
        description="Check service health",
        source="http_api",
        operation_class="read",
        binding=ToolBinding(
            connector_id="binding-2",
            operation=ConnectorOperationDescriptor(
                required_capabilities=("http.head",),
                resource_types=(),
                operation_class="read",
            ),
        ),
    )
    entry = render_tool_manifest([tool])["tools"][0]
    assert entry["required_capabilities"] == ["http.head"]
    assert "resource_types" not in entry


def test_v3_manifest_fails_closed_without_explicit_capability_metadata() -> None:
    tool = ToolDefinition(
        name="github.get_issue",
        description="Read issue",
        source="github",
        operation_class="read",
        binding=ToolBinding(connector_id="binding-1"),
    )
    try:
        render_tool_manifest([tool])
    except ValueError as exc:
        assert "explicit binding and operation" in str(exc)
    else:
        raise AssertionError("expected missing operation descriptor to fail closed")
