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

**Every design or review must address all applicable rules below.** Do not
stop after addressing the first rule that comes to mind — check each rule
against your plan before considering it complete.

1. Define semantic names, permissions, resource kinds, and delegated context in
   the canonical tool schema.
2. Never accept tenant, organization, or workspace identifiers from the model.
   Resolve them from the authenticated harness key/proxy context, and name
   that source when you describe a design (a chat guild or channel ID is not
   an authenticated scope on its own).
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

## Scenario patterns

When asked to design or review a governed proxy integration, address **all**
applicable implementation rules, not just the first one that comes to mind.
Pay special attention to these recurring patterns:

### Proxy-unavailable during write

When the proxy sidecar is down during a provider write, the outcome is
**uncertain** — the write may or may not have been received. The correct
response is:

1. **Fail closed** — do not fall back to a direct provider client, inline
   credential resolution, or ungoverned API call.
2. **Reconcile before retrying** — check the actual provider state to
   determine whether the write succeeded, then retry with a deterministic
   idempotency key so a completed mutation is never blindly duplicated.
3. **Audit the denial** — record the blocked attempt with reason
   `proxy_unreachable`.

"Fail closed" is necessary but not sufficient; reconciliation and
idempotency are equally required when the call was a write.

### Connector schema review

When reviewing a tool schema, name each violation, the rule it breaks, and
the fix:

- `tenant_id`, `workspace_id`, org IDs as parameters: remove them; scope is
  resolved from the authenticated harness key/proxy context (rule 2).
- Tokens or secrets in binding metadata: replace them with an opaque
  connector ID and credential reference (rule 4).
- A direct provider handler: remove it; execution goes through the governed
  proxy invocation, which fails closed on a missing proxy, denied policy or
  transport failure (rule 5).

Then propose the corrected, handlerless schema: semantic name, permission,
resource kind, and delegated context (rule 1).

### CRM-to-provider projection

Cross-provider data projection (e.g., CRM fields into a Linear task) must:

1. Require explicit consent before projecting CRM context into another
   provider.
2. Allowlist only the fields needed for the projection.
3. Redact contact data, notes, secrets, tokens, and arbitrary fields by
   default.

Never assume projection is allowed by default — it requires all three.

## Release gate

Every tool must be registered and proxy-reachable, or explicitly quarantined.
Quarantined tools must be absent from model/harness exposure and have a test
proving direct invocation cannot reach a provider adapter. When asked whether
a tool can ship, give both paths: register it and route it through the proxy,
or quarantine it with those two requirements. Merging a pull
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
