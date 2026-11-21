# Route: self-edit

## Contents

- [When it starts](#when-it-starts)
- [Propose the change](#propose-the-change)
- [Apply and record](#apply-and-record)
- [Skills and agents](#skills-and-agents)

## When it starts

Entered from [SKILL.md](../SKILL.md#routes) or [Deploy](deploy.md#approve-and-run) when:

- a step or check failed because of a rule: a wrong command, port, tag, or context in the target entry or a deploy file, or a workbook statement that is missing or wrong;
- the user corrects a rule ("never deploy on Fridays", "always use the staging context first");
- the same step was fixed by hand in two runs (the deploy log shows it).

A failure of the app itself or of the platform is not a self-edit.

## Propose the change

Follow `dev-core`'s self-edit and root-cause method when `dev-core` is present (`${CLAUDE_SKILL_DIR}/../dev-core/references/self-edit.md`); its four steps are, in short:

1. **Quote** the rule that caused it, with its file and line: the target entry's step, the deploy file, the workbook statement, or this skill's instruction; or say where the missing rule belongs.
2. **Classify and place it at the lowest level that resolves it:**
   - A technology fact (how Kubernetes rolls out, where a cluster keeps images) goes to a workbook, through `dev-workbook`'s Propose.
   - A fact about this target (a context, a port, a check, a step order, "never on Fridays" for this target) goes to the target entry.
   - Only a process step of this skill itself (what it asks, when it rolls back) goes to this skill's files, with evidence why the workbook and the target entry cannot hold it.
3. **Show the smallest change** as a diff, with its level, in one message, and ask for the yes. Never apply it yourself.

## Apply and record

1. After the yes: a workbook fact through `dev-workbook`'s Propose; a target entry change through `DEPLOY target write ... --write` after its preview; a skill change through `skill-builder` with the change plan the method describes (target files, cause, smallest change, why not lower, calling skill `dev-deploy`).
2. `DEPLOY self-edit --workspace "<workspace>" --trigger "<negative response / execution error / repeated correction>" --quote "<the quoted rule, file:line>" --change-text "<the change and its level>" --route "<dev-workbook / target entry / skill-builder>" --status "<proposed, approved, applied: where, or declined: reason>"` (with `--change` inside the dev process); write the row when you propose, and again when its status changes.
3. Return to the route that was running; a deploy that stopped for the self-edit starts again from [Check the gate](deploy.md#check-the-gate).

## Skills and agents

- [SKILL.md](../SKILL.md) - the rules; [Deploy](deploy.md) - the route this one returns to; [scripts/deploy.py](../scripts/deploy.py) - target write and self-edit.
- `dev-core` - the self-edit and root-cause method; `dev-workbook` - Propose; `skill-builder` - changes to this skill's files.
- No agents are used.
