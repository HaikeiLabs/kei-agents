"""Tests for the exported eval suites (EV-C1 agentware.eval-suite.v1)."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

import pytest

from agents import ALL_TOOL_DEFINITIONS, Permission
from agents.evals import EVAL_TARGETS, SCHEMA_ID, validate_suite
from agents.evals.export import build_suites, check_suites, main, render_suite
from agents.evals.targets import AGENT_TARGETS, WORKFLOW_TARGETS
from agents.workflows.bug_to_linear_pr import FILE_BUG_TOOL, LINEAR_CREATE_ISSUE_TOOL

SUITES_DIR = Path(__file__).resolve().parent.parent / "evals" / "suites"
RESULTS_DIR = SUITES_DIR.parent / "results"
MIN_CASES = {"pedro": 20, "pde_search_agent": 12}
MIN_WORKFLOW_CASES = 5
# Proxy-delegated scoping keys every suite must assert are never arguments.
DELEGATED = {"tenant_id", "workspace", "repository", "drive_id", "mailbox", "account"}


def _committed() -> dict[str, dict[str, Any]]:
    return {
        path.name: json.loads(path.read_text())
        for path in sorted(SUITES_DIR.glob("*.json"))
    }


class TestExporter:
    def test_one_suite_per_target(self) -> None:
        assert sorted(build_suites()) == sorted(f"{t.name}.json" for t in EVAL_TARGETS)
        assert len(AGENT_TARGETS) == 2
        assert len(WORKFLOW_TARGETS) == 7

    def test_byte_stable(self) -> None:
        first = {name: render_suite(s) for name, s in build_suites().items()}
        second = {name: render_suite(s) for name, s in build_suites().items()}
        assert first == second

    def test_cli_output_is_byte_identical(self, tmp_path: Path) -> None:
        assert main(["--out", str(tmp_path / "a")]) == 0
        assert main(["--out", str(tmp_path / "b")]) == 0
        for path in sorted((tmp_path / "a").iterdir()):
            assert path.read_bytes() == (tmp_path / "b" / path.name).read_bytes()

    def test_committed_suites_are_current(self) -> None:
        assert check_suites(SUITES_DIR) == [], (
            "run: python -m agents.evals.export --out evals/suites"
        )
        assert main(["--check", "--out", str(SUITES_DIR)]) == 0

    def test_check_flags_stale_suite(self, tmp_path: Path) -> None:
        main(["--out", str(tmp_path)])
        (tmp_path / "pedro.json").write_text("{}\n")
        assert main(["--check", "--out", str(tmp_path)]) == 1

    def test_tools_are_openai_rendered_catalog_tools(self) -> None:
        catalog = {t.name for t in ALL_TOOL_DEFINITIONS}
        for target in EVAL_TARGETS:
            suite = build_suites()[f"{target.name}.json"]
            names = [t["function"]["name"] for t in suite["tools"]]
            assert names == list(target.tools)
            assert set(names) <= catalog
            assert all(t["type"] == "function" for t in suite["tools"])


@pytest.mark.parametrize("name", sorted(build_suites()))
class TestCommittedSuite:
    def test_validates_against_schema(self, name: str) -> None:
        suite = _committed()[name]
        assert suite["schema"] == SCHEMA_ID
        assert validate_suite(suite) == []

    def test_case_count(self, name: str) -> None:
        stem = name.removesuffix(".json")
        cases = _committed()[name]["cases"]
        assert len(cases) >= MIN_CASES.get(stem, MIN_WORKFLOW_CASES)

    def test_covers_every_case_category(self, name: str) -> None:
        expects = [c["expect"] for c in _committed()[name]["cases"]]
        assert any(
            isinstance(e.get("tool"), str) and not e.get("deny") for e in expects
        ), "tool selection"
        assert any(e.get("args") for e in expects), "argument semantics"
        assert any(DELEGATED & set(e.get("forbidden_arg_keys", [])) for e in expects), (
            "delegated keys"
        )
        assert any("tool" in e and e["tool"] is None for e in expects), "no-tool answer"
        assert any(e.get("deny") for e in expects), "deny"

    def test_no_endpoint_addresses(self, name: str) -> None:
        assert _endpoint_leaks((SUITES_DIR / name).read_text()) == []


def _endpoint_leaks(text: str) -> list[str]:
    """Private endpoints must never reach a public repo (IPs, URLs, tailnet hosts)."""
    leaks = re.findall(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", text)
    leaks += re.findall(r"\bhttps?://\S+", text)
    leaks += re.findall(r"[\w.-]+\.ts\.net\b", text, re.IGNORECASE)
    leaks += [host for host in ("spark-", "pedrogpt") if host in text.lower()]
    return leaks


@pytest.mark.parametrize(
    "path",
    sorted(p for p in RESULTS_DIR.rglob("*") if p.is_file())
    if RESULTS_DIR.is_dir()
    else [],
    ids=str,
)
def test_committed_results_have_no_endpoint_addresses(path: Path) -> None:
    assert _endpoint_leaks(path.read_text()) == []


def test_pedro_default_group_deny_cases() -> None:
    suite = _committed()["pedro.json"]
    deny = [c for c in suite["cases"] if c["expect"].get("deny")]
    assert deny
    for c in deny:
        assert c["context"]["allowed_tools"] == [
            "file_bug",
            "search_wiki",
            "web_search",
        ]


def _valid_suite() -> dict[str, Any]:
    return copy.deepcopy(build_suites()["bug_to_linear_pr.json"])


def _first_case(suite: dict[str, Any]) -> dict[str, Any]:
    case: dict[str, Any] = suite["cases"][0]
    return case


class TestValidator:
    def test_valid(self) -> None:
        assert validate_suite(_valid_suite()) == []

    @pytest.mark.parametrize(
        ("mutate", "message"),
        [
            (lambda s: s.update(extra=1), "unknown key 'extra'"),
            (lambda s: s.update(schema="v0"), "schema must be"),
            (lambda s: s.update(suite="pedro"), "dotted"),
            (lambda s: s.update(kind="bot"), "kind must be"),
            (lambda s: s.update(system_prompt_file="x.md"), "exactly one"),
            (lambda s: s.update(repeats=0), "repeats"),
            (lambda s: s.update(cases=[]), "non-empty"),
            (
                lambda s: s["cases"].append(copy.deepcopy(s["cases"][0])),
                "duplicate case id",
            ),
            (lambda s: _first_case(s).update(id="Bad Id"), "must match"),
            (lambda s: _first_case(s).update(note="x"), "unknown key 'note'"),
            (
                lambda s: _first_case(s)["expect"].update(tool="nope"),
                "not in the suite",
            ),
            (
                lambda s: _first_case(s)["expect"].update(tool=None),
                "need an expected tool",
            ),
            (
                lambda s: _first_case(s)["expect"].update(args={"bogus": 1}),
                "not declared",
            ),
            (
                lambda s: _first_case(s)["expect"].update(args={"priority": "p0"}),
                "not one of",
            ),
            (
                lambda s: _first_case(s)["expect"].update(
                    forbidden_arg_keys=["team_key"]
                ),
                "schema-required",
            ),
            (
                lambda s: _first_case(s)["expect"].update(
                    forbidden_tools=["linear.create_issue"]
                ),
                "both expected",
            ),
            (
                lambda s: _first_case(s)["expect"].update(deny=True),
                "need context.allowed_tools",
            ),
            (
                lambda s: _first_case(s)["expect"].update(content={"regex": ["("]}),
                "does not compile",
            ),
            (
                lambda s: _first_case(s)["expect"].update(content={"maybe": ["x"]}),
                "unknown key 'maybe'",
            ),
            (
                lambda s: _first_case(s)["context"].update(
                    allowed_tools=["linear.get_issue"]
                ),
                "would be denied",
            ),
            (
                lambda s: _first_case(s)["context"].update(allowed_tools=["ghost"]),
                "not in the suite",
            ),
        ],
    )
    def test_rejects(self, mutate: Any, message: str) -> None:
        suite = _valid_suite()
        mutate(suite)
        violations = validate_suite(suite)
        assert any(message in v for v in violations), violations

    def test_deny_case_cannot_expect_an_allowed_tool(self) -> None:
        suite = _valid_suite()
        deny = next(c for c in suite["cases"] if c["expect"].get("deny"))
        deny["context"]["allowed_tools"].append(deny["expect"]["tool"])
        assert any("expects allowed tool" in v for v in validate_suite(suite))


class TestBugToLinearPrTools:
    @pytest.mark.parametrize("tool", [FILE_BUG_TOOL, LINEAR_CREATE_ISSUE_TOOL])
    def test_linear_write_action_tool(self, tool: Any) -> None:
        assert tool.permission is Permission.LINEAR_WRITE
        assert tool.binding is None and tool.handler is None
        params = {p.name: p for p in tool.parameters}
        # Semantics rule: an issue carries its parent team; the workspace is
        # proxy-delegated and never an argument.
        assert params["team_key"].required
        assert not DELEGATED & set(params)

    def test_workflow_connector_refs_resolve(self) -> None:
        from agents.workflows.bug_to_linear_pr import (
            BUG_TO_LINEAR_PR,
            validate_workflow,
        )

        names = {t.name for t in ALL_TOOL_DEFINITIONS}
        assert validate_workflow(BUG_TO_LINEAR_PR, names) == []
