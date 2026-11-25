# Scope rubric

## Risk factors

The riskiest factor sets the size, not the count of files.

| Factor | Small | Medium | Large |
| --- | --- | --- | --- |
| Components touched | one, in line with its existing code | one subsystem, with new parts inside it | a new system or subsystem, or several subsystems |
| Data | none, or reversible (a new nullable column, a new table) | a migration that can be rolled back | a change to existing data that cannot be undone (drop, rename, rewrite, backfill without a copy) |
| Contracts | none | a new endpoint, message, or setting others may start to use | a change to an existing public API, message, file format, or schema others read |
| Outside effects | none | new calls to a service already in use | new sends, payments, or external services; anything a user outside the team sees at once |
| Repositories | one | one | more than one |
| Reversibility | a revert undoes it | a revert plus a known step (a down migration, a flag) | a revert alone does not undo it |
| Untested neighbours | covered, or untested with at most three callers (`dev-test` pins them with characterization tests first) | more than three callers, some untested | no tests on the touched path, and many callers |
| Precedent | the codebase does the same elsewhere | a new pattern a workbook covers | a technology with no workbook and no precedent |

Cite the facts that set a factor next to the size reason, for example "Large: renames `users.email` (`db/migrations/012.sql:4`), read by the billing service (inferred: shared schema in `docs/architecture.md`)".

## Sizes

- **Small:** a bug fix or a change in line with the codebase, reversible.
- **Medium:** a new feature in one subsystem that fits one build session.
- **Large:** a new system or subsystem, an irreversible data or contract change, or a change across repositories.

What each size means for the plan, the review, and the split is in the `draft`, `review`, and `split` stages.

- Anything irreversible is at least Medium; an irreversible data or contract change is Large.
- Size the change as requested, before the plan's mitigations: an expand-then-contract order makes a rename safe to ship, but the change is still sized by the rename.
- When two sizes fit, pick the larger and say why.

## One session

A unit of work fits one agent build session when all of these hold:

- about 15 files or fewer, in one repository and at most two components;
- its tests can be written and run in the same session, against local or test targets;
- at most three acceptance criteria groups (for example, one endpoint's success, error, and authorization cases);
- no decision that another unbuilt item makes.

A Medium change that breaks any of these is split; a work item that breaks one is split further or merged with the item it depends on.
