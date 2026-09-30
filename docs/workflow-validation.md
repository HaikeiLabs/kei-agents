# Workflow spec validation

`validate_read_first` (in `agents.workflows.finance`), built on the shared
`validate_step_graph` (in `agents.workflows.step_graph`), checks the **structure**
of a workflow spec. A spec that passes is well formed, not permitted: whether a
particular subject may run a step is decided at invocation time by ABAC and the
tenant-side proxy PEP (ADR-011).

`validate_fundraising_workflow` (in `agents.workflows.fundraising`) applies
the same rules with fundraising payloads and permissions (`fundraising_write`
for mutations). It also rejects any `InvestorStageUpdate` that is not a valid
pipeline transition (`<id>: invalid stage transition prospect -> committed`).

## Rules

| Rule | Violation message |
|------|-------------------|
| Step ids are unique | `<id>: duplicate step_id` |
| Every `depends_on` entry names a step in the spec | `<id>: depends_on '<dep>' not found in steps` |
| The dependency graph is acyclic (self-loops included) | `dependency cycle: a -> b -> a` |
| `permission` is a `Permission` member, never a bare string | `<id>: permission must be a Permission member, got bare '<value>'` |
| A mutation (finance: `CRMUpdate`, `DriveArchive`; fundraising: `DataRoomShare`, `InvestorStageUpdate`) holds the domain write permission | `<id>: mutation step requires finance_write permission, ...` |
| A mutation has a read step (finance: `DriveRead`, `CRMLookup`; fundraising: `InvestorLookup`, `InvestorPipelineRead`, `DataRoomRead`) among its ancestors | `<id>: mutation step must depend on a read step` |

When the spec has a cycle, the validator reports it and stops. Read
findings from inside a cycle would only add noise to the real defect.

## Egress is classified, not gated

`LinearTask` and `Notify` leave the governed boundary: they put text in a
ticket, a mailbox, or a chat channel. `egress_steps(spec)` returns them so a
harness can submit each one to ABAC as an egress-class request, and so a
reviewer can see a workflow's egress surface. The validator does **not**
require them to be gated. That decision belongs to the policy decision point.
A per-spec flag would be unenforceable, and it would silently drift from the
policy that actually runs (decision 2026-09-19, reconfirmed 2026-09-28 for
HAI-205).

## Typed permissions

`FinanceWorkflowStep.permission` is a `Permission`. Because `Permission` is a
`str` enum, the bare string `"finance_write"` compares equal to
`Permission.FINANCE_WRITE`. The validator therefore checks the type: an
untyped value has no typo protection and no enforcement path in the policy
engine.
