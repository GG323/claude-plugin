---
name: dev-core
description: Shared foundation of the howtoai-dev skills - project settings and their one-time setup, the plan folder (one change folder per change with state.json, and dev-plans/INDEX.md), and the document templates every dev stage fills (plan, questions record, work item, review doc, learn record, deploy log, lesson line, TESTING.md). Used by dev-plan, dev-test, dev-build, dev-review, dev-deploy, dev-learn, and dev-workbook; not started by the user directly. Use when a dev skill needs the workspace's dev settings, runs the dev setup, starts a change, records a stage, approval, workbook receipt, or work item, or rebuilds the plan index.
user-invocable: false
compatibility: Needs Python 3 (standard library only). Written for Claude Code; other harnesses run the script by its path relative to this skill's folder.
---

# Dev core

## Contents

- [What this skill holds](#what-this-skill-holds)
- [Before you start](#before-you-start)
- [Routes](#routes)
  - [Read settings](#read-settings)
  - [Setup](#setup)
  - [Start a change](#start-a-change)
  - [Record state](#record-state)
  - [Rebuild the index](#rebuild-the-index)
- [Plan folder contract](#plan-folder-contract)
- [Templates](#templates)
- [Output contract](#output-contract)
- [Verify the output](#verify-the-output)
- [Common failures](#common-failures)
- [What it can't do](#what-it-cant-do)
- [Feedback](#feedback)
- [Skills and agents](#skills-and-agents)

## What this skill holds

Every `howtoai-dev` skill shares one settings file, one plan folder, and one set of templates, so every run looks the same and state never depends on the model's memory. This skill keeps them; the other dev skills call its script and copy its templates. It holds no process instructions of its own beyond these routes: each stage's process lives in its own skill.

## Before you start

1. **Python.** The script runs as `py -3 -I "${CLAUDE_SKILL_DIR}/scripts/devcore.py" <command>` (`python3 -I` outside Windows). From another dev skill, the path is `${CLAUDE_SKILL_DIR}/../dev-core/scripts/devcore.py`. Without Python 3, stop and say that the dev skills need it. Call the chosen command `DEVCORE` below.
2. **Workspace.** Run `DEVCORE root --cwd "<the session's working directory>"`. It returns the nearest folder holding `AGENTS.md` or `CLAUDE.md`. If none is found, ask the user which folder is the workspace and pass it as `--workspace` from then on.
3. Every command prints one JSON object. `"ok": false` carries the error; report it and stop the step that needed it. Never edit `state.json`, `INDEX.md`, or the settings file by hand.

## Routes

Take the route the calling skill names.

### Read settings

`DEVCORE settings --workspace "<workspace>"` returns the merged settings (schema defaults, then the user's `~/.claude/howtoai/dev-settings.json`, then the project's `<workspace>/.howtoai/dev/settings.json`), the source of each top-level key, and `configured`. When `configured` is false and the caller is `dev-plan`, run [Setup](#setup) first. The keys and their meaning are in [assets/settings.schema.json](assets/settings.schema.json).

### Setup

Runs once per workspace, the first time `dev-plan` starts there, or when the user asks to change the dev settings.

1. Look up what can be found before asking: the tracker from the repository (a `.github/` folder, a Jira key in the README or branch names), the technologies from manifests (`*.csproj`, `package.json`, `pyproject.toml`, `Dockerfile`, `*.tf`), deploy entry points from CI files (`.github/workflows/`, `azure-pipelines.yml`, `Makefile` targets), and environments from `.env.example` and compose files. Read files only; never read a real `.env` or other secret store.
2. Ask the rest with the `grilling` skill's method, in one or two rounds: the tracker (recommended: Markdown), the production markers to deny (hosts, connection-string fragments, cloud profiles), the allowed test targets, and the deploy entry points. Name accounts and profiles only, never credentials.
3. Show the settings as a preview: `DEVCORE setup --workspace "<workspace>" --values '<json>'`. It validates every key and refuses values that look like secrets.
4. After the user approves the preview, write it: the same command with `--write`. A later run merges new values into the file.

### Start a change

`DEVCORE new-change --workspace "<workspace>" --title "<title>" [--slug <slug>]` creates `<plan_folder>/<date>-<slug>/state.json` with the stage `plan`, and rebuilds the index. The date comes from the system clock. It returns the change ID and folder; the caller writes its documents into that folder from the [templates](#templates).

### Record state

`DEVCORE state "<change folder>"` prints the change's state. To change it, add `--patch '<json>'`:

| Patch key | Value | Used by |
| --- | --- | --- |
| `stage` | `plan`, `accept`, `tests-first`, `build`, `test`, `review`, `human-review`, `deploy`, `done`, `dropped` | every stage, when it starts |
| `size` | `Small`, `Medium`, `Large` | `dev-plan` scope triage |
| `title` | new title | `dev-plan` |
| `append.approvals` | `{"what", "by", "conditions"}` | plan acceptance, human review, production deploy steps |
| `append.receipts` | `{"stage", "statements": [IDs], "workbooks": {name: version}}` | every step that consulted `dev-workbook` |
| `append.wi` | `{"n", "title", "tracker_key", "depends_on"}` | `dev-plan` split |
| `append.declined` | `{"finding", "reason"}` | human review |
| `increment` | `{"<loop name>": 1}`, for example `{"plan-review": 1}` | every loop with a stop rule |

Stage changes go into `history` with a timestamp; every write rebuilds the index. Entries that look like secrets are refused.

### Rebuild the index

`DEVCORE index --workspace "<workspace>"` rewrites `<plan_folder>/INDEX.md` in full from every `state.json`, newest first. The other commands already do this; run it alone after the user moves or deletes change folders.

## Plan folder contract

- One folder at the workspace root, `dev-plans/` by default (`plan_folder` in the settings), with one subfolder per change, named `<YYYY-MM-DD>-<slug>`.
- A change folder holds `state.json` (written only by the script), and the documents the stages write from the templates: `questions.md`, `plan.md`, `wi/<n>.md`, `review-<round>.md`, `learn-<round>.md`, `deploy-log.md`.
- The dev skills never archive, move, or delete a change folder. Cleaning up old changes is the user's job; after they do, rebuild the index.
- Lessons go to `<workspace>/.howtoai/dev/lessons.md`, one line each in the [lesson](assets/templates/lesson.md) format; `dev-learn` owns that file.

## Templates

Copy a template, fill every `{placeholder}`, and keep every section. A section with nothing to say gets the stated placeholder ("none", "none found"), never removal, so every run has the same shape.

| Template | Filled by | Saved as |
| --- | --- | --- |
| [plan.md](assets/templates/plan.md) | `dev-plan` | `<change>/plan.md` |
| [questions.md](assets/templates/questions.md) | `dev-plan` | `<change>/questions.md` |
| [wi.md](assets/templates/wi.md) | `dev-plan` split | `<change>/wi/<n>.md` |
| [review.md](assets/templates/review.md) | `dev-review` | `<change>/review-<round>.md` |
| [learn.md](assets/templates/learn.md) | `dev-learn` | `<change>/learn-<round>.md` |
| [deploy-log.md](assets/templates/deploy-log.md) | `dev-deploy` | `<change>/deploy-log.md` |
| [lesson.md](assets/templates/lesson.md) | `dev-learn` | a line in `<workspace>/.howtoai/dev/lessons.md` |
| [TESTING.md](assets/templates/TESTING.md) | `dev-test` | `TESTING.md` in each directory that holds tests |

The templates are Markdown because agents read them and git diffs them. They follow their own fixed shape, not the workspace's title and contents-list rules, except `TESTING.md`, which lives in the user's code and follows those rules.

## Output contract

- **Deliverables:** the settings file, change folders with `state.json`, and `INDEX.md`, all written by the script; the templates, copied by the calling skill.
- **Report:** the script's JSON is returned to the calling skill, never shown to the user raw. The calling skill tells the user in one line what changed, for example "Started change `2026-11-18-login-rate-limit`".
- **Writes:** only `<workspace>/<plan_folder>/` and `<workspace>/.howtoai/dev/`. Settings are written only after the user approves the preview.

## Verify the output

- Each command returned `"ok": true`; on `false`, the error is reported and the step stopped.
- After setup, `DEVCORE settings` shows `"configured": true` and the approved values.
- After a state change, the change's row in `INDEX.md` shows the new stage.

## Common failures

| Symptom | Cause | Fix |
| --- | --- | --- |
| "no AGENTS.md or CLAUDE.md at or above" | The session started outside a workspace | Ask for the workspace folder and pass `--workspace` |
| "unknown key" from setup | A value outside the schema | Use the keys in [assets/settings.schema.json](assets/settings.schema.json) |
| "looks like it holds a secret" | A token, key, or password in a URL | Name the account or profile instead; credentials stay in the user's secret store |
| A change missing from `INDEX.md` | Its `state.json` was removed or moved by hand | Run [Rebuild the index](#rebuild-the-index) |

## What it can't do

- It does not plan, test, build, review, or deploy: each stage skill holds its own process.
- It does not hold technology rules: `dev-workbook` keeps them.
- It does not clean up old change folders.

## Feedback

Send requested changes or reported problems to the `skill-builder` skill (`/skill-builder` in Claude Code), not by file path. If `skill-builder` is unavailable, agree the change with the user first, keep it as small as the problem needs, and check the skill afterwards.

## Skills and agents

- `dev-plan`, `dev-test`, `dev-build`, `dev-review`, `dev-deploy`, `dev-learn`, `dev-workbook` - the dev skills that call this one.
- `grilling` - the question method used in [Setup](#setup).
- `skill-builder` - changes this skill.
- No agents are used.
