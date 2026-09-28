"""Typed fundraising workflow specification.

Semantic step definitions for governed fundraising workflows that compose
CRM (investor records), Drive (the data room), and Linear (follow-up tasks)
operations, and move an investor through the pipeline::

    prospect -> contacted -> meeting -> diligence -> committed
         \\          \\          \\          \\
          +----------+----------+----------+-> passed

Every canonical workflow is read-first, and every data-room share, stage
change, Linear follow-up, and notification sits downstream of an explicit
fundraising approval gate. The validator enforces the structural rules
(docs/workflow-validation.md). Whether a given egress needs approval in a
given tenant is decided at invocation time by ABAC and the tenant-side proxy
PEP, so the canonical specs gate egress by construction, not because the
validator requires it.

This is a harness-neutral data specification. Each step defines domain
intent only; the consuming harness resolves connector bindings, enforces
policy, and invokes provider adapters. No provider clients, credentials, or
org/workspace identifiers appear here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from agents.tool_definitions import Permission
from agents.workflows.finance import ApprovalGate, LinearTask, Notify
from agents.workflows.step_graph import validate_step_graph


class InvestorStage(str, Enum):
    """Pipeline stage of an investor."""

    PROSPECT = "prospect"
    CONTACTED = "contacted"
    MEETING = "meeting"
    DILIGENCE = "diligence"
    COMMITTED = "committed"
    PASSED = "passed"


INVESTOR_STAGE_TRANSITIONS: dict[InvestorStage, frozenset[InvestorStage]] = {
    InvestorStage.PROSPECT: frozenset({InvestorStage.CONTACTED, InvestorStage.PASSED}),
    InvestorStage.CONTACTED: frozenset({InvestorStage.MEETING, InvestorStage.PASSED}),
    InvestorStage.MEETING: frozenset({InvestorStage.DILIGENCE, InvestorStage.PASSED}),
    InvestorStage.DILIGENCE: frozenset(
        {InvestorStage.COMMITTED, InvestorStage.PASSED}
    ),
    InvestorStage.COMMITTED: frozenset(),
    InvestorStage.PASSED: frozenset(),
}

TERMINAL_INVESTOR_STAGES: frozenset[InvestorStage] = frozenset(
    stage for stage, nxt in INVESTOR_STAGE_TRANSITIONS.items() if not nxt
)


def is_valid_stage_transition(from_stage: InvestorStage, to_stage: InvestorStage) -> bool:
    """Report whether an investor may move from *from_stage* to *to_stage*."""
    return to_stage in INVESTOR_STAGE_TRANSITIONS.get(from_stage, frozenset())


# ---------------------------------------------------------------------------
# Step payloads - each dataclass captures the domain intent of one step.
# LinearTask, Notify, and ApprovalGate are shared with the finance spec.
# ---------------------------------------------------------------------------


@dataclass
class InvestorLookup:
    """Look up one investor record in the governed CRM."""

    lookup_by: Literal["id", "email", "name"]
    lookup_value: str


@dataclass
class InvestorPipelineRead:
    """List investor records in the governed CRM, optionally by stage."""

    stage: InvestorStage | None = None


@dataclass
class DataRoomRead:
    """Read the data room in the governed Drive.

    With no *document_id*, lists the data-room folder bound in the governed
    connection preset; with one, reads that document.
    """

    document_id: str | None = None


@dataclass
class DataRoomShare:
    """Grant an investor time-limited, view-only access to data-room documents."""

    investor_id: str
    document_ids: list[str] = field(default_factory=list)
    access: Literal["view"] = "view"
    expires_in_days: int = 14


@dataclass
class InvestorStageUpdate:
    """Move an investor to a new pipeline stage in the governed CRM."""

    investor_id: str
    from_stage: InvestorStage
    to_stage: InvestorStage


FundraisingStepPayload = (
    InvestorLookup
    | InvestorPipelineRead
    | DataRoomRead
    | DataRoomShare
    | InvestorStageUpdate
    | LinearTask
    | ApprovalGate
    | Notify
)


@dataclass
class FundraisingWorkflowStep:
    """A single step in a fundraising workflow DAG."""

    step_id: str
    description: str
    payload: FundraisingStepPayload
    depends_on: list[str] = field(default_factory=list)
    permission: Permission = Permission.FUNDRAISING_READ


@dataclass
class FundraisingWorkflowSpec:
    """A complete fundraising workflow specification (pure data)."""

    workflow_id: str
    name: str
    description: str
    steps: list[FundraisingWorkflowStep]
    tags: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Validation and classification
# ---------------------------------------------------------------------------

_READ_PAYLOAD_TYPES = (InvestorLookup, InvestorPipelineRead, DataRoomRead)
_MUTATION_PAYLOAD_TYPES = (DataRoomShare, InvestorStageUpdate)
# Classified for ABAC egress-class requests, not gated by the validator; see
# the matching note in agents.workflows.finance.
_EGRESS_PAYLOAD_TYPES = (LinearTask, Notify)


def fundraising_egress_steps(
    spec: FundraisingWorkflowSpec,
) -> list[FundraisingWorkflowStep]:
    """Return the steps whose execution leaves the governed boundary.

    A classification helper, not a gate: it tells a harness which steps to
    submit to ABAC as egress-class requests.
    """
    return [s for s in spec.steps if isinstance(s.payload, _EGRESS_PAYLOAD_TYPES)]


def validate_fundraising_workflow(spec: FundraisingWorkflowSpec) -> list[str]:
    """Validate a fundraising workflow's structure.

    Applies the shared step-graph rules (unique ids, resolvable dependencies,
    no cycles, typed permissions, every mutation has a read and an approval
    gate among its ancestors, mutations hold ``fundraising_write``, gates hold
    ``fundraising_approve``) and checks every stage update is a valid
    pipeline transition. A spec that passes is well formed, not permitted.

    Returns a list of violations; an empty list means the spec is valid.
    """
    violations = validate_step_graph(
        spec.steps,
        read_types=_READ_PAYLOAD_TYPES,
        mutation_types=_MUTATION_PAYLOAD_TYPES,
        gate_types=(ApprovalGate,),
        mutation_permissions=(Permission.FUNDRAISING_WRITE,),
        approve_permission=Permission.FUNDRAISING_APPROVE,
    )
    for step in spec.steps:
        payload = step.payload
        if isinstance(payload, InvestorStageUpdate) and not is_valid_stage_transition(
            payload.from_stage, payload.to_stage
        ):
            violations.append(
                f"{step.step_id}: invalid stage transition "
                f"{payload.from_stage.value} -> {payload.to_stage.value}"
            )
    return violations


# ---------------------------------------------------------------------------
# Pre-built workflow specs
# ---------------------------------------------------------------------------

_APPROVER = "fundraising_approver"


def _lookup_investor(depends_on: list[str] | None = None) -> FundraisingWorkflowStep:
    return FundraisingWorkflowStep(
        step_id="lookup_investor",
        description="Look up the investor record in the governed CRM",
        payload=InvestorLookup(lookup_by="id", lookup_value=""),
        depends_on=depends_on or [],
    )


def _approval(step_id: str, reason: str, depends_on: list[str]) -> FundraisingWorkflowStep:
    return FundraisingWorkflowStep(
        step_id=step_id,
        description=reason,
        payload=ApprovalGate(required_role=_APPROVER, reason=reason),
        permission=Permission.FUNDRAISING_APPROVE,
        depends_on=depends_on,
    )


def _followup(title: str, depends_on: list[str]) -> FundraisingWorkflowStep:
    return FundraisingWorkflowStep(
        step_id="create_followup_task",
        description="Create a Linear follow-up task for the investor",
        payload=LinearTask(title=title, labels=["fundraising"], priority="high"),
        permission=Permission.FUNDRAISING_WRITE,
        depends_on=depends_on,
    )


def _stage_update(
    from_stage: InvestorStage, to_stage: InvestorStage, depends_on: list[str]
) -> FundraisingWorkflowStep:
    return FundraisingWorkflowStep(
        step_id="advance_stage",
        description=f"Move the investor from {from_stage.value} to {to_stage.value}",
        payload=InvestorStageUpdate(
            investor_id="", from_stage=from_stage, to_stage=to_stage
        ),
        permission=Permission.FUNDRAISING_WRITE,
        depends_on=depends_on,
    )


def investor_outreach_workflow() -> FundraisingWorkflowSpec:
    """First outreach to a prospect: prospect -> contacted.

      1. Look up the investor in CRM
      2. Approval gate
      3. Create a Linear follow-up task (egress)
      4. Notify the investor (egress)
      5. Advance the stage (mutation)
    """
    return FundraisingWorkflowSpec(
        workflow_id="fundraising.investor_outreach",
        name="Investor Outreach",
        description="Approve and record first outreach to a prospective investor",
        tags=["fundraising", "investor", "outreach", "approval"],
        steps=[
            _lookup_investor(),
            _approval(
                "approve_outreach",
                "Outreach to an investor requires fundraising approval",
                ["lookup_investor"],
            ),
            _followup("Follow up with investor", ["approve_outreach"]),
            FundraisingWorkflowStep(
                step_id="notify_investor",
                description="Send the approved outreach message to the investor",
                payload=Notify(channel="email", recipient="", message=""),
                permission=Permission.FUNDRAISING_WRITE,
                depends_on=["approve_outreach"],
            ),
            _stage_update(
                InvestorStage.PROSPECT, InvestorStage.CONTACTED, ["notify_investor"]
            ),
        ],
    )


def data_room_share_workflow() -> FundraisingWorkflowSpec:
    """Open the data room to an investor: meeting -> diligence.

      1. Look up the investor in CRM
      2. Read the data room in Drive
      3. Approval gate
      4. Share the data room, view-only and time-limited (mutation)
      5. Advance the stage (mutation)
      6. Create a Linear follow-up task (egress)
      7. Notify the investor (egress)
    """
    return FundraisingWorkflowSpec(
        workflow_id="fundraising.data_room_share",
        name="Data Room Share",
        description="Approve and grant an investor view-only data-room access",
        tags=["fundraising", "investor", "data_room", "approval"],
        steps=[
            _lookup_investor(),
            FundraisingWorkflowStep(
                step_id="read_data_room",
                description="List the data-room documents in the governed Drive",
                payload=DataRoomRead(),
                depends_on=["lookup_investor"],
            ),
            _approval(
                "approve_share",
                "Sharing the data room requires fundraising approval",
                ["read_data_room"],
            ),
            FundraisingWorkflowStep(
                step_id="share_data_room",
                description="Grant the investor view-only, time-limited access",
                payload=DataRoomShare(investor_id=""),
                permission=Permission.FUNDRAISING_WRITE,
                depends_on=["approve_share"],
            ),
            _stage_update(
                InvestorStage.MEETING, InvestorStage.DILIGENCE, ["share_data_room"]
            ),
            _followup("Track investor diligence", ["share_data_room"]),
            FundraisingWorkflowStep(
                step_id="notify_investor",
                description="Tell the investor the data room is available",
                payload=Notify(channel="email", recipient="", message=""),
                permission=Permission.FUNDRAISING_WRITE,
                depends_on=["share_data_room"],
            ),
        ],
    )


def investor_decision_workflow(
    outcome: InvestorStage = InvestorStage.COMMITTED,
) -> FundraisingWorkflowSpec:
    """Record an investor's decision: diligence -> committed or passed.

      1. Read the diligence pipeline in CRM
      2. Look up the investor in CRM
      3. Approval gate
      4. Record the decision stage (mutation)
      5. Create a Linear follow-up task (egress)
      6. Notify the team (egress)
    """
    if outcome not in TERMINAL_INVESTOR_STAGES:
        raise ValueError(
            f"outcome must be a terminal stage "
            f"({', '.join(sorted(s.value for s in TERMINAL_INVESTOR_STAGES))}), "
            f"got {outcome.value!r}"
        )
    return FundraisingWorkflowSpec(
        workflow_id="fundraising.investor_decision",
        name="Investor Decision",
        description="Approve and record an investor's commit or pass decision",
        tags=["fundraising", "investor", "decision", "approval"],
        steps=[
            FundraisingWorkflowStep(
                step_id="read_pipeline",
                description="List investors in diligence in the governed CRM",
                payload=InvestorPipelineRead(stage=InvestorStage.DILIGENCE),
            ),
            _lookup_investor(["read_pipeline"]),
            _approval(
                "approve_decision",
                "Recording an investor decision requires fundraising approval",
                ["lookup_investor"],
            ),
            _stage_update(InvestorStage.DILIGENCE, outcome, ["approve_decision"]),
            _followup("Close out investor decision", ["advance_stage"]),
            FundraisingWorkflowStep(
                step_id="notify_team",
                description="Tell the fundraising team about the decision",
                payload=Notify(channel="slack", recipient="", message=""),
                permission=Permission.FUNDRAISING_WRITE,
                depends_on=["advance_stage"],
            ),
        ],
    )


FUNDRAISING_WORKFLOW_SPECS: dict[str, FundraisingWorkflowSpec] = {
    "fundraising.investor_outreach": investor_outreach_workflow(),
    "fundraising.data_room_share": data_room_share_workflow(),
    "fundraising.investor_decision": investor_decision_workflow(),
}

__all__ = [
    "FUNDRAISING_WORKFLOW_SPECS",
    "INVESTOR_STAGE_TRANSITIONS",
    "TERMINAL_INVESTOR_STAGES",
    "ApprovalGate",
    "DataRoomRead",
    "DataRoomShare",
    "FundraisingStepPayload",
    "FundraisingWorkflowSpec",
    "FundraisingWorkflowStep",
    "InvestorLookup",
    "InvestorPipelineRead",
    "InvestorStage",
    "InvestorStageUpdate",
    "LinearTask",
    "Notify",
    "data_room_share_workflow",
    "fundraising_egress_steps",
    "investor_decision_workflow",
    "investor_outreach_workflow",
    "is_valid_stage_transition",
    "validate_fundraising_workflow",
]
