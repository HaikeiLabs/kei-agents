"""Google Drive doc write action tools (harness-side, confirm-required).

These are agent action tools gated by ``Permission.DRIVE_WRITE``, not
governed connector capabilities: they carry no binding, and the harness runs
them with the user's own OAuth token (see :mod:`agents.drive_write`).
Semantics rule: a new doc carries its parent ``folder_id``; the Drive itself
is never an argument.
"""

from __future__ import annotations

from agents.drive_write import CREATE_DOC_TOOL, UPDATE_DOC_TOOL
from agents.tool_definitions import (
    Permission,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
)

_CONFIRM_NOTE = (
    " The user sees a preview and must confirm it before anything is written,"
    " so call it once with the full content and never claim the doc was"
    " written until the result says so."
)
_MARKDOWN = ToolParameter(
    name="markdown",
    description="Full document content in Markdown; Drive converts it to a Google Doc",
    required=True,
)

DRIVE_CREATE_DOC_TOOL = ToolDefinition(
    name=CREATE_DOC_TOOL,
    description=(
        "Create a new Google Doc from Markdown inside a Drive folder. Use when"
        " the user asks to publish, upload, or save a document to a Drive"
        " folder and gives the folder id." + _CONFIRM_NOTE
    ),
    parameters=[
        ToolParameter(
            name="folder_id",
            description="Id of the parent Drive folder the new doc goes in",
            required=True,
        ),
        ToolParameter(name="title", description="Document title", required=True),
        _MARKDOWN,
    ],
    permission=Permission.DRIVE_WRITE,
    category=ToolCategory.DRIVE,
    service="drive",
    tags=["drive-write", "governed-action", "confirm-required", "harness-side"],
)

DRIVE_UPDATE_DOC_TOOL = ToolDefinition(
    name=UPDATE_DOC_TOOL,
    description=(
        "Replace the content of an existing Google Doc with Markdown. Use when"
        " the user asks to update, overwrite, or republish a doc and gives the"
        " doc id." + _CONFIRM_NOTE
    ),
    parameters=[
        ToolParameter(
            name="doc_id",
            description="Id of the Google Doc to replace",
            required=True,
        ),
        _MARKDOWN,
    ],
    permission=Permission.DRIVE_WRITE,
    category=ToolCategory.DRIVE,
    service="drive",
    tags=["drive-write", "governed-action", "confirm-required", "harness-side"],
)

DRIVE_WRITE_TOOL_DEFINITIONS: list[ToolDefinition] = [
    DRIVE_CREATE_DOC_TOOL,
    DRIVE_UPDATE_DOC_TOOL,
]

__all__ = [
    "DRIVE_CREATE_DOC_TOOL",
    "DRIVE_UPDATE_DOC_TOOL",
    "DRIVE_WRITE_TOOL_DEFINITIONS",
]
