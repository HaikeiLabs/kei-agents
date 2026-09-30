# Kei Agents

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/HaikeiLabs/kei-agents/actions/workflows/tests.yaml/badge.svg)](https://github.com/HaikeiLabs/kei-agents/actions/workflows/tests.yaml)
[![Dependency Review](https://github.com/HaikeiLabs/kei-agents/actions/workflows/security.yaml/badge.svg)](https://github.com/HaikeiLabs/kei-agents/actions/workflows/security.yaml)

Agent definitions, tools, and prompts for the Kei AI platform.

## Architecture

This repository defines agent capabilities/tool schemas and semantic mappings
only. Provider execution and customer data retrieval happen in the
tenant-side distributed proxy; Kei is a metadata catalog and ABAC is a policy
decision point.

- **Tool schemas and semantic mappings**: This repository owns agent
  capabilities, tool definitions, and semantic mappings between them.
- **Connector bindings are non-secret routing metadata**: Bindings reference
  credentials and endpoints by opaque identifiers; they never carry credential
  material.
- **Provider execution is tenant-side**: Provider execution and customer data
  retrieval happen in the tenant-side distributed proxy, never in Kei or ABAC.
- **ABAC is metadata/policy only**: ABAC receives metadata/policy requests
  only and never customer payloads, results, or credentials.
- **Writes are agent action tools**: GitHub, CRM, and Linear writes are agent
  action tools executed by the agent harness, not ABAC connector capabilities.

Do not add provider clients or credential resolution to this repository. This
is a docs-only repository; see [CONTRIBUTING.md](CONTRIBUTING.md) and
[AGENTS.md](AGENTS.md).

## Installation

```bash
pip install kei-agents
```

> **Note**: PyPI publication is planned. See the [PyPI Distribution Plan](docs/pypi-distribution-plan.md) for the release timeline.

## Quick Start

```python
from agents import TOOL_DEFINITIONS, render_tools, ModelFormat

# Get tools in OpenAI format
tools = render_tools(TOOL_DEFINITIONS, ModelFormat.OPENAI)

# Or detect automatically from model name
tools = render_tools(TOOL_DEFINITIONS, "gpt-4")
```

## Features

- **Multi-model support**: OpenAI, Anthropic, Ollama, Llama, vLLM
- **Tool definitions**: Pre-built tool schemas for common operations
- **Permission-based access**: Tools gated by permissions
- **Category organization**: Tools organized by category

## Available Tools

| Tool | Description | Permission |
|------|-------------|------------|
| search_wiki | Search conversation history | search_wiki |
| web_search | Search the web for current info | web_search |
| schedule_meeting | Schedule calendar meetings | schedule_meetings |
| list_prs | List GitHub pull requests | github_read |
| list_issues | List GitHub issues | github_read |
| create_issue | Create GitHub issues | github_write |
| get_workflow_status | Get CI/CD workflow status | github_read |
| create_pull_request | Create PRs | github_write |
| start_game | Start interactive games | search_wiki |

See `src/agents/tool_definitions.py` for full list.

### Governed Connector Read Schemas

Provider-neutral, schema-only read capabilities for governed connectors
(GitHub, Linear, Google Drive/Docs, S3, http_api/CRM, Gmail, Tito). Each schema expresses a
capability/resource/action binding and a delegated-context contract; it carries
no credentials, arbitrary URLs, tenant identifiers, or handlers — execution is
delegated to the tenant-side distributed proxy. See
[docs/connector-tool-schemas.md](docs/connector-tool-schemas.md).

| Tool | Connector | Resource | Permission |
|------|-----------|----------|------------|
| github.get_repository | github | repository | github_read |
| github.get_issue | github | issues | github_read |
| github.get_pull_request | github | pull_requests | github_read |
| linear.list_issues | linear | issues | linear_read |
| linear.get_issue | linear | issues | linear_read |
| linear.list_projects | linear | projects | linear_read |
| drive.list_files | drive | files | drive_read |
| drive.get_file | drive | files | drive_read |
| docs.get_document | drive | documents | drive_read |
| s3.list_objects | s3 | objects | s3_read |
| s3.get_object | s3 | objects | s3_read |
| s3.get_object_metadata | s3 | objects | s3_read |
| http_api.list_records | http_api | records | http_api_read |
| http_api.get_record | http_api | records | http_api_read |
| gmail.search_messages | gmail | messages | gmail_read |
| gmail.get_message | gmail | messages | gmail_read |
| tito.list_events | tito | events | tito_read |
| tito.get_event | tito | events | tito_read |
| tito.list_releases | tito | releases | tito_read |
| tito.get_ticket_summary | tito | tickets | tito_read |

### Harness Agent Definitions

`agents.agent_definitions` declares each harness agent's grant surface as data:
typed `Permission` members and the catalog tools it exposes.
`validate_agent_definitions` rejects bare-string permissions, unknown tools,
tools whose permission is not granted, and any `*_approve` permission (reserved).

| Agent | Harness | Permissions |
|-------|---------|-------------|
| `pde_search_agent` | `pde` | `drive_read`, `notion_read`, `gmail_read`, `tito_read` |
| `pedro` | `discord` | `github_read`, `github_write`, `crm_read`, `crm_write`, `linear_read`, `linear_write`, `drive_read`, `fundraising_read`, `fundraising_write`, `finance_read`, `finance_write` |

### Fundraising Workflow Spec

`agents.workflows.fundraising` is a harness-neutral fundraising spec. The
investor pipeline is `prospect → contacted → meeting → diligence → committed`,
and any open stage can move to `passed`. There are three canonical workflows:
`fundraising.investor_outreach`, `fundraising.data_room_share`, and
`fundraising.investor_decision`. Each one reads from CRM or the Drive data room
first, then places every data-room share, stage change, Linear follow-up, and
notification.
`validate_fundraising_workflow` checks the spec structure; see
[docs/workflow-validation.md](docs/workflow-validation.md).

## Development

```bash
# Clone repository
git clone https://github.com/HaikeiLabs/kei-agents.git
cd kei-agents

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check .

# Type check
mypy src/agents
```

## Security

- Dependency vulnerabilities scanned weekly via `pip-audit`
- Dependency review on all PRs
- See [Security Policy](SECURITY.md)

## Distribution

For details on PyPI distribution, release process, and container registry strategy, see the [PyPI Distribution Plan](docs/pypi-distribution-plan.md).

## Contributing

Contributions welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md).

All contributors must be approved by existing maintainers. See [CONTRIBUTORS](CONTRIBUTORS).

### Design Documents

- [Workflow Spec Validation](docs/workflow-validation.md) - structural rules `validate_read_first` enforces: cycles, reachability-based approval gates, typed permissions, egress classification
- [npm Distribution Strategy](docs/npm-distribution-strategy.md) - proposal for publishing a JS/TypeScript consumable, plus Go distribution as a separate workstream (not approved)

## License

MIT License - see [LICENSE](LICENSE).

## Links

- [GitHub](https://github.com/HaikeiLabs/kei-agents)
- [Issues](https://github.com/HaikeiLabs/kei-agents/issues)