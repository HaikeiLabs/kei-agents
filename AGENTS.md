# AGENTS.md

Instructions for coding agents working in this repository.

## Before starting any task

1. **Search the wiki first.** Query the personal LLM-Wiki knowledge base for the
   topic before writing or editing anything:
   `wiki search <topic>`. The wiki is the durable coordination surface for the
   Kei connector stack (decisions, claims, sources, entities).
2. **Read the canonical tenant-side proxy architecture.** The authoritative
   architecture is captured in the wiki under the "tenant data must stay behind
   distributed proxy" decision: Kei is a metadata catalog and ABAC is a policy
   decision point only. Provider execution and customer data retrieval happen in
   the tenant-side distributed proxy. Re-read that entry and any related
   decisions before updating architecture documentation.
3. **Coordinate via the wiki.** Record durable decisions, blockers, ownership,
   test evidence, and resolved interface questions in the wiki. Worktrees and
   PRs remain the source of truth for implementation code.
4. **Do not duplicate shared contracts or migrations.** Kei connector
   contracts (`data_connectors` migration, connector metadata, credential
   references, ABAC decision/audit contracts) are single-owner. Do not copy,
   re-define, or re-number shared migrations or contract schemas into this
   repository.

## Architecture invariants

- This repository defines agent metadata and semantic mappings only. Canonical
  tool definitions live in `kei-connector-contracts/schemas/*.tool-definition.v1.json`;
  Kei infers tool names at call time.
- Connector bindings are non-secret routing metadata.
- Provider execution and customer data retrieval happen in the tenant-side
  distributed proxy.
- ABAC receives metadata/policy requests only and never customer payloads,
  results, or credentials.
- GitHub and Linear writes are agent action tools, not ABAC connector
  capabilities.

## Hard rules

- Docs-only repository: do not add provider clients or credential resolution.
- Do not add provider clients or credential resolution.
