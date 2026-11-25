---
name: dev-build
description: Builds an approved howtoai-dev work item after its tests have failed first - the smallest change that makes them pass (a reuse-first ladder - is it needed at all, existing code, standard library, installed dependency, one line, and only then new code), the workbook rules for each touched language and tool, every changed line traced to the work item, and a gate of lint, format, and type-check commands, then the work item's tests. Leaves a build record with a skipped-or-unchecked footer for review. Stage 4 of the howtoai-dev process; also applies review findings marked fix now. Use when asked to build, implement, or code a dev-plan work item, to continue the build stage of a change, or to apply the fix-now findings of a code review.
compatibility: Needs Python 3 (standard library only), git, and the dev-core, dev-workbook, and dev-test skills from the same plugin; the project's own toolchain for its gate. The test-first and safe-target hooks run in Claude Code when the howtoai-dev plugin is installed; elsewhere the same rules apply as instructions only.
---

# Dev build

## Goal

Stage 4 of `howtoai-dev`. **Build** (after `dev-test`'s red check): the smallest product-code change that makes a work item's failing tests pass, chosen on [the ladder](#the-ladder), every hunk traced to an acceptance criterion or test-map row, through the gate (lint, format check, type-check, then the work item's tests); the stage then moves to `test`. **Fix** (after `dev-review`): the findings the user marked fix now, traced to their finding IDs. Each run leaves the code uncommitted in the working tree, `<change folder>/build-<n>.md` from `dev-core`'s [build template](../dev-core/assets/templates/build.md) with every section kept (it has its own fixed shape), and the snapshot and gate records `BUILD` writes in `<change folder>/raw/build-<n>/`.

## Before you start

1. **Commands**, by path from this skill's folder (`python3 -I -B` instead of `py -3 -I -B` outside Windows):
   - `DEVCORE` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/../dev-core/scripts/devcore.py"`
   - `WORKBOOK` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/../dev-workbook/scripts/workbook.py"`
   - `BUILD` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/scripts/build.py"`

   `"ok": false` carries the error, which you report before stopping that step. Without Python 3 or git, stop and say the dev build needs them.
2. **The change:** the folder the user names, else the newest `<workspace>/<plan_folder>/INDEX.md` row at `build` or `human-review`. Read it with `DEVCORE state "<change folder>"`; never edit `state.json` by hand.
3. **Settings:** `DEVCORE settings --workspace "<workspace>"`. When `configured` is false, stop: the dev settings come from `dev-plan`'s Setup.
4. **Hooks.** Check every edit and command yourself first, as [Without hooks](../dev-test/references/safety-rules.md#without-hooks) lists; with the plugin installed, `dev-test-first` and `dev-safe-target` are a second layer. A denial or question from them is a rule working, not an error: follow its reason and never work around it (no other tool, no renamed file, no split command).

## Routes

"Stage" means the `howtoai-dev` stage in `state.json`.

| State or request | Route |
| --- | --- |
| Stage `build` whose latest red-check run in `test_runs` is `red`, or the user asks to build a work item of such a change | [Build](routes/build.md) |
| Stage `human-review` and the latest `review-<round>.md` has findings marked fix now, or the user asks to apply them | [Fix](routes/fix.md) |
| Stage `tests-first`, or stage `build` whose latest red-check run is missing or `red-failed` | Stop: the tests come first; hand back to `dev-test`'s Write route |
| Stage `plan` or `accept` | Stop: the plan is not approved yet; hand back to `dev-plan` |
| Stage `test` or `review` | Stop: the build is done; hand on to `dev-test`'s Run route or `dev-review` |

## Core rules

- **Smallest complete change.** Take the first rung of [the ladder](#the-ladder) that fully works, and finish every part the work item needs (callers, configuration, exports): a short diff that leaves a caller broken is not done.
- **Every changed line traces to the work item.** A hunk with no acceptance criterion, test-map row, or fix-now finding behind it is reverted, not justified. Tidying, renaming, and reformatting the work item does not need stay out, also when asked in passing; offer them as a new work item.
- **Tests and CI are not yours to change.** `TESTING.md` belongs to `dev-test`. Never edit tests, test data, test settings, thresholds, CI configuration, or lockfiles to make the gate pass. If the work item really needs such a change, ask, and record the approval with its `paths`.
- **Production markers.** Before any command or MCP call, check it against the settings' `environments.deny` markers; on a match, stop and ask.
- **Destructive commands** (drops, truncates, bulk deletes, down-migrations, resets, destroy, prune) only on a throwaway container this run created; otherwise ask first.
- **Destructive migrations need a yes.** A migration that drops, truncates, or renames needs the user's yes, recorded with its `paths` as `append.approvals`, before you write it.
- **The project's own commands.** The gate runs only the commands saved in `build.gate`, through `BUILD gate`; the tests run through `dev-test`. Never ad-hoc commands.
- **Numbers from scripts.** Hunks, trace, gate, and test results come from `BUILD` and `dev-test`, never from your own reading of a diff or log.
- **No commits.** Never commit, push, branch, or open a pull request; `dev-deploy` commits. Outside the working tree and the change folder, write only the gate settings in `<workspace>/AGENTS/howtoai/dev/settings.json` after the user approves them, and the git objects of the snapshot (no commit, branch, or index change).
- **State** goes through `DEVCORE`: each workbook use as `append.receipts`, each approval (gate settings, a pre-existing gate failure, a protected path) as `append.approvals`, each finished run as `append.builds`, and the stage.
- **Chat:** one line per step, every question as its own message, no raw JSON. The closing report gives the result, the hunks and what they trace to, the gate, the Skipped or unchecked lines, and the next stage.

Tracing is by hunk, not meaning (`dev-review` checks meaning), and callers found by search can miss dynamic calls, which go under Skipped or unchecked. The hooks run only in Claude Code with the plugin installed; elsewhere these rules hold as instructions only. Changes to this skill go to `skill-builder` (not by file path; if it is unavailable, agree the change with the user first), process lessons to `dev-learn`, and technology facts to `dev-workbook`.

## The ladder

For each thing the work item or finding needs, go down the rungs and stop at the first that fully meets it; record it as a Ladder decisions row.

1. **Not needed.** No criterion, test, or finding asks for it: options, settings, and "for later" hooks stay out. Name what you left out under Skipped or unchecked.
2. **Existing code** the repository already has, used the way the code around it does. Search before writing anything.
3. **Standard library or platform**, unless the project wraps it in its own helper, which then wins.
4. **Installed dependency** the project already references. A new one is the user's decision, never a rung.
5. **One line** a reader understands at a glance.
6. **New code:** the least that meets the criteria, in the code's existing structure, layers, and naming.

While you climb:

- **No speculative structure:** no abstraction, wrapper, interface, option, setting, or type conversion the work item does not ask for. Removing code beats adding it.
- **Bug fixes at the cause:** find every caller, then fix the shared code once.
- **Equal size, correct edges:** take the option right on boundaries, nulls, and empty input.
- **Comments say why**, in one line; a deliberate shortcut names its limit and when to revisit it.
- **Never trimmed:** validation at trust boundaries, error handling that prevents data loss, security, accessibility, and anything the work item asks for, also in code you move or merge.

## Verify the output

Before the closing report:

- `BUILD check "<change folder>" --n <n>` returns `"passed": true`: every hunk traced once, every trace ID real, no protected or test file changed without approval, every gate command passed on the final code (or failed before and after with the user's approval), and, on the Build route, a green work-item test run after the last gate run (on the Fix route that check is listed under `skipped`).
- `build-<n>.md` has no `{placeholder}` left and at least one line under Skipped or unchecked.
- `DEVCORE state` shows the build in `builds` and the new stage.
- A stopped build (fix-round cap, a declined approval) also writes `build-<n>.md` with Result `stopped`, records the build as `stopped`, and keeps the stage `build`.

## Common failures

| Symptom | Fix |
| --- | --- |
| `hunk not traced` for lines a formatter or IDE fix touched | Revert those hunks; format only your own lines, then run the gate again |
| `the last 'after' run was on other code` | Run every gate command again with `--label after`, then the work item's tests |
| The format check fails on files the build did not touch (the baseline already failed) | Ask whether to go on; on a yes, record the approval with `build` and `gate`, and list it under Skipped or unchecked |
| `--command must equal the configured command` | Copy it from `build.gate`; to change the gate, ask and save it through `DEVCORE setup` |
| A test still fails after `build.max_fix_rounds` rounds | Stop and report; the user decides whether the plan or the test changes |
