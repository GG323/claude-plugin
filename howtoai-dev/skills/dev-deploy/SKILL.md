---
name: dev-deploy
description: Deploys, releases, or rolls back an app to a named target - a local Docker or Kubernetes cluster, a server, or a cloud - with the tools the project and this computer already have. The first time a target is named it sets it up after approval (finds the existing deploy files and CLIs, makes or finds the workbook for each technology through dev-workbook, records the steps, rollback, and health checks), then for every run checks a gate, shows the plan with its rollback first, runs each production step only after the user's yes, watches the run, checks the result, rolls back on approval, keeps a deploy log, and proposes fixes to its own rules when a step fails or the user corrects it. Works on its own in any workspace, and as the last stage of the howtoai-dev process. Use when asked to deploy, release, ship, publish, or roll back something, to deploy to a named place ("deploy this to my local Kubernetes"), to set up a deploy target, or when a deploy failed.
compatibility: Needs Python 3 (standard library only), git, the target's own CLIs (for example docker and kubectl), and the dev-workbook skill for technology facts. dev-core (state and the self-edit method) and skill-builder are used when present. No subagents.
---

# Dev deploy

## Goal

The app running on the target the user names, deployed with that target's own tools, checked healthy, and logged; or, when it fails, rolled back after the user's yes and logged as failed. No target is built in: the first deploy to a target sets it up once, so later deploys reuse it. In any workspace on its own, and as the last stage of `howtoai-dev`, where it also moves the change to `done`.

- The deploy log: `<change folder>/deploy-log.md` inside the dev process, else `<workspace>/AGENTS/howtoai/deploy/log.md`, written only by `DEPLOY log` and `DEPLOY self-edit` from [assets/deploy-log.md](assets/deploy-log.md) in its own fixed shape: one row per run, newest first, and a Self-edits table.
- For a new target, its entry in `<workspace>/AGENTS/howtoai/deploy/targets.json` (shape: [assets/target-example.json](assets/target-example.json)) and any deploy files the user approved.
- Chat: before the run, the plan (target, steps with rollback, checks, what needs a yes); after it, one message: "Deploy to <target>: <outcome>", the steps run, the check results, any rollback, the log path, and, inside the dev process, the stage.

## Before you start

1. **Commands**, by path from this skill's folder (`python3 -I -B` instead of `py -3 -I -B` outside Windows):
   - `DEPLOY` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/scripts/deploy.py"`
   - `WORKBOOK` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/../dev-workbook/scripts/workbook.py"` (workbooks are read through its `resolve`, never by path)
   - `DEVCORE` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/../dev-core/scripts/devcore.py"`, only inside the dev process.

   Each prints one JSON object. Read its `ok` field, not the exit code: for `gate` and `check`, `"ok": false` with exit code 0 means the gate or check failed; an `"error"` field means the command itself failed, which you report before stopping that step. Without Python 3, stop and say the deploy steps need it.
2. **The workspace:** the nearest folder at or above the working directory that holds `AGENTS.md` or `CLAUDE.md`, else the working directory. The targets file is `<workspace>/AGENTS/howtoai/deploy/targets.json`.
3. **The dev process:** when the user names a change, or a change folder under the workspace's plan folder is at stage `deploy`, the deploy belongs to it: pass `--change "<change folder>"` to `DEPLOY gate` and `DEPLOY log`. Otherwise it is a deploy on its own, and every dev-process step is skipped.
4. **The target:** match the request ("to my local Kubernetes", "to staging") against `DEPLOY target list --workspace "<workspace>"`, by name, then technologies and notes. One match: use it and say so. Several: ask which. None: it is new, so give it a short name (lowercase, hyphens, for example `local-k8s`) and set it up. No target named and exactly one in the file: use it and say so.

## Routes

| State or request | Route |
| --- | --- |
| `DEPLOY target show --workspace "<workspace>" --name <target>` returns no target, or the user asks to set up a target | [Set up a target](routes/setup-target.md), then [Deploy](routes/deploy.md) |
| The target exists | [Deploy](routes/deploy.md) |
| The user asks to roll back the last deploy | [Deploy](routes/deploy.md#roll-back), straight to its rollback section |
| The user says a step or a rule is wrong ("never deploy on Fridays"), or a step failed because of a rule | [Self-edit](routes/self-edit.md), then back to the route that was running |

## Rules

- **One yes per production step.** A production step runs only after the user approves that step in chat. A target marked `"production": false` still shows its plan and asks once for the whole run. Either way, `DEPLOY approve` records each step's exact command with a short expiry before it runs, and `DEPLOY use` checks and claims that approval right before the step, so it runs once and every logged step names its approval. For production steps that record is also the only thing that lets the `dev-safe-target` hook pass the command.
- **Rollback first.** No step runs without its rollback written down. A rollback runs only after the user's yes, unless the user approved "roll back on a failed check" for this run.
- **Read before acting on failure.** Read a failed step or check (its output, logs, and events) before anything is retried; retry at most once, and a second failure stops the run.
- **Existing tools first.** Use the project's own deploy files and the computer's own CLIs. Write a new deploy file or install a tool only when none exists, and only after the user's yes; a missing CLI is proposed as an install, never installed unasked.
- **No credentials.** Never create cloud accounts, sign in, or handle secrets: the user signs in to each tool, and the target entry names accounts and contexts only.
- **No product code changes, no builds.** Inside the dev process `dev-build` and `dev-test` build, test, and fix the code; outside it, the app must already build, and a code fix is proposed to the user.
- **Self-edits are proposals.** A fix to a rule lands at the lowest level that resolves it: a workbook or the target entry first, then a skill file only with evidence that a lower level cannot. It is applied by `dev-workbook`, `DEPLOY target write`, or `skill-builder`, after the user's yes.
- **No outward actions beyond the deploy.** No commits, pushes, posts, or messages, unless a step the user approved is one.

## Verify the output

- `DEPLOY check` (or the target's command checks) passed after the run, or the run is logged as failed with its rollback state.
- Every step in the log names its approval ID, and `AGENTS/howtoai/deploy/approvals.json` shows each one claimed once by `DEPLOY use`; where the `dev-safe-target` hook is active, each production approval is also used once.
- The log row names the steps, outcome, checks, and rollback.

## Common failures

| Symptom | Fix |
| --- | --- |
| `DEPLOY use` refuses an approved step, or the hook denies it: the command differs from the approved one (spacing, quoting, a changed tag), or the approval expired or was used | Check first with `DEPLOY use`, with the hook as a second layer; run the exact approved command, and for a changed command, ask again and `DEPLOY approve` it |
| A Kubernetes rollout never finishes (bad image tag, crash, failing probe) | Read `kubectl describe` and the pod logs before anything else, then offer the rollback |
| The health check fails right after the rollout | Compare the target entry's check (port, URL) with the deploy files; raise retries only with evidence |
| A local cluster answers in one run and not the next (its VM stops when idle, as WSL's does) | The `ready` command fails, so the gate offers the entry's `start` commands; keep them in the target entry |
| An image built locally is not found by the cluster (a different image store) | Check the workbook's statement for that cluster; build into the cluster's store or load the image there |

## Feedback

Changes to this skill go to `skill-builder`, not by file path; technology facts go to `dev-workbook`. Without `skill-builder`, agree the change with the user first and keep it small.
