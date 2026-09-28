"""Tests for provider-neutral read tool schemas for governed connectors."""

from __future__ import annotations

from agents import (
    ALL_TOOL_DEFINITIONS,
    CONNECTOR_READ_TOOL_DEFINITIONS,
    Permission,
    ToolBinding,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
    get_tool_by_name,
    get_tools_by_permission,
    validate_tool_definitions,
)

CONNECTOR_NAMES = {
    "github.get_repository",
    "github.get_issue",
    "github.get_pull_request",
    "linear.list_issues",
    "linear.get_issue",
    "linear.list_projects",
    "drive.list_files",
    "drive.get_file",
    "docs.get_document",
    "s3.list_objects",
    "s3.get_object",
    "s3.get_object_metadata",
    "http_api.list_records",
    "http_api.get_record",
    "notion.list_pages",
    "notion.get_page",
    "notion.list_databases",
    "notion.get_database",
    "gmail.search_messages",
    "gmail.get_message",
    "tito.list_events",
    "tito.get_event",
    "tito.list_releases",
    "tito.get_ticket_summary",
}

READ_PERMISSIONS = {
    Permission.GITHUB_READ,
    Permission.LINEAR_READ,
    Permission.DRIVE_READ,
    Permission.S3_READ,
    Permission.HTTP_API_READ,
    Permission.NOTION_READ,
    Permission.GMAIL_READ,
    Permission.TITO_READ,
}

CATEGORIES = {
    ToolCategory.GITHUB,
    ToolCategory.LINEAR,
    ToolCategory.DRIVE,
    ToolCategory.S3,
    ToolCategory.HTTP_API,
    ToolCategory.NOTION,
    ToolCategory.GMAIL,
    ToolCategory.TITO,
}


def _param_names(tool: ToolDefinition) -> set[str]:
    params = tool.parameters
    if isinstance(params, dict):
        return set(params.get("properties", {}).keys())
    return {param.name for param in params or []}


class TestConnectorReadCatalog:
    def test_catalog_is_schema_only(self):
        names = {tool.name for tool in CONNECTOR_READ_TOOL_DEFINITIONS}
        assert names == CONNECTOR_NAMES
        assert len(CONNECTOR_READ_TOOL_DEFINITIONS) == len(CONNECTOR_NAMES)

    def test_catalog_validates(self):
        assert validate_tool_definitions(CONNECTOR_READ_TOOL_DEFINITIONS) == []

    def test_all_tools_include_connector_reads(self):
        merged = {tool.name for tool in ALL_TOOL_DEFINITIONS}
        assert CONNECTOR_NAMES <= merged

    def test_connector_reads_are_bound_and_handlerless(self):
        for tool in CONNECTOR_READ_TOOL_DEFINITIONS:
            assert tool.binding is not None
            assert tool.binding.connector_id
            assert tool.handler is None

    def test_connector_reads_use_read_permissions_and_categories(self):
        for tool in CONNECTOR_READ_TOOL_DEFINITIONS:
            assert tool.permission in READ_PERMISSIONS
            assert tool.category in CATEGORIES
            assert tool.service

    def test_each_connector_declares_delegated_context(self):
        for tool in CONNECTOR_READ_TOOL_DEFINITIONS:
            assert tool.binding is not None
            assert "tenant_id" in tool.binding.delegated_context

    def test_no_param_collides_with_delegated_context(self):
        for tool in CONNECTOR_READ_TOOL_DEFINITIONS:
            delegated = set(tool.binding.delegated_context) if tool.binding else set()
            assert delegated.isdisjoint(_param_names(tool))

    def test_no_secrets_or_urls_in_bindings(self):
        for tool in CONNECTOR_READ_TOOL_DEFINITIONS:
            assert tool.binding is not None
            for key, value in tool.binding.config.items():
                assert "token" not in key.lower()
                assert "secret" not in key.lower()
                assert "key" not in key.lower()
                assert "password" not in key.lower()
                if isinstance(value, str):
                    assert "://" not in value

    def test_permission_lookup_returns_new_reads(self):
        names = {tool.name for tool in get_tools_by_permission(Permission.LINEAR_READ)}
        assert {
            "linear.list_issues",
            "linear.get_issue",
            "linear.list_projects",
        } <= names

    def test_all_connector_reads_found_by_name(self):
        for name in CONNECTOR_NAMES:
            assert get_tool_by_name(name) is not None, name


class TestConnectorSchemaValidation:
    def test_delegated_context_collision_flagged(self):
        tool = ToolDefinition(
            name="s3.bad",
            description="a",
            permission=Permission.S3_READ,
            category=ToolCategory.S3,
            service="s3",
            parameters=[ToolParameter(name="bucket", description="b", required=True)],
            binding=ToolBinding(
                connector_id="conn_s3_1",
                config={"resource": "objects"},
                delegated_context=["tenant_id", "bucket"],
            ),
        )
        assert any("delegated context" in v for v in validate_tool_definitions([tool]))

    def test_tenant_identifier_param_flagged_for_connector_read(self):
        tool = ToolDefinition(
            name="http_api.bad",
            description="a",
            permission=Permission.HTTP_API_READ,
            category=ToolCategory.HTTP_API,
            service="http_api",
            parameters=[
                ToolParameter(name="tenant_id", description="t", required=True)
            ],
            binding=ToolBinding(connector_id="conn_1", delegated_context=["tenant_id"]),
        )
        assert any("tenant identifier" in v for v in validate_tool_definitions([tool]))

    def test_handler_on_connector_read_flagged(self):
        def handler() -> dict[str, object]:
            return {}

        tool = ToolDefinition(
            name="linear.bad",
            description="a",
            permission=Permission.LINEAR_READ,
            category=ToolCategory.LINEAR,
            service="linear",
            binding=ToolBinding(
                connector_id="conn_1",
                delegated_context=["tenant_id", "workspace"],
            ),
            handler=handler,
        )
        assert any("handler" in v for v in validate_tool_definitions([tool]))

    def test_missing_service_on_connector_read_flagged(self):
        tool = ToolDefinition(
            name="s3.bad",
            description="a",
            permission=Permission.S3_READ,
            category=ToolCategory.S3,
            binding=ToolBinding(
                connector_id="conn_1", delegated_context=["tenant_id", "bucket"]
            ),
        )
        assert any(
            "must declare a service" in v for v in validate_tool_definitions([tool])
        )

    def test_url_in_binding_config_flagged(self):
        tool = ToolDefinition(
            name="http_api.url",
            description="a",
            permission=Permission.HTTP_API_READ,
            category=ToolCategory.HTTP_API,
            service="http_api",
            binding=ToolBinding(
                connector_id="conn_1",
                config={"resource": "records", "base_url": "https://api.example.com"},
                delegated_context=["tenant_id"],
            ),
        )
        assert any(
            "endpoint" in v or "URL" in v for v in validate_tool_definitions([tool])
        )

    def test_delegated_context_secret_name_flagged(self):
        tool = ToolDefinition(
            name="s3.bad",
            description="a",
            permission=Permission.S3_READ,
            category=ToolCategory.S3,
            service="s3",
            binding=ToolBinding(connector_id="conn_1", delegated_context=["api_key"]),
        )
        assert any("secret" in v for v in validate_tool_definitions([tool]))
