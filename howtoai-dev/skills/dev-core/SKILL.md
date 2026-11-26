---
name: dev-core
description: Shared foundation of the howtoai-dev skills - project settings and their one-time setup, the plan folder (one change folder per change with state.json, and dev-plans/INDEX.md), and the document templates every dev stage fills (plan, questions record, work item, plan review, code review, learn record, lesson line, test map, test run, build record, TESTING.md), and the findings tally script both review loops share. Used by dev-plan, dev-test, dev-build, dev-review, dev-deploy, dev-learn, and dev-workbook; not started by the user directly. Use when a dev skill needs the workspace's dev settings, runs the dev setup, starts a change, records a stage, approval, workbook receipt, or work item, tallies review findings, or rebuilds the plan index.
user-invocable: false
compatibility: Needs Python 3 (standard library only). Written for Claude Code; other harnesses run the script by its path relative to this skill's folder.
---

# Dev core

## Contents

- [Goal](#goal)
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
- [Verify the output](#verify-the-output)

## Goal

Keep the one settings file, plan folder, and template set every `howtoai-dev` skill shares, so state never depends on the model's memory. The other dev skills call this skill's scripts and copy its templates; each stage's process lives in its own skill, and technology rules in `dev-workbook`. The self-edit and root-cause method that `dev-review`, `dev-deploy`, and `dev-learn` follow is [references/self-edit.md](references/self-edit.md).

## Before you start

- `DEVCORE` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/scripts/devcore.py" <command>` (`python3 -I -B` outside Windows); from another dev skill, `${CLAUDE_SKILL_DIR}/../dev-core/scripts/devcore.py`. Without Python 3, stop and say that the dev skills need it.
- **Workspace:** `DEVCORE root --cwd "<the session's working directory>"` returns the nearest folder holding `AGENTS.md` or `CLAUDE.md`. If none is found, ask the user which folder is the workspace and pass it as `--workspace` from then on.
- Every command except `root` takes `--user-file "<path>"` to read that file instead of the user's own defaults (tests use it). Every command prints one JSON object; `"ok": false` carries the error: report it and stop the step that needed it. The JSON goes to the calling skill, never raw to the user; the caller says in one line what changed ("Started change `2026-11-18-login-rate-limit`").
- Never edit `state.json`, `INDEX.md`, or the settings file by hand.
- Never create, read, or write `skills/dev-core/state/replies.jsonl`: only the `dev-reply-log` hook writes it, on a real user prompt, and only `DEVCORE state` reads it.
- **Documents are written with the file tools only**, never a shell command ([Plan folder contract](#plan-folder-contract)).

## Routes

Take the route the calling skill names.

### Read settings

`DEVCORE settings --workspace "<workspace>"` returns the merged settings (schema defaults, then the user's `~/.claude/howtoai/dev-settings.json`, then the project's `<workspace>/AGENTS/settings.json`), the source of each top-level key, and `configured`. When `configured` is false and the caller is `dev-plan`, run [Setup](#setup) first. The keys are in [assets/settings.schema.json](assets/settings.schema.json); "unknown key" means a value outside it.

Then apply each `hook_rules` entry yourself before each command or edit: when its `match` finds the command or file path, stop and give its `reason` on `block`, and say it on `warn`. The `dev-safe-target` hook applies the same rules as a second layer, where it runs.

### Setup

Runs once per workspace, the first time `dev-plan` starts there, or when the user asks to change the dev settings. The plugin's `INSTALL.md` runs this route as one of its steps; when the plugin was never installed through it, say so in one line and offer it. For a nontechnical user, offer the full setup by name, with no file name.

When the user asks to set up or install `howtoai-dev`, follow the plugin's `INSTALL.md` from its start instead (`${CLAUDE_SKILL_DIR}/../../INSTALL.md`). When `INSTALL.md` sent you here, skip this paragraph.

For a nontechnical user, the nontechnical form wins over any step's wording that gives a command, path, or file name: name the step, what it is for, and who can do it. In messages, only a write preview keeps the exact text; the install record and other files you write keep it as usual.

1. Look up what can be found before asking, reading files only (never a real `.env` or other secret store):
   - **Tracker:** Jira shows as an issue key such as `ABC-123` in branch names, commit messages, or the README; GitHub Issues as `.github/ISSUE_TEMPLATE/` or issue links in the README; Azure DevOps Boards as an `AB#123` mention in commit messages, a git remote on `dev.azure.com` or `visualstudio.com`, or work item links in the README. A `.github/` folder with only workflows, or an `azure-pipelines.yml` alone, is no sign.
   - **Technologies:** manifests such as `*.csproj`, `package.json`, `pyproject.toml`, `Dockerfile`, `*.tf`.
   - **Deploy entry points:** CI files (`.github/workflows/`, `azure-pipelines.yml`) and `Makefile` targets. A command the CI calls but the workspace lacks is recorded as found, with a note that it is missing.
   - **Environments:** `.env.example`, compose files, and comments in them that name production or test hosts; and production application settings such as `appsettings.Production.json`, with a command that prints only host, database, and account names, never a secret value.
   - **Test entry points:** CI test steps, `Makefile` test targets, and `test` scripts in package files, recorded in `testing.entry_points` as found, for `dev-test` to confirm on its first run.
   - **Secret env files:** files named `.env` or `.env.*`, apart from test settings (`.env.test`, `.env.testing`) and templates (`.env.example`, `.env.sample`, `.env.template`), found by listing file names, hidden and ignored files included. Never search their content, and never open them.
   - **Gate commands:** the lint, format-check, and build or type-check steps of the CI files, in check mode only, recorded in `build.gate` as found, each with its `source`, for `dev-build` to confirm on its first run.
2. Say what the lookups found as "From `<file>`: …", for the user to correct (for a nontechnical user, each source named by what it is, with no file name), and ask only what is still open with the `grilling` skill's method, in one round of at most four questions:
   - **Crucial** (asked unless a file answers them): the production markers to deny (hosts, connection-string fragments, cloud profiles, account names; production only: a shared target that is not production, such as a team's dev database, goes on neither list, so `dev-test` asks), the allowed test targets, and the deploy entry points when the CI deploys anything.
   - **Defaults** (stated under **Assumed — tell me if wrong**): the tracker (Markdown, unless step 1 found a sign of Jira, GitHub Issues, or Azure DevOps, then that one is asked with its project), the plan format (`plan.publish` `auto`: an artifact where the harness has one, else an HTML file), the plan folder `dev-plans`, and the review defaults. For a nontechnical user, state each default in plain words, with no setting name.
   - Name accounts and profiles only, never credentials, which stay in the user's secret store. Safest choices when the user will not decide: Markdown work items; deny every production marker the files name; allow only local targets, because any target not on the allow list counts as production anyway; record no deploy entry points. Technologies found in manifests go into `workbooks.technologies` as found.
3. After the answers, show the settings as a preview in its own message: `DEVCORE setup --workspace "<workspace>" --values-file "<file>"` (write the JSON to a temporary file outside the workspace with the Write tool: production markers in a command's text make `dev-safe-target` deny it). It validates every key, refuses values that look like secrets, and refuses `plan.publish` `tracker` without a tracker other than Markdown. `--scope user` writes the user's defaults file instead, for choices the user wants in every workspace.
4. Only after the user approves the preview, run the same command with `--write`. A later run merges new values into the file. The plan folder is created by [Start a change](#start-a-change), not here.
5. **Deny rules for secret env files**, only when step 1 found some that the workspace's `.claude/settings.json` does not deny yet. Propose one rule per file name, for example `Read(**/.env.production)`, as its own question, and show the rules. Say what they cover: Claude's Read and Grep tools, in subagents too, but not a shell command such as `grep -r`, which can still print those files; and they hold only in sessions that load that settings file, which one started in a nested folder may not. In a git repository, say to commit the file by itself before a change starts, so it stays out of that change's diff. Only after the user's yes, have `update-config` merge them into `permissions.deny` of the workspace's `.claude/settings.json`, never user-level settings; without `update-config`, give the user the rules to add. For a nontechnical user, describe each rule by what it does ("stop Claude from opening the live passwords file"), and keep the exact rule text only in the write preview.

### Start a change

`DEVCORE new-change --workspace "<workspace>" --title "<title>" [--slug <slug>]` creates `<plan_folder>/<date>-<slug>/state.json` at stage `plan` (date from the system clock) and rebuilds the index. It returns the change ID and folder; the caller writes its documents there from the [templates](#templates), with the file tools.

### Record state

`DEVCORE state "<change folder>"` prints the change's state; `--patch '<json>'` changes it:

| Patch key | Value | Used by |
| --- | --- | --- |
| `stage` | `plan`, `accept`, `tests-first`, `build`, `test`, `review`, `human-review`, `deploy`, `done`, `dropped` | every stage, when it starts |
| `size` | `Small`, `Medium`, `Large` | `dev-plan` scope triage |
| `title` | new title | `dev-plan` |
| `plan_item` | `{"tracker_key", "kind", "url"}`, replacing any earlier one | `dev-plan`, when `plan.publish` is `tracker` and it created the plan's parent item |
| `append.approvals` | `{"what", "by", "conditions", "reply"}`, see below | plan acceptance, human review, and the deploy as a whole |
| `append.receipts` | `{"stage", "statements": [IDs], "workbooks": {name: version}}` | every step that consulted `dev-workbook` |
| `append.wi` | `{"n", "title", "tracker_key", "depends_on"}` | `dev-plan` split |
| `append.declined` | `{"finding", "reason"}` | human review |
| `append.test_runs` | `{"n", "route": "red-check"\|"run", "wi", "result": "red"\|"red-failed"\|"green"\|"refused", "passed", "failed", "flaky", "commit", "report"}` | `dev-test`, after every run |
| `append.ephemeral` | `{"run_id", "name", "label", "state": "created"\|"removed"\|"left"}` | `dev-test`, for each throwaway target |
| `append.builds` | `{"n", "wi", "route": "build"\|"fix", "result": "passed"\|"stopped", "hunks", "fix_rounds", "report"}` | `dev-build`, after every build or fix run |
| `increment` | `{"<loop name>": 1}`, for example `{"plan-review": 1}` | every loop with a stop rule |

Approvals:

- `"by": "plan"` (a path the approved work item names): the script requires the user's plan approval and adds `"covers"` citing it.
- `"by": "user"`: `"reply"` is required, the user's reply word for word, recorded only after the user answered. The script checks it against `skills/dev-core/state/replies.jsonl` (the `dev-reply-log` hook's hash of each user prompt, never its text) and refuses a reply that matches no prompt since the change's last user approval, so one reply that approves several items is one record whose `"what"` names them all.
- Without that log it records the approval with `"unverified": true` and prints a warning: show every unverified approval to the user in your next message.
- `dev-deploy` records each production step's approval, with its exact command and expiry, in `<workspace>/AGENTS/state/approvals.json`, which the `dev-safe-target` hook reads.

Stage changes go into `history` with a timestamp, and every write rebuilds the index. A move from `tests-first` to `build` is refused when git shows files changed since the `tests-first` stage outside `testing.test_globs`, the plan folder, and `AGENTS/` (tooling, settings, and run state); without git it is recorded with `"unchecked"` and a warning. Entries that look like secrets are refused.

### Rebuild the index

`DEVCORE index --workspace "<workspace>"` rewrites `<plan_folder>/INDEX.md` in full from every `state.json`, newest first. The other commands already do this; run it alone after the user moves or deletes change folders, or when a change is missing from `INDEX.md`.

### Tally findings

`FINDINGS` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/scripts/findings.py"` (from another dev skill, `${CLAUDE_SKILL_DIR}/../dev-core/scripts/findings.py`) counts review findings, so no review loop relies on the model's tally. The calling skill saves each reviewer's reply as `<raw dir>/<viewpoint>.md`, the scorer's as `scores.md`, and the verifier's as `verdicts.md`.

| Command | Does |
| --- | --- |
| `FINDINGS collect "<raw dir>" [--kind plan\|code]` | Merges the reviewer tables into `findings.json`, `findings.md` (for the scorer), and `high-impact.md` (Blocker or Critical, and Major, for the verifier); refuses unknown severities and duplicate IDs; merges two findings with the same location and quote into one, which tally lists as a duplicate; skips `declined.md`, `fix-now.md`, `inspection.md`, `workbook-statements.md` |
| `FINDINGS tally "<raw dir>" --round <n> --out "<file>" [--kind plan\|code] [--threshold 80] [--title] [--change-id] [--size] [--diff] [--changed <changed.json>] [--inspection <file>]` | Applies scores and verdicts (every Score a whole number from 0 to 100, else it stops and names the rows) and writes the round's review from the [plan-review](assets/templates/plan-review.md) or [review](assets/templates/review.md) shape; for code, `--changed` sends findings on unchanged lines to the appendix (spec and process findings excepted) and `--inspection` fills Test inspection; `clean` is true when no Blocker, Critical, or Major is kept. Will not overwrite filled-in resolutions without `--force` |
| `FINDINGS check "<review file>"` | Lists kept findings still without a resolution (plan: `fixed:`, `decided:`, `asked:`, `declined:`; code: `fix now`, `later`, `decline`) |
| `FINDINGS stop "<change folder>" [--prefix plan-review] [--clean-rounds 2] [--max-rounds 5]` | Reads every round's Result line: `stop` is `clean`, `cap`, or `continue`, and `last_clean` says whether the last round was clean |

## Plan folder contract

- **File tools only.** Write and edit every document in a change folder, in `AGENTS/` (`settings.json`, `install.md`, `lessons.md`, `workbooks/`, `state/`), and each `TESTING.md` with the file tools (Write, Edit), never through a shell redirect, heredoc, or here-string: `dev-safe-target` denies a command whose text names a production marker, and these documents often name one. A script that writes its own file is not affected.
- One folder at the workspace root, `dev-plans/` by default (`plan_folder`), with one subfolder per change named `<YYYY-MM-DD>-<slug>`.
- A change folder holds `state.json` (written only by the script) and the documents the stages write: `questions.md`, `plan.md`, `plan-review-<round>.md`, `plan.html`, `wi/<n>.md`, `test-map.md` (or `test-map-<n>.md` per work item), `test-run-<n>.md`, `build-<n>.md`, `review-<round>.md`, `learn-<round>.md`, `deploy-log.md`. Reviewers' raw replies go in `raw/<loop>-<round>/`, and `dev-build`'s snapshot and gate records in `raw/build-<n>/`.
- The dev skills never archive, move, or delete a change folder: cleanup is the user's job; after it, rebuild the index.
- Lessons go to `<workspace>/AGENTS/lessons.md`, one line each in the [lesson](assets/templates/lesson.md) format; `dev-learn` owns that file and removes each lesson once its fix is applied or declined.

## Templates

Copy a template with the file tools, fill every `{placeholder}`, and keep every section. A section with nothing to say gets the stated placeholder ("none", "none found"), never removal, so every run has the same shape. Templates keep their own fixed shape, not the workspace's title and contents rules, except `TESTING.md`, which lives in the user's code and follows them.

| Template | Filled by | Saved as |
| --- | --- | --- |
| [plan.md](assets/templates/plan.md) | `dev-plan` | `<change>/plan.md` |
| [questions.md](assets/templates/questions.md) | `dev-plan` | `<change>/questions.md` |
| [wi.md](assets/templates/wi.md) | `dev-plan` split | `<change>/wi/<n>.md` |
| [plan-review.md](assets/templates/plan-review.md) | `findings.py tally` for `dev-plan` | `<change>/plan-review-<round>.md` |
| [review.md](assets/templates/review.md) | `findings.py tally` for `dev-review` | `<change>/review-<round>.md` |
| [learn.md](assets/templates/learn.md) | `dev-learn` | `<change>/learn-<round>.md` |
| [lesson.md](assets/templates/lesson.md) | `dev-learn` | a line in `<workspace>/AGENTS/lessons.md` |
| [test-map.md](assets/templates/test-map.md) | `dev-test` Write route | `<change>/test-map.md`, or `test-map-<n>.md` per work item |
| [test-run.md](assets/templates/test-run.md) | `dev-test` | `<change>/test-run-<n>.md` |
| [build.md](assets/templates/build.md) | `dev-build` | `<change>/build-<n>.md` |
| [TESTING.md](assets/templates/TESTING.md) | `dev-test` | `TESTING.md` in each directory that holds tests |

`dev-deploy` keeps its own deploy-log template, because it also runs outside the dev process.

## Verify the output

- **Deliverables:** the settings file, change folders with `state.json`, and `INDEX.md`, written by `devcore.py`; review rounds, by `findings.py`; the other documents, from the templates by the calling skill.
- **Writes:** only `<workspace>/<plan_folder>/` and this plugin's `"howtoai-dev"` key in `<workspace>/AGENTS/settings.json` (other tools' keys are kept), plus the deny rules that [Setup](#setup) has `update-config` merge into `<workspace>/.claude/settings.json` after their own yes. Settings are written only after the user approves the preview.
- Each command returned `"ok": true`. After setup, `DEVCORE settings` shows `"configured": true` and the approved values, and the workspace's `.claude/settings.json` holds each approved deny rule. After a state change, the change's `INDEX.md` row shows the new stage.
- After any change to a script, run `py -3 -I -B "${CLAUDE_SKILL_DIR}/evals/test_devcore.py"` and `py -3 -I -B "${CLAUDE_SKILL_DIR}/evals/test_findings.py"`; they work in temporary folders and touch no real settings.
- This skill does not plan, test, build, review, deploy, hold technology rules, or clean up change folders. Send requested changes or problems with it to the `skill-builder` skill (`/skill-builder` in Claude Code), not by file path; if `skill-builder` is unavailable, agree the change with the user first, keep it as small as the problem needs, and check the skill afterwards.
