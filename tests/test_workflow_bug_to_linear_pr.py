"""Tests for the bug-to-Linear-PR workflow specification."""

from __future__ import annotations

from agents.workflows.bug_to_linear_pr import (
    BUG_TO_LINEAR_PR,
    BugReport,
    ConnectorRef,
    LinearTicketRef,
    PRResult,
    PRSpec,
    Severity,
    WorkflowSpec,
    WorkflowStep,
    get_step,
    validate_workflow,
)

# Known connector tool names that the workflow may reference.
# This mirrors the set of tools registered in the agent catalog.
_KNOWN_CONNECTOR_NAMES: set[str] = {
    # Connector read schemas (governed)
    "github.get_repository",
    "github.get_issue",
    "github.get_pull_request",
    "linear.list_issues",
    "linear.get_issue",
    "linear.list_projects",
    "drive.list_files",
    "drive.get_file",
    "docs.get_document",
    "s3.list_objects",
    "s3.get_object",
    "s3.get_object_metadata",
    "http_api.list_records",
    "http_api.get_record",
    # Action tools (harness-side)
    "list_issues",
    "create_issue",
    "get_workflow_status",
    "list_prs",
    "create_pull_request",
    # Future Linear write tool (declared by this workflow)
    "linear.create_issue",
}


class TestBugIntakeStep:
    def test_bug_report_defaults(self) -> None:
        report = BugReport(
            title="Login fails on Firefox",
            description="Users cannot log in on Firefox 120+",
            severity="high",
            affected_feature="authentication",
        )
        assert report.title == "Login fails on Firefox"
        assert report.severity == "high"
        assert report.labels == ["bug"]
        assert report.reporter == ""

    def test_bug_report_full(self) -> None:
        report = BugReport(
            title="Crash on export",
            description="Exporting large files crashes the service",
            severity=Severity.CRITICAL,
            affected_feature="export",
            environment="production",
            steps_to_reproduce="1. Open app\n2. Click export\n3. Crash",
            expected_behaviour="File exports successfully",
            actual_behaviour="Service crashes with OOM",
            reporter="qa@example.com",
            labels=["bug", "priority:critical"],
        )
        assert report.severity == Severity.CRITICAL
        assert "priority:critical" in report.labels

    def test_severity_enum_values(self) -> None:
        assert list(Severity) == [
            Severity.CRITICAL,
            Severity.HIGH,
            Severity.MEDIUM,
            Severity.LOW,
        ]


class TestLinearTicketStep:
    def test_linear_ticket_ref_creation(self) -> None:
        ref = LinearTicketRef(
            issue_key="ENG-456", url="https://linear.app/kei/issue/ENG-456"
        )
        assert ref.issue_key == "ENG-456"
        assert "linear.app" in ref.url

    def test_linear_ticket_ref_default_url(self) -> None:
        ref = LinearTicketRef(issue_key="ENG-789")
        assert ref.url == ""

    def test_linear_ticket_step_present(self) -> None:
        step = get_step(BUG_TO_LINEAR_PR, "linear_ticket")
        assert step is not None
        assert step.input_type == BugReport
        assert step.output_type == LinearTicketRef
        assert "linear_write" in step.required_permissions

    def test_linear_connector_refs_defined(self) -> None:
        step = get_step(BUG_TO_LINEAR_PR, "linear_ticket")
        assert step is not None
        names = {ref.name for ref in step.connector_dependencies}
        assert "linear.create_issue" in names
        assert "linear.get_issue" in names


class TestGitHubPRStep:
    def test_pr_spec_default_base(self) -> None:
        spec = PRSpec(
            title="Fix login crash on Firefox 120+",
            body="## Summary\nFixes the login crash on Firefox 120+.",
            head_branch="fix/login-firefox-crash",
        )
        assert spec.base_branch == "main"

    def test_pr_spec_custom_base(self) -> None:
        spec = PRSpec(
            title="Hotfix: export OOM",
            body="Bumps memory limit and adds chunked processing.",
            head_branch="hotfix/export-oom",
            base_branch="release/v2.1",
        )
        assert spec.base_branch == "release/v2.1"

    def test_pr_result(self) -> None:
        result = PRResult(
            pr_url="https://github.com/kei/kei-agent-definitions/pull/42",
            pr_number=42,
        )
        assert result.pr_number == 42

    def test_github_pr_step_present(self) -> None:
        step = get_step(BUG_TO_LINEAR_PR, "github_pr")
        assert step is not None
        assert step.input_type == PRSpec
        assert step.output_type == PRResult

    def test_github_pr_requires_write(self) -> None:
        step = get_step(BUG_TO_LINEAR_PR, "github_pr")
        assert step is not None
        assert "github_write" in step.required_permissions

    def test_github_pr_is_terminal(self) -> None:
        step = get_step(BUG_TO_LINEAR_PR, "github_pr")
        assert step is not None
        assert step.next_steps == []


class TestBugIntakeStepProperties:
    def test_bug_intake_step_present(self) -> None:
        step = get_step(BUG_TO_LINEAR_PR, "bug_intake")
        assert step is not None
        assert step.input_type == BugReport
        assert step.output_type == BugReport

    def test_bug_intake_is_entry(self) -> None:
        assert BUG_TO_LINEAR_PR.entry_step == "bug_intake"

    def test_bug_intake_requires_no_permissions(self) -> None:
        step = get_step(BUG_TO_LINEAR_PR, "bug_intake")
        assert step is not None
        assert step.required_permissions == []

    def test_bug_intake_no_connector_deps(self) -> None:
        step = get_step(BUG_TO_LINEAR_PR, "bug_intake")
        assert step is not None
        assert step.connector_dependencies == []

    def test_bug_intake_transitions_to_linear(self) -> None:
        step = get_step(BUG_TO_LINEAR_PR, "bug_intake")
        assert step is not None
        assert step.next_steps == ["linear_ticket"]


class TestWorkflowSpecStructure:
    def test_spec_name(self) -> None:
        assert BUG_TO_LINEAR_PR.name == "bug_to_linear_pr"

    def test_spec_version(self) -> None:
        assert BUG_TO_LINEAR_PR.version == "0.1.0"

    def test_spec_has_all_steps(self) -> None:
        names = {s.name for s in BUG_TO_LINEAR_PR.steps}
        assert names == {"bug_intake", "linear_ticket", "github_pr"}

    def test_spec_tags(self) -> None:
        assert "bug" in BUG_TO_LINEAR_PR.tags

    def test_spec_no_duplicate_step_names(self) -> None:
        names = [s.name for s in BUG_TO_LINEAR_PR.steps]
        assert len(names) == len(set(names))

    def test_spec_ordered_steps(self) -> None:
        assert BUG_TO_LINEAR_PR.steps[0].name == "bug_intake"
        assert BUG_TO_LINEAR_PR.steps[1].name == "linear_ticket"
        assert BUG_TO_LINEAR_PR.steps[2].name == "github_pr"


class TestConnectorRefSemantics:
    def test_connector_ref_structure(self) -> None:
        ref = ConnectorRef(
            name="linear.create_issue",
            description="Create a Linear issue",
            required_permission="linear_write",
        )
        assert ref.name == "linear.create_issue"
        assert ref.required_permission == "linear_write"

    def test_all_connector_refs_resolvable(self) -> None:
        """Every connector ref in the workflow must be in the known catalog."""
        for step in BUG_TO_LINEAR_PR.steps:
            for ref in step.connector_dependencies:
                assert ref.name in _KNOWN_CONNECTOR_NAMES, (
                    f"{step.name}: connector ref {ref.name!r} not in known catalog"
                )

    def test_connector_refs_are_semantic_strings(self) -> None:
        """Connector refs must be plain string names, not imported objects."""
        for step in BUG_TO_LINEAR_PR.steps:
            for ref in step.connector_dependencies:
                assert isinstance(ref.name, str)
                assert "." in ref.name or "_" in ref.name

    def test_github_pr_uses_existing_action_tool(self) -> None:
        step = get_step(BUG_TO_LINEAR_PR, "github_pr")
        assert step is not None
        names = {ref.name for ref in step.connector_dependencies}
        assert "create_pull_request" in names
        assert "github_write" in {
            ref.required_permission for ref in step.connector_dependencies
        }


class TestWorkflowValidation:
    def test_valid_workflow_passes(self) -> None:
        violations = validate_workflow(BUG_TO_LINEAR_PR, _KNOWN_CONNECTOR_NAMES)
        assert violations == [], f"unexpected violations: {violations}"

    def test_missing_entry_step(self) -> None:
        spec = WorkflowSpec(name="empty", description="no steps")
        violations = validate_workflow(spec, set())
        assert any("entry_step" in v for v in violations)

    def test_unreachable_step(self) -> None:
        steps = [
            WorkflowStep(
                name="a",
                description="A",
                input_type=BugReport,
                output_type=BugReport,
                next_steps=["b"],
            ),
            WorkflowStep(
                name="b",
                description="B",
                input_type=BugReport,
                output_type=BugReport,
                next_steps=[],
            ),
            WorkflowStep(
                name="c",
                description="C",
                input_type=BugReport,
                output_type=BugReport,
                next_steps=[],
            ),
        ]
        spec = WorkflowSpec(name="test", description="t", entry_step="a", steps=steps)
        violations = validate_workflow(spec, set())
        assert any("unreachable" in v for v in violations)
        assert any("c" in v for v in violations)

    def test_unknown_next_step(self) -> None:
        steps = [
            WorkflowStep(
                name="a",
                description="A",
                input_type=BugReport,
                output_type=BugReport,
                next_steps=["does_not_exist"],
            ),
        ]
        spec = WorkflowSpec(name="test", description="t", entry_step="a", steps=steps)
        violations = validate_workflow(spec, set())
        assert any("next_step" in v for v in violations)

    def test_unresolved_connector_ref(self) -> None:
        steps = [
            WorkflowStep(
                name="a",
                description="A",
                input_type=BugReport,
                output_type=BugReport,
                connector_dependencies=[
                    ConnectorRef(
                        name="nonexistent.tool",
                        description="nope",
                        required_permission="nope",
                    ),
                ],
                next_steps=[],
            ),
        ]
        spec = WorkflowSpec(name="test", description="t", entry_step="a", steps=steps)
        violations = validate_workflow(spec, set())
        assert any("unresolved connector" in v for v in violations)

    def test_missing_step_description(self) -> None:
        steps = [
            WorkflowStep(
                name="a",
                description="",
                input_type=BugReport,
                output_type=BugReport,
                next_steps=[],
            ),
        ]
        spec = WorkflowSpec(name="test", description="t", entry_step="a", steps=steps)
        violations = validate_workflow(spec, set())
        assert any("description is required" in v for v in violations)

    def test_empty_step_name(self) -> None:
        steps = [
            WorkflowStep(
                name="",
                description="empty name",
                input_type=BugReport,
                output_type=BugReport,
                next_steps=[],
            ),
        ]
        spec = WorkflowSpec(name="test", description="t", entry_step="", steps=steps)
        violations = validate_workflow(spec, set())
        assert any("empty name" in v for v in violations)


class TestWorkflowIntegration:
    def test_get_step_missing(self) -> None:
        assert get_step(BUG_TO_LINEAR_PR, "does_not_exist") is None

    def test_full_workflow_reachable(self) -> None:
        """Every declared step must be reachable from the entry step."""
        step_map = {s.name: s for s in BUG_TO_LINEAR_PR.steps}
        visited: set[str] = set()
        stack = [BUG_TO_LINEAR_PR.entry_step]
        while stack:
            name = stack.pop()
            if name in visited:
                continue
            visited.add(name)
            step = step_map.get(name)
            if step:
                for next_name in step.next_steps:
                    if next_name is not None:
                        stack.append(next_name)
        declared = {s.name for s in BUG_TO_LINEAR_PR.steps}
        assert visited == declared, f"unreachable: {declared - visited}"

    def test_no_provider_clients_in_spec(self) -> None:
        """Verify the spec contains no provider client imports or hardcoded args."""
        import inspect

        source = inspect.getsource(type(BUG_TO_LINEAR_PR))

        forbidden_imports = [
            "requests",
            "httpx",
            "aiohttp",
            "github",
            "linear",
            "discord",
            "slack",
        ]
        for mod in forbidden_imports:
            assert mod not in source, (
                f"provider client {mod!r} leaked into workflow spec"
            )

        forbidden_args = [
            "org_id",
            "workspace",
            "tenant_id",
            "api_key",
            "token",
            "credential",
        ]
        for arg in forbidden_args:
            assert arg not in source, f"hardcoded arg {arg!r} leaked into workflow spec"

    def test_workflow_spec_is_module_constant(self) -> None:
        """BUG_TO_LINEAR_PR must be a WorkflowSpec instance at module level."""
        assert isinstance(BUG_TO_LINEAR_PR, WorkflowSpec)
