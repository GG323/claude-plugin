---
name: dev-test
description: Writes the tests for an approved howtoai-dev plan before any code (unit, integration, and end-to-end tests from the Verification section and work items, plus characterization tests for untested code next to the change) and proves they fail first; later runs the suite safely - classifies every database, queue, API, and server the tests could reach, refuses production, uses a throwaway container when no allowed target fits, reruns failures to find flaky tests, and regenerates each test folder's TESTING.md. Stages 3 and 5 of the howtoai-dev process. Use when asked to write tests first for a dev plan, run or rerun the tests for a change, check which environments tests would hit, or refresh TESTING.md.
compatibility: Needs Python 3 (standard library only) and the dev-core and dev-workbook skills from the same plugin; Docker only for throwaway targets. The test-first and safe-target hooks run in Claude Code when the howtoai-dev plugin is installed; elsewhere the same rules apply as instructions only.
---

# Dev test

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

`dev-test` is stages 3 and 5 of the `howtoai-dev` process. After `dev-plan`'s approval, the **Write route** turns every Verification criterion and acceptance criterion into a test, writes them before any code, and proves each one fails for the expected reason. After `dev-build`, the **Run route** runs the suite through the project's own entry points, but only after every target the tests could reach is classified by evidence and none is production. Each run leaves a report in the change folder and a regenerated Latest run section in each affected `TESTING.md`.

## Before you start

1. **Commands.** Call these by their paths relative to this skill's folder (`python3 -I -B` instead of `py -3 -I -B` outside Windows):
   - `DEVCORE` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/../dev-core/scripts/devcore.py"`
   - `WORKBOOK` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/../dev-workbook/scripts/workbook.py"`
   - `TARGETS` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/scripts/targets.py"`
   - `RESULTS` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/scripts/results.py"`
   - `TESTINGMD` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/scripts/testing_md.py"`
   - `EPHEMERAL` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/scripts/ephemeral.py"`

   Each prints one JSON object; `"ok": false` carries the error, which you report before stopping that step. Without Python 3, stop and say the dev skills need it.
2. **The change.** Find the change folder: the one the user names, else the newest row of `<workspace>/<plan_folder>/INDEX.md` at a stage this skill runs (`tests-first`, `build`, `test`). Read it with `DEVCORE state "<change folder>"`. Never edit `state.json` by hand.
3. **Settings.** `DEVCORE settings --workspace "<workspace>"`. When `configured` is false, stop: the dev settings come from `dev-plan`'s Setup, because the allow and deny lists must exist before any test runs.
4. **Hooks.** With the plugin installed, `dev-test-first` runs on every file edit and `dev-safe-target` on every command, MCP call, and edit. A denial or question from them is a rule working, not an error: follow its reason and never work around it (no other tool, no renamed file, no split command).

## Routes

Each route is one file in `routes/`. "Stage" in this skill always means a stage of the `howtoai-dev` process, as `state.json` records it (`tests-first`, `build`, `test`, `review`).

| State or request | Route |
| --- | --- |
| Stage `tests-first` (the plan is approved), or the user asks to write the tests first | [Write](routes/write.md) |
| Stage `test` (the build is done), a rerun asked by `dev-review` or the user, or "which environments would the tests hit" | [Run](routes/run.md) |
| Stage `build` and the user asks to run the tests | [Run](routes/run.md), reported as a progress run; the stage stays `build` |
| Stage `plan` or `accept` | Stop: the plan is not approved yet; hand back to `dev-plan` |
| "Refresh TESTING.md" with no test run | [Run](routes/run.md) from [Start the run](routes/run.md#start-the-run), so the targets are classified and refused as in every run: the Latest run section only ever describes a real run |

The Write route calls the Run route for its red check; the Run route never calls the Write route.

## Core rules

The full list, with the layer that enforces each rule, is in [references/safety-rules.md](references/safety-rules.md).

- **Workbook rules load as `dev-workbook` says.** Before the first `WORKBOOK resolve`, read `${CLAUDE_SKILL_DIR}/../dev-workbook/references/loading.md` and follow it; every resolve prints that rule again.
- **Unknown is production.** Only targets the allow list matches by evidence (host, database, profile, environment variable), in-memory or file databases, and containers this run created are used. An unknown target stops the run and asks; a production target or marker refuses it.
- **Never read real secrets.** Read config files and `.env.test`, never `.env`, `.env.production`, a secret store, or a key vault. Never print, log, or write a secret, including into `TESTING.md` and the reports.
- **The project's own entry points.** Run the commands CI runs (`testing.entry_points`), never ad-hoc ones, and never edit CI configuration, test settings, or thresholds to make tests pass.
- **No gate weakening.** Never skip, delete, loosen, or mark as expected-to-fail a test or assertion unless the plan approved it; report it instead.
- **Tests before code.** In the Write route only test files, test data, and the change folder change.
- **Synthetic data, no real side effects.** Seed generated data; email, SMS, payments, and webhooks go to catchers or a provider's test mode.
- **Numbers from scripts.** Targets, result counts, flaky tests, and staleness come from `TARGETS`, `RESULTS`, and `TESTINGMD`, never from your own reading of the output.

## Output contract

- **Audience:** the developer running the change, and the later dev stages that read the records (`dev-build`, `dev-review`, `dev-learn`); `TESTING.md` is for anyone working in that test folder.
- **Format:** Markdown files from fixed `dev-core` templates, because agents read them and git diffs them; tests in the repository's own language and framework.
- **Deliverables:**
  - Write route: test files in the repository, in its own style; `<change folder>/test-map.md` (or `test-map-<n>.md` per work item) from `dev-core`'s [test-map template](../dev-core/assets/templates/test-map.md).
  - Both routes: `<change folder>/test-run-<n>.md` from the [test-run template](../dev-core/assets/templates/test-run.md), one per run (the red check counts as a run); the Latest run section of each affected `TESTING.md`, rewritten by `TESTINGMD`.
  - A new `TESTING.md`, base part included, only after the user approved it.
- **State:** each run as `append.test_runs`, each throwaway container as `append.ephemeral`, each workbook use as `append.receipts`, and the stage (`build` after a red check, `review` after a green run, `build` after a red run), all through `DEVCORE`.
- **Chat:** one line per step ("Targets: 2 local, 1 in-memory; no production"), every question as its own message, and a short closing report: result, failures with their reading, flaky tests, what was created and removed, and the next stage. No raw JSON.
- **Writes outside the repository and change folder:** none, except Docker containers after approval, always removed.

## Verify the output

Before the closing report (a refused run checks only the report, state, and tear-down; it keeps its stage and skips `TESTING.md`):

- After the Write route: `test-map.md` has one row per Verification criterion, acceptance criterion, and "must not change" entry, and no `{placeholder}` left.
- `test-run-<n>.md` figures match the `RESULTS` output, and its Targets table matches the `TARGETS` output.
- `TESTINGMD check --workspace "<workspace>" --dirs <affected test folders>` returns `"passed": true`, or lists only folders whose new `TESTING.md` the user has not approved yet; name those in the closing report as waiting for approval.
- `EPHEMERAL down --run-id <run id>` ran (`docker_missing` counts as nothing to remove), and `DEVCORE state` shows each ephemeral entry as `removed` or `left` with the reason.
- `DEVCORE state` shows the run and the new stage.

## Common failures

| Symptom | Cause | Fix |
| --- | --- | --- |
| A base config file with a production connection string refuses every run | The tests override it in code, which `TARGETS` cannot see | Ask the user to add a test-scope override (`appsettings.Test.json`, `.env.test`) or an allow-list item; never run anyway |
| A new test passes before the build | The behaviour exists already, or the test asserts too little | Read why; strengthen the test, or ask the user whether the criterion is already met |
| A new test fails for another reason (a missing package, a wrong fixture path) | The test is broken, not red | Fix the test until it fails for the expected reason |
| The hook denies an edit to a test file | Its path does not match `testing.test_globs` | Ask the user to extend `testing.test_globs` in the dev settings; never rename to dodge it |
| Results show 0 tests | The entry point wrote no result file, or wrote it elsewhere | Add the logger option the workbook names (for example `--logger trx`) to the entry point's `results`, with the user's confirmation |
| A container is left after a failed run | The run stopped before tear-down | `EPHEMERAL down --run-id <id>`, then `EPHEMERAL sweep` |

## What it can't do

- It does not write product code: `dev-build` does, after the red check.
- It sees configuration in files and environment variables, not overrides made in test code; those count as not seen.
- It does not create remote test servers or cloud resources; only local Docker containers, and none without Docker.
- It does not edit CI configuration; it reports a CI entry point that is missing or broken.
- The hooks run only in Claude Code with the plugin installed; in other harnesses the rules hold as instructions only.

## Feedback

Send requested changes or reported problems to the `skill-builder` skill (`/skill-builder` in Claude Code), not by file path. Lessons about a change's process go to `dev-learn`; technology facts (a test framework's behaviour) go to `dev-workbook`. If `skill-builder` is unavailable, agree the change with the user first, keep it as small as the problem needs, and check the skill afterwards.

## Skills and agents

- `dev-core` - settings, state, the change folder, and the test-map, test-run, and `TESTING.md` templates.
- `dev-workbook` - the Testing, Commands, and Our situation statements for the touched technologies.
- `dev-plan` - the stage before; its plan and work items are this skill's input.
- `dev-build` - the next stage after the Write route; `dev-review` - the next stage after a green run.
- `skill-builder` - changes this skill.
- Hooks from this plugin: `dev-test-first` and `dev-safe-target` (in `hooks/`).
- No agents are used.
