"""Property tests for the finance workflow validator (HAI-205).

The validator checks spec *structure* only; egress authorization stays with
ABAC and the tenant-side proxy PEP (see docs/workflow-validation.md). These
tests pin that contract over randomly generated specs:

- cycles are always rejected;
- a mutation is accepted iff a read step is an ancestor, by any path;
- step permissions are typed ``Permission`` members, never bare strings;
- egress steps (LinearTask, Notify) are classified, not gated.
"""

from __future__ import annotations

import random

import pytest

from agents import Permission
from agents.workflows.finance import (
    FINANCE_WORKFLOW_SPECS,
    CRMUpdate,
    DriveRead,
    FinanceEntity,
    FinanceWorkflowSpec,
    FinanceWorkflowStep,
    LinearTask,
    Notify,
    StepPayload,
    egress_steps,
    validate_read_first,
)

SEEDS = range(200)


def _step(
    step_id: str,
    payload: StepPayload,
    depends_on: list[str],
    permission: Permission = Permission.FINANCE_READ,
) -> FinanceWorkflowStep:
    return FinanceWorkflowStep(
        step_id=step_id,
        description=step_id,
        payload=payload,
        depends_on=depends_on,
        permission=permission,
    )


def _read(step_id: str, deps: list[str]) -> FinanceWorkflowStep:
    return _step(step_id, DriveRead(entity=FinanceEntity.INVOICE), deps)


def _mutation(step_id: str, deps: list[str]) -> FinanceWorkflowStep:
    payload = CRMUpdate(entity_type="customer", record_id="c-1", updates={})
    return _step(step_id, payload, deps, Permission.FINANCE_WRITE)


def _spec(steps: list[FinanceWorkflowStep]) -> FinanceWorkflowSpec:
    return FinanceWorkflowSpec(
        workflow_id="test.prop", name="prop", description="prop", steps=steps
    )


def _random_valid_dag(rng: random.Random) -> FinanceWorkflowSpec:
    """A valid spec: read -> chain of reads -> mutation, plus noise.

    Each step depends only on earlier steps, so the graph is acyclic.
    """
    steps = [_read("r0", [])]
    for i in range(rng.randint(0, 6)):
        parents = rng.sample([s.step_id for s in steps], k=rng.randint(1, len(steps)))
        steps.append(_read(f"r{i + 1}", parents))
    tail = [s.step_id for s in steps]
    steps.append(_mutation("m0", [rng.choice(tail)]))
    rng.shuffle(steps)
    return _spec(steps)


class TestCycles:
    @pytest.mark.parametrize("seed", SEEDS)
    def test_random_valid_dag_passes(self, seed: int) -> None:
        assert validate_read_first(_random_valid_dag(random.Random(seed))) == []

    @pytest.mark.parametrize("seed", SEEDS)
    def test_any_back_edge_is_rejected(self, seed: int) -> None:
        rng = random.Random(seed)
        spec = _random_valid_dag(rng)
        by_id = {s.step_id: s for s in spec.steps}
        # Pick an edge child -> parent and add parent -> child: a cycle.
        edges = [(s.step_id, d) for s in spec.steps for d in s.depends_on]
        child, parent = rng.choice(edges)
        by_id[parent].depends_on.append(child)
        violations = validate_read_first(spec)
        assert any(v.startswith("dependency cycle:") for v in violations)

    def test_self_loop_rejected(self) -> None:
        spec = _spec([_read("r", ["r"])])
        assert any("dependency cycle" in v for v in validate_read_first(spec))


class TestTypedPermissions:
    def test_canonical_specs_use_permission_members(self) -> None:
        for spec in FINANCE_WORKFLOW_SPECS.values():
            for step in spec.steps:
                assert type(step.permission) is Permission, step.step_id

    @pytest.mark.parametrize("value", ["finance_read", "finance_write", "fin_write"])
    def test_bare_string_permission_rejected(self, value: str) -> None:
        step = _read("r", [])
        step.permission = value  # type: ignore[assignment]
        violations = validate_read_first(_spec([step]))
        assert any("must be a Permission member" in v for v in violations)


class TestEgressClassification:
    @pytest.mark.parametrize(
        "payload",
        [
            LinearTask(title="t"),
            Notify(channel="email", recipient="ap@example.test", message="m"),
        ],
    )
    def test_egress_is_classified_not_gated(self, payload: StepPayload) -> None:
        # Deliberate (decision 2026-09-28, HAI-205): egress authorization is an
        # ABAC/PEP decision, so an ungated egress step is structurally valid
        # and reported by egress_steps() for submission to ABAC.
        spec = _spec([_read("r", []), _step("e", payload, ["r"])])
        assert validate_read_first(spec) == []
        assert [s.step_id for s in egress_steps(spec)] == ["e"]

    def test_egress_steps_excludes_non_egress(self) -> None:
        spec = _spec([_read("r", []), _mutation("m", ["r"])])
        assert egress_steps(spec) == []
