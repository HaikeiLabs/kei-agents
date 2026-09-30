"""Sync test: DVL tool definitions must agree with the vendored catalog.

Refresh the vendored fixture by re-fetching from
``DVL-Group/utilities`` agent/assistant-tools.v1.yaml (staging):

    gh api repos/DVL-Group/utilities/contents/agent/assistant-tools.v1.yaml?ref=staging --jq '.content' | base64 -d > tests/fixtures/assistant-tools.v1.yaml
"""

from __future__ import annotations

from pathlib import Path

import yaml

from agents.tool_definitions import (
    ToolParameter,
    validate_tool_definitions,
)
from agents.tools.dvl_utilities import DVL_UTILITIES_TOOL_DEFINITIONS

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "assistant-tools.v1.yaml"

# Map catalog proto types to JSON-schema types used in ToolParameter.
_TYPE_MAP: dict[str, str] = {
    "int32": "integer",
    "bool": "boolean",
    "string": "string",
    "platform.v1.PageRequest": "object",
    "Lane": "string",
    "Stage": "string",
    "OrderArExitState": "string",
}


def _load_catalog() -> list[dict]:
    with open(FIXTURE) as f:
        doc = yaml.safe_load(f)
    return doc["tools"]


def _catalog_key(entry: dict) -> str:
    return entry["name"]


def _build_catalog_index() -> dict[str, dict]:
    return {_catalog_key(e): e for e in _load_catalog()}


def test_dvl_tools_validate() -> None:
    violations = validate_tool_definitions(DVL_UTILITIES_TOOL_DEFINITIONS)
    assert violations == [], f"validation failed: {violations}"


def test_all_catalog_entries_have_definitions() -> None:
    defined = {t.name for t in DVL_UTILITIES_TOOL_DEFINITIONS}
    catalogued = set(_build_catalog_index())
    missing = catalogued - defined
    assert not missing, f"catalog entries without a ToolDefinition: {sorted(missing)}"


def test_no_extra_definitions() -> None:
    defined = {t.name for t in DVL_UTILITIES_TOOL_DEFINITIONS}
    catalogued = set(_build_catalog_index())
    extra = defined - catalogued
    assert not extra, f"ToolDefinitions without a catalog entry: {sorted(extra)}"


def test_definitions_match_catalog() -> None:
    catalog = _build_catalog_index()
    tools_by_name = {t.name: t for t in DVL_UTILITIES_TOOL_DEFINITIONS}

    for name, entry in sorted(catalog.items()):
        tool = tools_by_name.get(name)
        assert tool is not None, f"missing definition for {name!r}"

        # Summary -> description.
        assert tool.description == entry["summary"], (
            f"{name}: description {tool.description!r} != summary {entry['summary']!r}"
        )

        # Arguments -> parameters.
        catalog_args: list[dict] = entry.get("arguments") or []
        raw = tool.parameters
        tool_params: list[ToolParameter] = list(raw) if isinstance(raw, list) else []

        assert len(tool_params) == len(catalog_args), (
            f"{name}: expected {len(catalog_args)} parameters, got {len(tool_params)}"
        )

        for cat_arg, tool_param in zip(catalog_args, tool_params):
            assert tool_param.name == cat_arg["field"], (
                f"{name}: parameter name {tool_param.name!r} != field {cat_arg['field']!r}"
            )
            expected_type = _TYPE_MAP.get(cat_arg["type"])
            assert expected_type is not None, (
                f"{name}: unknown catalog type {cat_arg['type']!r}; "
                f"add a mapping to _TYPE_MAP"
            )
            assert tool_param.type == expected_type, (
                f"{name}: param {tool_param.name} type {tool_param.type!r} != {expected_type!r}"
            )
            assert tool_param.description == cat_arg["description"], (
                f"{name}: param {tool_param.name} description "
                f"{tool_param.description!r} != {cat_arg['description']!r}"
            )
