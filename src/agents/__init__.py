"""Agent identity, permissions, action adapters, and workflow metadata."""

from agents.agent_definitions import (
    BUG_REPORT_TRIAGE_AGENT,
    FIX_PROPOSAL_AGENT,
    HARNESS_AGENT_DEFINITIONS,
    ONBOARDING_E2E_TRIAGE_AGENT,
    PDE_SEARCH_AGENT,
    PEDRO_AGENT,
    AgentDefinition,
    Harness,
    load_system_prompt,
    validate_agent_definitions,
)
from agents.github import GovernanceConfig, MockGitHubAdapter
from agents.github.tools import GITHUB_FIX_ACTION_TOOL
from agents.permissions import Permission
from agents.policy import (
    AuthorizationResult,
    PermissionContext,
    PolicyDecision,
    PolicyEngine,
    check_tool_access,
    create_user_context,
    filter_accessible_tools,
)
from agents.workflow_registry import WorkflowManifest, WorkflowRegistry
from agents.workflows import (
    BUG_TO_LINEAR_PR,
    WORKFLOW_DEFINITIONS,
    PRReviewFinding,
    PRReviewFindingSeverity,
    PRReviewInput,
    PRReviewOutput,
    PRReviewStep,
    PRReviewWorkflowSpec,
    ReviewAction,
    ReviewActionKind,
    WorkflowPrincipal,
    WorkflowSpec,
    WorkflowStep,
)

__version__ = "0.1.0"

__all__ = [
    "BUG_REPORT_TRIAGE_AGENT",
    "BUG_TO_LINEAR_PR",
    "FIX_PROPOSAL_AGENT",
    "GITHUB_FIX_ACTION_TOOL",
    "HARNESS_AGENT_DEFINITIONS",
    "ONBOARDING_E2E_TRIAGE_AGENT",
    "PDE_SEARCH_AGENT",
    "PEDRO_AGENT",
    "WORKFLOW_DEFINITIONS",
    "AgentDefinition",
    "AuthorizationResult",
    "GovernanceConfig",
    "Harness",
    "MockGitHubAdapter",
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
    "WorkflowManifest",
    "WorkflowPrincipal",
    "WorkflowRegistry",
    "WorkflowSpec",
    "WorkflowStep",
    "check_tool_access",
    "create_user_context",
    "filter_accessible_tools",
    "load_system_prompt",
    "validate_agent_definitions",
]
