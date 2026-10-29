# Deprecation of kei-agents

**Status:** deprecated as of 2026-10-29, by decision of the project owners.
This repository was an example repository for building agents on Haikei Labs
tooling and is no longer being developed or recommended for new work.

## What is frozen

- No new features will be added.
- Security fixes are made only if feasible.
- Existing tests and CI keep running, but no further development is planned.

Nothing is removed or yanked by this deprecation. Existing pins and
already-published versions keep working; this is not a breaking change.

## What existing consumers should do

Nothing right now. Existing pins keep working as they are — do not bump pins
blindly as part of this deprecation. There is no migration to perform today.

## What to use instead

For building agents and tool calls on Haikei Labs tooling, the recommended
path is the Agentware SDK. No replacement for the example agents in this
repository has been decided yet.

No decision has been made about archiving or removing this repository, and no
date is announced for either.

## Questions

Open an issue on this repository. Security reports follow
[SECURITY.md](../SECURITY.md) (a private security advisory, or
team@kei.ai).
