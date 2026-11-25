# Route: self-edit

Done: the smallest fix to the rule that caused the problem is proposed to the user, its `DEPLOY self-edit` row is in the log, and after the user's yes it is applied by its owner.

## When it starts

- A step or check failed because of a rule: a wrong command, port, tag, or context in the target entry or a deploy file, or a workbook statement that is missing or wrong.
- The user corrects a rule ("never deploy on Fridays", "always use the staging context first").
- The plan check finds the steps and the deploy files disagree before anything runs (a build tag the manifest does not use).
- The same step was fixed by hand in two runs (the deploy log shows it).

A failure of the app itself or of the platform is not a self-edit.

## Propose the change

Follow `dev-core`'s self-edit and root-cause method when `dev-core` is present (`${CLAUDE_SKILL_DIR}/../dev-core/references/self-edit.md`):

1. **Quote** the rule that caused it, with its file and line (the target entry's step, the deploy file, the workbook statement, or this skill's instruction), or say where the missing rule belongs.
2. **Place it at the lowest level that resolves it:**
   - A technology fact (how Kubernetes rolls out, where a cluster keeps images): a workbook, through `dev-workbook`'s Propose.
   - A fact about this target (a context, a port, a check, a step order, "never on Fridays" for this target): the target entry. A fix to a deploy file the entry runs (a manifest's image tag) is shown as a diff of that file and written only after the yes.
   - A rule a hook can enforce on every command ("never apply to the prod context from this computer"): the project's `hook_rules`, through `dev-core`'s Setup preview, when the workspace has dev settings.
   - Only a process step of this skill (what it asks, when it rolls back): this skill's files, with evidence why the workbook and the target entry cannot hold it.
3. **Show the smallest change** as a diff, with its level, in one message, and ask for the yes. Never apply it yourself: a yes for the deploy's steps does not cover a change to a rule or a deploy file.

## Apply and record

1. Write the row as soon as you propose, before any report, and again when its status changes: `DEPLOY self-edit --workspace "<workspace>" --trigger "<negative response / execution error / plan check / repeated correction>" --quote "<the quoted rule, file:line>" --change-text "<the change and its level>" --route "<dev-workbook / target entry / deploy file / hook rule / skill-builder>" --status "<proposed, approved, applied: where, or declined: reason>"` (with `--change` inside the dev process).
2. After the yes: a workbook fact through `dev-workbook`'s Propose; a target entry change through `DEPLOY target write ... --write` after its preview; a skill change through `skill-builder` with the change plan the method describes (target files, cause, smallest change, why not lower, calling skill `dev-deploy`).
3. Return to the route that was running; a deploy that stopped for the self-edit starts again from [Check the gate](deploy.md#check-the-gate).
