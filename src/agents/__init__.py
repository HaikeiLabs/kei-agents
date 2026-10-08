"""Kei Agents - Agent definitions, tools, and prompts for the Kei AI platform.

This package provides:
- Tool definitions with multi-model format support (OpenAI, Anthropic, Ollama)
- Provider-neutral read schemas for governed connectors (GitHub, Linear,
  Google Drive/Docs, S3, http_api/CRM, Notion, Gmail, Tito)
- CRM tools for lead management (mock adapter)
- GitHub tools for issue/PR management (with governance)
- Permission-based access control
 - Harness agent definitions (PDE search agent, Pedro)
- Harness-neutral workflow registry for discovering workflows by tool or
  connector dependency
- Harness-neutral composable workflow definitions

Install: pip install kei-agents

Usage:
    from agents import TOOL_DEFINITIONS, render_tools, ModelFormat
    tools = render_tools(TOOL_DEFINITIONS, ModelFormat.OPENAI)

    from agents import WorkflowRegistry
    registry = WorkflowRegistry.get_default()
    workflows = registry.discover_by_tool("github.get_repository")
"""

from agents.agent_definitions import (
    HARNESS_AGENT_DEFINITIONS,
    PDE_SEARCH_AGENT,
    PEDRO_AGENT,
    PEDRO_DEFAULT_GROUP_TOOLS,
    AgentDefinition,
    Harness,
    get_agent_tools,
    load_system_prompt,
    validate_agent_definitions,
)
from agents.crm import (
    CRMAdapter,
    Lead,
    LeadSource,
    LeadStatus,
)
from agents.github import (
    GovernanceConfig,
    MockGitHubAdapter,
)
from agents.policy import (
    AuthorizationResult,
    PermissionContext,
    PolicyDecision,
    PolicyEngine,
    check_tool_access,
    create_user_context,
    filter_accessible_tools,
)
from agents.tool_definitions import (
    ALL_TOOL_DEFINITIONS,
    TOOL_DEFINITIONS,
    ModelFormat,
    Permission,
    ToolBinding,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
    detect_model_format,
    get_tool_by_name,
    get_tools_by_category,
    get_tools_by_permission,
    get_tools_for_model,
    render_anthropic_tools,
    render_ollama_tools,
    render_openai_tools,
    render_tools,
    validate_tool_definitions,
)

__version__ = "0.1.0"

# Imported after tool_definitions so its bottom-of-module import of this
# package resolves without a circular import.
from agents.connectors import (
    CONNECTOR_READ_TOOL_DEFINITIONS,
    DRIVE_READ_TOOL_DEFINITIONS,
    GITHUB_READ_TOOL_DEFINITIONS,
    GMAIL_READ_TOOL_DEFINITIONS,
    HTTP_API_READ_TOOL_DEFINITIONS,
    LINEAR_READ_TOOL_DEFINITIONS,
    NOTION_READ_TOOL_DEFINITIONS,
    S3_READ_TOOL_DEFINITIONS,
    TITO_READ_TOOL_DEFINITIONS,
)

# Imported after connectors so the workflow registry's module-level
# _register_builtin_workflows() sees the full CONNECTOR_READ_TOOL_DEFINITIONS
# list.
from agents.workflow_registry import (
    WorkflowManifest,
    WorkflowRegistry,
)

# Workflow definitions (imported after core types are available).
from agents.workflows import (
    PR_REVIEW_TOOL_DEPENDENCIES,
    WORKFLOW_DEFINITIONS,
    PRReviewFinding,
    PRReviewFindingSeverity,
    PRReviewInput,
    PRReviewOutput,
    PRReviewStep,
    PRReviewWorkflowSpec,
    ReviewAction,
    ReviewActionKind,
)

__all__ = [
    "ALL_TOOL_DEFINITIONS",
    "CONNECTOR_READ_TOOL_DEFINITIONS",
    "DRIVE_READ_TOOL_DEFINITIONS",
    "GITHUB_READ_TOOL_DEFINITIONS",
    "GMAIL_READ_TOOL_DEFINITIONS",
    "HARNESS_AGENT_DEFINITIONS",
    "HTTP_API_READ_TOOL_DEFINITIONS",
    "LINEAR_READ_TOOL_DEFINITIONS",
    "NOTION_READ_TOOL_DEFINITIONS",
    "PDE_SEARCH_AGENT",
    "PEDRO_AGENT",
    "PEDRO_DEFAULT_GROUP_TOOLS",
    "PR_REVIEW_TOOL_DEPENDENCIES",
    "S3_READ_TOOL_DEFINITIONS",
    "TITO_READ_TOOL_DEFINITIONS",
    "TOOL_DEFINITIONS",
    "WORKFLOW_DEFINITIONS",
    "AgentDefinition",
    "AuthorizationResult",
    "CRMAdapter",
    "GovernanceConfig",
    "Harness",
    "Lead",
    "LeadSource",
    "LeadStatus",
    "MockGitHubAdapter",
    "ModelFormat",
    "PRReviewFinding",
    "PRReviewFindingSeverity",
    "PRReviewInput",
    "PRReviewOutput",
    "PRReviewStep",
    "PRReviewWorkflowSpec",
    "Permission",
    "PermissionContext",
    "PolicyDecision",
    "PolicyEngine",
    "ReviewAction",
    "ReviewActionKind",
    "ToolBinding",
    "ToolCategory",
    "ToolDefinition",
    "ToolParameter",
    "WorkflowManifest",
    "WorkflowRegistry",
    "check_tool_access",
    "create_user_context",
    "detect_model_format",
    "filter_accessible_tools",
    "get_agent_tools",
    "get_tool_by_name",
    "get_tools_by_category",
    "get_tools_by_permission",
    "get_tools_for_model",
    "load_system_prompt",
    "render_anthropic_tools",
    "render_ollama_tools",
    "render_openai_tools",
    "render_tools",
    "validate_agent_definitions",
    "validate_tool_definitions",
]
