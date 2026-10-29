# Workflow spec validation

`validate_step_graph` (in `agents.workflows.step_graph`) checks the
**structure** of a workflow spec built from a typed step DAG. A spec that
passes is well formed, not permitted: whether a particular subject may run a
step is decided at invocation time by ABAC and the tenant-side proxy PEP
(ADR-011). The domain specs that used it (finance, fundraising) were removed
in HAI-384; the validator stays for future specs.

## Workflow principal

`WorkflowSpec.principal` declares the security principal a harness should use
for a workflow invocation. It defaults to `WorkflowPrincipal("invoker")`,
which preserves the existing caller identity. A workflow that runs under an
organization-managed service principal declares its name instead, for example
`WorkflowPrincipal("kei-bug-intake")` on `BUG_TO_LINEAR_PR`. Names are
validated at construction against the identity service's
`^[a-z][a-z0-9-]{1,47}$` format. This is metadata for the harness to select a
runtime session; it does not open sessions, grant access, or change policy.

## Rules

| Rule | Violation message |
|------|-------------------|
| Step ids are unique | `<id>: duplicate step_id` |
| Every `depends_on` entry names a step in the spec | `<id>: depends_on '<dep>' not found in steps` |
| The dependency graph is acyclic (self-loops included) | `dependency cycle: a -> b -> a` |
| `permission` is a `Permission` member, never a bare string | `<id>: permission must be a Permission member, got bare '<value>'` |
| A mutation holds one of the spec's write permissions | `<id>: mutation step requires <permission> permission, ...` |
| A mutation has a read step among its ancestors | `<id>: mutation step must depend on a read step` |

When the spec has a cycle, the validator reports it and stops. Read
findings from inside a cycle would only add noise to the real defect.

## Typed permissions

A step's `permission` is a `Permission`. Because `Permission` is a `str` enum,
a bare string such as `"linear_write"` compares equal to
`Permission.LINEAR_WRITE`. The validator therefore checks the type: an untyped
value has no typo protection and no enforcement path in the policy engine.
