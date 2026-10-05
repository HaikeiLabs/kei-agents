"""Provider-neutral read tool schemas for the governed S3 connector.

Read capabilities are scoped to the bucket bound in the governed connection
preset (delegated context); agents can never target arbitrary buckets or supply
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

S3_READ_TOOL_DEFINITIONS: list[ToolDefinition] = [
    ToolDefinition(
        name="s3.list_objects",
        source="s3",
        operation_class="read",
        description="List objects in the governed bucket",
        parameters=[
            ToolParameter(
                name="prefix",
                description="Only list objects whose keys start with this prefix",
                required=False,
            ),
            ToolParameter(
                name="delimiter",
                description="Group keys by a delimiter (folder-style listing)",
                required=False,
            ),
            ToolParameter(
                name="max_keys",
                description="Maximum number of object keys to return",
                type="integer",
                required=False,
                default=1000,
            ),
        ],
        permission=Permission.S3_READ,
        category=ToolCategory.S3,
        service="s3",
        tags=["s3-read", "governed-connector"],
        binding=ToolBinding(
            operation=ConnectorOperationDescriptor(operation_class="read", required_capabilities=("object.list",), resource_types=(ResourceTypeDescriptor(type="object", parent_type="bucket"),)),
            connector_id="conn_s3_1",
            config={"resource": "objects"},
            delegated_context=["tenant_id", "bucket"],
        ),
    ),
    ToolDefinition(
        name="s3.get_object",
        source="s3",
        operation_class="read",
        description="Read an object from the governed bucket",
        parameters=[
            ToolParameter(
                name="key",
                description="Object key within the governed bucket",
                required=True,
            ),
            ToolParameter(
                name="version_id",
                description="Optional object version to read",
                required=False,
            ),
        ],
        permission=Permission.S3_READ,
        category=ToolCategory.S3,
        service="s3",
        tags=["s3-read", "governed-connector"],
        binding=ToolBinding(
            operation=ConnectorOperationDescriptor(operation_class="read", required_capabilities=("object.read",), resource_types=(ResourceTypeDescriptor(type="object", parent_type="bucket"),)),
            connector_id="conn_s3_1",
            config={"resource": "objects"},
            delegated_context=["tenant_id", "bucket"],
        ),
    ),
    ToolDefinition(
        name="s3.get_object_metadata",
        source="s3",
        operation_class="read",
        description="Read metadata for an object in the governed bucket without its body",
        parameters=[
            ToolParameter(
                name="key",
                description="Object key within the governed bucket",
                required=True,
            ),
        ],
        permission=Permission.S3_READ,
        category=ToolCategory.S3,
        service="s3",
        tags=["s3-read", "governed-connector"],
        binding=ToolBinding(
            operation=ConnectorOperationDescriptor(operation_class="read", required_capabilities=("object.read",), resource_types=(ResourceTypeDescriptor(type="object", parent_type="bucket"),)),
            connector_id="conn_s3_1",
            config={"resource": "objects"},
            delegated_context=["tenant_id", "bucket"],
        ),
    ),
]

__all__ = ["S3_READ_TOOL_DEFINITIONS"]
