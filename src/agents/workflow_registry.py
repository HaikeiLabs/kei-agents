"""Harness-neutral workflow registry and manifest abstraction.

A WorkflowManifest declares what a workflow does (name, version, purpose),
which semantic tools and governed connectors it depends on, its input/output
contract, scheduling, and audit metadata.  The
WorkflowRegistry provides registration and discovery so that workflows can be
resolved by name, by tool dependency, or by connector dependency without
coupling to any specific harness (Agentware, Discord, CLI, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agents.tool_definitions import (
    ALL_TOOL_DEFINITIONS,
    CONNECTOR_READ_TOOL_DEFINITIONS,
    ToolDefinition,
)


@dataclass
class WorkflowManifest:
    """Declarative description of a workflow and its dependencies.

    Attributes:
        name: Unique workflow identifier (``^[a-z0-9_]+(\\.[a-z0-9_]+)*$``).
        version: Semantic version of this workflow manifest.
        purpose: Human-readable description of the workflow's goal.
        tool_dependencies: Names of ToolDefinition entries this workflow
            depends on (semantic tool names, e.g. ``github.get_repository``).
        connector_dependencies: Connector IDs (from ToolBinding.connector_id)
            this workflow requires at runtime.
        input_schema: JSON Schema-like dict describing expected input
            parameters for the workflow.
        output_schema: JSON Schema-like dict describing the workflow's
            output shape.
        schedule: Optional cron expression for recurring execution.  ``None``
            means the workflow is invoked on demand only.
        audit_metadata: Free-form key/value pairs for audit trails
            (e.g. owner, change-ticket, compliance-scope).
    """

    name: str
    version: str
    purpose: str
    tool_dependencies: list[str] = field(default_factory=list)
    connector_dependencies: list[str] = field(default_factory=list)
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    schedule: str | None = None
    audit_metadata: dict[str, Any] = field(default_factory=dict)


_ORG_OR_WORKSPACE_HINTS = (
    "org_id",
    "organization_id",
    "workspace_id",
    "workspace",
)


def _has_org_or_workspace_param(params: list[dict[str, Any]] | None) -> bool:
    if not params:
        return False
    for p in params:
        name = p.get("name", "") if isinstance(p, dict) else ""
        if name in _ORG_OR_WORKSPACE_HINTS:
            return True
    return False


def _extract_tool_params(tool: ToolDefinition) -> list[dict[str, Any]]:
    if isinstance(tool.parameters, dict):
        props = tool.parameters.get("properties", {})
        required = set(tool.parameters.get("required", []))
        return [
            {
                "name": name,
                "type": schema.get("type", "string"),
                "required": name in required,
            }
            for name, schema in props.items()
        ]
    return [
        {
            "name": p.name,
            "type": p.type,
            "required": p.required,
        }
        for p in (tool.parameters or [])
    ]


class WorkflowRegistry:
    """Registry for discovering workflows by name, tool, or connector.

    Usage::

        registry = WorkflowRegistry.get_default()
        registry.register(manifest)

        all_workflows = registry.list_workflows()
        for tool_dep = registry.discover_by_tool("github.get_repository")
        for conn_dep = registry.discover_by_connector("conn_github_1")
    """

    _default_instance: WorkflowRegistry | None = None

    def __init__(self) -> None:
        self._workflows: dict[str, WorkflowManifest] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, manifest: WorkflowManifest) -> None:
        """Register a workflow manifest (replaces any existing entry with the
        same name)."""
        self._workflows[manifest.name] = manifest

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, name: str) -> WorkflowManifest | None:
        """Look up a workflow by its unique name."""
        return self._workflows.get(name)

    def list_workflows(self) -> list[WorkflowManifest]:
        """Return all registered workflow manifests."""
        return list(self._workflows.values())

    def discover_by_tool(self, tool_name: str) -> list[WorkflowManifest]:
        """Return all workflows that depend on a given semantic tool."""
        return [
            wf for wf in self._workflows.values() if tool_name in wf.tool_dependencies
        ]

    def discover_by_connector(self, connector_id: str) -> list[WorkflowManifest]:
        """Return all workflows that depend on a given governed connector."""
        return [
            wf
            for wf in self._workflows.values()
            if connector_id in wf.connector_dependencies
        ]

    def validate(self) -> list[str]:
        """Validate all registered manifests.

        Checks:
        - tool_dependencies reference known ToolDefinition names.
        - connector_dependencies reference known ToolBinding.connector_id
          values.
        - No input or output schema field is named org_id, organization_id,
          workspace_id, or workspace (org/workspace are proxy-delegated).
        """
        violations: list[str] = []

        known_tools = {t.name for t in ALL_TOOL_DEFINITIONS}
        known_connectors = {
            t.binding.connector_id
            for t in ALL_TOOL_DEFINITIONS
            if t.binding is not None
        }

        for wf in self._workflows.values():
            prefix = f"{wf.name}"
            for dep in wf.tool_dependencies:
                if dep not in known_tools:
                    violations.append(f"{prefix}: unknown tool dependency {dep!r}")
            for dep in wf.connector_dependencies:
                if dep not in known_connectors:
                    violations.append(f"{prefix}: unknown connector dependency {dep!r}")
            for field_name in list(wf.input_schema) + list(wf.output_schema):
                if field_name in _ORG_OR_WORKSPACE_HINTS:
                    violations.append(
                        f"{prefix}: schema field {field_name!r} looks like an "
                        "org/workspace identifier; org/workspace are "
                        "proxy-delegated and must not appear in workflow schemas"
                    )

        return violations

    # ------------------------------------------------------------------
    # Default singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_default(cls) -> WorkflowRegistry:
        if cls._default_instance is None:
            cls._default_instance = cls()
        return cls._default_instance

    @classmethod
    def reset_default(cls) -> None:
        cls._default_instance = None


# ---------------------------------------------------------------------------
# Built-in workflow manifests
# ---------------------------------------------------------------------------


def _register_builtin_workflows() -> WorkflowRegistry:
    """Populate the default registry with manifests for the existing governed
    connector tool schemas and add Notion / custom HTTP API entries."""

    registry = WorkflowRegistry.get_default()

    # Group connector read tools by connector_id so we can derive manifests.
    connector_tools: dict[str, list[ToolDefinition]] = {}
    for t in CONNECTOR_READ_TOOL_DEFINITIONS:
        if t.binding is not None:
            connector_tools.setdefault(t.binding.connector_id, []).append(t)

    manifest_defs: list[WorkflowManifest] = [
        # -- GitHub governed connector -----------------------------------
        WorkflowManifest(
            name="github.repository_read",
            version="0.1.0",
            purpose="Read repository metadata, issues, and pull requests "
            "from the governed GitHub connection",
            tool_dependencies=[
                "github.get_repository",
                "github.get_issue",
                "github.get_pull_request",
            ],
            connector_dependencies=["conn_github_1"],
            input_schema={
                "ref": {
                    "type": "string",
                    "description": "Branch or tag to inspect",
                },
                "issue_number": {
                    "type": "integer",
                    "description": "Issue number to retrieve",
                },
                "pr_number": {
                    "type": "integer",
                    "description": "Pull request number to retrieve",
                },
            },
            output_schema={
                "repository": {"type": "object"},
                "issue": {"type": "object"},
                "pull_request": {"type": "object"},
            },
            audit_metadata={
                "owner": "kei-agents",
                "connector_type": "github",
                "compliance_scope": "read-only",
            },
        ),
        # -- Linear governed connector -----------------------------------
        WorkflowManifest(
            name="linear.workspace_read",
            version="0.1.0",
            purpose="List and read issues and projects from the governed "
            "Linear workspace",
            tool_dependencies=[
                "linear.list_issues",
                "linear.get_issue",
                "linear.list_projects",
            ],
            connector_dependencies=["conn_linear_1"],
            input_schema={
                "state": {
                    "type": "string",
                    "description": "Filter by workflow state",
                },
                "priority": {"type": "string", "description": "Filter by priority"},
                "issue_key": {
                    "type": "string",
                    "description": "Issue key e.g. ENG-123",
                },
            },
            output_schema={
                "issues": {"type": "array"},
                "projects": {"type": "array"},
            },
            audit_metadata={
                "owner": "kei-agents",
                "connector_type": "linear",
                "compliance_scope": "read-only",
            },
        ),
        # -- Google Drive / Docs governed connector ----------------------
        WorkflowManifest(
            name="drive.document_read",
            version="0.1.0",
            purpose="List and read files and documents from the governed "
            "Google Drive / Docs workspace",
            tool_dependencies=[
                "drive.list_files",
                "drive.get_file",
                "docs.get_document",
            ],
            connector_dependencies=["conn_drive_1"],
            input_schema={
                "query": {
                    "type": "string",
                    "description": "Search query for files",
                },
                "file_id": {
                    "type": "string",
                    "description": "File identifier",
                },
                "document_id": {
                    "type": "string",
                    "description": "Document identifier",
                },
            },
            output_schema={
                "files": {"type": "array"},
                "file": {"type": "object"},
                "document": {"type": "object"},
            },
            audit_metadata={
                "owner": "kei-agents",
                "connector_type": "drive",
                "compliance_scope": "read-only",
            },
        ),
        # -- S3 governed connector ---------------------------------------
        WorkflowManifest(
            name="s3.object_read",
            version="0.1.0",
            purpose="List and read objects from the governed S3 bucket",
            tool_dependencies=[
                "s3.list_objects",
                "s3.get_object",
                "s3.get_object_metadata",
            ],
            connector_dependencies=["conn_s3_1"],
            input_schema={
                "prefix": {
                    "type": "string",
                    "description": "Object key prefix to filter by",
                },
                "key": {
                    "type": "string",
                    "description": "Object key to read",
                },
            },
            output_schema={
                "objects": {"type": "array"},
                "object": {"type": "object"},
                "metadata": {"type": "object"},
            },
            audit_metadata={
                "owner": "kei-agents",
                "connector_type": "s3",
                "compliance_scope": "read-only",
            },
        ),
        # -- HTTP API / CRM governed connector ---------------------------
        WorkflowManifest(
            name="http_api.record_read",
            version="0.1.0",
            purpose="List and read records from the governed HTTP API / CRM connection",
            tool_dependencies=[
                "http_api.list_records",
                "http_api.get_record",
            ],
            connector_dependencies=["conn_http_api_1"],
            input_schema={
                "entity": {
                    "type": "string",
                    "description": "Entity to query (e.g. leads)",
                },
                "filters": {
                    "type": "string",
                    "description": "Query-style filters",
                },
                "record_id": {
                    "type": "string",
                    "description": "Record identifier",
                },
            },
            output_schema={
                "records": {"type": "array"},
                "record": {"type": "object"},
            },
            audit_metadata={
                "owner": "kei-agents",
                "connector_type": "http_api",
                "compliance_scope": "read-only",
            },
        ),
        # -- Notion governed connector (registered below) ----------------
        WorkflowManifest(
            name="notion.workspace_read",
            version="0.1.0",
            purpose="List and read pages and databases from the governed "
            "Notion workspace",
            tool_dependencies=[
                "notion.list_pages",
                "notion.get_page",
                "notion.list_databases",
                "notion.get_database",
            ],
            connector_dependencies=["conn_notion_1"],
            input_schema={
                "query": {
                    "type": "string",
                    "description": "Search query for pages",
                },
                "page_id": {
                    "type": "string",
                    "description": "Page identifier",
                },
                "database_id": {
                    "type": "string",
                    "description": "Database identifier",
                },
            },
            output_schema={
                "pages": {"type": "array"},
                "page": {"type": "object"},
                "databases": {"type": "array"},
                "database": {"type": "object"},
            },
            audit_metadata={
                "owner": "kei-agents",
                "connector_type": "notion",
                "compliance_scope": "read-only",
            },
        ),
    ]

    for m in manifest_defs:
        registry.register(m)

    return registry


# Eagerly populate the default registry.
_builtin_registry = _register_builtin_workflows()

__all__ = [
    "WorkflowManifest",
    "WorkflowRegistry",
]
