"""Tests for the harness-neutral support-management workflow specification."""

from __future__ import annotations

from agents.workflows.support import (
    SUPPORT_WORKFLOW,
    EscalationRule,
    FailureState,
    RedactionRule,
    ResourceMapping,
    SupportWorkflow,
    WorkflowStep,
    validate_support_workflow,
)


def _step_names() -> set[str]:
    return {step.name for step in SUPPORT_WORKFLOW.steps}


def _write_steps() -> list[WorkflowStep]:
    return [s for s in SUPPORT_WORKFLOW.steps if s.kind == "write"]


def _read_steps() -> list[WorkflowStep]:
    return [s for s in SUPPORT_WORKFLOW.steps if s.kind == "read"]


class TestWorkflowSpecShape:
    def test_workflow_name_and_version(self):
        assert SUPPORT_WORKFLOW.name == "support-management"
        assert SUPPORT_WORKFLOW.version == "1.0.0"
        assert SUPPORT_WORKFLOW.description

    def test_has_steps(self):
        assert len(SUPPORT_WORKFLOW.steps) > 0

    def test_step_names_are_unique(self):
        names = _step_names()
        assert len(names) == len(SUPPORT_WORKFLOW.steps)

    def test_has_resource_mappings(self):
        assert len(SUPPORT_WORKFLOW.resource_mappings) > 0

    def test_has_escalation_rules(self):
        assert len(SUPPORT_WORKFLOW.escalation_rules) > 0

    def test_has_redaction_rules(self):
        assert len(SUPPORT_WORKFLOW.redaction_rules) > 0

    def test_has_failure_states(self):
        assert len(SUPPORT_WORKFLOW.failure_states) > 0


class TestReadSteps:
    def test_read_steps_use_read_kind(self):
        for step in _read_steps():
            assert step.kind == "read"

    def test_read_steps_compose_expected_connectors(self):
        connectors = {step.connector for step in _read_steps()}
        assert "notion" in connectors
        assert "drive" in connectors
        assert "http_api" in connectors

    def test_read_steps_use_governed_tool_names(self):
        for step in _read_steps():
            assert "." in step.tool_name, (
                f"read step {step.name!r} should use a dotted tool name"
            )

    def test_read_steps_have_param_hints(self):
        for step in _read_steps():
            assert len(step.param_hints) > 0, (
                f"read step {step.name!r} should declare param hints"
            )


class TestWriteSteps:
    def test_write_steps_use_write_kind(self):
        for step in _write_steps():
            assert step.kind == "write"

    def test_write_steps_have_failure_states(self):
        for step in _write_steps():
            assert step.failure_state is not None, (
                f"write step {step.name!r} must have a failure state"
            )

    def test_write_steps_use_governed_tool_names(self):
        for step in _write_steps():
            assert "." in step.tool_name, (
                f"write step {step.name!r} should use a dotted tool name"
            )


class TestResourceMappings:
    def test_mappings_cover_all_three_connectors(self):
        connectors = {rm.connector for rm in SUPPORT_WORKFLOW.resource_mappings}
        assert "notion" in connectors
        assert "drive" in connectors
        assert "http_api" in connectors

    def test_mappings_have_valid_tool_names(self):
        for rm in SUPPORT_WORKFLOW.resource_mappings:
            assert "." in rm.tool_name

    def test_mappings_have_entities(self):
        for rm in SUPPORT_WORKFLOW.resource_mappings:
            assert rm.entity

    def test_mappings_have_descriptions(self):
        for rm in SUPPORT_WORKFLOW.resource_mappings:
            assert rm.description

    def test_ticket_entity_mapped_from_notion(self):
        entities = {
            rm.entity
            for rm in SUPPORT_WORKFLOW.resource_mappings
            if rm.connector == "notion"
        }
        assert "support_ticket" in entities

    def test_customer_document_mapped_from_drive(self):
        entities = {
            rm.entity
            for rm in SUPPORT_WORKFLOW.resource_mappings
            if rm.connector == "drive"
        }
        assert "customer_document" in entities

    def test_customer_account_mapped_from_http_api(self):
        entities = {
            rm.entity
            for rm in SUPPORT_WORKFLOW.resource_mappings
            if rm.connector == "http_api"
        }
        assert "customer_account" in entities


class TestEscalationRules:
    def test_escalation_rules_have_conditions(self):
        for rule in SUPPORT_WORKFLOW.escalation_rules:
            assert rule.condition

    def test_escalation_rules_have_actions(self):
        for rule in SUPPORT_WORKFLOW.escalation_rules:
            assert rule.action

    def test_escalation_rules_have_target_tools(self):
        for rule in SUPPORT_WORKFLOW.escalation_rules:
            assert "." in rule.target_tool

    def test_critical_severity_escalation_exists(self):
        conditions = [r.condition for r in SUPPORT_WORKFLOW.escalation_rules]
        assert any("critical" in c for c in conditions)

    def test_sla_breach_escalation_exists(self):
        conditions = [r.condition for r in SUPPORT_WORKFLOW.escalation_rules]
        assert any("sla" in c.lower() for c in conditions)


class TestRedactionRules:
    def test_redaction_rules_have_patterns(self):
        for rule in SUPPORT_WORKFLOW.redaction_rules:
            assert rule.field_pattern

    def test_redaction_rules_have_scopes(self):
        for rule in SUPPORT_WORKFLOW.redaction_rules:
            assert rule.scope

    def test_redaction_rules_have_replacements(self):
        for rule in SUPPORT_WORKFLOW.redaction_rules:
            assert rule.replacement
            assert "REDACTED" in rule.replacement

    def test_email_redaction_exists(self):
        patterns = [r.field_pattern for r in SUPPORT_WORKFLOW.redaction_rules]
        assert any("@" in p for p in patterns)

    def test_phone_redaction_exists(self):
        assert any("PHONE" in r.replacement for r in SUPPORT_WORKFLOW.redaction_rules)

    def test_ssn_redaction_exists(self):
        patterns = [r.field_pattern for r in SUPPORT_WORKFLOW.redaction_rules]
        assert any("ssn" in p.lower() for p in patterns)


class TestFailureStates:
    def test_all_steps_have_failure_states(self):
        fs_steps = {fs.step_name for fs in SUPPORT_WORKFLOW.failure_states}
        step_names = _step_names()
        assert step_names <= fs_steps

    def test_failure_states_reference_known_steps(self):
        step_names = _step_names()
        for fs in SUPPORT_WORKFLOW.failure_states:
            assert fs.step_name in step_names

    def test_failure_states_have_valid_strategies(self):
        valid = {"abort", "skip", "retry", "fallback"}
        for fs in SUPPORT_WORKFLOW.failure_states:
            assert fs.on_failure in valid

    def test_retry_states_have_max_retries(self):
        for fs in SUPPORT_WORKFLOW.failure_states:
            if fs.on_failure == "retry":
                assert fs.max_retries >= 1

    def test_fallback_states_have_fallback_step(self):
        step_names = _step_names()
        for fs in SUPPORT_WORKFLOW.failure_states:
            if fs.on_failure == "fallback":
                assert fs.fallback_step is not None
                assert fs.fallback_step in step_names


class TestHarnessNeutrality:
    def test_no_discord_references(self):
        for step in SUPPORT_WORKFLOW.steps:
            assert "discord" not in step.tool_name.lower()
            assert "discord" not in step.connector.lower()
            assert "discord" not in step.description.lower()
        for rm in SUPPORT_WORKFLOW.resource_mappings:
            assert "discord" not in rm.connector.lower()
            assert "discord" not in rm.description.lower()
        for rule in SUPPORT_WORKFLOW.escalation_rules:
            assert "discord" not in rule.action.lower()
            assert "discord" not in rule.description.lower()

    def test_no_provider_clients(self):
        for step in SUPPORT_WORKFLOW.steps:
            assert not hasattr(step, "handler")

    def test_no_secret_material_in_param_hints(self):
        secret_hints = ("token", "secret", "password", "api_key", "credential")
        for step in SUPPORT_WORKFLOW.steps:
            for hint in step.param_hints:
                lower = hint.lower()
                for sh in secret_hints:
                    assert sh not in lower, (
                        f"step {step.name!r} param hint {hint!r} "
                        f"contains secret hint {sh!r}"
                    )

    def test_no_urls_in_param_hints(self):
        for step in SUPPORT_WORKFLOW.steps:
            for hint in step.param_hints:
                assert "://" not in hint

    def test_no_tenant_identifier_params(self):
        tenant_ids = ("tenant_id", "account_id", "customer_id", "org_id")
        for step in SUPPORT_WORKFLOW.steps:
            for hint in step.param_hints:
                assert hint not in tenant_ids, (
                    f"step {step.name!r} has tenant identifier param {hint!r}"
                )

    def test_no_org_or_workspace_params(self):
        org_ws = ("organization_id", "org_id", "workspace_id", "workspace")
        for step in SUPPORT_WORKFLOW.steps:
            for hint in step.param_hints:
                assert hint not in org_ws, (
                    f"step {step.name!r} has org/workspace param {hint!r}"
                )


class TestValidation:
    def test_default_workflow_is_valid(self):
        assert validate_support_workflow(SUPPORT_WORKFLOW) == []

    def test_duplicate_step_name_flagged(self):
        workflow = SupportWorkflow(
            name="test",
            version="0.1",
            description="test",
            steps=(
                WorkflowStep(
                    name="a",
                    kind="read",
                    tool_name="notion.get_page",
                    connector="notion",
                    description="a",
                ),
                WorkflowStep(
                    name="a",
                    kind="read",
                    tool_name="drive.list_files",
                    connector="drive",
                    description="a",
                ),
            ),
            resource_mappings=(),
            escalation_rules=(),
            redaction_rules=(),
            failure_states=(),
        )
        assert any("duplicate" in v for v in validate_support_workflow(workflow))

    def test_invalid_step_kind_flagged(self):
        workflow = SupportWorkflow(
            name="test",
            version="0.1",
            description="test",
            steps=(
                WorkflowStep(
                    name="a",
                    kind="execute",
                    tool_name="notion.get_page",
                    connector="notion",
                    description="a",
                ),
            ),
            resource_mappings=(),
            escalation_rules=(),
            redaction_rules=(),
            failure_states=(),
        )
        assert any("invalid kind" in v for v in validate_support_workflow(workflow))

    def test_unknown_connector_flagged(self):
        workflow = SupportWorkflow(
            name="test",
            version="0.1",
            description="test",
            steps=(
                WorkflowStep(
                    name="a",
                    kind="read",
                    tool_name="slack.get_message",
                    connector="slack",
                    description="a",
                ),
            ),
            resource_mappings=(),
            escalation_rules=(),
            redaction_rules=(),
            failure_states=(),
        )
        assert any("connector" in v for v in validate_support_workflow(workflow))

    def test_secret_param_hint_flagged(self):
        workflow = SupportWorkflow(
            name="test",
            version="0.1",
            description="test",
            steps=(
                WorkflowStep(
                    name="a",
                    kind="read",
                    tool_name="notion.get_page",
                    connector="notion",
                    description="a",
                    param_hints=("api_key",),
                ),
            ),
            resource_mappings=(),
            escalation_rules=(),
            redaction_rules=(),
            failure_states=(),
        )
        assert any("secret" in v for v in validate_support_workflow(workflow))

    def test_tenant_id_param_hint_flagged(self):
        workflow = SupportWorkflow(
            name="test",
            version="0.1",
            description="test",
            steps=(
                WorkflowStep(
                    name="a",
                    kind="read",
                    tool_name="notion.get_page",
                    connector="notion",
                    description="a",
                    param_hints=("tenant_id",),
                ),
            ),
            resource_mappings=(),
            escalation_rules=(),
            redaction_rules=(),
            failure_states=(),
        )
        assert any(
            "tenant identifier" in v for v in validate_support_workflow(workflow)
        )

    def test_url_param_hint_flagged(self):
        workflow = SupportWorkflow(
            name="test",
            version="0.1",
            description="test",
            steps=(
                WorkflowStep(
                    name="a",
                    kind="read",
                    tool_name="notion.get_page",
                    connector="notion",
                    description="a",
                    param_hints=("https://example.com",),
                ),
            ),
            resource_mappings=(),
            escalation_rules=(),
            redaction_rules=(),
            failure_states=(),
        )
        assert any("URL" in v for v in validate_support_workflow(workflow))

    def test_failure_state_unknown_step_flagged(self):
        workflow = SupportWorkflow(
            name="test",
            version="0.1",
            description="test",
            steps=(
                WorkflowStep(
                    name="a",
                    kind="read",
                    tool_name="notion.get_page",
                    connector="notion",
                    description="a",
                ),
            ),
            resource_mappings=(),
            escalation_rules=(),
            redaction_rules=(),
            failure_states=(
                FailureState(
                    step_name="nonexistent",
                    on_failure="abort",
                ),
            ),
        )
        assert any("unknown step" in v for v in validate_support_workflow(workflow))

    def test_fallback_without_target_flagged(self):
        workflow = SupportWorkflow(
            name="test",
            version="0.1",
            description="test",
            steps=(
                WorkflowStep(
                    name="a",
                    kind="read",
                    tool_name="notion.get_page",
                    connector="notion",
                    description="a",
                    failure_state=FailureState(
                        step_name="a",
                        on_failure="fallback",
                    ),
                ),
            ),
            resource_mappings=(),
            escalation_rules=(),
            redaction_rules=(),
            failure_states=(),
        )
        assert any("fallback_step" in v for v in validate_support_workflow(workflow))

    def test_retry_without_max_retries_flagged(self):
        workflow = SupportWorkflow(
            name="test",
            version="0.1",
            description="test",
            steps=(
                WorkflowStep(
                    name="a",
                    kind="read",
                    tool_name="notion.get_page",
                    connector="notion",
                    description="a",
                    failure_state=FailureState(
                        step_name="a",
                        on_failure="retry",
                        max_retries=0,
                    ),
                ),
            ),
            resource_mappings=(),
            escalation_rules=(),
            redaction_rules=(),
            failure_states=(),
        )
        assert any("max_retries" in v for v in validate_support_workflow(workflow))

    def test_empty_redaction_pattern_flagged(self):
        workflow = SupportWorkflow(
            name="test",
            version="0.1",
            description="test",
            steps=(),
            resource_mappings=(),
            escalation_rules=(),
            redaction_rules=(
                RedactionRule(
                    field_pattern="",
                    scope="ticket_body",
                    replacement="[REDACTED]",
                    description="test",
                ),
            ),
            failure_states=(),
        )
        assert any("field_pattern" in v for v in validate_support_workflow(workflow))

    def test_resource_mapping_unknown_connector_flagged(self):
        workflow = SupportWorkflow(
            name="test",
            version="0.1",
            description="test",
            steps=(),
            resource_mappings=(
                ResourceMapping(
                    connector="slack",
                    tool_name="slack.get_message",
                    resource="messages",
                    entity="message",
                    description="test",
                ),
            ),
            escalation_rules=(),
            redaction_rules=(),
            failure_states=(),
        )
        assert any("connector" in v for v in validate_support_workflow(workflow))

    def test_escalation_rule_invalid_tool_flagged(self):
        workflow = SupportWorkflow(
            name="test",
            version="0.1",
            description="test",
            steps=(),
            resource_mappings=(),
            escalation_rules=(
                EscalationRule(
                    condition="x",
                    action="notify",
                    target_tool="Invalid-Tool",
                    description="test",
                ),
            ),
            redaction_rules=(),
            failure_states=(),
        )
        assert any("target_tool" in v for v in validate_support_workflow(workflow))
