"""Provider-neutral read tool schemas for the governed Gmail connector.

Read capabilities are scoped to the mailbox bound in the governed connection
preset (delegated context); agents can never target arbitrary mailboxes or
supply URLs/credentials. Results are message metadata and snippet only; the
full body is released only when ABAC authorizes the ``gmail_include_body``
policy attribute, so it is never an agent parameter. Execution is delegated
to the tenant-side distributed proxy - these schemas declare no handlers.

Tool names map to the kei-policy-catalog ``gmail`` provider capabilities:
``gmail.search_messages`` -> ``message.search``, ``gmail.get_message`` ->
``message.get``.
"""

from __future__ import annotations

from agents.tool_definitions import (
    Permission,
    ToolBinding,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
)

GMAIL_READ_TOOL_DEFINITIONS: list[ToolDefinition] = [
    ToolDefinition(
        name="gmail.search_messages",
        description=(
            "Search messages in the governed mailbox; returns metadata and snippet only"
        ),
        parameters=[
            ToolParameter(
                name="query",
                description="Gmail search query applied within the governed mailbox",
                required=False,
            ),
            ToolParameter(
                name="page_size",
                description="Maximum number of messages to return",
                type="integer",
                required=False,
                default=25,
            ),
            ToolParameter(
                name="page_token",
                description="Opaque cursor from a previous search result page",
                required=False,
            ),
        ],
        permission=Permission.GMAIL_READ,
        category=ToolCategory.GMAIL,
        service="gmail",
        tags=["gmail-read", "governed-connector"],
        binding=ToolBinding(
            connector_id="conn_gmail_1",
            config={"resource": "messages"},
            delegated_context=["tenant_id", "mailbox"],
        ),
    ),
    ToolDefinition(
        name="gmail.get_message",
        description=(
            "Read a single message's metadata and snippet from the governed mailbox"
        ),
        parameters=[
            ToolParameter(
                name="message_id",
                description="Message identifier within the governed mailbox",
                required=True,
            ),
        ],
        permission=Permission.GMAIL_READ,
        category=ToolCategory.GMAIL,
        service="gmail",
        tags=["gmail-read", "governed-connector"],
        binding=ToolBinding(
            connector_id="conn_gmail_1",
            config={"resource": "messages"},
            delegated_context=["tenant_id", "mailbox"],
        ),
    ),
]

__all__ = ["GMAIL_READ_TOOL_DEFINITIONS"]
