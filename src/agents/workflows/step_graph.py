"""Structural validation shared by workflow specs built from typed step DAGs.

A domain spec (finance, fundraising) supplies which payload types are reads
and mutations, and which permissions those steps must hold;
:func:`validate_step_graph` checks the graph. It validates *structure* only
— a spec that passes is well formed, not permitted. Authorization is decided
at invocation time by ABAC and the tenant-side proxy PEP (ADR-011). See
docs/workflow-validation.md.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from agents.tool_definitions import Permission


class WorkflowStepLike(Protocol):
    """The step shape the validator reads; satisfied by the step dataclasses."""

    @property
    def step_id(self) -> str: ...

    @property
    def depends_on(self) -> list[str]: ...

    @property
    def payload(self) -> object: ...

    @property
    def permission(self) -> object: ...


def find_cycle(steps: Sequence[WorkflowStepLike]) -> list[str] | None:
    """Return one dependency cycle as a list of step ids, or None if acyclic.

    A spec is a DAG by contract. Nothing enforced that, so a cycle would reach
    a harness interpreter and hang it rather than being rejected here.
    """
    dependencies = {
        step.step_id: [d for d in step.depends_on if d != step.step_id]
        for step in steps
    }
    # Self-dependency is a cycle of length one; report it directly since the
    # traversal below skips it to keep the walk simple.
    for step in steps:
        if step.step_id in step.depends_on:
            return [step.step_id, step.step_id]

    WHITE, GREY, BLACK = 0, 1, 2
    colour = dict.fromkeys(dependencies, WHITE)

    def walk(node: str, path: list[str]) -> list[str] | None:
        colour[node] = GREY
        path.append(node)
        for dep in dependencies.get(node, ()):
            if dep not in colour:
                continue  # unknown dep: reported separately as a dangling edge
            if colour[dep] == GREY:
                return path[path.index(dep) :] + [dep]
            if colour[dep] == WHITE:
                found = walk(dep, path)
                if found is not None:
                    return found
        path.pop()
        colour[node] = BLACK
        return None

    for node in dependencies:
        if colour[node] == WHITE:
            cycle = walk(node, [])
            if cycle is not None:
                return cycle
    return None


def has_ancestor(
    step: WorkflowStepLike,
    by_id: dict[str, WorkflowStepLike],
    payload_types: tuple[type, ...],
) -> bool:
    """Report whether a step with one of *payload_types* is an ancestor of *step*."""
    seen: set[str] = set()
    frontier = list(step.depends_on)
    while frontier:
        current = frontier.pop()
        if current in seen:
            continue
        seen.add(current)
        dependency = by_id.get(current)
        if dependency is None:
            continue
        if isinstance(dependency.payload, payload_types):
            return True
        frontier.extend(dependency.depends_on)
    return False


def validate_step_graph(
    steps: Sequence[WorkflowStepLike],
    *,
    read_types: tuple[type, ...],
    mutation_types: tuple[type, ...],
    mutation_permissions: tuple[Permission, ...],
) -> list[str]:
    """Validate a step DAG's read-first invariants.

    Checks, in order: unique step ids, resolvable dependencies, no cycles;
    every permission is a typed :class:`Permission`; every mutation holds one
    of *mutation_permissions* and has a read among its ancestors.

    Returns a list of violations; an empty list means the graph is valid.
    """
    violations: list[str] = []
    by_id: dict[str, WorkflowStepLike] = {}

    for step in steps:
        if step.step_id in by_id:
            violations.append(f"{step.step_id}: duplicate step_id")
        by_id[step.step_id] = step

    for step in steps:
        for dep in step.depends_on:
            if dep not in by_id:
                violations.append(
                    f"{step.step_id}: depends_on {dep!r} not found in steps"
                )

    cycle = find_cycle(steps)
    if cycle is not None:
        violations.append(f"dependency cycle: {' -> '.join(cycle)}")
        # Reachability checks below assume an acyclic graph is meaningful to
        # traverse. The traversals terminate regardless, but reporting
        # gate/read findings from inside a cycle would be noise on top of the
        # real defect, so stop here.
        return violations

    allowed = " or ".join(p.value for p in mutation_permissions)
    for step in steps:
        permission = step.permission
        # Permission is a str enum, so a bare "finance_write" compares equal to
        # Permission.FINANCE_WRITE; check the type so typos and untyped values
        # cannot slip past the policy engine.
        if not isinstance(permission, Permission):
            violations.append(
                f"{step.step_id}: permission must be a Permission member, "
                f"got bare {permission!r}"
            )
            continue
        if isinstance(step.payload, mutation_types):
            if permission not in mutation_permissions:
                violations.append(
                    f"{step.step_id}: mutation step requires "
                    f"{allowed} permission, got {permission.value!r}"
                )
            if not has_ancestor(step, by_id, read_types):
                violations.append(
                    f"{step.step_id}: mutation step must depend on a read step"
                )

    return violations


__all__ = [
    "WorkflowStepLike",
    "find_cycle",
    "has_ancestor",
    "validate_step_graph",
]
