"""Tests for exported Agentware eval suites."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

import pytest

from agents.evals import EVAL_TARGETS, SCHEMA_ID, validate_suite
from agents.evals.export import build_suites, check_suites, main, render_suite
from agents.evals.targets import AGENT_TARGETS, WORKFLOW_TARGETS

SUITES_DIR = Path(__file__).resolve().parent.parent / "evals" / "suites"
RESULTS_DIR = SUITES_DIR.parent / "results"


def _committed() -> dict[str, dict[str, Any]]:
    return {
        path.name: json.loads(path.read_text())
        for path in sorted(SUITES_DIR.glob("*.json"))
    }


class TestExporter:
    def test_one_suite_per_target(self) -> None:
        assert sorted(build_suites()) == sorted(f"{t.name}.json" for t in EVAL_TARGETS)
        assert len(AGENT_TARGETS) == 2
        assert len(WORKFLOW_TARGETS) == 4

    def test_suites_rely_on_runtime_tool_inference(self) -> None:
        for suite in build_suites().values():
            assert suite["tools"] == []
            assert suite["cases"]
            assert all(case["expect"].get("tool") is None for case in suite["cases"])

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
        assert check_suites(SUITES_DIR) == []
        assert main(["--check", "--out", str(SUITES_DIR)]) == 0

    def test_check_flags_stale_suite(self, tmp_path: Path) -> None:
        main(["--out", str(tmp_path)])
        (tmp_path / "pedro.json").write_text("{}\n")
        assert main(["--check", "--out", str(tmp_path)]) == 1


@pytest.mark.parametrize("name", sorted(build_suites()))
class TestCommittedSuite:
    def test_validates_against_schema(self, name: str) -> None:
        suite = _committed()[name]
        assert suite["schema"] == SCHEMA_ID
        assert validate_suite(suite) == []

    def test_cases_are_no_tool_cases(self, name: str) -> None:
        suite = _committed()[name]
        assert suite["tools"] == []
        assert suite["cases"]
        assert all(case["expect"].get("tool") is None for case in suite["cases"])

    def test_no_endpoint_addresses(self, name: str) -> None:
        assert _endpoint_leaks((SUITES_DIR / name).read_text()) == []


def _endpoint_leaks(text: str) -> list[str]:
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


def _valid_suite() -> dict[str, Any]:
    return copy.deepcopy(build_suites()["bug_to_linear_pr.json"])


def _first_case(suite: dict[str, Any]) -> dict[str, Any]:
    return suite["cases"][0]


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
                lambda s: _first_case(s)["expect"].update(content={"regex": ["("]}),
                "does not compile",
            ),
            (
                lambda s: _first_case(s)["expect"].update(content={"maybe": ["x"]}),
                "unknown key 'maybe'",
            ),
        ],
    )
    def test_rejects(self, mutate: Any, message: str) -> None:
        suite = _valid_suite()
        mutate(suite)
        violations = validate_suite(suite)
        assert any(message in v for v in violations), violations
