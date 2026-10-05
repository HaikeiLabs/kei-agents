"""Provider-neutral read tool schemas for the governed Notion connector.

Read capabilities are scoped to the Notion workspace bound in the governed
connection preset (delegated context); agents can never target arbitrary
workspaces or supply URLs/credentials.  Execution is delegated to the
tenant-side distributed proxy -- these schemas declare no handlers.
"""

from __future__ import annotations

from agents.tool_definitions import (
    ConnectorOperationDescriptor,
    Permission,
    ResourceTypeDescriptor,
    ToolBinding,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
)

NOTION_READ_TOOL_DEFINITIONS: list[ToolDefinition] = [
    ToolDefinition(
        name="notion.list_pages",
        source="notion",
        operation_class="read",
        description=("Search or list pages in the governed Notion workspace"),
        parameters=[
            ToolParameter(
                name="query",
                description="Search query applied within the governed workspace",
                required=False,
            ),
            ToolParameter(
                name="limit",
                description="Maximum number of pages to return",
                type="integer",
                required=False,
                default=50,
            ),
        ],
        permission=Permission.NOTION_READ,
        category=ToolCategory.NOTION,
        service="notion",
        tags=["notion-read", "governed-connector"],
        binding=ToolBinding(
            operation=ConnectorOperationDescriptor(operation_class="read", required_capabilities=("search",), resource_types=(ResourceTypeDescriptor(type="page", parent_type="workspace"),)),
            connector_id="conn_notion_1",
            config={"resource": "pages"},
            delegated_context=["tenant_id", "workspace"],
        ),
    ),
    ToolDefinition(
        name="notion.get_page",
        source="notion",
        operation_class="read",
        description="Read a single page from the governed Notion workspace",
        parameters=[
            ToolParameter(
                name="page_id",
                description="Page identifier within the governed workspace",
                required=True,
            ),
        ],
        permission=Permission.NOTION_READ,
        category=ToolCategory.NOTION,
        service="notion",
        tags=["notion-read", "governed-connector"],
        binding=ToolBinding(
            operation=ConnectorOperationDescriptor(operation_class="read", required_capabilities=("page.read",), resource_types=(ResourceTypeDescriptor(type="page", parent_type="workspace"),)),
            connector_id="conn_notion_1",
            config={"resource": "pages"},
            delegated_context=["tenant_id", "workspace"],
        ),
    ),
    ToolDefinition(
        name="notion.list_databases",
        source="notion",
        operation_class="read",
        description="List databases in the governed Notion workspace",
        parameters=[
            ToolParameter(
                name="limit",
                description="Maximum number of databases to return",
                type="integer",
                required=False,
                default=50,
            ),
        ],
        permission=Permission.NOTION_READ,
        category=ToolCategory.NOTION,
        service="notion",
        tags=["notion-read", "governed-connector"],
        binding=ToolBinding(
            operation=ConnectorOperationDescriptor(operation_class="read", required_capabilities=("database.query",), resource_types=(ResourceTypeDescriptor(type="database", parent_type="workspace"),)),
            connector_id="conn_notion_1",
            config={"resource": "databases"},
            delegated_context=["tenant_id", "workspace"],
        ),
    ),
    ToolDefinition(
        name="notion.get_database",
        source="notion",
        operation_class="read",
        description="Read a single database from the governed Notion workspace",
        parameters=[
            ToolParameter(
                name="database_id",
                description="Database identifier within the governed workspace",
                required=True,
            ),
        ],
        permission=Permission.NOTION_READ,
        category=ToolCategory.NOTION,
        service="notion",
        tags=["notion-read", "governed-connector"],
        binding=ToolBinding(
            operation=ConnectorOperationDescriptor(operation_class="read", required_capabilities=("database.query",), resource_types=(ResourceTypeDescriptor(type="database", parent_type="workspace"),)),
            connector_id="conn_notion_1",
            config={"resource": "databases"},
            delegated_context=["tenant_id", "workspace"],
        ),
    ),
]

__all__ = ["NOTION_READ_TOOL_DEFINITIONS"]
