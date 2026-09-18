"""Semantic action schema for creating a governed Linear follow-up task.

This is intentionally handlerless. The Discord harness translates the action
to a tenant-side proxy invocation; it never resolves credentials or calls
Linear directly.
"""

from __future__ import annotations

from agents.tool_definitions import (
    Permission,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
)

LINEAR_CREATE_FOLLOWUP_TOOL = ToolDefinition(
    name="linear.create_followup_task",
    description="Create a Linear follow-up task from an approved, redacted CRM projection",
    parameters=[
        ToolParameter(name="lead_id", description="Governed CRM lead identifier", required=True),
        ToolParameter(name="title", description="Follow-up task title", required=True),
        ToolParameter(name="summary", description="Redacted CRM context approved for sharing", required=True),
        ToolParameter(name="approval_id", description="Approval reference for the write", required=False),
        ToolParameter(name="idempotency_key", description="Stable replay key for this task creation", required=True),
    ],
    permission=Permission.LINEAR_WRITE,
    category=ToolCategory.LINEAR,
    service="linear",
    tags=["linear-write", "crm-followup", "governed-action", "harness-neutral"],
)

CRM_LINEAR_FOLLOWUP_TOOL_DEFINITIONS: list[ToolDefinition] = [
    LINEAR_CREATE_FOLLOWUP_TOOL
]

__all__ = ["CRM_LINEAR_FOLLOWUP_TOOL_DEFINITIONS", "LINEAR_CREATE_FOLLOWUP_TOOL"]
