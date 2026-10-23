# Eval suites for the prebuilt agents

kei-agents keeps deterministic eval suites for its two prebuilt agents and
workflow prompts. Kei infers tool names at call time, so suites do not embed
tool definitions. The retained cases cover prompts that need no tool call;
cases that asserted a catalog tool invocation or catalog-based access decision
were removed with the duplicate catalogs.

## Layout

| Path | What it holds |
| --- | --- |
| `src/agents/prompts/*.md` | Agent system prompts |
| `src/agents/prompts/workflows/*.md` | Workflow system prompts |
| `src/agents/evals/targets.py` | Prompts included in the suites |
| `src/agents/evals/cases/*.py` | Hand-written no-tool case tables |
| `src/agents/evals/schema.py` | Validator for the suite schema |
| `src/agents/evals/export.py` | Renders `evals/suites/*.json` |
| `evals/suites/*.json` | Generated suites (committed) |

## Regenerate the suites

```bash
uv run python -m agents.evals.export --out evals/suites
uv run python -m agents.evals.export --out evals/suites --check
```

The output is byte-stable. Tool definitions are supplied by Kei at call time
and are intentionally absent from these suite files.
