---
name: dev-test
description: Writes the tests for an approved howtoai-dev plan before any code (unit, integration, and end-to-end tests from the Verification section and work items, plus characterization tests for untested code next to the change) and proves they fail first; later runs the suite safely - classifies every database, queue, API, and server the tests could reach, refuses production, uses a throwaway container when no allowed target fits, reruns failures to find flaky tests, and regenerates each test folder's TESTING.md. Stages 3 and 5 of the howtoai-dev process. Use when asked to write tests first for a dev plan, run or rerun the tests for a change, check which environments tests would hit, or refresh TESTING.md.
compatibility: Needs Python 3 (standard library only) and the dev-core and dev-workbook skills from the same plugin; Docker only for throwaway targets. The test-first and safe-target hooks run in Claude Code when the howtoai-dev plugin is installed; elsewhere the same rules apply as instructions only.
---

# Dev test

## Goal

Stages 3 and 5 of `howtoai-dev`. **Write** (after `dev-plan`'s approval): every Verification criterion, acceptance criterion, and "must not change" entry becomes a test, written before any code and proven to fail for the expected reason, mapped in `<change folder>/test-map.md` (or `test-map-<n>.md` per work item). **Run** (after `dev-build`): the suite runs through the project's own entry points, only after every target it could reach is classified by evidence and none is production. Every run, the red check included, leaves `<change folder>/test-run-<n>.md` and a regenerated Latest run section in each affected `TESTING.md`. `dev-build` follows a red check, `dev-review` a green run.

## Before you start

1. **Commands**, by path from this skill's folder (`python3 -I -B` instead of `py -3 -I -B` outside Windows):
   - `DEVCORE` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/../dev-core/scripts/devcore.py"`
   - `WORKBOOK` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/../dev-workbook/scripts/workbook.py"`
   - `TARGETS` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/scripts/targets.py"`
   - `RESULTS` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/scripts/results.py"`
   - `TESTINGMD` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/scripts/testing_md.py"`
   - `EPHEMERAL` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/scripts/ephemeral.py"`

   `"ok": false` carries the error, which you report before stopping that step. Without Python 3, stop and say the dev skills need it.
2. **The change:** the folder the user names, else the newest `<workspace>/<plan_folder>/INDEX.md` row at `tests-first`, `build`, or `test`. Read it with `DEVCORE state "<change folder>"`; never edit `state.json` by hand.
3. **Settings:** `DEVCORE settings --workspace "<workspace>"`. When `configured` is false, stop: the dev settings come from `dev-plan`'s Setup, because the allow and deny lists must exist before any test runs.
4. **Hooks.** Check every edit, command, and MCP call yourself first, as [Without hooks](references/safety-rules.md#without-hooks) lists; with the plugin installed, `dev-test-first` and `dev-safe-target` are a second layer. A denial or question from them is a rule working, not an error: follow its reason and never work around it (no other tool, no renamed file, no split command).

## Routes

"Stage" means the `howtoai-dev` stage in `state.json`.

| State or request | Route |
| --- | --- |
| Stage `tests-first`, or the user asks to write the tests first | [Write](routes/write.md) |
| Stage `test`, a rerun asked by `dev-review` or the user, or "which environments would the tests hit" | [Run](routes/run.md) |
| Stage `build` and the user asks to run the tests | [Run](routes/run.md) as a progress run; the stage stays `build` |
| Stage `plan` or `accept` | Stop: the plan is not approved yet; hand back to `dev-plan` |
| "Refresh TESTING.md" with no test run | [Run](routes/run.md) from [Start the run](routes/run.md#start-the-run), so the targets are classified and refused as in every run: the Latest run section only ever describes a real run |

Write calls Run for its red check; Run never calls Write.

## Core rules

Each rule's layers are in [references/safety-rules.md](references/safety-rules.md).

- **Unknown is production.** Use only targets the allow list matches by evidence (host, database, profile, environment variable), in-memory or file databases, and containers this run created. An unknown target stops the run and asks; a production target or marker refuses it.
- **Production markers.** Before any command or MCP call, check it against the settings' `environments.deny` markers; on a match, stop and ask.
- **Destructive commands** (drops, truncates, bulk deletes, down-migrations, resets) only on a throwaway container this run created; otherwise ask first.
- **Never read real secrets.** Read config files and `.env.test`, never `.env`, `.env.production`, a secret store, or a key vault. Never print, log, or write a secret, including into `TESTING.md` and the reports.
- **The project's own entry points.** Run the commands CI runs (`testing.entry_points`), never ad-hoc ones, and never edit CI configuration, test settings, or thresholds to make tests pass. Report a missing or broken CI entry point instead of fixing it.
- **No gate weakening.** Never skip, delete, loosen, or mark as expected-to-fail a test or assertion unless the plan approved it; report it instead.
- **Tests before code.** In the Write route only test files, test data, and the change folder change; product code is `dev-build`'s, after the red check.
- **Synthetic data, no real side effects.** Seed generated data; email, SMS, payments, and webhooks go to catchers or a provider's test mode.
- **Numbers from scripts.** Targets, result counts, flaky tests, and staleness come from `TARGETS`, `RESULTS`, and `TESTINGMD`, never from your own reading of the output.
- **Local only.** Throwaway targets are local Docker containers, created after approval and always removed; none without Docker, and no remote test servers or cloud resources. Nothing else is written outside the repository and the change folder.
- **A new `TESTING.md`**, base part included, only after the user approved it.
- **State** goes through `DEVCORE`: each run as `append.test_runs`, each container as `append.ephemeral`, each workbook use as `append.receipts`, and the stage (`build` after a red check, `review` after a green run, `build` after a red run).
- **Chat:** one line per step, every question as its own message, no raw JSON. The closing report gives the result, failures with their reading, flaky tests, what was created and removed, and the next stage.

The hooks run only in Claude Code with the plugin installed; elsewhere these rules hold as instructions only. Config overrides made in test code are invisible to `TARGETS` and count as not seen. Changes to this skill go to `skill-builder` (not by file path; if it is unavailable, agree the change with the user first), process lessons to `dev-learn`, and technology facts to `dev-workbook`.

## Verify the output

Before the closing report (a refused run checks only the report, state, and tear-down; it keeps its stage and skips `TESTING.md`):

- After Write: `test-map.md` has one row per Verification criterion, acceptance criterion, and "must not change" entry, and no `{placeholder}` left.
- `test-run-<n>.md` figures match the `RESULTS` output, and its Targets table matches the `TARGETS` output.
- `TESTINGMD check --workspace "<workspace>" --dirs <affected test folders>` returns `"passed": true`, or lists only folders whose new `TESTING.md` the user has not approved yet; name those in the closing report as waiting for approval.
- `EPHEMERAL down --run-id <run id>` ran (`docker_missing` counts as nothing to remove), and `DEVCORE state` shows each ephemeral entry as `removed` or `left` with the reason, the run, and the new stage.

## Common failures

| Symptom | Fix |
| --- | --- |
| A base config file with a production connection string refuses every run (the tests override it in code) | Ask the user for a test-scope override (`appsettings.Test.json`, `.env.test`) or an allow-list item; never run anyway |
| A test file you are about to edit does not match `testing.test_globs`, or the hook denies it | Check the path against `testing.test_globs` before the edit, with the hook as a second layer; on no match, ask the user to extend `testing.test_globs`; never rename to dodge it |
| Results show 0 tests | Add the logger option the workbook names (for example `--logger trx`) to the entry point's `results`, with the user's confirmation |
| A container is left after a failed run | `EPHEMERAL down --run-id <id>`, then `EPHEMERAL sweep` |
