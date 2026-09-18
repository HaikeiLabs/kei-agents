---
name: kei-governed-proxy
description: Build or review agents that use the Kei tenant-side governed proxy for CRM, Linear, GitHub, or other connector work. Use this whenever an agent, Discord/Slack harness, workflow, connector tool, policy gate, credential reference, audit event, workspace/org scope, consent gate, or provider adapter is being added or changed.
---

# Kei governed-proxy agent skill

Use this skill for agent capabilities that touch governed customer data or
provider writes. The harness owns conversation and workflow state; the
tenant-side Kei proxy owns provider execution and credential resolution. Kei's
catalog stores non-secret metadata, and ABAC evaluates policy metadata only.

## Required path

Implement and verify this path:

```text
semantic tool definition
  -> canonical manifest/catalog registration
  -> harness/model exposure
  -> proxy PEP invocation
  -> local policy + Kei/ABAC decision
  -> tenant-side provider adapter
  -> redacted result and audit event
```

Do not add provider clients, credential lookup, inline endpoints, or customer
payload handling to a metadata-only agent catalog. A harness may hold provider
results inside the tenant runtime when the proxy contract permits it, but it
must never send provider payloads, credentials, or secret values to Kei/ABAC.

## Implementation rules

1. Define semantic names, permissions, resource kinds, and delegated context in
   the canonical tool schema.
2. Never accept tenant, organization, or workspace identifiers from the model.
   Resolve them from the authenticated harness key/proxy context.
3. Treat local role/configuration mappings as discovery or UX filters only.
   They are not authorization. The proxy decision is authoritative.
4. Use opaque connector IDs and credential references only. Never resolve or
   return credentials in the harness.
5. Route every provider read/write through the governed invocation endpoint or
   its equivalent proxy command. Fail closed on missing proxy, denied policy,
   invalid scope, inactive connector, missing approval, or transport failure.
6. Require explicit consent before projecting CRM context into another
   provider, and require an approval reference for policy-controlled writes.
7. Use deterministic idempotency keys for writes. Reconcile unknown outcomes
   before retrying and never blindly duplicate a provider mutation.
8. Allowlist CRM fields for cross-provider projection. Redact contact data,
   notes, secrets, tokens, and arbitrary fields by default.
9. Emit audit metadata (subject, org/workspace, agent, framework, capability,
   action, resource, approval, trace, idempotency, decision, and digests), not
   provider payloads or credentials.

## Release gate

Every tool must be registered and proxy-reachable, or explicitly quarantined.
Quarantined tools must be absent from model/harness exposure and have a test
proving direct invocation cannot reach a provider adapter. Merging a pull
request or passing schema-only tests is not governance evidence.

## Verification checklist

Add synthetic tests for:

- catalog and manifest discovery;
- harness exposure and exact semantic-name mapping;
- proxy request shape and PEP reachability;
- allow, deny, missing connector, revoked connector, and timeout outcomes;
- org/workspace isolation;
- consent and approval gates;
- idempotent replay and uncertain-write recovery;
- CRM projection redaction and prompt-injection resistance;
- audit attribution and payload/secret absence;
- quarantined tools failing closed without provider calls.

Use fake proxy transports and synthetic CRM/Linear fixtures. Do not contact live
providers or use customer data in unit or integration tests.
