"""Typed tool-manifest v3 generation for Kei runtime registration."""

from __future__ import annotations

from typing import Any

from agents.tool_definitions import ToolDefinition

TOOL_MANIFEST_SCHEMA_V3 = "kei.tool-manifest/v3"


def render_tool_manifest(tools: list[ToolDefinition]) -> dict[str, Any]:
    """Render v3 routes from explicit operation or harness registrations.

    A binding takes precedence over a handler/registration. Connector
    capabilities and resource kinds are never inferred from permissions or
    binding config.
    """
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for tool in tools:
        if tool.name in seen:
            raise ValueError(f"duplicate tool name: {tool.name}")
        seen.add(tool.name)
        if not tool.source or tool.operation_class not in {"read", "write"}:
            raise ValueError(f"{tool.name}: source and operation_class are required")
        entry: dict[str, Any] = {
            "name": tool.name,
            "source": tool.source,
            "operation_class": tool.operation_class,
            "description": tool.description,
        }
        if tool.binding is not None:
            operation = tool.operation or tool.binding.operation
            if not tool.binding.connector_id or operation is None:
                raise ValueError(f"{tool.name}: connector route requires an explicit binding and operation")
            if not operation.required_capabilities or any(not cap for cap in operation.required_capabilities):
                raise ValueError(f"{tool.name}: connector operation requires non-empty capabilities")
            if len(set(operation.required_capabilities)) != len(operation.required_capabilities):
                raise ValueError(f"{tool.name}: duplicate required capability")
            if any(not resource.type or resource.parent_type == "" for resource in operation.resource_types):
                raise ValueError(f"{tool.name}: invalid resource type descriptor")
            if operation.operation_class != tool.operation_class:
                raise ValueError(f"{tool.name}: operation_class metadata mismatch")
            entry["route"] = {"connector_binding": {"connector_id": tool.binding.connector_id}}
            entry["required_capabilities"] = list(operation.required_capabilities)
            if operation.resource_types:
                entry["resource_types"] = [
                    {"type": resource.type, **({"parent_type": resource.parent_type} if resource.parent_type else {})}
                    for resource in operation.resource_types
                ]
        elif tool.harness_registration is not None:
            if tool.operation is not None:
                raise ValueError(f"{tool.name}: harness route cannot carry connector operation metadata")
            if not tool.harness_registration.executor or not tool.harness_registration.registration:
                raise ValueError(f"{tool.name}: incomplete harness_executor registration")
            entry["route"] = {"harness_executor": {
                "executor": tool.harness_registration.executor,
                "registration": tool.harness_registration.registration,
            }}
        else:
            raise ValueError(f"{tool.name}: no registered route")
        entries.append(entry)
    return {"schema": TOOL_MANIFEST_SCHEMA_V3, "tools": entries}
