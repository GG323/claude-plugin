# Scope rubric

## Contents

- [Risk factors](#risk-factors)
- [Sizes](#sizes)
- [One session](#one-session)
- [Skills and agents](#skills-and-agents)

## Risk factors

Rate each factor from the scope facts. The riskiest factor sets the size, not the count of files.

| Factor | Small | Medium | Large |
| --- | --- | --- | --- |
| Components touched | One, in line with its existing code | One subsystem, with new parts inside it | A new system or subsystem, or several subsystems |
| Data | None, or reversible (a new nullable column, a new table) | A migration that can be rolled back | A change to existing data that cannot be undone (drop, rename, rewrite, backfill without a copy) |
| Contracts | None | A new endpoint, message, or setting others may start to use | A change to an existing public API, message, file format, or schema others read |
| Outside effects | None | New calls to a service already in use | New sends, payments, or external services; anything a user outside the team sees at once |
| Repositories | One | One | More than one |
| Reversibility | A revert undoes it | A revert plus a known step (a down migration, a flag) | A revert alone does not undo it |
| Untested neighbours | Covered by tests | Some callers untested | The touched path has no tests and many callers |
| Precedent | The codebase does the same thing elsewhere | A new pattern for this codebase that a workbook covers | A technology with no workbook and no precedent |

Each fact in the Scope and size table that sets a factor is cited next to the size reason, for example "Large: renames `users.email` (`db/migrations/012.sql:4`), read by the billing service (inferred: shared schema in `docs/architecture.md`)".

## Sizes

| Size | Typical change | Plan depth | Review | Split |
| --- | --- | --- | --- | --- |
| Small | A bug fix or a change in line with the codebase, reversible | Short plan; full Verification | One round: comprehension and critic | No |
| Medium | A new feature in one subsystem that fits one build session | Full plan | Loop with the viewpoints the change needs | Only if it does not fit [one session](#one-session) |
| Large | A new system or subsystem, an irreversible data or contract change, or a change across repositories | Full plan, top-down by layer, three architect proposals first | All four viewpoints, loop until the stop rule | Required |

- Anything irreversible is at least Medium; an irreversible data or contract change is Large.
- Rate the change as requested, before the plan's mitigations: an expand-then-contract order makes a rename safe to ship, but the change is still sized by the rename.
- When two sizes fit, pick the larger and say why.

## One session

A unit of work fits one agent build session when all of these hold:

- It changes or adds about 15 files or fewer, in one repository and at most two components.
- Its tests can be written and run in the same session, against local or test targets.
- It has at most three acceptance criteria groups (for example, one endpoint's success, error, and authorization cases).
- It needs no decision that another unbuilt item makes.

A Medium change that breaks any of these is split; a work item that breaks one is split further or merged with the item it depends on.

## Skills and agents

- `dev-plan` - reads this file in its scope and split stages.
- No agents are used.
