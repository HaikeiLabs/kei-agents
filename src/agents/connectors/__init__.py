"""Provider-neutral read tool schemas for governed connectors.

Schema-only agent capabilities bound to governed connectors (GitHub, Linear,
Google Drive/Docs, S3, http_api/CRM, Notion, Gmail, Tito). Each schema expresses a
capability/resource/action binding and a delegated-context contract; it never
carries provider credentials, arbitrary URLs, tenant identifiers chosen by the
agent, or provider clients/handlers. Provider execution and customer data
retrieval happen in the tenant-side distributed proxy, never in this catalog.
"""

from __future__ import annotations

from agents.connectors.drive import DRIVE_READ_TOOL_DEFINITIONS
from agents.connectors.github import GITHUB_READ_TOOL_DEFINITIONS
from agents.connectors.gmail import GMAIL_READ_TOOL_DEFINITIONS
from agents.connectors.http_api import HTTP_API_READ_TOOL_DEFINITIONS
from agents.connectors.linear import LINEAR_READ_TOOL_DEFINITIONS
from agents.connectors.notion import NOTION_READ_TOOL_DEFINITIONS
from agents.connectors.s3 import S3_READ_TOOL_DEFINITIONS
from agents.connectors.tito import TITO_READ_TOOL_DEFINITIONS
from agents.tool_definitions import ToolDefinition

CONNECTOR_READ_TOOL_DEFINITIONS: list[ToolDefinition] = [
    *GITHUB_READ_TOOL_DEFINITIONS,
    *LINEAR_READ_TOOL_DEFINITIONS,
    *DRIVE_READ_TOOL_DEFINITIONS,
    *S3_READ_TOOL_DEFINITIONS,
    *HTTP_API_READ_TOOL_DEFINITIONS,
    *NOTION_READ_TOOL_DEFINITIONS,
    *GMAIL_READ_TOOL_DEFINITIONS,
    *TITO_READ_TOOL_DEFINITIONS,
]

__all__ = [
    "CONNECTOR_READ_TOOL_DEFINITIONS",
    "DRIVE_READ_TOOL_DEFINITIONS",
    "GITHUB_READ_TOOL_DEFINITIONS",
    "GMAIL_READ_TOOL_DEFINITIONS",
    "HTTP_API_READ_TOOL_DEFINITIONS",
    "LINEAR_READ_TOOL_DEFINITIONS",
    "NOTION_READ_TOOL_DEFINITIONS",
    "S3_READ_TOOL_DEFINITIONS",
    "TITO_READ_TOOL_DEFINITIONS",
]
