# Route: self-edit

## Contents

- [When it starts](#when-it-starts)
- [Propose the change](#propose-the-change)
- [Skills and agents](#skills-and-agents)

## When it starts

Entered from [SKILL.md](../SKILL.md#routes) or from [Human review](human-review.md#record-the-choices) when the user says a finding is wrong or corrects a rule this skill or one of its goldfish applied, for example "that is not a bug, we round half to even on purpose" or "never flag generated files". A plain decline with no claim about a rule needs no self-edit.

## Propose the change

Follow `dev-core`'s [self-edit method](../../dev-core/references/self-edit.md) for the correction, with these places to look for the instruction that caused it:

- the reviewer's agent file (`agents/goldfish-<viewpoint>.md`), when its Review steps asked for the finding;
- this skill's files (`SKILL.md`, `routes/`, `references/viewpoints.md`), when the choice of reviewers, the brief, or the filter let it through;
- the workbook statement the finding cites, when the claim is a technology fact.

Change nothing before the user approves the proposed diff. Record the outcome, approved and handed on, or declined, under the finding's Your choice cell as `decline: <reason>; self-edit <proposed | applied | declined>`, then return to the route that was running.

## Skills and agents

- `dev-core` - the [self-edit method](../../dev-core/references/self-edit.md).
- `dev-workbook` - technology facts; `skill-builder` - process instructions, through its supplied change plan route.
- No agents are used.
