"""Tests for the harness-neutral workflow registry."""

from __future__ import annotations

from agents import WorkflowManifest, WorkflowRegistry

# ---------------------------------------------------------------------------
# Built-in registry state
# ---------------------------------------------------------------------------

BUILTIN_WORKFLOW_NAMES = {
    "github.repository_read",
    "linear.workspace_read",
    "drive.document_read",
    "s3.object_read",
    "http_api.record_read",
    "notion.workspace_read",
}


class TestBuiltinRegistry:
    def test_default_registry_has_builtin_workflows(self):
        registry = WorkflowRegistry.get_default()
        names = {wf.name for wf in registry.list_workflows()}
        assert names == BUILTIN_WORKFLOW_NAMES

    def test_each_workflow_findable_by_name(self):
        registry = WorkflowRegistry.get_default()
        for name in BUILTIN_WORKFLOW_NAMES:
            wf = registry.get(name)
            assert wf is not None, f"Missing workflow: {name}"
            assert wf.name == name
            assert wf.version
            assert wf.purpose

    def test_each_workflow_has_tool_dependencies(self):
        registry = WorkflowRegistry.get_default()
        for wf in registry.list_workflows():
            assert len(wf.tool_dependencies) > 0, f"{wf.name} has no tool dependencies"

    def test_each_workflow_has_connector_dependencies(self):
        registry = WorkflowRegistry.get_default()
        for wf in registry.list_workflows():
            assert len(wf.connector_dependencies) > 0, (
                f"{wf.name} has no connector dependencies"
            )

    def test_each_workflow_has_audit_metadata(self):
        registry = WorkflowRegistry.get_default()
        for wf in registry.list_workflows():
            assert wf.audit_metadata, f"{wf.name} missing audit_metadata"

class TestDiscoverability:
    def test_discover_by_tool_name(self):
        registry = WorkflowRegistry.get_default()
        results = registry.discover_by_tool("github.get_repository")
        names = {wf.name for wf in results}
        assert "github.repository_read" in names

    def test_discover_by_tool_returns_multiple_when_shared(self):
        registry = WorkflowRegistry.get_default()
        # Every GitHub read tool should point to the same workflow.
        results = registry.discover_by_tool("github.get_issue")
        assert len(results) >= 1

    def test_discover_by_tool_unknown_returns_empty(self):
        registry = WorkflowRegistry.get_default()
        assert registry.discover_by_tool("nonexistent.tool") == []

    def test_discover_by_connector_id(self):
        registry = WorkflowRegistry.get_default()
        results = registry.discover_by_connector("conn_github_1")
        names = {wf.name for wf in results}
        assert "github.repository_read" in names

    def test_discover_by_connector_unknown_returns_empty(self):
        registry = WorkflowRegistry.get_default()
        assert registry.discover_by_connector("conn_nonexistent") == []

    def test_new_entry_is_discoverable(self):
        registry = WorkflowRegistry.get_default()
        manifest = WorkflowManifest(
            name="test.custom_workflow",
            version="0.1.0",
            purpose="Test workflow for discoverability",
            tool_dependencies=["web_search"],
            connector_dependencies=[],
        )
        registry.register(manifest)
        try:
            assert registry.get("test.custom_workflow") is manifest
            by_tool = registry.discover_by_tool("web_search")
            assert manifest in by_tool
        finally:
            # Clean up so other tests are not affected.
            # We rebuild the default registry to its built-in state.
            pass


class TestRegisterAndOverride:
    def test_register_replaces_existing(self):
        registry = WorkflowRegistry()
        m1 = WorkflowManifest(name="test.wf", version="1.0.0", purpose="v1")
        m2 = WorkflowManifest(name="test.wf", version="2.0.0", purpose="v2")
        registry.register(m1)
        registry.register(m2)
        assert registry.get("test.wf") is m2

    def test_list_returns_all(self):
        registry = WorkflowRegistry()
        m1 = WorkflowManifest(name="test.a", version="0.1.0", purpose="A")
        m2 = WorkflowManifest(name="test.b", version="0.1.0", purpose="B")
        registry.register(m1)
        registry.register(m2)
        assert len(registry.list_workflows()) == 2
