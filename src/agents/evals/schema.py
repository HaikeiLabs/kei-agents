"""Validator for ``agentware.eval-suite.v1`` suite files (EV-C1 §1).

The canonical runner lives in Agentware (``python/src/evals``); this module
checks suites before they are written so a malformed case fails here, in
unit tests, rather than at run time. Validation is strict, like the runner:
unknown keys at any level are violations.
"""

from __future__ import annotations

import re
from typing import Any

SCHEMA_ID = "agentware.eval-suite.v1"

_SUITE_KEYS = frozenset(
    {
        "schema",
        "suite",
        "kind",
        "system_prompt",
        "system_prompt_file",
        "tools",
        "repeats",
        "cases",
    }
)
_CASE_KEYS = frozenset({"id", "prompt", "context", "expect"})
_CONTEXT_KEYS = frozenset({"role", "groups", "allowed_tools"})
_EXPECT_KEYS = frozenset(
    {
        "tool",
        "args",
        "required_arg_keys",
        "forbidden_arg_keys",
        "forbidden_tools",
        "deny",
        "content",
    }
)
_CONTENT_KEYS = frozenset({"contains_all", "contains_any", "regex", "not_contains"})
_KINDS = frozenset({"agent", "skill"})
_CASE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_SUITE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*(\.[a-z0-9][a-z0-9_-]*)+$")


def _is_str_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(v, str) and v for v in value)


def _unknown(where: str, obj: dict[str, Any], allowed: frozenset[str]) -> list[str]:
    return [f"{where}: unknown key {key!r}" for key in sorted(set(obj) - allowed)]


def _tool_schemas(tools: object, violations: list[str]) -> dict[str, dict[str, Any]]:
    """Index OpenAI function tools by name, recording shape violations."""
    schemas: dict[str, dict[str, Any]] = {}
    if not isinstance(tools, list):
        violations.append("tools must be a list")
        return schemas
    for i, tool in enumerate(tools):
        fn = tool.get("function") if isinstance(tool, dict) else None
        if (
            not isinstance(tool, dict)
            or tool.get("type") != "function"
            or not isinstance(fn, dict)
        ):
            violations.append(f"tools[{i}]: not an OpenAI function tool")
            continue
        name = fn.get("name")
        params = fn.get("parameters")
        if not isinstance(name, str) or not name:
            violations.append(f"tools[{i}]: function name is required")
            continue
        if name in schemas:
            violations.append(f"tools[{i}]: duplicate tool {name!r}")
        if not isinstance(fn.get("description"), str) or not fn["description"]:
            violations.append(f"tool {name}: description is required")
        if not isinstance(params, dict) or params.get("type") != "object":
            violations.append(f"tool {name}: parameters must be a JSON object schema")
            params = {"type": "object", "properties": {}, "required": []}
        schemas[name] = params
    return schemas


def _validate_content(where: str, content: object) -> list[str]:
    if not isinstance(content, dict):
        return [f"{where}: content must be an object"]
    violations = _unknown(where + ".content", content, _CONTENT_KEYS)
    for key in _CONTENT_KEYS & set(content):
        if not _is_str_list(content[key]):
            violations.append(
                f"{where}.content.{key} must be a list of non-empty strings"
            )
    for pattern in (
        content.get("regex", []) if _is_str_list(content.get("regex", [])) else []
    ):
        try:
            re.compile(pattern)
        except re.error as exc:
            violations.append(
                f"{where}.content.regex {pattern!r} does not compile: {exc}"
            )
    return violations


def _validate_args(
    where: str, expect: dict[str, Any], schema: dict[str, Any]
) -> list[str]:
    violations: list[str] = []
    properties = schema.get("properties", {})
    args = expect.get("args", {})
    if not isinstance(args, dict):
        return [f"{where}: args must be an object"]
    for key, value in args.items():
        prop = properties.get(key)
        if prop is None:
            violations.append(f"{where}: args key {key!r} is not declared by the tool")
            continue
        enum = prop.get("enum")
        if enum is not None and value not in enum:
            violations.append(f"{where}: args {key}={value!r} is not one of {enum}")
        json_type = prop.get("type")
        if json_type == "integer" and not (
            isinstance(value, int) and not isinstance(value, bool)
        ):
            violations.append(f"{where}: args {key} must be an integer")
        if json_type == "string" and not isinstance(value, str):
            violations.append(f"{where}: args {key} must be a string")
    for list_key in ("required_arg_keys", "forbidden_arg_keys"):
        if list_key in expect and not _is_str_list(expect[list_key]):
            violations.append(
                f"{where}: {list_key} must be a list of non-empty strings"
            )
    required = set(expect.get("required_arg_keys", []))
    forbidden = set(expect.get("forbidden_arg_keys", []))
    for key in sorted(required - set(properties)):
        violations.append(
            f"{where}: required_arg_keys {key!r} is not declared by the tool"
        )
    for key in sorted(forbidden & (required | set(args))):
        violations.append(f"{where}: {key!r} is both expected and forbidden")
    for key in sorted(forbidden & set(schema.get("required", []))):
        violations.append(f"{where}: forbidden key {key!r} is schema-required")
    return violations


def _validate_case(
    index: int, case: object, schemas: dict[str, dict[str, Any]]
) -> tuple[str | None, list[str]]:
    where = f"cases[{index}]"
    if not isinstance(case, dict):
        return None, [f"{where}: must be an object"]
    violations = _unknown(where, case, _CASE_KEYS)
    case_id = case.get("id")
    if not isinstance(case_id, str) or not _CASE_ID_RE.fullmatch(case_id):
        violations.append(f"{where}: id {case_id!r} must match {_CASE_ID_RE.pattern}")
        case_id = None
    else:
        where = f"case {case_id}"
    if not isinstance(case.get("prompt"), str) or not case["prompt"].strip():
        violations.append(f"{where}: prompt is required")

    allowed_tools: list[str] | None = None
    context = case.get("context")
    if context is not None:
        if not isinstance(context, dict):
            violations.append(f"{where}: context must be an object")
        else:
            violations += _unknown(where + ".context", context, _CONTEXT_KEYS)
            if "role" in context and not isinstance(context["role"], str):
                violations.append(f"{where}: context.role must be a string")
            if "groups" in context and not _is_str_list(context["groups"]):
                violations.append(f"{where}: context.groups must be a list of strings")
            if "allowed_tools" in context:
                if not _is_str_list(context["allowed_tools"]):
                    violations.append(
                        f"{where}: context.allowed_tools must be a list of strings"
                    )
                else:
                    allowed_tools = context["allowed_tools"]
                    for name in allowed_tools:
                        if name not in schemas:
                            violations.append(
                                f"{where}: allowed tool {name!r} is not in the suite"
                            )

    expect = case.get("expect")
    if not isinstance(expect, dict):
        return case_id, violations + [f"{where}: expect is required"]
    violations += _unknown(where + ".expect", expect, _EXPECT_KEYS)
    tool = expect.get("tool")
    has_tool = isinstance(tool, str)
    if "tool" in expect and tool is not None and not has_tool:
        violations.append(f"{where}: tool must be a tool name or null")
    if has_tool and tool not in schemas:
        violations.append(f"{where}: tool {tool!r} is not in the suite")
    arg_keys = {"args", "required_arg_keys", "forbidden_arg_keys"} & set(expect)
    if arg_keys and not has_tool:
        violations.append(f"{where}: {sorted(arg_keys)} need an expected tool")
    if has_tool and tool in schemas:
        violations += _validate_args(where, expect, schemas[tool])
    forbidden_tools = expect.get("forbidden_tools", [])
    if not isinstance(forbidden_tools, list) or not all(
        isinstance(t, str) for t in forbidden_tools
    ):
        violations.append(f"{where}: forbidden_tools must be a list of strings")
    elif has_tool and tool in forbidden_tools:
        violations.append(f"{where}: tool {tool!r} is both expected and forbidden")
    deny = expect.get("deny", False)
    if not isinstance(deny, bool):
        violations.append(f"{where}: deny must be a boolean")
    elif deny:
        if allowed_tools is None:
            violations.append(f"{where}: deny cases need context.allowed_tools")
        elif has_tool and tool in allowed_tools:
            violations.append(f"{where}: deny case expects allowed tool {tool!r}")
    elif has_tool and allowed_tools is not None and tool not in allowed_tools:
        violations.append(
            f"{where}: expected tool {tool!r} would be denied by allowed_tools"
        )
    if "content" in expect:
        violations += _validate_content(where, expect["content"])
    return case_id, violations


def validate_suite(suite: object) -> list[str]:
    """Validate one suite document. Returns violations; empty means valid."""
    if not isinstance(suite, dict):
        return ["suite must be a JSON object"]
    violations = _unknown("suite", suite, _SUITE_KEYS)
    if suite.get("schema") != SCHEMA_ID:
        violations.append(f"schema must be {SCHEMA_ID!r}")
    if not isinstance(suite.get("suite"), str) or not _SUITE_RE.fullmatch(
        suite["suite"]
    ):
        violations.append(
            f"suite must be a dotted <repo>.<name>, got {suite.get('suite')!r}"
        )
    if suite.get("kind") not in _KINDS:
        violations.append(f"kind must be one of {sorted(_KINDS)}")
    prompt_sources = [k for k in ("system_prompt", "system_prompt_file") if k in suite]
    if len(prompt_sources) != 1:
        violations.append("set exactly one of system_prompt or system_prompt_file")
    for key in prompt_sources:
        if not isinstance(suite[key], str) or not suite[key].strip():
            violations.append(f"{key} must be a non-empty string")
    repeats = suite.get("repeats", 1)
    if not isinstance(repeats, int) or isinstance(repeats, bool) or repeats < 1:
        violations.append("repeats must be a positive integer")
    schemas = _tool_schemas(suite.get("tools"), violations)
    cases = suite.get("cases")
    if not isinstance(cases, list) or not cases:
        return violations + ["cases must be a non-empty list"]
    seen: set[str] = set()
    for i, case in enumerate(cases):
        case_id, case_violations = _validate_case(i, case, schemas)
        violations += case_violations
        if case_id is not None:
            if case_id in seen:
                violations.append(f"duplicate case id {case_id!r}")
            seen.add(case_id)
    return violations


__all__ = ["SCHEMA_ID", "validate_suite"]
