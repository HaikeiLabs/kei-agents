# Eval benchmark: qwen3.8-27b

- Model: `qwen3.8-27b`
- Harness: agentware
- Created: 2026-10-08T18:16:32+00:00
- Git SHA: `3edc30d462eb943980ae0665c191ba085c7b2ba2`
- Threshold: 95%

| Suite | Kind | Passed | Failed | Errors | Total | Pass rate | Mean case time | Status |
|---|---|---:|---:|---:|---:|---:|---:|---|
| kei-agents.pedro | agent | 27 | 0 | 0 | 27 | 100.0% | 33.5s | PASS |
| kei-agents.pde_search_agent | agent | 16 | 0 | 0 | 16 | 100.0% | 78.2s | PASS |
| kei-agents.bug_to_linear_pr | agent | 7 | 0 | 0 | 7 | 100.0% | 341.4s | PASS |
| kei-agents.crm_linear_followup | agent | 6 | 0 | 0 | 6 | 100.0% | 372.5s | PASS |
| kei-agents.finance | agent | 7 | 0 | 0 | 7 | 100.0% | 225.9s | PASS |
| kei-agents.fundraising | agent | 7 | 0 | 0 | 7 | 100.0% | 57.4s | PASS |
| kei-agents.github_pr_review | agent | 7 | 0 | 0 | 7 | 100.0% | 200.4s | PASS |
| kei-agents.leads | agent | 7 | 0 | 0 | 7 | 100.0% | 127.8s | PASS |
| kei-agents.support | agent | 7 | 0 | 0 | 7 | 100.0% | 1.8s | PASS |

Runner: suites ran on agentware 3edc30d and a279763, which score identically (python/src/evals is unchanged across them).
