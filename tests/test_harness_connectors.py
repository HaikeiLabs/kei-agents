"""Tests for the Gmail and Tito governed connector read schemas (HAI-205)."""

from __future__ import annotations

from agents import (
    ALL_TOOL_DEFINITIONS,
    CONNECTOR_READ_TOOL_DEFINITIONS,
    GMAIL_READ_TOOL_DEFINITIONS,
    TITO_READ_TOOL_DEFINITIONS,
    Permission,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
    validate_tool_definitions,
)

GMAIL_NAMES = {"gmail.search_messages", "gmail.get_message"}
TITO_NAMES = {
    "tito.list_events",
    "tito.get_event",
    "tito.list_releases",
    "tito.get_ticket_summary",
}


def _param_names(tool: ToolDefinition) -> set[str]:
    params = tool.parameters
    assert isinstance(params, list)
    return {p.name for p in params if isinstance(p, ToolParameter)}


class TestGmailReadSchemas:
    def test_names(self) -> None:
        assert {t.name for t in GMAIL_READ_TOOL_DEFINITIONS} == GMAIL_NAMES

    def test_validate(self) -> None:
        assert validate_tool_definitions(GMAIL_READ_TOOL_DEFINITIONS) == []

    def test_permission_category_service(self) -> None:
        for tool in GMAIL_READ_TOOL_DEFINITIONS:
            assert tool.permission is Permission.GMAIL_READ
            assert tool.category is ToolCategory.GMAIL
            assert tool.service == "gmail"

    def test_bound_handlerless_and_delegated(self) -> None:
        for tool in GMAIL_READ_TOOL_DEFINITIONS:
            assert tool.handler is None
            assert tool.binding is not None
            assert tool.binding.connector_id == "conn_gmail_1"
            assert tool.binding.config == {"resource": "messages"}
            assert tool.binding.delegated_context == ["tenant_id", "mailbox"]

    def test_body_inclusion_is_not_agent_chosen(self) -> None:
        # Full body is a policy attribute (gmail_include_body) decided by ABAC,
        # never a parameter the agent can set.
        for tool in GMAIL_READ_TOOL_DEFINITIONS:
            assert not any("body" in name for name in _param_names(tool))

    def test_search_params_match_catalog_capability(self) -> None:
        search = next(
            t for t in GMAIL_READ_TOOL_DEFINITIONS if t.name == "gmail.search_messages"
        )
        assert _param_names(search) == {"query", "page_size", "page_token"}
        get = next(
            t for t in GMAIL_READ_TOOL_DEFINITIONS if t.name == "gmail.get_message"
        )
        assert _param_names(get) == {"message_id"}


class TestTitoReadSchemas:
    def test_names(self) -> None:
        assert {t.name for t in TITO_READ_TOOL_DEFINITIONS} == TITO_NAMES

    def test_validate(self) -> None:
        assert validate_tool_definitions(TITO_READ_TOOL_DEFINITIONS) == []

    def test_permission_category_service(self) -> None:
        for tool in TITO_READ_TOOL_DEFINITIONS:
            assert tool.permission is Permission.TITO_READ
            assert tool.category is ToolCategory.TITO
            assert tool.service == "tito"

    def test_bound_handlerless_and_delegated(self) -> None:
        for tool in TITO_READ_TOOL_DEFINITIONS:
            assert tool.handler is None
            assert tool.binding is not None
            assert tool.binding.connector_id == "conn_tito_1"
            assert tool.binding.delegated_context == ["tenant_id", "account"]

    def test_no_attendee_pii_params(self) -> None:
        for tool in TITO_READ_TOOL_DEFINITIONS:
            names = _param_names(tool)
            assert not names & {"email", "attendee", "attendee_email", "name"}


class TestCatalogInclusion:
    def test_connector_reads_include_gmail_and_tito(self) -> None:
        names = {t.name for t in CONNECTOR_READ_TOOL_DEFINITIONS}
        assert GMAIL_NAMES | TITO_NAMES <= names

    def test_all_tools_include_gmail_and_tito(self) -> None:
        names = {t.name for t in ALL_TOOL_DEFINITIONS}
        assert GMAIL_NAMES | TITO_NAMES <= names

    def test_full_catalog_still_validates(self) -> None:
        assert validate_tool_definitions(ALL_TOOL_DEFINITIONS) == []
