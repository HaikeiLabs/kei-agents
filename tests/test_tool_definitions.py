"""Tests for the agent-capability tool definitions module."""

from __future__ import annotations

from agents import (
    ALL_TOOL_DEFINITIONS,
    TOOL_DEFINITIONS,
    ModelFormat,
    Permission,
    ToolBinding,
    ToolCategory,
    ToolDefinition,
    detect_model_format,
    get_tool_by_name,
    get_tools_by_category,
    get_tools_by_permission,
    get_tools_for_model,
    render_anthropic_tools,
    render_ollama_tools,
    render_openai_tools,
    render_tools,
    validate_tool_definitions,
)

# (name, description, permission) rows from the README "Available Tools" table.
README_TOOLS: list[tuple[str, str, Permission]] = [
    ("search_wiki", "Search conversation history", Permission.SEARCH_WIKI),
    ("web_search", "Search the web for current info", Permission.WEB_SEARCH),
    ("schedule_meeting", "Schedule calendar meetings", Permission.SCHEDULE_MEETINGS),
    ("list_prs", "List GitHub pull requests", Permission.GITHUB_READ),
    ("list_issues", "List GitHub issues", Permission.GITHUB_READ),
    ("create_issue", "Create GitHub issues", Permission.GITHUB_WRITE),
    ("get_workflow_status", "Get CI/CD workflow status", Permission.GITHUB_READ),
    (
        "create_pull_request",
        (
            "Open a GitHub pull request from an existing branch. Use it when the"
            " user says the work is on a branch and asks for a PR; call it"
            " directly, without reading the linked issue first"
        ),
        Permission.GITHUB_WRITE,
    ),
    ("start_game", "Start interactive games", Permission.SEARCH_WIKI),
]


class TestReadmeExamples:
    def test_quick_start_openai_enum(self):
        tools = render_tools(TOOL_DEFINITIONS, ModelFormat.OPENAI)
        assert isinstance(tools, list)
        assert len(tools) == len(TOOL_DEFINITIONS)
        assert all(entry["type"] == "function" for entry in tools)

    def test_quick_start_model_name(self):
        tools = render_tools(TOOL_DEFINITIONS, "gpt-4")
        assert isinstance(tools, list)
        assert all(entry["type"] == "function" for entry in tools)

    def test_readme_tool_table_present(self):
        for name, description, permission in README_TOOLS:
            tool = get_tool_by_name(TOOL_DEFINITIONS, name)
            assert tool is not None, (
                f"README tool {name!r} missing from TOOL_DEFINITIONS"
            )
            assert tool.description == description
            assert tool.permission == permission


class TestSchemaValidation:
    def test_default_catalog_is_valid(self):
        assert validate_tool_definitions(TOOL_DEFINITIONS) == []

    def test_all_tool_definitions_unique_names(self):
        names = [tool.name for tool in ALL_TOOL_DEFINITIONS]
        assert len(names) == len(set(names))

    def test_duplicate_name_flagged(self):
        tools = [
            ToolDefinition(name="dup", description="a"),
            ToolDefinition(name="dup", description="b"),
        ]
        assert "duplicate tool name: 'dup'" in validate_tool_definitions(tools)

    def test_invalid_name_flagged(self):
        tools = [ToolDefinition(name="Create-Issue", description="a")]
        assert any("invalid name" in v for v in validate_tool_definitions(tools))

    def test_dotted_name_allowed(self):
        tools = [ToolDefinition(name="github.create_pr", description="a")]
        assert validate_tool_definitions(tools) == []

    def test_missing_description_flagged(self):
        tools = [ToolDefinition(name="no_desc", description="")]
        assert any(
            "description is required" in v for v in validate_tool_definitions(tools)
        )

    def test_invalid_permission_flagged(self):
        tool = ToolDefinition(name="t", description="a")
        tool.permission = "admin"  # type: ignore[assignment]
        assert any("invalid permission" in v for v in validate_tool_definitions([tool]))

    def test_invalid_service_flagged(self):
        tools = [ToolDefinition(name="t", description="a", service="github api")]
        assert any("invalid service" in v for v in validate_tool_definitions(tools))

    def test_secret_key_in_binding_flagged(self):
        tools = [
            ToolDefinition(
                name="t",
                description="a",
                binding=ToolBinding(
                    connector_id="conn_1", config={"api_key": "sk-123"}
                ),
            )
        ]
        assert any("secret" in v for v in validate_tool_definitions(tools))

    def test_secret_value_in_binding_flagged(self):
        tools = [
            ToolDefinition(
                name="t",
                description="a",
                binding=ToolBinding(
                    connector_id="conn_1", config={"auth_token": "abcdef"}
                ),
            )
        ]
        assert any("secret" in v for v in validate_tool_definitions(tools))

    def test_binding_missing_connector_id_flagged(self):
        tools = [
            ToolDefinition(
                name="t",
                description="a",
                binding=ToolBinding(connector_id=""),
            )
        ]
        assert any("connector_id" in v for v in validate_tool_definitions(tools))

    def test_non_secret_binding_passes(self):
        tools = [
            ToolDefinition(
                name="t",
                description="a",
                service="github",
                binding=ToolBinding(
                    connector_id="conn_github_1",
                    config={"default_branch": "main"},
                ),
            )
        ]
        assert validate_tool_definitions(tools) == []


class TestLookupAndFiltering:
    def test_get_tool_by_name_hit(self):
        tool = get_tool_by_name("create_pull_request")
        assert tool is not None
        assert tool.name == "create_pull_request"

    def test_get_tool_by_name_miss(self):
        assert get_tool_by_name("does_not_exist") is None

    def test_get_tool_by_name_explicit_collection(self):
        tools = [ToolDefinition(name="a", description="A")]
        found = get_tool_by_name(tools, "a")
        assert found is not None
        assert found.name == "a"

    def test_get_tools_by_category_enum(self):
        github = get_tools_by_category(ToolCategory.GITHUB)
        assert {
            "list_prs",
            "list_issues",
            "create_issue",
            "get_workflow_status",
            "create_pull_request",
        } <= {tool.name for tool in github}

    def test_get_tools_by_category_string(self):
        search = get_tools_by_category("search")
        assert {"search_wiki", "web_search"} <= {tool.name for tool in search}

    def test_get_tools_by_permission_string(self):
        write_tools = get_tools_by_permission("github_write")
        assert {"create_issue", "create_pull_request"} <= {
            tool.name for tool in write_tools
        }

    def test_get_tools_by_permission_enum(self):
        read_tools = get_tools_by_permission(Permission.GITHUB_READ)
        assert {
            "list_prs",
            "list_issues",
            "get_workflow_status",
        } <= {tool.name for tool in read_tools}

    def test_get_tools_by_permission_explicit_collection(self):
        tools = [
            ToolDefinition(
                name="w", description="w", permission=Permission.GITHUB_WRITE
            ),
            ToolDefinition(
                name="r", description="r", permission=Permission.GITHUB_READ
            ),
        ]
        assert [
            tool.name for tool in get_tools_by_permission(tools, "github_write")
        ] == ["w"]


class TestRendering:
    def test_openai_render_structure(self):
        rendered = render_openai_tools(TOOL_DEFINITIONS)
        assert len(rendered) == len(TOOL_DEFINITIONS)
        for entry in rendered:
            assert entry["type"] == "function"
            fn = entry["function"]
            assert fn["name"]
            assert fn["description"]
            assert fn["parameters"]["type"] == "object"
            assert "properties" in fn["parameters"]
            assert "required" in fn["parameters"]

    def test_openai_required_params(self):
        tool = get_tool_by_name("web_search")
        assert tool is not None
        rendered = render_openai_tools([tool])[0]
        assert rendered["function"]["parameters"]["required"] == ["query"]

    def test_openai_enum_preserved(self):
        tool = get_tool_by_name("list_prs")
        assert tool is not None
        rendered = render_openai_tools([tool])[0]
        state = rendered["function"]["parameters"]["properties"]["state"]
        assert state["enum"] == ["open", "closed", "all"]

    def test_anthropic_render_structure(self):
        rendered = render_anthropic_tools(TOOL_DEFINITIONS)
        assert len(rendered) == len(TOOL_DEFINITIONS)
        for entry in rendered:
            assert "name" in entry
            assert "description" in entry
            assert entry["input_schema"]["type"] == "object"
            assert "properties" in entry["input_schema"]
            assert "required" in entry["input_schema"]

    def test_ollama_matches_openai(self):
        assert render_ollama_tools(TOOL_DEFINITIONS) == render_openai_tools(
            TOOL_DEFINITIONS
        )

    def test_render_tools_format_selection(self):
        assert render_tools(
            TOOL_DEFINITIONS, ModelFormat.ANTHROPIC
        ) == render_anthropic_tools(TOOL_DEFINITIONS)
        assert render_tools(TOOL_DEFINITIONS, "claude-3") == render_anthropic_tools(
            TOOL_DEFINITIONS
        )
        assert render_tools(TOOL_DEFINITIONS, "ollama/llama2") == render_ollama_tools(
            TOOL_DEFINITIONS
        )

    def test_detect_model_format(self):
        assert detect_model_format("gpt-4") == ModelFormat.OPENAI
        assert detect_model_format("claude-3-opus") == ModelFormat.ANTHROPIC
        assert detect_model_format("ollama/llama2") == ModelFormat.OLLAMA

    def test_get_tools_for_model_renders_catalog(self):
        rendered = get_tools_for_model("gpt-4")
        assert isinstance(rendered, list)
        assert all(isinstance(entry, dict) for entry in rendered)
        assert rendered == render_openai_tools(TOOL_DEFINITIONS)

    def test_get_tools_for_model_explicit_collection(self):
        tools = [ToolDefinition(name="a", description="A")]
        assert get_tools_for_model(
            tools, ModelFormat.ANTHROPIC
        ) == render_anthropic_tools(tools)


class TestAgentCapabilityModel:
    def test_github_write_tools_are_action_tools(self):
        for name in ("create_issue", "create_pull_request"):
            tool = get_tool_by_name(name)
            assert tool is not None
            assert tool.permission == Permission.GITHUB_WRITE
            assert tool.binding is None, f"{name} must not be a connector capability"

    def test_github_read_tools_have_non_secret_routing_binding(self):
        for name in ("list_prs", "list_issues", "get_workflow_status"):
            tool = get_tool_by_name(name)
            assert tool is not None
            assert tool.binding is not None
            assert tool.binding.connector_id
            assert validate_tool_definitions([tool]) == []

    def test_policy_only_tools_have_no_service(self):
        for name in ("search_wiki", "web_search", "start_game"):
            tool = get_tool_by_name(name)
            assert tool is not None
            assert tool.service == ""

    def test_no_secret_material_in_catalog(self):
        for tool in TOOL_DEFINITIONS:
            if tool.binding is None:
                continue
            for key in tool.binding.config:
                assert "token" not in key.lower()
                assert "secret" not in key.lower()
                assert "key" not in key.lower()
                assert "password" not in key.lower()
