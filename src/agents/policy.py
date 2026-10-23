"""Policy and permission system for tool access control.

This module provides:
- Permission context for tracking user permissions
- Policy enforcement for tool access
- Authorization results for governance
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agents.permissions import Permission


class AuthorizationResult(str, Enum):
    """Authorization result enum."""

    ALLOW = "allow"
    DENY = "deny"


@dataclass
class PolicyDecision:
    """Policy decision with metadata."""

    result: AuthorizationResult
    reason: str | None = None
    required_permission: Permission | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PermissionContext:
    """Context for permission evaluation."""

    user_id: str
    permissions: set[Permission] = field(default_factory=set)
    roles: set[str] = field(default_factory=set)

    def has_permission(self, permission: Permission) -> bool:
        """Check if context has a specific permission."""
        return permission in self.permissions

    def add_permission(self, permission: Permission) -> None:
        """Add a permission to the context."""
        self.permissions.add(permission)

    def remove_permission(self, permission: Permission) -> None:
        """Remove a permission from the context."""
        self.permissions.discard(permission)


class PolicyEngine:
    """Policy engine for evaluating tool access."""

    def __init__(self) -> None:
        self._custom_policies: dict[
            str, Callable[[Permission, PermissionContext], PolicyDecision]
        ] = {}

    def evaluate(
        self,
        tool_name: str,
        permission: Permission,
        context: PermissionContext,
    ) -> PolicyDecision:
        """Evaluate if a tool should be allowed for the given context."""
        if tool_name in self._custom_policies:
            return self._custom_policies[tool_name](permission, context)

        if context.has_permission(permission):
            return PolicyDecision(
                result=AuthorizationResult.ALLOW,
                required_permission=permission,
            )

        return PolicyDecision(
            result=AuthorizationResult.DENY,
            reason=f"Missing required permission: {permission.value}",
            required_permission=permission,
        )

    def register_policy(
        self,
        tool_name: str,
        policy: Callable[[Permission, PermissionContext], PolicyDecision],
    ) -> None:
        """Register a custom policy for a specific tool."""
        self._custom_policies[tool_name] = policy

    def evaluate_many(
        self,
        tools: dict[str, Permission],
        context: PermissionContext,
    ) -> dict[str, PolicyDecision]:
        """Evaluate multiple tools at once."""
        return {
            name: self.evaluate(name, permission, context)
            for name, permission in tools.items()
        }


def create_user_context(
    user_id: str,
    permission_names: list[str] | None = None,
    roles: list[str] | None = None,
) -> PermissionContext:
    """Create a permission context for a user.

    Args:
        user_id: Unique user identifier
        permission_names: List of permission names to grant
        roles: List of roles to assign

    Returns:
        Configured PermissionContext
    """
    permissions = set()
    if permission_names:
        for name in permission_names:
            try:
                permissions.add(Permission(name))
            except ValueError:
                pass

    return PermissionContext(
        user_id=user_id,
        permissions=permissions,
        roles=set(roles) if roles else set(),
    )


_default_policy_engine = PolicyEngine()


def get_policy_engine() -> PolicyEngine:
    """Get the default policy engine instance."""
    return _default_policy_engine


def set_policy_engine(engine: PolicyEngine) -> None:
    """Set the default policy engine instance."""
    global _default_policy_engine
    _default_policy_engine = engine


def check_tool_access(
    tool_name: str,
    permission: Permission,
    context: PermissionContext,
) -> PolicyDecision:
    """Check if a tool can be accessed with the given context."""
    return get_policy_engine().evaluate(tool_name, permission, context)


def filter_accessible_tools(
    tools: dict[str, Permission],
    context: PermissionContext,
) -> dict[str, Permission]:
    """Filter a name-to-permission map using local permission context."""
    engine = get_policy_engine()
    return {
        name: permission
        for name, permission in tools.items()
        if engine.evaluate(name, permission, context).result == AuthorizationResult.ALLOW
    }


__all__ = [
    "AuthorizationResult",
    "PermissionContext",
    "PolicyDecision",
    "PolicyEngine",
    "check_tool_access",
    "create_user_context",
    "filter_accessible_tools",
    "get_policy_engine",
    "set_policy_engine",
]
