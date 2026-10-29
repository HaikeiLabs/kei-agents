# Connector tool definitions

The canonical tool-definition format is owned by
`kei-connector-contracts/schemas/*.tool-definition.v1.json`. This repository
does not define or copy those schemas and does not contain provider clients,
credential resolution, or connector bindings.

Kei infers available tool names at call time through Agentware and the
tenant-side `kei-proxy`. Provider execution and customer data retrieval stay
inside that tenant-side proxy. ABAC receives policy metadata only; it never
receives customer payloads, results, or credentials.

GitHub and Linear writes are agent action tools rather than connector
capabilities. See [the Google Drive write flow](drive-write.md) for the
harness-side Drive action.
