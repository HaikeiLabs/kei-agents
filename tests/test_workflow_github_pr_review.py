"""Tests for the harness-neutral GitHub PR review workflow module."""

from __future__ import annotations

from agents.permissions import Permission
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


class TestPRReviewInput:
    def test_default_input(self):
        inp = PRReviewInput(pr_number=42)
        assert inp.pr_number == 42
        assert inp.ref is None
        assert inp.review_depth == "full"

    def test_validation_passes(self):
        inp = PRReviewInput(pr_number=1)
        assert inp.validate() == []

    def test_validation_fails_negative_number(self):
        inp = PRReviewInput(pr_number=0)
        violations = inp.validate()
        assert any("positive integer" in v for v in violations)

    def test_validation_fails_invalid_depth(self):
        inp = PRReviewInput(pr_number=1, review_depth="deep")
        violations = inp.validate()
        assert any("review_depth" in v for v in violations)

    def test_validation_passes_valid_depths(self):
        for depth in ("full", "surface", "security"):
            inp = PRReviewInput(pr_number=1, review_depth=depth)
            assert inp.validate() == []


class TestPRReviewFinding:
    def test_minimal_finding(self):
        f = PRReviewFinding(
            severity=PRReviewFindingSeverity.INFO,
            message="LGTM",
        )
        assert f.severity == PRReviewFindingSeverity.INFO
        assert f.message == "LGTM"
        assert f.file_path is None
        assert f.metadata == {}

    def test_full_finding(self):
        f = PRReviewFinding(
            severity=PRReviewFindingSeverity.CRITICAL,
            message="SQL injection in query",
            file_path="src/db.py",
            line_start=42,
            line_end=45,
            category="security",
            suggestion="Use parameterized queries",
            metadata={"cwe": "CWE-89"},
        )
        assert f.file_path == "src/db.py"
        assert f.line_start == 42
        assert f.suggestion == "Use parameterized queries"
        assert f.metadata["cwe"] == "CWE-89"


class TestReviewAction:
    def test_default_requires_approval(self):
        action = ReviewAction(
            kind=ReviewActionKind.COMMENT,
            body="Looks good!",
        )
        assert action.require_approval is True
        assert action.approval_permission == Permission.GITHUB_WRITE

    def test_opt_out_approval(self):
        action = ReviewAction(
            kind=ReviewActionKind.APPROVE,
            body="Approved.",
            require_approval=False,
        )
        assert action.require_approval is False


class TestPRReviewOutput:
    def test_empty_output(self):
        out = PRReviewOutput(pr_number=1, summary="")
        assert out.findings == []
        assert out.finding_count == {}
        assert out.has_critical_findings is False
        assert out.approval_required is False

    def test_finding_counts(self):
        out = PRReviewOutput(
            pr_number=1,
            summary="Review complete",
            findings=[
                PRReviewFinding(
                    severity=PRReviewFindingSeverity.CRITICAL, message="c1"
                ),
                PRReviewFinding(severity=PRReviewFindingSeverity.WARNING, message="w1"),
                PRReviewFinding(
                    severity=PRReviewFindingSeverity.CRITICAL, message="c2"
                ),
                PRReviewFinding(severity=PRReviewFindingSeverity.INFO, message="i1"),
            ],
        )
        assert out.finding_count == {"critical": 2, "warning": 1, "info": 1}

    def test_has_critical_findings(self):
        out = PRReviewOutput(
            pr_number=1,
            summary="",
            findings=[
                PRReviewFinding(
                    severity=PRReviewFindingSeverity.CRITICAL, message="bad"
                ),
            ],
        )
        assert out.has_critical_findings is True

    def test_no_critical_findings(self):
        out = PRReviewOutput(
            pr_number=1,
            summary="",
            findings=[
                PRReviewFinding(
                    severity=PRReviewFindingSeverity.WARNING, message="meh"
                ),
            ],
        )
        assert out.has_critical_findings is False

    def test_approval_required(self):
        out = PRReviewOutput(
            pr_number=1,
            summary="",
            suggested_actions=[
                ReviewAction(
                    kind=ReviewActionKind.COMMENT,
                    body="Review",
                    require_approval=True,
                ),
            ],
        )
        assert out.approval_required is True

    def test_approval_not_required(self):
        out = PRReviewOutput(
            pr_number=1,
            summary="",
            suggested_actions=[
                ReviewAction(
                    kind=ReviewActionKind.COMMENT,
                    body="Review",
                    require_approval=False,
                ),
            ],
        )
        assert out.approval_required is False

    def test_completed_steps_tracking(self):
        out = PRReviewOutput(
            pr_number=1,
            summary="",
            completed_steps=[
                PRReviewStep.FETCH_PR,
                PRReviewStep.ANALYZE_CHANGES,
            ],
        )
        assert PRReviewStep.FETCH_PR in out.completed_steps
        assert PRReviewStep.POST_REVIEW not in out.completed_steps


class TestPRReviewWorkflowSpec:
    def test_spec_has_expected_attributes(self):
        spec = PRReviewWorkflowSpec()
        assert spec.name == "github_pr_review"
        assert spec.version == "0.1.0"
        assert spec.read_only_by_default is True
        assert spec.required_permission == Permission.GITHUB_READ
        assert spec.write_permission == Permission.GITHUB_WRITE

    def test_spec_has_ordered_steps(self):
        spec = PRReviewWorkflowSpec()
        assert spec.steps == [
            PRReviewStep.FETCH_PR,
            PRReviewStep.FETCH_REPOSITORY,
            PRReviewStep.ANALYZE_CHANGES,
            PRReviewStep.PRODUCE_FINDINGS,
            PRReviewStep.POST_REVIEW,
        ]

    def test_spec_declares_tool_dependencies(self):
        spec = PRReviewWorkflowSpec()
        assert "github.get_pull_request" in spec.tool_dependencies
        assert "github.get_repository" in spec.tool_dependencies

    def test_spec_has_input_output_types(self):
        spec = PRReviewWorkflowSpec()
        assert spec.input_type is PRReviewInput
        assert spec.output_type is PRReviewOutput


class TestPRReviewStepEnum:
    def test_all_steps_have_values(self):
        for step in PRReviewStep:
            assert step.value
            assert isinstance(step.value, str)

    def test_step_order(self):
        steps = list(PRReviewStep)
        assert steps.index(PRReviewStep.FETCH_PR) < steps.index(
            PRReviewStep.ANALYZE_CHANGES
        )
        assert steps.index(PRReviewStep.ANALYZE_CHANGES) < steps.index(
            PRReviewStep.POST_REVIEW
        )


class TestFindingSeverityEnum:
    def test_all_severities(self):
        assert PRReviewFindingSeverity.CRITICAL.value == "critical"
        assert PRReviewFindingSeverity.WARNING.value == "warning"
        assert PRReviewFindingSeverity.INFO.value == "info"
        assert PRReviewFindingSeverity.QUESTION.value == "question"


class TestReviewActionKindEnum:
    def test_all_action_kinds(self):
        assert ReviewActionKind.COMMENT.value == "comment"
        assert ReviewActionKind.APPROVE.value == "approve"
        assert ReviewActionKind.REQUEST_CHANGES.value == "request_changes"


class TestToolDependencies:
    def test_dependencies_are_connector_capability_names(self):
        for dep in PR_REVIEW_TOOL_DEPENDENCIES:
            assert dep.startswith("github.")
            assert dep.count(".") == 1


class TestWorkflowRegistryExport:
    def test_workflow_definitions_contains_pr_review(self):
        assert len(WORKFLOW_DEFINITIONS) == 1
        spec = WORKFLOW_DEFINITIONS[0]
        assert isinstance(spec, PRReviewWorkflowSpec)
        assert spec.name == "github_pr_review"

    def test_registry_is_minimal(self):
        names = [spec.name for spec in WORKFLOW_DEFINITIONS]
        assert names == ["github_pr_review"]
