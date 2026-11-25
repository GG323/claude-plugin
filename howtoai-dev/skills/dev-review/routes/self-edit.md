# Route: self-edit

Done: a proposed fix of the instruction that produced a wrong finding, approved or declined by the user, with the outcome in the finding's Your choice cell.

## When it starts

From [SKILL.md](../SKILL.md#routes), or from [Human review](human-review.md#record-the-choices), when the user says a finding is wrong or corrects a rule this skill or a goldfish applied ("that is not a bug, we round half to even on purpose", "never flag generated files"). A plain decline with no claim about a rule needs no self-edit.

## Propose the change

Follow `dev-core`'s [self-edit method](../../dev-core/references/self-edit.md). Look for the instruction that caused the finding in:

- the reviewer's agent file (`agents/goldfish-<viewpoint>.md`), when its Review steps asked for the finding;
- this skill's files (`SKILL.md`, `routes/`, `references/viewpoints.md`), when the choice of reviewers, the brief, or the filter let it through;
- the workbook statement the finding cites, when the claim is a technology fact.

Change nothing before the user approves the proposed diff. Record the outcome in the finding's Your choice cell as `decline: <reason>; self-edit <proposed | applied | declined>`, then return to the route that was running.
