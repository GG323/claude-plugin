---
name: dev-deploy
description: Deploys, releases, or rolls back an app to a named target - a local Docker or Kubernetes cluster, a server, or a cloud - with the tools the project and this computer already have. The first time a target is named it sets it up after approval (finds the existing deploy files and CLIs, makes or finds the workbook for each technology through dev-workbook, records the steps, rollback, and health checks), then for every run checks a gate, shows the plan with its rollback first, runs each production step only after the user's yes, watches the run, checks the result, rolls back on approval, keeps a deploy log, and proposes fixes to its own rules when a step fails or the user corrects it. Works on its own in any workspace, and as the last stage of the howtoai-dev process. Use when asked to deploy, release, ship, publish, or roll back something, to deploy to a named place ("deploy this to my local Kubernetes"), to set up a deploy target, or when a deploy failed.
compatibility: Needs Python 3 (standard library only), git, the target's own CLIs (for example docker and kubectl), and the dev-workbook skill for technology facts. dev-core (state and the self-edit method) and skill-builder are used when present. No subagents.
---

# Dev deploy

## Contents

- [What it does](#what-it-does)
- [Before you start](#before-you-start)
- [Routes](#routes)
- [Core rules](#core-rules)
- [Output contract](#output-contract)
- [Verify the output](#verify-the-output)
- [Common failures](#common-failures)
- [What it can't do](#what-it-cant-do)
- [Feedback](#feedback)
- [Skills and agents](#skills-and-agents)

## What it does

`dev-deploy` takes an app to a target the user names, through that target's own tools. No target is built in: the first deploy to a target sets it up, records it in the workspace's targets file, and keeps its technology knowledge in workbooks, so later deploys reuse it. Every run checks a gate, shows its plan with a rollback for each step, runs production steps only after the user's yes for each, watches the run, checks the result, and writes a deploy log row. When a step fails or the user corrects a rule, it proposes the smallest fix to its own rules. It works in any workspace; inside the `howtoai-dev` process it is the last stage and also checks the change's acceptance.

## Before you start

1. **Commands.** Call these by their paths relative to this skill's folder (`python3 -I -B` instead of `py -3 -I -B` outside Windows):
   - `DEPLOY` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/scripts/deploy.py"`
   - `WORKBOOK` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/../dev-workbook/scripts/workbook.py"` (workbooks are read through its `resolve`, never by path)
   - `DEVCORE` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/../dev-core/scripts/devcore.py"`, only inside the dev process.

   Each prints one JSON object. Read its `ok` field, not the exit code: for `gate` and `check`, `"ok": false` with exit code 0 means the gate or check failed; an `"error"` field means the command itself failed, which you report before stopping that step. Without Python 3, stop and say the deploy steps need it.
2. **The workspace.** The nearest folder at or above the working directory that holds `AGENTS.md` or `CLAUDE.md`, else the working directory. The targets file is `<workspace>/.howtoai/deploy/targets.json`.
3. **The dev process.** When the user names a change, or a change folder under the workspace's plan folder is at stage `deploy`, this deploy belongs to it: pass `--change "<change folder>"` to `DEPLOY gate` and `DEPLOY log`. Otherwise it is a deploy on its own, and every dev-process step below is skipped.
4. **The target.** Take it from the request ("to my local Kubernetes", "to staging") and match it against `DEPLOY target list --workspace "<workspace>"`: the name, then the technologies and notes ("local Kubernetes" matches a non-production target with `kubernetes`). One match: use it and say so. Several: ask which. None: the target is new, so give it a short name (lowercase, hyphens, for example `local-k8s`) and set it up. When the request names no target and the file holds exactly one, use it and say so.

## Routes

| State or request | Route |
| --- | --- |
| `DEPLOY target show --workspace "<workspace>" --name <target>` returns no target, or the user asks to set up a target | [Set up a target](routes/setup-target.md), then [Deploy](routes/deploy.md) |
| The target exists | [Deploy](routes/deploy.md) |
| The user asks to roll back the last deploy | [Deploy](routes/deploy.md#roll-back), straight to its rollback section |
| The user says a step or a rule is wrong ("never deploy on Fridays"), or a step failed because of a rule | [Self-edit](routes/self-edit.md), then back to the route that was running |

## Core rules

- **Workbook rules load as `dev-workbook` says.** Before the first `WORKBOOK resolve`, read `${CLAUDE_SKILL_DIR}/../dev-workbook/references/loading.md` and follow it; every resolve prints that rule again.
- **Existing tools first.** Use the project's own deploy files and the computer's own CLIs. A new deploy file (for example a Kubernetes manifest) or tool is written or installed only when none exists, and only after the user's yes.
- **One yes per production step.** A production step runs only after the user approves that step in chat. A target marked `"production": false` still shows its plan and asks once for the whole run. Either way, `DEPLOY approve` records each step's exact command with a short expiry before it runs, so every step in the log names its approval; for production steps that record is the only thing that lets the `dev-safe-target` hook pass the command.
- **Rollback first.** No step runs without its rollback written down; a rollback runs only after the user's yes, except when the user approved "roll back on a failed check" for this run.
- **Read before acting on failure.** A failed step or check is read (its output, logs, and events) before anything is retried; a retry happens at most once, and a second failure stops the run.
- **No product code changes.** Inside the dev process a code fix goes back through `dev-build` and `dev-test`; outside it, it is proposed to the user.
- **Self-edits are proposals.** A fix to a rule lands at the lowest level that resolves it: a workbook or the target entry first, then a skill file only with evidence that a lower level cannot; it is applied by `dev-workbook`, by `DEPLOY target write`, or by `skill-builder`, after the user's yes.
- **No outward actions beyond the deploy.** No commits, pushes, posts, or messages, unless a step the user approved is one.

## Output contract

- **Audience:** the user running the deploy.
- **Deliverables:**
  - The deploy itself, on the named target.
  - The deploy log: `<change folder>/deploy-log.md` inside the dev process, else `<workspace>/.howtoai/deploy/log.md`, written only by `DEPLOY log` and `DEPLOY self-edit` from [assets/deploy-log.md](assets/deploy-log.md) (exempt from the workspace's title and contents rules): one row per run, newest first, and a Self-edits table.
  - For a new target, its entry in `<workspace>/.howtoai/deploy/targets.json` (shape: [assets/target-example.json](assets/target-example.json)) and any deploy files the user approved.
- **Report:** before the run, the plan message (target, steps with rollback, checks, what needs a yes); after it, one message: "Deploy to <target>: <outcome>", the steps run, the check results, any rollback, the log path, and, inside the dev process, the stage.

## Verify the output

- `DEPLOY check` (or the target's command checks) passed after the run, or the run is logged as failed with its rollback state.
- Every step in the log names its approval ID; where the `dev-safe-target` hook is active, `.howtoai/deploy/approvals.json` shows each production approval used once.
- The log row exists and names the steps, outcome, checks, and rollback.

## Common failures

| Symptom | Cause | Fix |
| --- | --- | --- |
| The hook denies an approved step | The command run differs from the approved one (spacing, quoting, a changed tag) or the approval expired | Run the exact approved command; for a changed command, ask again and `DEPLOY approve` it |
| A Kubernetes rollout never finishes | The new pods fail to start (bad image tag, crash, failing probe) | Read `kubectl describe` and the pod logs before anything else, then offer the rollback |
| The health check fails right after the rollout | The service port or the check URL in the target entry is wrong, or the app needs longer to start | Compare the target entry's check with the deploy files; raise retries only with evidence |
| A local cluster answers in one run and not the next | It runs in a VM that stops when idle (for example WSL shuts down its VM) | The `ready` command fails, so the gate offers the entry's `start` commands; keep them in the target entry |
| An image built locally is not found by the cluster | The cluster uses a different image store than the docker CLI | Check the workbook's statement for that cluster; build into the cluster's store or load the image there |

## What it can't do

- It does not create cloud accounts, sign in, or handle credentials: the user signs in to each tool; the target entry names accounts and contexts, never secrets.
- It does not build or test the app's code: inside the dev process `dev-build` and `dev-test` do; outside it, the app must already build.
- A target needs a CLI on this computer; where none is installed it proposes the install and waits for the user's yes.

## Feedback

Send requested changes or reported problems to the `skill-builder` skill (`/skill-builder` in Claude Code), not by file path. Technology facts go to `dev-workbook`. If `skill-builder` is unavailable, agree the change with the user first, keep it as small as the problem needs, and check the skill afterwards.

## Skills and agents

- [Set up a target](routes/setup-target.md), [Deploy](routes/deploy.md), and [Self-edit](routes/self-edit.md) - the routes; [scripts/deploy.py](scripts/deploy.py) - discover, target, gate, approve, check, log, and self-edit.
- `dev-workbook` - finds or makes each technology's workbook and returns its statements; takes new technology facts through Propose.
- `dev-core` - the change's state and the self-edit and root-cause method, inside the dev process; `skill-builder` - applies a change to this skill's files.
- The `dev-safe-target` hook in the same plugin reads the approvals file.
- No agents are used.
