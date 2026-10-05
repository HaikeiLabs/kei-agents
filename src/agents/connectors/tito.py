"""Provider-neutral read tool schemas for the governed Tito connector.

Read capabilities are scoped to the Tito account bound in the governed
connection preset (delegated context); agents can never target arbitrary
accounts or supply URLs/credentials. Attendee PII (names, emails) is never
returned; ticket data is aggregate counts only. Execution is delegated to the
tenant-side distributed proxy - these schemas declare no handlers.

Tool names map to the kei-policy-catalog ``tito`` provider capabilities:
``tito.list_events`` -> ``event.list``, ``tito.get_event`` -> ``event.get``,
``tito.list_releases`` -> ``release.list``, ``tito.get_ticket_summary`` ->
``ticket.summary``.
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

_EVENT_ID = ToolParameter(
    name="event_id",
    description="Event identifier within the governed Tito account",
    required=True,
)


def _binding(resource: str, capability: str, resource_type: str) -> ToolBinding:
    return ToolBinding(
        connector_id="conn_tito_1",
        operation=ConnectorOperationDescriptor(operation_class="read", required_capabilities=(capability,), resource_types=(ResourceTypeDescriptor(type=resource_type, parent_type="account"),)),
        config={"resource": resource},
        delegated_context=["tenant_id", "account"],
    )


TITO_READ_TOOL_DEFINITIONS: list[ToolDefinition] = [
    ToolDefinition(
        name="tito.list_events",
        source="tito",
        operation_class="read",
        description="List events in the governed Tito account",
        parameters=[],
        permission=Permission.TITO_READ,
        category=ToolCategory.TITO,
        service="tito",
        tags=["tito-read", "governed-connector"],
        binding=_binding("events", "event.list", "event"),
    ),
    ToolDefinition(
        name="tito.get_event",
        source="tito",
        operation_class="read",
        description="Read a single event in the governed Tito account",
        parameters=[_EVENT_ID],
        permission=Permission.TITO_READ,
        category=ToolCategory.TITO,
        service="tito",
        tags=["tito-read", "governed-connector"],
        binding=_binding("events", "event.get", "event"),
    ),
    ToolDefinition(
        name="tito.list_releases",
        source="tito",
        operation_class="read",
        description="List ticket releases for an event in the governed Tito account",
        parameters=[_EVENT_ID],
        permission=Permission.TITO_READ,
        category=ToolCategory.TITO,
        service="tito",
        tags=["tito-read", "governed-connector"],
        binding=_binding("releases", "release.list", "release"),
    ),
    ToolDefinition(
        name="tito.get_ticket_summary",
        source="tito",
        operation_class="read",
        description=(
            "Read aggregate ticket counts by state and type for an event; "
            "no attendee data"
        ),
        parameters=[_EVENT_ID],
        permission=Permission.TITO_READ,
        category=ToolCategory.TITO,
        service="tito",
        tags=["tito-read", "governed-connector"],
        binding=_binding("tickets", "ticket.summary", "ticket"),
    ),
]

__all__ = ["TITO_READ_TOOL_DEFINITIONS"]
