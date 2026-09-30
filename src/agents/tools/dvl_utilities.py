"""DVL Assistant utility-tool definitions (read-only RPC surface).

These tools mirror the catalog in ``DVL-Group/utilities``
``agent/assistant-tools.v1.yaml`` (``staging`` branch). Each entry is a
policy-only read tool: no provider client, no connector binding, no handler.
Kei ABAC policy references them by the ``utilities.<utility>.<snake_rpc>``
naming convention.

Refresh by re-copying the YAML from the ``DVL-Group/utilities`` repository's
``staging`` branch and updating the definitions below.
"""

from __future__ import annotations

from agents.tool_definitions import (
    Permission,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
)


def _param(
    name: str,
    type: str = "string",
    description: str = "",
    required: bool = False,
) -> ToolParameter:
    return ToolParameter(
        name=name, type=type, description=description, required=required
    )


DVL_UTILITIES_TOOL_DEFINITIONS: list[ToolDefinition] = [
    # ----- A-1: bonus cycle status and blockers -----
    ToolDefinition(
        name="utilities.admin_bonus.get_active_workflow",
        description="The active admin-bonus workflow for the current cycle.",
        permission=Permission.UTILITIES_READ,
        category=ToolCategory.UTILITIES,
    ),
    ToolDefinition(
        name="utilities.admin_bonus.get_workflow_status",
        description="Workflow status (steps, milestones, blockers) for an admin-bonus period.",
        parameters=[
            _param(
                "period_id", "integer", "The bonus period to inspect.", required=True
            ),
        ],
        permission=Permission.UTILITIES_READ,
        category=ToolCategory.UTILITIES,
    ),
    ToolDefinition(
        name="utilities.admin_bonus.list_approval_blockers",
        description="Approval blockers standing between a bonus period and sign-off.",
        parameters=[
            _param(
                "period_id", "integer", "The bonus period to inspect.", required=True
            ),
        ],
        permission=Permission.UTILITIES_READ,
        category=ToolCategory.UTILITIES,
    ),
    ToolDefinition(
        name="utilities.tech_bonus.get_workflow_status",
        description="Workflow status for a tech-bonus pay period.",
        parameters=[
            _param(
                "pay_period_id",
                "integer",
                "The tech-bonus pay period to inspect.",
                required=True,
            ),
        ],
        permission=Permission.UTILITIES_READ,
        category=ToolCategory.UTILITIES,
    ),
    ToolDefinition(
        name="utilities.tech_bonus.list_sales_manager_approvals",
        description="Sales-manager bonus approvals in the cycle.",
        parameters=[
            _param("page", "object", "Pagination cursor and limit."),
        ],
        permission=Permission.UTILITIES_READ,
        category=ToolCategory.UTILITIES,
    ),
    # ----- A-2: OMS daily attention digest -----
    ToolDefinition(
        name="utilities.oms.list_orders",
        description="Orders filtered by lane, stage, owner, flags, or search text.",
        parameters=[
            _param("lane", "string", "Filter by order lane."),
            _param("stage", "string", "Filter by order stage."),
            _param("mine", "boolean", "Only orders owned by the caller."),
            _param("flags_only", "boolean", "Only flagged orders."),
            _param("search", "string", "Free-text search over orders."),
            _param("page", "object", "Pagination cursor and limit."),
            _param("owner", "string", "Filter by order owner."),
            _param("include_returns", "boolean", "Include return lines."),
            _param("workflow", "string", "Filter by workflow."),
        ],
        permission=Permission.UTILITIES_READ,
        category=ToolCategory.UTILITIES,
    ),
    ToolDefinition(
        name="utilities.oms.get_quality_tally",
        description="Order-quality tally for the attention digest.",
        permission=Permission.UTILITIES_READ,
        category=ToolCategory.UTILITIES,
    ),
    ToolDefinition(
        name="utilities.oms.list_triage",
        description="Unmatched extract rows parked in triage.",
        parameters=[
            _param("page", "object", "Pagination cursor and limit."),
        ],
        permission=Permission.UTILITIES_READ,
        category=ToolCategory.UTILITIES,
    ),
    ToolDefinition(
        name="utilities.oms.list_orders_ar",
        description="Orders with accounts-receivable state, filterable by exit state.",
        parameters=[
            _param("search", "string", "Free-text search over orders."),
            _param("page", "object", "Pagination cursor and limit."),
            _param("exit_state", "string", "Filter by AR exit state."),
        ],
        permission=Permission.UTILITIES_READ,
        category=ToolCategory.UTILITIES,
    ),
    ToolDefinition(
        name="utilities.oms.list_ar_ledger",
        description="AR ledger lines for the attention digest.",
        parameters=[
            _param(
                "include_opening_balance", "boolean", "Include the opening balance row."
            ),
            _param("search", "string", "Free-text search over ledger lines."),
            _param("page", "object", "Pagination cursor and limit."),
        ],
        permission=Permission.UTILITIES_READ,
        category=ToolCategory.UTILITIES,
    ),
    # ----- A-3: payroll export pre-flight -----
    ToolDefinition(
        name="utilities.admin_bonus.get_salary_audit",
        description="Salary audit rows for a bonus period (pre-flight check).",
        parameters=[
            _param(
                "period_id", "integer", "The bonus period to inspect.", required=True
            ),
            _param("page", "object", "Pagination cursor and limit."),
        ],
        permission=Permission.UTILITIES_READ,
        category=ToolCategory.UTILITIES,
    ),
    ToolDefinition(
        name="utilities.admin_bonus.list_exclusions",
        description="Bonus exclusions in force for the period.",
        parameters=[
            _param("page", "object", "Pagination cursor and limit."),
        ],
        permission=Permission.UTILITIES_READ,
        category=ToolCategory.UTILITIES,
    ),
    ToolDefinition(
        name="utilities.admin_bonus.list_manager_submissions",
        description="Manager bonus submissions and their approval state.",
        parameters=[
            _param(
                "period_id", "integer", "The bonus period to inspect.", required=True
            ),
            _param("page", "object", "Pagination cursor and limit."),
        ],
        permission=Permission.UTILITIES_READ,
        category=ToolCategory.UTILITIES,
    ),
    ToolDefinition(
        name="utilities.admin_bonus.list_one_off_bonus_totals",
        description="One-off bonus totals for the period (pre-flight check).",
        parameters=[
            _param(
                "period_id", "integer", "The bonus period to inspect.", required=True
            ),
            _param("page", "object", "Pagination cursor and limit."),
        ],
        permission=Permission.UTILITIES_READ,
        category=ToolCategory.UTILITIES,
    ),
    # ----- A-9: post-deploy health -----
    ToolDefinition(
        name="utilities.project_health.list_my_projects",
        description="The caller's project health cards (proves the utility serves data).",
        permission=Permission.UTILITIES_READ,
        category=ToolCategory.UTILITIES,
    ),
    ToolDefinition(
        name="utilities.project_health.get_my_commission_summary",
        description="The caller's roll-up commission summary card.",
        permission=Permission.UTILITIES_READ,
        category=ToolCategory.UTILITIES,
    ),
]


__all__ = [
    "DVL_UTILITIES_TOOL_DEFINITIONS",
]
