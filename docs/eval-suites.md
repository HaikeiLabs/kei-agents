# Eval suites for the prebuilt agents

kei-agents ships table-test eval suites for its prebuilt agents (Pedro, the PDE
search agent) and its seven workflows. They measure how well a model uses
the system prompts and tool schemas defined here, regardless of the harness
(Discord, PDE, openwebui) that later hosts the agent.

Suites follow the EV-C1 `agentware.eval-suite.v1` contract. No LLM grades
them: each case is a prompt plus a deterministic expected outcome, and the
result is pass or fail.

## Layout

| Path | What it holds |
| --- | --- |
| `src/agents/prompts/*.md` | Agent system prompts (`AgentDefinition.system_prompt_file`) |
| `src/agents/prompts/workflows/*.md` | Workflow system prompts |
| `src/agents/evals/targets.py` | Which prompt and catalog tools each suite uses |
| `src/agents/evals/cases/*.py` | The hand-written case tables |
| `src/agents/evals/schema.py` | Strict validator for the suite schema |
| `src/agents/evals/export.py` | Renders `evals/suites/*.json` |
| `evals/suites/*.json` | Generated suites (committed) |
| `evals/results/<date>-<profile>/` | Committed run results |

## Regenerate the suites

```bash
uv run python -m agents.evals.export --out evals/suites
uv run python -m agents.evals.export --out evals/suites --check   # CI: exit 1 if stale
```

The output is byte-stable. Tools are rendered with
`render_tools(..., ModelFormat.OPENAI)`, so a change to a tool description
shows up as a diff in the suites.

## What every suite covers

- **Tool selection:** the first tool call is the expected one.
- **Argument semantics:** exact values for the arguments that matter,
  including the parent of a child resource (`team_key` for a Linear issue,
  `entity` for a CRM record, `lead_id` for a follow-up task).
- **Delegated scoping:** `forbidden_arg_keys` asserts that proxy-delegated
  scope (`tenant_id`, `workspace`, `repository`, `drive_id`, `mailbox`,
  `account`) never appears as an argument.
- **No-tool answers:** `"tool": null` for greetings, general knowledge, and
  requests the agent must decline.
- **Deny:** `context.allowed_tools` drives the runner's agentware policy. A
  `deny` case passes when the policy denies the call, or the model never
  attempts a disallowed tool, and the reply says it was not allowed. For
  Pedro, the Discord `default` group may use only `file_bug`, `search_wiki`,
  and `web_search`; every data tool is admin-only.

The model never sees the caller's role. Access is enforced by policy, so the
prompts tell the agent to call the tool the request needs and to report a
denial honestly.

## Run them

The canonical runner is Agentware's `python/src/evals`:

```bash
PYTHONPATH=<agentware>/python/src python -m evals.main \
  --suite evals/suites --model-profile deepseek-v4-flash \
  --profiles <agentware>/evals/model-profiles.yaml --out /tmp/ka-evals-ds --jobs 1
```

Model endpoints come from the environment (`EVAL_DEEPSEEK_BASE_URL`,
`EVAL_QWEN_BASE_URL`). Never commit endpoint addresses. Improve the
prompts and tool descriptions, not the cases, until every suite reaches at
least 90% locally. CI fails below 95%.
