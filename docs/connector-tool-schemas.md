# Governed Connector Read Tool Schemas

Provider-neutral, schema-only read capabilities for governed connectors. These
schemas are agent capabilities: they describe *what* an agent may read and the
governance contract around it. They are **not** provider clients and never
resolve credentials. Provider execution and customer data retrieval happen in
the tenant-side distributed proxy; Kei is a metadata catalog and ABAC is a
policy decision point only.

## Tool-manifest v3 route contract

Each v3 entry retains common `source` and `operation_class` metadata and has a
`route` object containing exactly one typed branch. Connector routes carry the
registered `connector_id` plus explicit operation metadata; harness routes
identify the executor and native registration and omit connector-only fields.
There is no free-standing `execution_class` field.

```json
{
  "schema": "kei.tool-manifest/v3",
  "tools": [
    {
      "name": "github.get_issue",
      "source": "github",
      "operation_class": "read",
      "route": {
        "connector_binding": {"connector_id": "conn_github_1"}
      },
      "required_capabilities": ["issue.read"],
      "resource_types": [{"type": "issue", "parent_type": "repository"}]
    },
    {
      "name": "codex.shell",
      "source": "codex",
      "operation_class": "write",
      "route": {
        "harness_executor": {
          "executor": "codex",
          "registration": "codex.shell"
        }
      }
    }
  ]
}
```

Connector `required_capabilities` (non-empty) and optional `resource_types`
must be declared by a typed connector operation descriptor. These entry-level
fields are not duplicated inside the route branch. Resource types may be omitted
only when the capability is genuinely resource-less; they name kinds, never a
resource ID. They are not inferred from `Permission`, `source`, or binding
config. If a binding and a harness handler are both present, the connector
binding selects the route. Unknown and malformed route branches fail closed.
V2 manifests remain readable during migration.

## Design principles

Each governed connector read schema expresses four things:

1. **Capability binding** — a `Permission` gate (e.g. `linear_read`) and a
   `ToolCategory` organize the schema; a separate explicit operation descriptor
   declares canonical `required_capabilities` for the v3 route.
2. **Resource binding** — typed operation metadata declares `resource_types`
   (resource kinds such as `repository`, `issue`, or `object`). These are not
   resource IDs and are not inferred from `ToolBinding.config`.
3. **Action binding** — the tool `name` and `description` are the action
   (list/get). Reads are the only connector capabilities here; writes remain
   agent action tools, never connector capabilities.
4. **Delegated context** — `ToolBinding.delegated_context` lists the non-secret
   field names the tenant-side proxy supplies at invocation (tenant/resource/
   region scoping). The agent never provides them, so they must not appear as
   tool parameters.

## Hard invariants (enforced by `validate_tool_definitions`)

- **No provider credentials** — binding config keys/values that look like
  secrets are rejected.
- **No arbitrary URLs** — binding config keys that look like endpoints
  (`url`, `endpoint`, `base_url`, `host`, ...) and any string value containing
  `://` are rejected. Endpoints are resolved from the governed connection
  preset (`abac.connection_presets`), never embedded.
- **No tenant IDs chosen by the agent** — a parameter that collides with a
  `delegated_context` field, or that looks like a tenant identifier
  (`tenant_id`, `account_id`, `customer_id`, `organization_id`, `org_id`), is
  rejected on governed connector read tools.
- **No direct provider calls** — governed connector read tools (a `*_read`
  permission with a binding) must not declare a `handler`; execution is
  delegated to the tenant-side proxy. They must also declare a `service`.

## Covered connectors

| Connector | Permission | Category | Read schemas | Delegated context |
|-----------|-----------|----------|--------------|-------------------|
| GitHub    | `github_read`   | `github`   | `github.get_repository`, `github.get_issue`, `github.get_pull_request` | `tenant_id`, `repository` |
| Linear    | `linear_read`   | `linear`   | `linear.list_issues`, `linear.get_issue`, `linear.list_projects` | `tenant_id`, `workspace` |
| Google Drive/Docs | `drive_read` | `drive` | `drive.list_files`, `drive.get_file`, `docs.get_document` | `tenant_id`, `drive_id` |
| S3        | `s3_read`       | `s3`       | `s3.list_objects`, `s3.get_object`, `s3.get_object_metadata` | `tenant_id`, `bucket` |
| http_api/CRM | `http_api_read` | `http_api` | `http_api.list_records`, `http_api.get_record` | `tenant_id` |
| Gmail     | `gmail_read`    | `gmail`    | `gmail.search_messages`, `gmail.get_message` | `tenant_id`, `mailbox` |
| Tito      | `tito_read`     | `tito`     | `tito.list_events`, `tito.get_event`, `tito.list_releases`, `tito.get_ticket_summary` | `tenant_id`, `account` |

Gmail reads return message metadata and snippet only; the full body is
released only when ABAC authorizes the `gmail_include_body` policy attribute,
so it is never an agent parameter. Tito reads never return attendee PII;
`tito.get_ticket_summary` is aggregate counts by state/type. Both map to the
kei-policy-catalog `gmail` (`message.search`, `message.get`) and `tito`
(`event.list`, `event.get`, `release.list`, `ticket.summary`) capabilities.

`connector_id` values (`conn_github_1`, `conn_linear_1`, ...) are placeholders
that reference `abac.connection_presets.id`; the tenant-side proxy resolves the
real preset, endpoint, and credentials at invocation time.

## What is out of scope

- Provider clients, credential resolution, or secret material (docs-only repo).
- Kei shared connector types, migrations, invocation envelopes, or deployment
  interfaces — this repo only defines agent capabilities and semantic mappings.
- Writes: GitHub/CRM/Linear writes remain agent action tools executed by the
  agent harness, not ABAC connector capabilities.
