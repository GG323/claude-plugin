---
name: dev-core
description: Shared foundation of the howtoai-dev skills - project settings and their one-time setup, the plan folder (one change folder per change with state.json, and dev-plans/INDEX.md), and the document templates every dev stage fills (plan, questions record, work item, plan review, code review, learn record, deploy log, lesson line, test map, test run, build record, TESTING.md), and the findings tally script both review loops share. Used by dev-plan, dev-test, dev-build, dev-review, dev-deploy, dev-learn, and dev-workbook; not started by the user directly. Use when a dev skill needs the workspace's dev settings, runs the dev setup, starts a change, records a stage, approval, workbook receipt, or work item, tallies review findings, or rebuilds the plan index.
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
  - [Tally findings](#tally-findings)
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

1. **Python.** The script runs as `py -3 -I -B "${CLAUDE_SKILL_DIR}/scripts/devcore.py" <command>` (`python3 -I -B` outside Windows). From another dev skill, the path is `${CLAUDE_SKILL_DIR}/../dev-core/scripts/devcore.py`. Without Python 3, stop and say that the dev skills need it. Call the chosen command `DEVCORE` below.
2. **Workspace.** Run `DEVCORE root --cwd "<the session's working directory>"`. It returns the nearest folder holding `AGENTS.md` or `CLAUDE.md`. If none is found, ask the user which folder is the workspace and pass it as `--workspace` from then on.
3. Every command except `root` takes `--user-file "<path>"` to read that file instead of the user's own defaults; tests use it so no real settings are read. Every command prints one JSON object. `"ok": false` carries the error; report it and stop the step that needed it. Never edit `state.json`, `INDEX.md`, or the settings file by hand.

## Routes

Take the route the calling skill names.

### Read settings

`DEVCORE settings --workspace "<workspace>"` returns the merged settings (schema defaults, then the user's `~/.claude/howtoai/dev-settings.json`, then the project's `<workspace>/.howtoai/dev/settings.json`), the source of each top-level key, and `configured`. When `configured` is false and the caller is `dev-plan`, run [Setup](#setup) first. The keys and their meaning are in [assets/settings.schema.json](assets/settings.schema.json).

### Setup

Runs once per workspace, the first time `dev-plan` starts there, or when the user asks to change the dev settings.

1. Look up what can be found before asking, reading files only (never a real `.env` or other secret store):
   - **Tracker:** a sign of Jira is an issue key such as `ABC-123` in branch names, commit messages, or the README; a sign of GitHub Issues is `.github/ISSUE_TEMPLATE/` or issue links in the README. A `.github/` folder with only workflows is no sign.
   - **Technologies:** manifests such as `*.csproj`, `package.json`, `pyproject.toml`, `Dockerfile`, `*.tf`.
   - **Deploy entry points:** CI files (`.github/workflows/`, `azure-pipelines.yml`) and `Makefile` targets. A command the CI calls but the workspace does not contain (for example, a missing script) is recorded as found, with a note that it is missing.
   - **Environments:** `.env.example`, compose files, and comments in them that name production or test hosts.
   - **Test entry points:** the test steps of the CI files, `Makefile` test targets, and `test` scripts in package files; recorded in `testing.entry_points` as found, for `dev-test` to confirm on its first run.
   - **Gate commands:** the lint, format-check, and build or type-check steps of the CI files, in check mode only; recorded in `build.gate` as found, each with its `source`, for `dev-build` to confirm on its first run.
2. Say what the lookups found as "From `<file>`: …", for the user to correct, and ask only what is still open with the `grilling` skill's method, in one round of at most four questions. These items are:
   - **Crucial** (asked unless a file answers them): the production markers to deny (hosts, connection-string fragments, cloud profiles, account names), the allowed test targets, and the deploy entry points when the CI deploys anything.
   - **Defaults** (stated under **Assumed — tell me if wrong**): the tracker (Markdown, unless step 1 found a sign of Jira or GitHub Issues, then that one is asked), the plan folder `dev-plans`, and the review defaults.
   - Name accounts and profiles only, never credentials. Safest choices when the user will not decide: Markdown work items; deny every production marker the files name; allow only local targets, because any target not on the allow list counts as production anyway; record no deploy entry points. Technologies found in manifests go into `workbooks.technologies` as found.
3. After the answers, show the settings as a preview in its own message: `DEVCORE setup --workspace "<workspace>" --values '<json>'`. It validates every key and refuses values that look like secrets.
4. After the user approves the preview, write it: the same command with `--write`. A later run merges new values into the file. The plan folder itself is created by [Start a change](#start-a-change), not by setup.

### Start a change

`DEVCORE new-change --workspace "<workspace>" --title "<title>" [--slug <slug>]` creates `<plan_folder>/<date>-<slug>/state.json` with the stage `plan`, and rebuilds the index. The date comes from the system clock. It returns the change ID and folder; the caller writes its documents into that folder from the [templates](#templates).

### Record state

`DEVCORE state "<change folder>"` prints the change's state. To change it, add `--patch '<json>'`:

| Patch key | Value | Used by |
| --- | --- | --- |
| `stage` | `plan`, `accept`, `tests-first`, `build`, `test`, `review`, `human-review`, `deploy`, `done`, `dropped` | every stage, when it starts |
| `size` | `Small`, `Medium`, `Large` | `dev-plan` scope triage |
| `title` | new title | `dev-plan` |
| `append.approvals` | `{"what", "by", "conditions"}` | plan acceptance, human review, and the deploy as a whole (`dev-deploy` records each production step's approval, with its exact command and expiry, in `<workspace>/.howtoai/deploy/approvals.json`, which the `dev-safe-target` hook reads) |
| `append.receipts` | `{"stage", "statements": [IDs], "workbooks": {name: version}}` | every step that consulted `dev-workbook` |
| `append.wi` | `{"n", "title", "tracker_key", "depends_on"}` | `dev-plan` split |
| `append.declined` | `{"finding", "reason"}` | human review |
| `append.test_runs` | `{"n", "route": "red-check"\|"run", "wi", "result": "red"\|"green"\|"refused", "passed", "failed", "flaky", "commit", "report"}` | `dev-test`, after every run |
| `append.ephemeral` | `{"run_id", "name", "label", "state": "created"\|"removed"\|"left"}` | `dev-test`, for each throwaway target |
| `append.builds` | `{"n", "wi", "route": "build"\|"fix", "result": "passed"\|"stopped", "hunks", "fix_rounds", "report"}` | `dev-build`, after every build or fix run |
| `increment` | `{"<loop name>": 1}`, for example `{"plan-review": 1}` | every loop with a stop rule |

Stage changes go into `history` with a timestamp; every write rebuilds the index. Entries that look like secrets are refused.

### Rebuild the index

`DEVCORE index --workspace "<workspace>"` rewrites `<plan_folder>/INDEX.md` in full from every `state.json`, newest first. The other commands already do this; run it alone after the user moves or deletes change folders.

### Tally findings

`findings.py` (call it `FINDINGS`: `py -3 -I -B "${CLAUDE_SKILL_DIR}/scripts/findings.py"`, or `${CLAUDE_SKILL_DIR}/../dev-core/scripts/findings.py` from another dev skill) counts review findings so no review loop relies on the model's tally. The calling skill saves each reviewer's reply as `<raw dir>/<viewpoint>.md`, the scorer's as `scores.md`, and the verifier's as `verdicts.md`; then:

| Command | Does |
| --- | --- |
| `FINDINGS collect "<raw dir>" [--kind plan\|code]` | Merges the reviewer tables into `findings.json`, `findings.md` (for the scorer), and `high-impact.md` (Blocker or Critical, and Major, for the verifier); refuses unknown severities and duplicate IDs; merges two findings with the same location and quote into one, which tally lists as a duplicate; skips the orchestrator's notes (`declined.md`, `inspection.md`, `workbook-statements.md`) |
| `FINDINGS tally "<raw dir>" --round <n> --out "<file>" [--kind plan\|code] [--threshold 80] [--title] [--change-id] [--size] [--diff] [--changed <changed.json>] [--inspection <file>]` | Applies scores and verdicts and writes the round's review from the [plan-review](assets/templates/plan-review.md) or [review](assets/templates/review.md) shape; for code, `--changed` sends findings on unchanged lines to the appendix (spec and process findings excepted) and `--inspection` fills Test inspection; `clean` is true when no Blocker, Critical, or Major is kept. Will not overwrite filled-in resolutions without `--force` |
| `FINDINGS check "<review file>"` | Lists kept findings still without a resolution (plan: `fixed:`, `decided:`, `asked:`, `declined:`; code: `fix now`, `later`, `decline`) |
| `FINDINGS stop "<change folder>" [--prefix plan-review] [--clean-rounds 2] [--max-rounds 5]` | Reads every round's Result line: `stop` is `clean`, `cap`, or `continue`, and `last_clean` says whether the last round was clean |

## Plan folder contract

- One folder at the workspace root, `dev-plans/` by default (`plan_folder` in the settings), with one subfolder per change, named `<YYYY-MM-DD>-<slug>`.
- A change folder holds `state.json` (written only by the script), and the documents the stages write from the templates: `questions.md`, `plan.md`, `plan-review-<round>.md`, `plan.html`, `wi/<n>.md`, `test-map.md` (or `test-map-<n>.md` per work item), `test-run-<n>.md`, `build-<n>.md`, `review-<round>.md`, `learn-<round>.md`, `deploy-log.md`. Reviewers' raw replies for each round go in `raw/<loop>-<round>/`, and `dev-build`'s snapshot and gate records in `raw/build-<n>/`.
- The dev skills never archive, move, or delete a change folder. Cleaning up old changes is the user's job; after they do, rebuild the index.
- Lessons go to `<workspace>/.howtoai/dev/lessons.md`, one line each in the [lesson](assets/templates/lesson.md) format; `dev-learn` owns that file and removes each lesson once its fix is applied or declined.

## Templates

Copy a template, fill every `{placeholder}`, and keep every section. A section with nothing to say gets the stated placeholder ("none", "none found"), never removal, so every run has the same shape.

| Template | Filled by | Saved as |
| --- | --- | --- |
| [plan.md](assets/templates/plan.md) | `dev-plan` | `<change>/plan.md` |
| [questions.md](assets/templates/questions.md) | `dev-plan` | `<change>/questions.md` |
| [wi.md](assets/templates/wi.md) | `dev-plan` split | `<change>/wi/<n>.md` |
| [plan-review.md](assets/templates/plan-review.md) | `findings.py tally` for `dev-plan` | `<change>/plan-review-<round>.md` |
| [review.md](assets/templates/review.md) | `findings.py tally` for `dev-review` | `<change>/review-<round>.md` |
| [learn.md](assets/templates/learn.md) | `dev-learn` | `<change>/learn-<round>.md` |
| [lesson.md](assets/templates/lesson.md) | `dev-learn` | a line in `<workspace>/.howtoai/dev/lessons.md` |
| [test-map.md](assets/templates/test-map.md) | `dev-test` Write route | `<change>/test-map.md`, or `test-map-<n>.md` per work item |
| [test-run.md](assets/templates/test-run.md) | `dev-test` | `<change>/test-run-<n>.md` |
| [build.md](assets/templates/build.md) | `dev-build` | `<change>/build-<n>.md` |
| [TESTING.md](assets/templates/TESTING.md) | `dev-test` | `TESTING.md` in each directory that holds tests |

`dev-deploy` keeps its own deploy-log template, because it also runs outside the dev process.

The templates are Markdown because agents read them and git diffs them. They follow their own fixed shape, not the workspace's title and contents-list rules, except `TESTING.md`, which lives in the user's code and follows those rules.

## Output contract

- **Deliverables:** the settings file, change folders with `state.json`, and `INDEX.md`, all written by `devcore.py`; review rounds, written by `findings.py`; the templates, copied by the calling skill.
- **Report:** the script's JSON is returned to the calling skill, never shown to the user raw. The calling skill tells the user in one line what changed, for example "Started change `2026-11-18-login-rate-limit`".
- **Writes:** only `<workspace>/<plan_folder>/` and `<workspace>/.howtoai/dev/`. Settings are written only after the user approves the preview.

## Verify the output

- Each command returned `"ok": true`; on `false`, the error is reported and the step stopped.
- After setup, `DEVCORE settings` shows `"configured": true` and the approved values.
- After a state change, the change's row in `INDEX.md` shows the new stage.
- After any change to a script, run its tests: `py -3 -I -B "${CLAUDE_SKILL_DIR}/evals/test_devcore.py"` and `py -3 -I -B "${CLAUDE_SKILL_DIR}/evals/test_findings.py"`. They work in temporary folders and touch no real settings.

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
- [references/self-edit.md](references/self-edit.md) - the shared self-edit and root-cause method: `dev-review` and `dev-deploy` follow it to correct their own instructions, and `dev-learn` for each collected finding; it sets the fix levels (workbook or reference file, then goldfish, then skill file).
- `skill-builder` - changes this skill.
- No agents are used.
