"""Tests for the harness-neutral fundraising workflow spec (HAI-207)."""

from __future__ import annotations

import dataclasses
import itertools

import pytest

from agents import Permission
from agents.workflows.fundraising import (
    FUNDRAISING_WORKFLOW_SPECS,
    INVESTOR_STAGE_TRANSITIONS,
    TERMINAL_INVESTOR_STAGES,
    DataRoomRead,
    DataRoomShare,
    FundraisingWorkflowSpec,
    FundraisingWorkflowStep,
    InvestorLookup,
    InvestorPipelineRead,
    InvestorStage,
    InvestorStageUpdate,
    LinearTask,
    Notify,
    data_room_share_workflow,
    fundraising_egress_steps,
    investor_decision_workflow,
    investor_outreach_workflow,
    is_valid_stage_transition,
    validate_fundraising_workflow,
)

S = InvestorStage
SPECS = list(FUNDRAISING_WORKFLOW_SPECS.values())
SPEC_IDS = list(FUNDRAISING_WORKFLOW_SPECS)


class TestInvestorStateMachine:
    def test_stages(self) -> None:
        assert [s.value for s in InvestorStage] == [
            "prospect",
            "contacted",
            "meeting",
            "diligence",
            "committed",
            "passed",
        ]

    def test_forward_path(self) -> None:
        path = [S.PROSPECT, S.CONTACTED, S.MEETING, S.DILIGENCE, S.COMMITTED]
        for a, b in itertools.pairwise(path):
            assert is_valid_stage_transition(a, b)

    @pytest.mark.parametrize("stage", [S.PROSPECT, S.CONTACTED, S.MEETING, S.DILIGENCE])
    def test_any_open_stage_can_pass(self, stage: InvestorStage) -> None:
        assert is_valid_stage_transition(stage, S.PASSED)

    def test_terminal_stages(self) -> None:
        assert TERMINAL_INVESTOR_STAGES == frozenset({S.COMMITTED, S.PASSED})
        for stage in TERMINAL_INVESTOR_STAGES:
            assert INVESTOR_STAGE_TRANSITIONS[stage] == frozenset()

    @pytest.mark.parametrize(
        ("a", "b"),
        [
            (S.PROSPECT, S.MEETING),  # skip
            (S.PROSPECT, S.COMMITTED),  # skip to terminal
            (S.MEETING, S.CONTACTED),  # backwards
            (S.COMMITTED, S.PASSED),  # out of terminal
            (S.PASSED, S.PROSPECT),  # reopen
            (S.DILIGENCE, S.DILIGENCE),  # self
        ],
    )
    def test_invalid_transitions(self, a: InvestorStage, b: InvestorStage) -> None:
        assert not is_valid_stage_transition(a, b)

    def test_every_stage_has_transitions_entry(self) -> None:
        assert set(INVESTOR_STAGE_TRANSITIONS) == set(InvestorStage)


class TestCanonicalSpecs:
    def test_registry(self) -> None:
        assert SPEC_IDS == [
            "fundraising.investor_outreach",
            "fundraising.data_room_share",
            "fundraising.investor_decision",
        ]
        for workflow_id, spec in FUNDRAISING_WORKFLOW_SPECS.items():
            assert spec.workflow_id == workflow_id
            assert "fundraising" in spec.tags

    @pytest.mark.parametrize("spec", SPECS, ids=SPEC_IDS)
    def test_valid(self, spec: FundraisingWorkflowSpec) -> None:
        assert validate_fundraising_workflow(spec) == []

    @pytest.mark.parametrize("spec", SPECS, ids=SPEC_IDS)
    def test_permissions_typed_and_fundraising_scoped(
        self, spec: FundraisingWorkflowSpec
    ) -> None:
        for step in spec.steps:
            assert type(step.permission) is Permission
            assert step.permission.value.startswith("fundraising_")

    @pytest.mark.parametrize("spec", SPECS, ids=SPEC_IDS)
    def test_egress_permission_is_write(self, spec: FundraisingWorkflowSpec) -> None:
        egress = fundraising_egress_steps(spec)
        assert egress, "every canonical spec has a follow-up or notification"
        for step in egress:
            assert isinstance(step.payload, (LinearTask, Notify))
            assert step.permission is Permission.FUNDRAISING_WRITE

    def test_outreach_shape(self) -> None:
        spec = investor_outreach_workflow()
        kinds = {type(s.payload) for s in spec.steps}
        assert {
            InvestorLookup,
            LinearTask,
            Notify,
            InvestorStageUpdate,
        } <= kinds
        update = next(
            s.payload for s in spec.steps if isinstance(s.payload, InvestorStageUpdate)
        )
        assert (update.from_stage, update.to_stage) == (S.PROSPECT, S.CONTACTED)

    def test_data_room_share_shape(self) -> None:
        spec = data_room_share_workflow()
        kinds = {type(s.payload) for s in spec.steps}
        assert {
            InvestorLookup,
            DataRoomRead,
            DataRoomShare,
            LinearTask,
            Notify,
        } <= kinds
        share = next(
            s.payload for s in spec.steps if isinstance(s.payload, DataRoomShare)
        )
        assert share.access == "view"
        update = next(
            s.payload for s in spec.steps if isinstance(s.payload, InvestorStageUpdate)
        )
        assert (update.from_stage, update.to_stage) == (S.MEETING, S.DILIGENCE)

    @pytest.mark.parametrize("outcome", [S.COMMITTED, S.PASSED])
    def test_decision_outcomes(self, outcome: InvestorStage) -> None:
        spec = investor_decision_workflow(outcome)
        assert validate_fundraising_workflow(spec) == []
        assert any(isinstance(s.payload, InvestorPipelineRead) for s in spec.steps)
        update = next(
            s.payload for s in spec.steps if isinstance(s.payload, InvestorStageUpdate)
        )
        assert (update.from_stage, update.to_stage) == (S.DILIGENCE, outcome)

    def test_decision_rejects_non_terminal_outcome(self) -> None:
        with pytest.raises(ValueError, match="terminal"):
            investor_decision_workflow(S.MEETING)

    def test_specs_carry_no_org_or_workspace_or_credentials(self) -> None:
        forbidden = (
            "org_id",
            "workspace",
            "tenant",
            "token",
            "secret",
            "credential",
            "url",
        )
        for spec in SPECS:
            for step in spec.steps:
                for f in dataclasses.fields(step.payload):
                    assert not any(h in f.name for h in forbidden), (
                        step.step_id,
                        f.name,
                    )


def _without_step(
    spec: FundraisingWorkflowSpec, step_id: str
) -> FundraisingWorkflowSpec:
    """Remove a step and rewire its dependents to its own dependencies."""
    removed = next(s for s in spec.steps if s.step_id == step_id)
    steps = []
    for step in spec.steps:
        if step.step_id == step_id:
            continue
        deps: list[str] = []
        for dep in step.depends_on:
            for d in removed.depends_on if dep == step_id else [dep]:
                if d not in deps:
                    deps.append(d)
        steps.append(dataclasses.replace(step, depends_on=deps))
    return dataclasses.replace(spec, steps=steps)


class TestMutatedVariantsRejected:
    @pytest.mark.parametrize("spec", SPECS, ids=SPEC_IDS)
    def test_bare_string_permission_is_rejected(
        self, spec: FundraisingWorkflowSpec
    ) -> None:
        first = spec.steps[0]
        steps = [
            dataclasses.replace(first, permission="fundraising_read"),
            *spec.steps[1:],
        ]
        violations = validate_fundraising_workflow(
            dataclasses.replace(spec, steps=steps)
        )
        assert any("must be a Permission member" in v for v in violations)

    @pytest.mark.parametrize("spec", SPECS, ids=SPEC_IDS)
    def test_cycle_is_rejected(self, spec: FundraisingWorkflowSpec) -> None:
        first, last = spec.steps[0], spec.steps[-1]
        steps = [
            dataclasses.replace(first, depends_on=[*first.depends_on, last.step_id]),
            *spec.steps[1:],
        ]
        violations = validate_fundraising_workflow(
            dataclasses.replace(spec, steps=steps)
        )
        assert any(v.startswith("dependency cycle:") for v in violations)

    def test_share_with_finance_permission_is_rejected(self) -> None:
        spec = data_room_share_workflow()
        steps = [
            dataclasses.replace(s, permission=Permission.FINANCE_WRITE)
            if isinstance(s.payload, DataRoomShare)
            else s
            for s in spec.steps
        ]
        violations = validate_fundraising_workflow(
            dataclasses.replace(spec, steps=steps)
        )
        assert any("mutation step requires fundraising_write" in v for v in violations)

    def test_invalid_stage_transition_is_rejected(self) -> None:
        spec = investor_outreach_workflow()
        steps = [
            dataclasses.replace(
                s,
                payload=InvestorStageUpdate(
                    investor_id="", from_stage=S.PROSPECT, to_stage=S.COMMITTED
                ),
            )
            if isinstance(s.payload, InvestorStageUpdate)
            else s
            for s in spec.steps
        ]
        violations = validate_fundraising_workflow(
            dataclasses.replace(spec, steps=steps)
        )
        assert any(
            "invalid stage transition prospect -> committed" in v for v in violations
        )


class TestStepConstruction:
    def test_default_permission_is_fundraising_read(self) -> None:
        step = FundraisingWorkflowStep(
            step_id="r", description="r", payload=DataRoomRead()
        )
        assert step.permission is Permission.FUNDRAISING_READ

    def test_ungated_egress_only_spec_is_structurally_valid(self) -> None:
        # Pinned deliberately: egress authorization is ABAC's decision, so the
        # validator accepts it; the canonical specs gate egress by construction.
        spec = FundraisingWorkflowSpec(
            workflow_id="fundraising.test",
            name="t",
            description="t",
            steps=[
                FundraisingWorkflowStep(
                    step_id="lookup",
                    description="lookup",
                    payload=InvestorLookup(lookup_by="id", lookup_value="inv-1"),
                ),
                FundraisingWorkflowStep(
                    step_id="notify",
                    description="notify",
                    payload=Notify(channel="slack", recipient="", message="m"),
                    depends_on=["lookup"],
                    permission=Permission.FUNDRAISING_WRITE,
                ),
            ],
        )
        assert validate_fundraising_workflow(spec) == []
        assert [s.step_id for s in fundraising_egress_steps(spec)] == ["notify"]


def test_package_exports() -> None:
    from agents import workflows

    for name in (
        "FUNDRAISING_WORKFLOW_SPECS",
        "InvestorStage",
        "FundraisingWorkflowSpec",
        "validate_fundraising_workflow",
        "fundraising_egress_steps",
    ):
        assert hasattr(workflows, name), name
