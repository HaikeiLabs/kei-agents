"""Provider-neutral read tool schemas for the governed http_api/CRM connector.

Read capabilities are scoped to the governed http_api connection preset
(delegated context); agents can never target arbitrary endpoints or supply
URLs/credentials. Execution is delegated to the tenant-side distributed proxy
- these schemas declare no handlers.
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

HTTP_API_READ_TOOL_DEFINITIONS: list[ToolDefinition] = [
    ToolDefinition(
        name="http_api.list_records",
        source="http_api",
        operation_class="read",
        description="List records of an entity through the governed http_api/CRM connection",
        parameters=[
            ToolParameter(
                name="entity",
                description="Entity to list (e.g. leads); defaults to the bound entity",
                required=False,
                default="leads",
            ),
            ToolParameter(
                name="filters",
                description="Query-style filters applied within the governed connection",
                required=False,
            ),
            ToolParameter(
                name="limit",
                description="Maximum number of records to return",
                type="integer",
                required=False,
                default=100,
            ),
            ToolParameter(
                name="offset",
                description="Number of records to skip",
                type="integer",
                required=False,
                default=0,
            ),
        ],
        permission=Permission.HTTP_API_READ,
        category=ToolCategory.HTTP_API,
        service="http_api",
        tags=["http-read", "governed-connector", "crm-read"],
        binding=ToolBinding(
            operation=ConnectorOperationDescriptor(operation_class="read", required_capabilities=("http.get",), resource_types=(ResourceTypeDescriptor(type="record"),)),
            connector_id="conn_http_api_1",
            config={"resource": "records", "api": "crm"},
            delegated_context=["tenant_id"],
        ),
    ),
    ToolDefinition(
        name="http_api.get_record",
        source="http_api",
        operation_class="read",
        description="Read a single record through the governed http_api/CRM connection",
        parameters=[
            ToolParameter(
                name="entity",
                description="Entity the record belongs to (e.g. leads)",
                required=False,
                default="leads",
            ),
            ToolParameter(
                name="record_id",
                description="Record identifier within the governed connection",
                required=True,
            ),
        ],
        permission=Permission.HTTP_API_READ,
        category=ToolCategory.HTTP_API,
        service="http_api",
        tags=["http-read", "governed-connector", "crm-read"],
        binding=ToolBinding(
            operation=ConnectorOperationDescriptor(operation_class="read", required_capabilities=("http.get",), resource_types=(ResourceTypeDescriptor(type="record"),)),
            connector_id="conn_http_api_1",
            config={"resource": "records", "api": "crm"},
            delegated_context=["tenant_id"],
        ),
    ),
]

__all__ = ["HTTP_API_READ_TOOL_DEFINITIONS"]
