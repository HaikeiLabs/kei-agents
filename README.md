# Kei Agents

> **DEPRECATED: this repository is deprecated.** It was an example repository
> for building agents on Haikei Labs tooling and is no longer being developed
> or recommended for new work.
>
> - **What still works:** existing pins and already-published versions keep
>   working. Nothing is removed or yanked by this change, and it is not a
>   breaking change.
> - **What to use instead:** for building agents and tool calls on Haikei Labs
>   tooling, the recommended path is the [Agentware SDK](https://github.com/HaikeiLabs/Agentware).
>   No replacement for the example agents in this repository has been decided
>   yet.
> - **Questions:** open an issue on this repository. Security reports follow
>   [SECURITY.md](SECURITY.md) (a private security advisory, or
>   <team@kei.ai>).

Agent identity, permission, action adapter, and workflow metadata for the Kei
platform.

## Architecture

This repository contains no provider clients, credentials, connector bindings,
or tool-definition catalogs. The canonical tool definitions are the read-only
contract files in `kei-connector-contracts/schemas/*.tool-definition.v1.json`.
Kei infers available tool names at call time through Agentware and the
tenant-side `kei-proxy`.

Provider execution and customer data retrieval happen in the tenant-side
distributed proxy. ABAC handles metadata and policy decisions only; it never
receives customer payloads, results, or credentials. GitHub, CRM, and Linear
writes are agent action tools. Google Drive document writes use the harness and
the invoking user's OAuth token.

## Installation

```bash
pip install kei-agents
```

PyPI publication is planned. See [the distribution plan](docs/pypi-distribution-plan.md).

## Package capabilities

- Agent identity, permissions, and system prompts
- Workflow manifests and workflow behavior
- CRM, GitHub, and Google Drive action implementations
- Local policy evaluation helpers

See [the connector architecture](docs/connector-tool-schemas.md) and
[Google Drive write flow](docs/drive-write.md).

## Opt-in GitHub fix action

`GITHUB_FIX_ACTION_TOOL` (`github.create_fix_pr`) is a harness-defined action
with a `Permission.GITHUB_WRITE` gate. It is available only to the dedicated
fix-proposal agent after an explicit user request. The server selects the
repository and branch, validates the unified diff, and controls draft status;
the action has no repository, branch, shell, or credential arguments.

## Additional harness agents

- `bug_report_triage`: read-only diagnosis of sanitized BugBot reports.
- `fix_proposal`: bounded draft fixes through the opt-in GitHub action.

Both definitions are metadata; the harness supplies their prompts and routes
actions, while Kei evaluates permission metadata at call time.
