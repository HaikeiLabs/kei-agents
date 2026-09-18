"""Tool definitions, rendering, and access metadata for Kei agents.

Tools are modeled as **agent capabilities**: each entry describes what an
agent can do (name, description, parameters), which permission gates it, and
which category organizes it. GitHub mutations (``create_issue``,
``create_pull_request``) are action tools gated by ``Permission.GITHUB_WRITE``
- they are never Kei connector capabilities.

A tool may carry optional ``binding`` metadata linking it to a registered
data source (``abac.connection_presets``). Bindings are **non-secret routing
metadata only**: they carry a ``connector_id`` and plain routing config that
the tenant-side proxy consumes to resolve bindings/auth and invoke provider
adapters. This module never contains provider clients, credential
resolution, or secret material - data stays in the tenant runtime.

The lookup helpers retain the original module-global calling convention while
also accepting an explicit tool collection for CRM, GitHub, and policy use.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ModelFormat(str, Enum):
    """Supported model tool formats."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    LLAMA = "llama"
    VLLM = "vllm"


class Permission(str, Enum):
    """Available permission scopes for tools."""

    SEARCH_WIKI = "search_wiki"
    WEB_SEARCH = "web_search"
    SCHEDULE_MEETINGS = "schedule_meetings"
    GITHUB_READ = "github_read"
    GITHUB_WRITE = "github_write"
    CRM_READ = "crm_read"
    CRM_WRITE = "crm_write"
    LINEAR_READ = "linear_read"
    LINEAR_WRITE = "linear_write"
    DRIVE_READ = "drive_read"
    S3_READ = "s3_read"
    HTTP_API_READ = "http_api_read"
    NOTION_READ = "notion_read"


class ToolCategory(str, Enum):
    """Tool categories for organization."""

    SEARCH = "search"
    PRODUCTIVITY = "productivity"
    GITHUB = "github"
    CRM = "crm"
    ENTERTAINMENT = "entertainment"
    LINEAR = "linear"
    DRIVE = "drive"
    S3 = "s3"
    HTTP_API = "http_api"
    NOTION = "notion"


@dataclass
class ToolParameter:
    """A parameter in a tool schema."""

    name: str
    type: str = "string"
    description: str = ""
    required: bool = False
    enum: list[str] | None = None
    default: Any = None


@dataclass
class ToolBinding:
    """Non-secret routing metadata mapping a tool to a registered data source.

    ``connector_id`` references ``abac.connection_presets.id`` in Kei. The
    ``config`` holds non-secret routing hints only and is consumed by the
    tenant-side proxy, which resolves bindings/auth and invokes provider
    adapters. ``delegated_context`` lists the non-secret field names the
    tenant-side proxy supplies at invocation (tenant/resource/region scoping);
    the agent never provides them, so they must not appear as tool parameters.
    This type never carries secrets, credentials, provider clients, or
    credential-resolution logic.
    """

    connector_id: str
    config: dict[str, Any] = field(default_factory=dict)
    delegated_context: list[str] = field(default_factory=list)


@dataclass
class ToolDefinition:
    """An agent capability with optional permission, routing, and handler metadata.

    Attributes:
        name: Unique tool id, ``^[a-z0-9_]+(\\.[a-z0-9_]+)*$``.
        description: What the tool does (fed to the LLM).
        parameters: Function arguments.
        permission: Permission gate for the tool.
        category: Organization category.
        service: Credential-lookup service; empty means policy-only.
        version: The tool's own version.
        tags: Tailscale-style labels (e.g. ``github-write``).
        binding: Non-secret routing metadata to a registered data source.
        handler: Optional execution callable (harness-side; not required for
            the agent capability catalog).
    """

    name: str
    description: str
    parameters: list[ToolParameter] | dict[str, Any] | None = None
    permission: Permission = Permission.WEB_SEARCH
    category: ToolCategory = ToolCategory.SEARCH
    service: str = ""
    version: str = ""
    tags: list[str] = field(default_factory=list)
    binding: ToolBinding | None = None
    handler: Callable[..., Any] | None = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = []


TOOL_DEFINITIONS: list[ToolDefinition] = [
    ToolDefinition(
        name="search_wiki",
        description="Search conversation history",
        parameters=[
            ToolParameter(name="query", description="Search query", required=True),
        ],
        permission=Permission.SEARCH_WIKI,
        category=ToolCategory.SEARCH,
        service="",
        tags=["wiki-read"],
    ),
    ToolDefinition(
        name="web_search",
        description="Search the web for current info",
        parameters=[
            ToolParameter(name="query", description="Search query", required=True),
        ],
        permission=Permission.WEB_SEARCH,
        category=ToolCategory.SEARCH,
        service="",
        tags=["web-read"],
    ),
    ToolDefinition(
        name="schedule_meeting",
        description="Schedule calendar meetings",
        parameters=[
            ToolParameter(name="title", description="Meeting title", required=True),
            ToolParameter(
                name="start_time",
                description="Meeting start time (ISO 8601)",
                required=True,
            ),
            ToolParameter(
                name="duration_minutes",
                description="Meeting duration in minutes",
                type="number",
                required=False,
                default=30,
            ),
            ToolParameter(
                name="attendees",
                description="Comma-separated attendee emails",
                required=False,
            ),
        ],
        permission=Permission.SCHEDULE_MEETINGS,
        category=ToolCategory.PRODUCTIVITY,
        service="calendar",
        tags=["calendar-write"],
        binding=ToolBinding(
            connector_id="conn_calendar_1",
            config={"provider": "google_calendar"},
        ),
    ),
    ToolDefinition(
        name="list_prs",
        description="List GitHub pull requests",
        parameters=[
            ToolParameter(
                name="state",
                description="Filter by PR state",
                required=False,
                enum=["open", "closed", "all"],
                default="open",
            ),
            ToolParameter(
                name="limit",
                description="Maximum number of PRs to return",
                type="integer",
                required=False,
                default=30,
            ),
        ],
        permission=Permission.GITHUB_READ,
        category=ToolCategory.GITHUB,
        service="github",
        tags=["github-read"],
        binding=ToolBinding(
            connector_id="conn_github_1",
            config={"default_branch": "main"},
        ),
    ),
    ToolDefinition(
        name="list_issues",
        description="List GitHub issues",
        parameters=[
            ToolParameter(
                name="state",
                description="Filter by issue state",
                required=False,
                enum=["open", "closed", "all"],
                default="open",
            ),
            ToolParameter(
                name="labels",
                description="Comma-separated list of labels to filter by",
                required=False,
            ),
            ToolParameter(
                name="limit",
                description="Maximum number of issues to return",
                type="integer",
                required=False,
                default=30,
            ),
        ],
        permission=Permission.GITHUB_READ,
        category=ToolCategory.GITHUB,
        service="github",
        tags=["github-read"],
        binding=ToolBinding(
            connector_id="conn_github_1",
            config={"default_branch": "main"},
        ),
    ),
    ToolDefinition(
        name="create_issue",
        description="Create GitHub issues",
        parameters=[
            ToolParameter(name="title", description="Issue title", required=True),
            ToolParameter(
                name="body", description="Issue body/description", required=False
            ),
            ToolParameter(
                name="labels",
                description="Comma-separated list of labels",
                required=False,
            ),
            ToolParameter(
                name="assignee",
                description="Username to assign the issue to",
                required=False,
            ),
        ],
        permission=Permission.GITHUB_WRITE,
        category=ToolCategory.GITHUB,
        service="github",
        tags=["github-write", "code-mutation"],
    ),
    ToolDefinition(
        name="get_workflow_status",
        description="Get CI/CD workflow status",
        parameters=[
            ToolParameter(
                name="workflow_name", description="Name of the workflow", required=True
            ),
        ],
        permission=Permission.GITHUB_READ,
        category=ToolCategory.GITHUB,
        service="github",
        tags=["github-read"],
        binding=ToolBinding(
            connector_id="conn_github_1",
            config={"default_branch": "main"},
        ),
    ),
    ToolDefinition(
        name="create_pull_request",
        description="Create PRs",
        parameters=[
            ToolParameter(name="title", description="PR title", required=True),
            ToolParameter(
                name="body", description="PR body/description", required=False
            ),
            ToolParameter(
                name="head",
                description="The branch where changes are implemented",
                required=True,
            ),
            ToolParameter(
                name="base",
                description="The branch the changes should be pulled into",
                required=False,
                default="main",
            ),
        ],
        permission=Permission.GITHUB_WRITE,
        category=ToolCategory.GITHUB,
        service="github",
        tags=["github-write", "code-mutation"],
    ),
    ToolDefinition(
        name="start_game",
        description="Start interactive games",
        parameters=[
            ToolParameter(
                name="game", description="Name of the game to start", required=True
            ),
        ],
        permission=Permission.SEARCH_WIKI,
        category=ToolCategory.ENTERTAINMENT,
        service="",
        tags=["game"],
    ),
]


def detect_model_format(model_name: str) -> ModelFormat:
    """Detect a rendering format from a model name."""
    name_lower = model_name.lower()
    if "claude" in name_lower:
        return ModelFormat.ANTHROPIC
    if "ollama" in name_lower:
        return ModelFormat.OLLAMA
    if "llama" in name_lower:
        return ModelFormat.LLAMA
    if "vllm" in name_lower:
        return ModelFormat.VLLM
    return ModelFormat.OPENAI


def _tool_parameters(tool: ToolDefinition) -> list[ToolParameter]:
    if isinstance(tool.parameters, dict):
        return [
            ToolParameter(
                name=name,
                type=value.get("type", "string"),
                description=value.get("description", ""),
                required=name in value.get("required", []),
            )
            for name, value in tool.parameters.get("properties", {}).items()
        ]
    return tool.parameters or []


def _render_openai_parameter(param: ToolParameter) -> dict[str, Any]:
    result: dict[str, Any] = {"type": param.type, "description": param.description}
    if param.enum:
        result["enum"] = param.enum
    return result


def render_openai_tools(tools: list[ToolDefinition]) -> list[dict[str, Any]]:
    """Render tools in OpenAI function-calling format."""
    result = []
    for tool in tools:
        schema: dict[str, Any] = {"type": "object", "properties": {}, "required": []}
        for param in _tool_parameters(tool):
            schema["properties"][param.name] = _render_openai_parameter(param)
            if param.required:
                schema["required"].append(param.name)
        result.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": schema,
                },
            }
        )
    return result


def render_anthropic_tools(tools: list[ToolDefinition]) -> list[dict[str, Any]]:
    """Render tools in Anthropic tool-use format."""
    result = []
    for tool in tools:
        schema: dict[str, Any] = {"type": "object", "properties": {}, "required": []}
        for param in _tool_parameters(tool):
            schema["properties"][param.name] = _render_openai_parameter(param)
            if param.required:
                schema["required"].append(param.name)
        result.append(
            {"name": tool.name, "description": tool.description, "input_schema": schema}
        )
    return result


def render_ollama_tools(tools: list[ToolDefinition]) -> list[dict[str, Any]]:
    """Render tools in Ollama's OpenAI-compatible format."""
    return render_openai_tools(tools)


def render_tools(
    tools: list[ToolDefinition], model: str | ModelFormat
) -> list[dict[str, Any]]:
    """Render tools in the format selected by a model name or enum."""
    if isinstance(model, ModelFormat):
        format_type = model
    else:
        format_type = detect_model_format(model)
    if format_type == ModelFormat.ANTHROPIC:
        return render_anthropic_tools(tools)
    if format_type == ModelFormat.OLLAMA:
        return render_ollama_tools(tools)
    return render_openai_tools(tools)


def get_tool_by_name(
    tools_or_name: list[ToolDefinition] | str, name: str | None = None
) -> ToolDefinition | None:
    tools = ALL_TOOL_DEFINITIONS if isinstance(tools_or_name, str) else tools_or_name
    wanted = tools_or_name if isinstance(tools_or_name, str) else name
    return next((tool for tool in tools if tool.name == wanted), None)


def get_tools_by_category(
    category_or_tools: str | ToolCategory | list[ToolDefinition],
    category: str | ToolCategory | None = None,
) -> list[ToolDefinition]:
    tools = (
        ALL_TOOL_DEFINITIONS
        if not isinstance(category_or_tools, list)
        else category_or_tools
    )
    wanted = category_or_tools if not isinstance(category_or_tools, list) else category
    return [
        tool
        for tool in tools
        if tool.category == wanted or tool.category.value == wanted
    ]


def get_tools_by_permission(
    permission_or_tools: str | Permission | list[ToolDefinition],
    permission: str | Permission | None = None,
) -> list[ToolDefinition]:
    tools = (
        ALL_TOOL_DEFINITIONS
        if not isinstance(permission_or_tools, list)
        else permission_or_tools
    )
    wanted = (
        permission_or_tools if not isinstance(permission_or_tools, list) else permission
    )
    return [
        tool
        for tool in tools
        if tool.permission == wanted or tool.permission.value == wanted
    ]


def get_tools_for_model(
    tools_or_model: list[ToolDefinition] | str | ModelFormat,
    model: str | ModelFormat | None = None,
) -> list[dict[str, Any]]:
    """Render the tool catalog (or an explicit collection) for a model.

    With a single model argument, renders ``TOOL_DEFINITIONS`` for that model.
    With an explicit tool collection and a model, renders the collection.
    """
    if isinstance(tools_or_model, list):
        return render_tools(tools_or_model, model or ModelFormat.OPENAI)
    return render_tools(TOOL_DEFINITIONS, tools_or_model)


_NAME_RE = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)*$")
_SERVICE_RE = re.compile(r"^[a-z0-9_]+$")
_SECRET_KEY_HINTS = (
    "token",
    "secret",
    "password",
    "passwd",
    "apikey",
    "api_key",
    "key",
    "credential",
    "auth",
    "bearer",
)
_SECRET_VALUE_HINTS = (
    "secret",
    "password",
    "passwd",
    "apikey",
    "api_key",
    "token",
    "credential",
    "authorization",
    "bearer",
    "sk-",
)
_FIELD_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_URL_VALUE_RE = re.compile(r"://")
_URL_KEY_HINTS = ("url", "endpoint", "base_url", "host", "api_url", "webhook")
_TENANT_IDENTIFIER_HINTS = (
    "tenant_id",
    "tenant",
    "account_id",
    "customer_id",
    "organization_id",
    "org_id",
)
_READ_PERMISSION_SUFFIX = "_read"


def _validate_binding(tool: ToolDefinition) -> list[str]:
    binding = tool.binding
    if binding is None:
        return []
    violations: list[str] = []
    prefix = f"{tool.name}.binding"
    if not binding.connector_id:
        violations.append(f"{prefix}.connector_id is required")
    for key, value in binding.config.items():
        lower_key = key.lower()
        if any(hint in lower_key for hint in _SECRET_KEY_HINTS):
            violations.append(
                f"{prefix}.config contains secret-looking key {key!r}; "
                "bindings must be non-secret routing metadata"
            )
        if any(hint in lower_key for hint in _URL_KEY_HINTS):
            violations.append(
                f"{prefix}.config key {key!r} looks like a URL/endpoint; "
                "endpoints are resolved from the governed connection preset, "
                "never embedded in routing metadata"
            )
        if isinstance(value, str):
            if _URL_VALUE_RE.search(value):
                violations.append(
                    f"{prefix}.config value for {key!r} looks like a URL; "
                    "endpoints are resolved from the governed connection preset, "
                    "never embedded in routing metadata"
                )
            if any(hint in value.lower() for hint in _SECRET_VALUE_HINTS):
                violations.append(
                    f"{prefix}.config value for {key!r} looks like a secret; "
                    "bindings must be non-secret routing metadata"
                )
    if len(set(binding.delegated_context)) != len(binding.delegated_context):
        violations.append(f"{prefix}.delegated_context contains duplicates")
    for name in binding.delegated_context:
        if not _FIELD_RE.fullmatch(name):
            violations.append(
                f"{prefix}.delegated_context contains invalid field name {name!r}"
            )
        if any(hint in name.lower() for hint in _SECRET_KEY_HINTS):
            violations.append(
                f"{prefix}.delegated_context field {name!r} looks like a secret; "
                "delegated context carries no secret material"
            )
    return violations


def validate_tool_definitions(tools: list[ToolDefinition]) -> list[str]:
    """Validate tool definitions against the cross-repo contract.

    Checks name format/uniqueness, required fields, valid permission and
    category enums, service identifiers, and the metadata-only invariant on
    bindings (no secret material). Returns a list of violations; an empty
    list means the definitions are valid.
    """
    violations: list[str] = []
    seen: set[str] = set()
    for tool in tools:
        if not tool.name:
            violations.append("tool has an empty name")
        elif not _NAME_RE.fullmatch(tool.name):
            violations.append(
                f"invalid name {tool.name!r}: must match {_NAME_RE.pattern}"
            )
        if tool.name in seen:
            violations.append(f"duplicate tool name: {tool.name!r}")
        seen.add(tool.name)
        if not tool.description:
            violations.append(f"{tool.name}: description is required")
        if not isinstance(tool.permission, Permission):
            violations.append(f"{tool.name}: invalid permission {tool.permission!r}")
        if not isinstance(tool.category, ToolCategory):
            violations.append(f"{tool.name}: invalid category {tool.category!r}")
        if tool.service and not _SERVICE_RE.fullmatch(tool.service):
            violations.append(f"{tool.name}: invalid service {tool.service!r}")
        is_connector_read = (
            tool.binding is not None
            and isinstance(tool.permission, Permission)
            and tool.permission.value.endswith(_READ_PERMISSION_SUFFIX)
        )
        if is_connector_read:
            if tool.handler is not None:
                violations.append(
                    f"{tool.name}: governed connector read tools must not declare "
                    "a handler; execution is delegated to the tenant-side proxy"
                )
            if not tool.service:
                violations.append(
                    f"{tool.name}: governed connector read tools must declare a service"
                )
        delegated = set(tool.binding.delegated_context) if tool.binding else set()
        for param in _tool_parameters(tool):
            if not param.name:
                violations.append(f"{tool.name}: parameter with an empty name")
            if param.name in delegated:
                violations.append(
                    f"{tool.name}: parameter {param.name!r} collides with a "
                    "delegated context field; delegated fields are resolved by "
                    "the tenant-side proxy, never supplied by the agent"
                )
            if is_connector_read and param.name in _TENANT_IDENTIFIER_HINTS:
                violations.append(
                    f"{tool.name}: parameter {param.name!r} looks like a tenant "
                    "identifier; tenant context is delegated, never agent-chosen"
                )
        violations.extend(_validate_binding(tool))
    return violations


def _unique_tools(*collections: list[ToolDefinition]) -> list[ToolDefinition]:
    """Merge tool collections, keeping the first definition for each name."""
    seen: set[str] = set()
    result: list[ToolDefinition] = []
    for tools in collections:
        for tool in tools:
            if tool.name in seen:
                continue
            seen.add(tool.name)
            result.append(tool)
    return result


# Imported at module bottom to break the circular import: the connector/crm/
# github tool modules import the types defined above from this module.
from agents.connectors import CONNECTOR_READ_TOOL_DEFINITIONS
from agents.crm.tools import CRM_TOOL_DEFINITIONS
from agents.github.tools import GITHUB_TOOL_DEFINITIONS
from agents.workflows.crm_linear_followup import CRM_LINEAR_FOLLOWUP_TOOL_DEFINITIONS
from agents.workflows.leads import REGISTERED_LEADS_WORKFLOW_TOOL_DEFINITIONS

ALL_TOOL_DEFINITIONS = _unique_tools(
    TOOL_DEFINITIONS,
    CONNECTOR_READ_TOOL_DEFINITIONS,
    CRM_TOOL_DEFINITIONS,
    GITHUB_TOOL_DEFINITIONS,
    REGISTERED_LEADS_WORKFLOW_TOOL_DEFINITIONS,
    CRM_LINEAR_FOLLOWUP_TOOL_DEFINITIONS,
)


__all__ = [
    "ALL_TOOL_DEFINITIONS",
    "CONNECTOR_READ_TOOL_DEFINITIONS",
    "TOOL_DEFINITIONS",
    "ModelFormat",
    "Permission",
    "ToolBinding",
    "ToolCategory",
    "ToolDefinition",
    "ToolParameter",
    "detect_model_format",
    "get_tool_by_name",
    "get_tools_by_category",
    "get_tools_by_permission",
    "get_tools_for_model",
    "render_anthropic_tools",
    "render_ollama_tools",
    "render_openai_tools",
    "render_tools",
    "validate_tool_definitions",
]
