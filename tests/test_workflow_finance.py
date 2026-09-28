"""Tests for the finance/bookkeeping workflow specification module."""

from __future__ import annotations

from agents import Permission
from agents.workflows.finance import (
    FINANCE_WORKFLOW_SPECS,
    ApprovalGate,
    CRMLookup,
    CRMUpdate,
    DriveArchive,
    DriveRead,
    FinanceEntity,
    FinanceWorkflowSpec,
    FinanceWorkflowState,
    FinanceWorkflowStep,
    LinearTask,
    Notify,
    StepPayload,
    egress_steps,
    expense_report_workflow,
    invoice_processing_workflow,
    validate_read_first,
    vendor_onboarding_workflow,
)


class TestFinanceWorkflowTypes:
    def test_finance_entity_values(self):
        assert FinanceEntity.INVOICE.value == "invoice"
        assert FinanceEntity.RECEIPT.value == "receipt"
        assert FinanceEntity.STATEMENT.value == "statement"
        assert FinanceEntity.PAYMENT.value == "payment"
        assert FinanceEntity.EXPENSE.value == "expense"
        assert FinanceEntity.QUOTE.value == "quote"
        assert FinanceEntity.PURCHASE_ORDER.value == "purchase_order"
        assert FinanceEntity.CREDIT_NOTE.value == "credit_note"
        assert FinanceEntity.VENDOR.value == "vendor"
        assert FinanceEntity.CUSTOMER.value == "customer"

    def test_finance_workflow_state_values(self):
        assert FinanceWorkflowState.DRAFT.value == "draft"
        assert FinanceWorkflowState.PENDING_REVIEW.value == "pending_review"
        assert FinanceWorkflowState.APPROVED.value == "approved"
        assert FinanceWorkflowState.REJECTED.value == "rejected"
        assert FinanceWorkflowState.COMPLETED.value == "completed"
        assert FinanceWorkflowState.CANCELLED.value == "cancelled"
        assert FinanceWorkflowState.ESCALATED.value == "escalated"

    def test_step_payload_union(self):
        read = DriveRead(entity=FinanceEntity.INVOICE)
        assert isinstance(read, StepPayload)

        gate = ApprovalGate()
        assert isinstance(gate, StepPayload)

        task = LinearTask(title="Test", labels=["finance"])
        assert isinstance(task, StepPayload)

        update = CRMUpdate(entity_type="customer", record_id="123", updates={})
        assert isinstance(update, StepPayload)

        lookup = CRMLookup(entity_type="vendor", lookup_by="name", lookup_value="Acme")
        assert isinstance(lookup, StepPayload)

        archive = DriveArchive(entity=FinanceEntity.INVOICE, document_id="doc_1")
        assert isinstance(archive, StepPayload)

        notify = Notify(channel="email", recipient="test@example.com", message="Done")
        assert isinstance(notify, StepPayload)

    def test_workflow_spec_construction(self):
        spec = FinanceWorkflowSpec(
            workflow_id="test.workflow",
            name="Test",
            description="A test workflow",
            steps=[
                FinanceWorkflowStep(
                    step_id="step_1",
                    description="Read invoice",
                    payload=DriveRead(entity=FinanceEntity.INVOICE),
                ),
            ],
        )
        assert spec.workflow_id == "test.workflow"
        assert spec.name == "Test"
        assert len(spec.steps) == 1
        assert spec.steps[0].step_id == "step_1"

    def test_step_depends_on_defaults_to_empty_list(self):
        step = FinanceWorkflowStep(
            step_id="s1",
            description="Test",
            payload=DriveRead(entity=FinanceEntity.INVOICE),
        )
        assert step.depends_on == []

    def test_step_tags_defaults_to_empty_list(self):
        spec = FinanceWorkflowSpec(
            workflow_id="test", name="Test", description="", steps=[]
        )
        assert spec.tags == []

    def test_drive_read_defaults(self):
        payload = DriveRead(entity=FinanceEntity.INVOICE)
        assert payload.query is None
        assert payload.document_id is None
        assert payload.mime_type is None

    def test_approval_gate_defaults(self):
        gate = ApprovalGate()
        assert gate.required_role == "finance_approver"
        assert gate.reason == ""
        assert gate.timeout_hours == 72
        assert gate.escalation_role is None

    def test_linear_task_defaults(self):
        task = LinearTask(title="Test")
        assert task.description is None
        assert task.assignee is None
        assert task.labels == []
        assert task.priority == "medium"
        assert task.state == "backlog"


class TestCanonicalWorkflows:
    def test_invoice_processing_has_correct_structure(self):
        spec = invoice_processing_workflow()
        assert spec.workflow_id == "finance.invoice_processing"
        assert spec.name == "Invoice Processing"
        assert len(spec.steps) == 7

    def test_invoice_processing_starts_with_read(self):
        spec = invoice_processing_workflow()
        assert isinstance(spec.steps[0].payload, DriveRead)
        assert spec.steps[0].payload.entity == FinanceEntity.INVOICE

    def test_invoice_processing_ends_with_notification(self):
        spec = invoice_processing_workflow()
        assert isinstance(spec.steps[-1].payload, Notify)

    def test_invoice_processing_has_approval_gate(self):
        spec = invoice_processing_workflow()
        assert any(isinstance(s.payload, ApprovalGate) for s in spec.steps)

    def test_invoice_processing_mutations_after_approval(self):
        spec = invoice_processing_workflow()
        approval_idx = next(
            i for i, s in enumerate(spec.steps) if isinstance(s.payload, ApprovalGate)
        )
        mutation_idxs = [
            i
            for i, s in enumerate(spec.steps)
            if isinstance(s.payload, (CRMUpdate, DriveArchive))
        ]
        for idx in mutation_idxs:
            assert idx > approval_idx, (
                f"Mutation {spec.steps[idx].step_id} should appear after "
                f"the approval gate (index {idx} > {approval_idx})"
            )

    def test_invoice_processing_mutations_depend_on_approval(self):
        spec = invoice_processing_workflow()
        for step in spec.steps:
            if isinstance(step.payload, (CRMUpdate, DriveArchive)):
                assert "approval" in step.depends_on, (
                    f"{step.step_id} must depend on approval gate"
                )

    def test_expense_report_has_correct_structure(self):
        spec = expense_report_workflow()
        assert spec.workflow_id == "finance.expense_report"
        assert spec.name == "Expense Report Processing"
        assert len(spec.steps) == 6

    def test_expense_report_starts_with_read(self):
        spec = expense_report_workflow()
        assert isinstance(spec.steps[0].payload, DriveRead)
        assert spec.steps[0].payload.entity == FinanceEntity.RECEIPT

    def test_expense_report_ends_with_notification(self):
        spec = expense_report_workflow()
        assert isinstance(spec.steps[-1].payload, Notify)

    def test_expense_report_has_approval_gate(self):
        spec = expense_report_workflow()
        assert any(isinstance(s.payload, ApprovalGate) for s in spec.steps)

    def test_vendor_onboarding_has_correct_structure(self):
        spec = vendor_onboarding_workflow()
        assert spec.workflow_id == "finance.vendor_onboarding"
        assert spec.name == "Vendor Onboarding"
        assert len(spec.steps) == 7

    def test_vendor_onboarding_starts_with_read(self):
        spec = vendor_onboarding_workflow()
        assert isinstance(spec.steps[0].payload, DriveRead)
        assert spec.steps[0].payload.entity == FinanceEntity.VENDOR

    def test_vendor_onboarding_ends_with_notification(self):
        spec = vendor_onboarding_workflow()
        assert isinstance(spec.steps[-1].payload, Notify)

    def test_full_registry(self):
        assert set(FINANCE_WORKFLOW_SPECS.keys()) == {
            "finance.invoice_processing",
            "finance.expense_report",
            "finance.vendor_onboarding",
        }


class TestReadFirstValidation:
    def test_valid_invoice_processing_passes(self):
        spec = invoice_processing_workflow()
        assert validate_read_first(spec) == []

    def test_valid_expense_report_passes(self):
        spec = expense_report_workflow()
        assert validate_read_first(spec) == []

    def test_valid_vendor_onboarding_passes(self):
        spec = vendor_onboarding_workflow()
        assert validate_read_first(spec) == []

    def test_mutation_without_read_dependency_flagged(self):
        spec = FinanceWorkflowSpec(
            workflow_id="test.bad",
            name="Bad",
            description="Mutation without read dependency",
            steps=[
                FinanceWorkflowStep(
                    step_id="update",
                    description="Update CRM",
                    payload=CRMUpdate(
                        entity_type="customer", record_id="123", updates={}
                    ),
                    permission=Permission.FINANCE_WRITE,
                ),
            ],
        )
        violations = validate_read_first(spec)
        assert any("must depend on a read step" in v for v in violations)
        assert any("must depend on an approval gate" in v for v in violations)

    def test_mutation_missing_approval_dependency_flagged(self):
        spec = FinanceWorkflowSpec(
            workflow_id="test.bad",
            name="Bad",
            description="Mutation with read but no approval",
            steps=[
                FinanceWorkflowStep(
                    step_id="read",
                    description="Read invoice",
                    payload=DriveRead(entity=FinanceEntity.INVOICE),
                ),
                FinanceWorkflowStep(
                    step_id="update",
                    description="Update CRM",
                    payload=CRMUpdate(
                        entity_type="customer", record_id="123", updates={}
                    ),
                    permission=Permission.FINANCE_WRITE,
                    depends_on=["read"],
                ),
            ],
        )
        violations = validate_read_first(spec)
        assert any("must depend on an approval gate" in v for v in violations)
        assert not any("must depend on a read step" in v for v in violations)

    def test_mutation_with_wrong_permission_flagged(self):
        spec = FinanceWorkflowSpec(
            workflow_id="test.bad",
            name="Bad",
            description="Mutation with wrong permission",
            steps=[
                FinanceWorkflowStep(
                    step_id="read",
                    description="Read",
                    payload=DriveRead(entity=FinanceEntity.INVOICE),
                ),
                FinanceWorkflowStep(
                    step_id="update",
                    description="Update CRM",
                    payload=CRMUpdate(
                        entity_type="customer", record_id="123", updates={}
                    ),
                    depends_on=["read"],
                    permission=Permission.FINANCE_READ,
                ),
            ],
        )
        violations = validate_read_first(spec)
        assert any("permission" in v for v in violations)

    def test_approval_gate_with_wrong_permission_flagged(self):
        spec = FinanceWorkflowSpec(
            workflow_id="test.bad",
            name="Bad",
            description="Approval with wrong permission",
            steps=[
                FinanceWorkflowStep(
                    step_id="approve",
                    description="Approve",
                    payload=ApprovalGate(),
                    permission=Permission.FINANCE_READ,
                ),
            ],
        )
        violations = validate_read_first(spec)
        assert any("approval gate requires finance_approve" in v for v in violations)

    def test_broken_dependency_flagged(self):
        spec = FinanceWorkflowSpec(
            workflow_id="test.bad",
            name="Bad",
            description="Missing dependency",
            steps=[
                FinanceWorkflowStep(
                    step_id="step_1",
                    description="Read",
                    payload=DriveRead(entity=FinanceEntity.INVOICE),
                    depends_on=["nonexistent"],
                ),
            ],
        )
        violations = validate_read_first(spec)
        assert any("depends_on" in v for v in violations)
        assert "nonexistent" in violations[0]

    def test_empty_workflow_validates(self):
        spec = FinanceWorkflowSpec(
            workflow_id="test.empty",
            name="Empty",
            description="Empty workflow",
            steps=[],
        )
        assert validate_read_first(spec) == []

    def test_read_only_workflow_validates(self):
        spec = FinanceWorkflowSpec(
            workflow_id="test.read_only",
            name="Read Only",
            description="Read-only workflow",
            steps=[
                FinanceWorkflowStep(
                    step_id="read_1",
                    description="Read invoice",
                    payload=DriveRead(entity=FinanceEntity.INVOICE),
                ),
                FinanceWorkflowStep(
                    step_id="lookup_1",
                    description="Look up customer",
                    payload=CRMLookup(
                        entity_type="customer",
                        lookup_by="name",
                        lookup_value="Acme",
                    ),
                    depends_on=["read_1"],
                ),
            ],
        )
        assert validate_read_first(spec) == []


class TestWorkflowTags:
    def test_invoice_processing_tags(self):
        spec = invoice_processing_workflow()
        assert "finance" in spec.tags
        assert "invoice" in spec.tags
        assert "approval" in spec.tags

    def test_expense_report_tags(self):
        spec = expense_report_workflow()
        assert "finance" in spec.tags
        assert "expense" in spec.tags
        assert "approval" in spec.tags

    def test_vendor_onboarding_tags(self):
        spec = vendor_onboarding_workflow()
        assert "finance" in spec.tags
        assert "vendor" in spec.tags
        assert "onboarding" in spec.tags


def _read(step_id: str, depends_on: list[str] | None = None) -> FinanceWorkflowStep:
    return FinanceWorkflowStep(
        step_id=step_id,
        description="read",
        payload=DriveRead(entity=FinanceEntity.INVOICE),
        depends_on=depends_on or [],
    )


def _gate(step_id: str, depends_on: list[str] | None = None) -> FinanceWorkflowStep:
    return FinanceWorkflowStep(
        step_id=step_id,
        description="gate",
        payload=ApprovalGate(),
        permission=Permission.FINANCE_APPROVE,
        depends_on=depends_on or [],
    )


def _mutation(step_id: str, depends_on: list[str]) -> FinanceWorkflowStep:
    return FinanceWorkflowStep(
        step_id=step_id,
        description="mutate",
        payload=CRMUpdate(entity_type="customer", record_id="c-1", updates={}),
        permission=Permission.FINANCE_WRITE,
        depends_on=depends_on,
    )


def _spec(steps: list[FinanceWorkflowStep]) -> FinanceWorkflowSpec:
    return FinanceWorkflowSpec(
        workflow_id="test.spec", name="Test", description="Test", steps=steps
    )


class TestCycleDetection:
    """A spec is a DAG by contract; a cycle must be rejected here rather than
    reaching a harness interpreter that would not terminate."""

    def test_two_step_cycle_is_reported(self):
        spec = _spec([_read("a", ["b"]), _read("b", ["a"])])
        violations = validate_read_first(spec)
        assert any("dependency cycle" in v for v in violations)

    def test_self_dependency_is_reported(self):
        spec = _spec([_read("a", ["a"])])
        violations = validate_read_first(spec)
        assert any("dependency cycle" in v for v in violations)

    def test_longer_cycle_is_reported(self):
        spec = _spec([_read("a", ["c"]), _read("b", ["a"]), _read("c", ["b"])])
        violations = validate_read_first(spec)
        assert any("dependency cycle" in v for v in violations)

    def test_cycle_message_names_the_steps(self):
        spec = _spec([_read("a", ["b"]), _read("b", ["a"])])
        cycle = next(
            v for v in validate_read_first(spec) if v.startswith("dependency cycle")
        )
        assert "a" in cycle and "b" in cycle

    def test_diamond_is_not_a_cycle(self):
        # a -> b, a -> c, b -> d, c -> d shares ancestors without cycling.
        spec = _spec(
            [
                _read("a"),
                _read("b", ["a"]),
                _read("c", ["a"]),
                _read("d", ["b", "c"]),
            ]
        )
        assert validate_read_first(spec) == []

    def test_canonical_workflows_are_acyclic(self):
        for factory in (
            invoice_processing_workflow,
            expense_report_workflow,
            vendor_onboarding_workflow,
        ):
            assert validate_read_first(factory()) == []


class TestApprovalReachability:
    """A gate may be any ancestor of a mutation, not only a direct dependency."""

    def test_transitive_gate_satisfies_the_mutation(self):
        spec = _spec(
            [
                _read("read"),
                _gate("gate", ["read"]),
                _read("enrich", ["gate"]),
                _mutation("update", ["enrich"]),
            ]
        )
        assert validate_read_first(spec) == []

    def test_direct_gate_still_satisfies_the_mutation(self):
        spec = _spec(
            [
                _read("read"),
                _gate("gate", ["read"]),
                _mutation("update", ["gate", "read"]),
            ]
        )
        assert validate_read_first(spec) == []

    def test_mutation_with_no_gate_anywhere_upstream_is_flagged(self):
        spec = _spec([_read("read"), _mutation("update", ["read"])])
        violations = validate_read_first(spec)
        assert any("approval gate" in v for v in violations)

    def test_gate_on_a_parallel_branch_does_not_count(self):
        # The gate is not an ancestor of the mutation, so it cannot block it.
        spec = _spec(
            [
                _read("read"),
                _gate("gate", ["read"]),
                _mutation("update", ["read"]),
            ]
        )
        violations = validate_read_first(spec)
        assert any("approval gate" in v for v in violations)

    def test_transitive_read_satisfies_the_read_requirement(self):
        spec = _spec(
            [
                _read("read"),
                _gate("gate", ["read"]),
                _mutation("update", ["gate"]),
            ]
        )
        assert validate_read_first(spec) == []


class TestGraphWellFormedness:
    def test_duplicate_step_id_is_reported(self):
        spec = _spec([_read("dup"), _read("dup")])
        assert any("duplicate step_id" in v for v in validate_read_first(spec))

    def test_dangling_dependency_is_reported(self):
        spec = _spec([_read("a", ["missing"])])
        assert any("not found in steps" in v for v in validate_read_first(spec))


class TestEgressClassification:
    """Egress steps are classified for the harness to submit to ABAC; the
    validator deliberately does not decide whether they are permitted."""

    def test_egress_steps_lists_task_and_notify(self):
        ids = [s.step_id for s in egress_steps(invoice_processing_workflow())]
        assert ids == ["create_review_task", "notify_customer"]

    def test_egress_is_not_a_validation_violation(self):
        # An ungated Notify is well formed. Whether this subject may send it is
        # an ABAC decision made at invocation time, not a property of the spec.
        spec = _spec(
            [
                _read("read"),
                FinanceWorkflowStep(
                    step_id="leak",
                    description="notify",
                    payload=Notify(
                        channel="email", recipient="a@example.test", message="balance"
                    ),
                    depends_on=["read"],
                ),
            ]
        )
        assert validate_read_first(spec) == []

    def test_every_canonical_workflow_exposes_its_egress_surface(self):
        for factory in (
            invoice_processing_workflow,
            expense_report_workflow,
            vendor_onboarding_workflow,
        ):
            assert egress_steps(factory()), "workflow should declare egress steps"
