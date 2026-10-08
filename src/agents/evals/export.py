"""Export the eval suites as ``agentware.eval-suite.v1`` JSON files.

Usage::

    python -m agents.evals.export --out evals/suites

Writes one ``<target>.json`` per agent and workflow. Output is byte-stable:
the same source always renders the same bytes, so the committed suites can
be diffed and checked in CI with ``--check``.
"""

from __future__ import annotations

import argparse
import json
import sys
from importlib import resources
from pathlib import Path
from typing import Any

from agents.evals.cases import CASES
from agents.evals.schema import SCHEMA_ID, validate_suite
from agents.evals.targets import EVAL_TARGETS, EvalTarget
from agents.tool_definitions import (
    ALL_TOOL_DEFINITIONS,
    ModelFormat,
    ToolDefinition,
    render_tools,
)


def _catalog_tools(names: tuple[str, ...]) -> list[ToolDefinition]:
    catalog = {tool.name: tool for tool in ALL_TOOL_DEFINITIONS}
    missing = [name for name in names if name not in catalog]
    if missing:
        raise ValueError(f"tools not in the catalog: {missing}")
    return [catalog[name] for name in names]


def build_suite(target: EvalTarget) -> dict[str, Any]:
    """Build one suite document; raises ``ValueError`` if it is invalid."""
    prompt = (
        resources.files("agents")
        .joinpath(target.prompt_file)
        .read_text(encoding="utf-8")
    )
    suite: dict[str, Any] = {
        "schema": SCHEMA_ID,
        "suite": target.suite,
        "kind": "agent",
        "system_prompt": prompt,
        "tools": render_tools(_catalog_tools(target.tools), ModelFormat.OPENAI),
        "repeats": 1,
        "cases": CASES[target.name],
    }
    violations = validate_suite(suite)
    if violations:
        raise ValueError(f"{target.suite} is invalid:\n  " + "\n  ".join(violations))
    return suite


def build_suites() -> dict[str, dict[str, Any]]:
    """Build every suite, keyed by output file name."""
    return {f"{target.name}.json": build_suite(target) for target in EVAL_TARGETS}


def render_suite(suite: dict[str, Any]) -> str:
    """Serialize a suite deterministically."""
    return json.dumps(suite, indent=2, ensure_ascii=False) + "\n"


def write_suites(out: Path) -> list[Path]:
    """Write every suite into *out*; returns the written paths."""
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for file_name, suite in build_suites().items():
        path = out / file_name
        path.write_text(render_suite(suite), encoding="utf-8")
        written.append(path)
    return written


def check_suites(out: Path) -> list[str]:
    """Report suite files in *out* that are missing or out of date."""
    stale = []
    for file_name, suite in build_suites().items():
        path = out / file_name
        if not path.is_file() or path.read_text(encoding="utf-8") != render_suite(
            suite
        ):
            stale.append(str(path))
    return stale


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out", type=Path, default=Path("evals/suites"), help="output directory"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if a committed suite differs from the source instead of writing",
    )
    args = parser.parse_args(argv)
    if args.check:
        stale = check_suites(args.out)
        for stale_path in stale:
            print(f"stale: {stale_path}", file=sys.stderr)
        return 1 if stale else 0
    for path in write_suites(args.out):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
