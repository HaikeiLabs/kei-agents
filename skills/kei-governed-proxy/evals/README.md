# kei-governed-proxy evals

Table-test evals for the `kei-governed-proxy` skill (EV-C1 contract): each
eval carries `expectations` plus a matching `checks` array of deterministic,
case-insensitive checks (`contains_all`, `contains_any`, `regex`,
`not_contains`) — one check per expectation, literal tokens taken from
SKILL.md. There is no LLM grader. Each prompt ends with "Do not execute anything — just explain in text." It does not forbid tools: the runner's sandbox offers only the skill tool, and the model has to be free to load the skill under test.

## Running

The runner is the skills runner from `HaikeiLabs/skills` at `origin/main`
(the deterministic-grading PR adds `--model-profile` and `--skills-dir`).
This skill lives in this repo, so point the runner's `--skills-dir` at this
repo's `skills/` directory:

```bash
export EVAL_DEEPSEEK_BASE_URL=<deepseek eval server>   # env only, never commit
export EVAL_QWEN_BASE_URL=<qwen eval server>           # env only, never commit

node <skills-runner>/scripts/run-evals.mjs \
  --skills-dir <this-repo>/skills \
  --skill kei-governed-proxy \
  --harness opencode \
  --model-profile deepseek-v4-flash --jobs 1 \
  --out /tmp/sk-int-out/kei-governed-proxy-deepseek

node <skills-runner>/scripts/run-evals.mjs \
  --skills-dir <this-repo>/skills \
  --skill kei-governed-proxy \
  --harness opencode \
  --model-profile qwen3.8-27b --jobs 1 \
  --out /tmp/sk-int-out/kei-governed-proxy-qwen
```

- `--jobs 1`: the model servers are shared with other workers.
- Profiles resolve from the runner's `evals/model-profiles.yaml`; the base
  URLs come from `EVAL_DEEPSEEK_BASE_URL` / `EVAL_QWEN_BASE_URL` (env only —
  never commit endpoints or hostnames).
- The runner runs each prompt with and without the skill, grades with the
  deterministic checks, and writes `benchmark.{json,md}` (schema
  `haikei.eval-benchmark.v1`); the default threshold is 0.9.
- The runner's sandbox denies `bash`, `edit`, `webfetch` and subagents by
  design. The only tool left is the skill loader (plus reads inside the
  installed skill), so evals judge the written answer the skill produces.

## Results

Deterministic checks, with the skill, 2 repeats (a case passes only if both pass).
Benchmarks are committed under `evals/results/<date>-<profile>/` (`benchmark.{json,md}`).

| Profile | Pass rate | Cases | Benchmark |
|---|---:|---:|---|
| deepseek-v4-flash | 100% | 6/6 | `results/2026-10-09-deepseek-v4-flash/` |
| qwen3.8-27b | 100% | 6/6 | `results/2026-10-09-qwen3.8-27b/` |

| # | Case | deepseek-v4-flash | qwen3.8-27b |
|---|---|---|---|
| 1 | Add a Discord tool that reads a CRM lead and creates a Linear follow-u | pass | pass |
| 2 | A legacy tool has a local role permission and a provider client handle | pass | pass |
| 3 | Review a connector tool schema for tenant_id, workspace_id, an API tok | pass | pass |
| 4 | Our harness's kei-proxy sidecar is down during a deploy. A user asks t | pass | pass |
| 5 | What exactly goes into the audit event for a governed CRM read, and wh | pass | pass |
| 6 | We want the agent to take a CRM contact's notes and include them in a  | pass | pass |
