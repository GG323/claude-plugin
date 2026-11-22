# Route: deploy

## Contents

- [Check the gate](#check-the-gate)
- [Plan the run](#plan-the-run)
- [Approve and run](#approve-and-run)
- [Check the result](#check-the-result)
- [Roll back](#roll-back)
- [Record and close](#record-and-close)
- [Skills and agents](#skills-and-agents)

## Check the gate

Entered from [SKILL.md](../SKILL.md#routes) or [Set up a target](setup-target.md).

1. `DEPLOY gate --workspace "<workspace>" --target <target>` (with `--change "<change folder>"` inside the dev process, and `--new-file <path>` for each deploy file a first setup just wrote). It checks the target exists, the work is committed, and, inside the dev process, that the change is at stage `deploy` with an accepted human review and a green latest test run.
2. Run each of the target's `ready` commands; each must answer. When one fails and the entry has `start` commands, offer them ("the cluster is stopped; start it with ...?"), run them only after the user's yes, and run the `ready` commands again.
3. Any other problem stops the run before the `ready` commands: tell the user what failed and what would clear it (for example "commit the work first"), change nothing, and write no log row. Skip the rest of this route.

## Plan the run

1. `DEPLOY target show --workspace "<workspace>" --name <target>`, and `WORKBOOK resolve --workspace "<workspace>" --stage deploy --technologies <the entry's technologies> --paths <the deploy files> --markdown`. A technology in `missing` does not stop the run: say so in the plan and offer `dev-workbook`'s Create route for it after the deploy.
2. Check that the steps and the deploy files agree before anything runs: the image name and tag a build step makes is the one the manifest or compose file references, the ports and paths the checks use are the ones the deploy files expose, and every command names its context. A mismatch is a rule problem: go to [Self-edit](self-edit.md) before running.
3. Fill in what changes per run (for example `{tag}` from the app's version or the commit) in every step and deploy file that uses it, the same value everywhere, without changing a step's shape; a step whose shape must change is a change to the target entry, shown and approved as in [Set up a target](setup-target.md#ask-and-write).
4. Show the plan in one message, starting with every entry the gate returned in `checks_skipped`, files outside every repository by name (when one of them is a step's script or a deploy file, it needs its own yes): then each step's command and rollback, the watch command, the checks, which steps are production, and the workbook statements that shaped them. Ask for the yes: for a production target, one yes per production step ("approve `apply`"), or for all of them by name; for a non-production target, one yes for the run. Also ask whether a failed check may roll back without asking again.

## Approve and run

For each step, in order:

1. **Approve.** After the user's yes (for that step, or for the whole run on a non-production target): `DEPLOY approve --workspace "<workspace>" --target <target> --step <id> --command "<the exact command>"`. Run the command exactly as approved; any change needs a new yes.
2. **Run.** Run the command, then its `watch` command when it has one.
3. **On failure.** Read before acting: the step's output, then the platform's own diagnostics (for Kubernetes: `kubectl describe` of the deployment and its pods, the pod logs, and the events). Classify the cause, first match wins:
   - **Flaky:** a timeout or a lost connection with no error from the app or platform. Offer one rerun.
   - **The app:** the app fails to start or answer (a crash, a failing probe, a missing config). Stop; inside the dev process propose a fix-now finding for `dev-build`, outside it propose the fix.
   - **The deploy files or target entry:** a wrong image tag, port, name, or context. Stop; this is a rule, so go to [Self-edit](self-edit.md) and propose the fix to the entry or file.
   - **The platform:** the cluster or host itself is down or out of resources. Stop and tell the user.
4. After a failure that left the target changed, go to [Roll back](#roll-back).

## Check the result

1. Run each check: `DEPLOY check --url <url> --expect <status> --contains "<text>" --retries <n> --wait <seconds>` for a URL, the command itself for a command check.
2. All passed: go to [Record and close](#record-and-close).
3. A check failed: read the evidence as in step 3 of [Approve and run](#approve-and-run), then roll back if the user allowed it for this run, else offer the rollback and wait.

## Roll back

1. Take the rollback of each step that ran, last step first. Unless the user allowed rollback without asking for this run, ask first; then `DEPLOY approve` it with the step ID `rollback-<id>`.
2. Run it, then the step's `watch` command, then the checks, so the log can say the old version is back and healthy.
3. A rollback that fails stops everything: tell the user the target's state as the platform reports it, and do not retry.

## Record and close

1. `DEPLOY log --workspace "<workspace>" --target <target> --steps "<step IDs run>" --outcome "<succeeded, or failed at <step>: <reason>>" --checks "<passed, or failed: which>" --rollback "<planned / used / not needed>" --approved "<you, approval IDs>"` (with `--change` inside the dev process).
2. Inside the dev process, after a clean run with passing checks: `DEVCORE state "<change folder>" --patch '{"stage": "done", "append": {"approvals": {"what": "deploy to <target>", "by": "user", "conditions": "<approval IDs>"}}}'`.
3. When the run failed because of a rule, run the [Self-edit](self-edit.md) route now: its `DEPLOY self-edit` row with status `proposed` is written before the report, and its proposal goes in the same message.
4. Report as the [output contract](../SKILL.md#output-contract) says.

## Skills and agents

- [SKILL.md](../SKILL.md) - the rules; [Set up a target](setup-target.md) and [Self-edit](self-edit.md) - the routes this one leads to; [scripts/deploy.py](../scripts/deploy.py) - gate, approve, check, and log.
- `dev-workbook` - the statements; `dev-core` - state, inside the dev process; `dev-build` - code fixes inside the dev process.
- No agents are used.
