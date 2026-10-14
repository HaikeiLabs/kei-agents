# Contributing to Kei Agents

We welcome contributions! Please follow these guidelines.

## Docs-only Repository

This is a docs-only repository: it defines agent capabilities/tool schemas and
semantic mappings, and must never add provider clients or credential
resolution. Provider execution and customer data retrieval happen in the
tenant-side distributed proxy; ABAC is a policy decision point only. Before
editing architecture or contracts documentation, follow the instructions in
[AGENTS.md](AGENTS.md) (search the wiki first, read the canonical tenant-side
proxy architecture, coordinate via the wiki, and do not duplicate shared
contracts or migrations).

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/kei-agents.git`
3. Install dev dependencies: `pip install -e ".[dev]"`

## Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Run linter
ruff check .

# Run type checker
mypy src/agents

# Run tests
pytest
```

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes
3. Ensure all tests pass and code passes linting/type checking
4. Update documentation if needed
5. Submit a Pull Request
6. Wait for review from a maintainer

## Agent evals

The `Agent evals` workflow (`.github/workflows/agent-evals.yaml`, a copy of
the HaikeiLabs/kei gate; runbook: kei `docs/agent-evals-gate.md`) grades the
suites in `evals/suites/` on both model profiles at a 95% threshold.

- **Pull requests** run only the suites the pull request changes, once per
  case. `agent-evals-report` is the check to watch. Each eval job stops after
  30 minutes (a timeout fails the check), and closing or merging the pull
  request cancels its eval run.
- **Nightly** (09:00 UTC on `main`, or by hand with workflow_dispatch) every
  suite runs 3 times per case. That averaged sweep is the record: a failing
  sweep opens or updates the "Nightly agent evals below 95%" issue, and a
  passing one closes it.
- **`evals:tuning`**: while a pull request is still tuning an agent's prompt
  or tools, add this label. Nothing runs, and the gate fails with
  "evals:tuning is set: remove the label to run the gate before merge". Remove
  it once the suite reaches at least 95% locally on both profiles with
  `--repeats 3`; removing it runs the gate.

## Code Style

- Use Python 3.11+ features
- Follow PEP 8 (enforced by ruff)
- Use type hints
- Write docstrings for public functions

## Commit Messages

Use conventional commits:
- `feat: add new tool definition`
- `fix: correct parameter type`
- `docs: update README`
- `chore: update dependencies`

## License

By contributing, you agree that your contributions will be licensed under the MIT License.