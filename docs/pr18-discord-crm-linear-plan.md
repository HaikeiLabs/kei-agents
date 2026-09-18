# PR #18 Discord CRM-to-Linear implementation plan

## Release gate

Every tool introduced by PR #18 must be either registered in the canonical
agent/tool schema and reachable through the Kei proxy for policy evaluation, or
explicitly denied and quarantined. A merged pull request and passing local
schema tests are not evidence of governance.

Registered tools must be discoverable from the package catalog, exposed by the
Discord harness, mapped to a canonical capability/resource, evaluated by the
proxy PEP, scoped by the authenticated organization/workspace, and covered by
allow/deny, redaction, audit, idempotency, and synthetic-provider tests.

Quarantined tools must be absent from model and Discord exposure, fail closed,
and have a test proving they cannot reach a provider adapter.

## Tool disposition

| Tool | Initial disposition |
| --- | --- |
| `leads_workflow.get_lead` | registered as CRM `lead.read` |
| `leads_workflow.list_leads` | registered as CRM `lead.read` |
| `leads_workflow.create_lead` | registered as CRM `lead.create` |
| `leads_workflow.update_lead` | registered as CRM `lead.update` |
| `leads_workflow.submit_for_approval` | registered as workflow approval metadata |
| `leads_workflow.approve_lead` | registered as workflow approval metadata |
| `leads_workflow.reject_lead` | registered as workflow approval metadata |
| `leads_workflow.resolve_duplicate` | quarantined until a provider/workflow contract exists |

Linear task creation is an agent action mapped to the tenant-side proxy
capability `issue.create`; it is not a credential-bearing connector schema.

## End-to-end contract

```text
Discord message -> canonical tool catalog -> harness exposure
  -> tenant-side Kei proxy PEP -> local policy/ABAC decision
  -> tenant-side CRM or Linear adapter -> redacted result and audit event
```

Tenant/workspace scope comes from the authenticated harness key. CRM context is
projected through an allowlist after explicit user consent. Email, phone,
free-form notes, secrets, and arbitrary provider fields are excluded by
default. Linear writes require an approval reference when policy requires it.

Idempotency keys are derived from tenant, workspace, Discord thread/message,
CRM record, and workflow version. Unknown write outcomes are reconciled before
retrying. Denials, scope failures, missing approval, revoked connectors, and
redaction violations fail closed.

## Required evidence

- canonical registration and Discord exposure tests;
- proxy reachability and local policy allow/deny tests;
- organization/workspace isolation tests;
- consent and approval tests;
- redacted audit-event tests;
- duplicate/retry/idempotency tests;
- synthetic CRM and Linear fixtures only.

## Reusable implementation skill

The governed-proxy implementation rules are captured in
`skills/kei-governed-proxy/SKILL.md`. Harness-local role mappings may control
discovery, but they do not authorize CRM or Linear operations; the proxy PEP
decision is authoritative.
