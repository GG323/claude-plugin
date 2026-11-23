---
name: dev-build
description: Builds an approved howtoai-dev work item after its tests have failed first - the smallest change that makes them pass (a reuse-first ladder - is it needed at all, existing code, standard library, installed dependency, one line, and only then new code), the workbook rules for each touched language and tool, every changed line traced to the work item, and a gate of lint, format, and type-check commands, then the work item's tests. Leaves a build record with a skipped-or-unchecked footer for review. Stage 4 of the howtoai-dev process; also applies review findings marked fix now. Use when asked to build, implement, or code a dev-plan work item, to continue the build stage of a change, or to apply the fix-now findings of a code review.
compatibility: Needs Python 3 (standard library only), git, and the dev-core, dev-workbook, and dev-test skills from the same plugin; the project's own toolchain for its gate. The test-first and safe-target hooks run in Claude Code when the howtoai-dev plugin is installed; elsewhere the same rules apply as instructions only.
---

# Dev build

## Contents

- [What it does](#what-it-does)
- [Before you start](#before-you-start)
- [Routes](#routes)
- [Core rules](#core-rules)
- [The ladder](#the-ladder)
- [Output contract](#output-contract)
- [Verify the output](#verify-the-output)
- [Common failures](#common-failures)
- [What it can't do](#what-it-cant-do)
- [Feedback](#feedback)
- [Skills and agents](#skills-and-agents)

## What it does

`dev-build` is stage 4 of the `howtoai-dev` process. After `dev-test`'s Write route has proven a work item's tests fail, the **Build route** writes the product code: the smallest change that makes them pass, chosen rung by rung on [the ladder](#the-ladder), following the workbook rules for every language and tool it touches. Every changed hunk is traced to an acceptance criterion or test-map row, and the change passes the gate (lint, format check, type-check, then the work item's tests) before the stage moves to `test`. Once `dev-review` has run, the **Fix route** applies the findings the user marked fix now, traced to their finding IDs.

## Before you start

1. **Commands.** Call these by their paths relative to this skill's folder (`python3 -I -B` instead of `py -3 -I -B` outside Windows):
   - `DEVCORE` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/../dev-core/scripts/devcore.py"`
   - `WORKBOOK` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/../dev-workbook/scripts/workbook.py"`
   - `BUILD` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/scripts/build.py"`

   Each prints one JSON object; `"ok": false` carries the error, which you report before stopping that step. Without Python 3 or git, stop and say the dev build needs them.
2. **The change.** Find the change folder: the one the user names, else the newest row of `<workspace>/<plan_folder>/INDEX.md` at stage `build` or `human-review`. Read it with `DEVCORE state "<change folder>"`. Never edit `state.json` by hand.
3. **Settings.** `DEVCORE settings --workspace "<workspace>"`. When `configured` is false, stop: the dev settings come from `dev-plan`'s Setup.
4. **Hooks.** With the plugin installed, `dev-test-first` and `dev-safe-target` run on every edit and command. A denial or question from them is a rule working, not an error: follow its reason and never work around it (no other tool, no renamed file, no split command).

## Routes

Each route is one file in `routes/`. "Stage" in this skill always means a stage of the `howtoai-dev` process, as `state.json` records it.

| State or request | Route |
| --- | --- |
| Stage `build` whose latest red-check run in `test_runs` is `red`, or the user asks to build a work item of such a change | [Build](routes/build.md) |
| Stage `human-review` and the latest `review-<round>.md` has findings marked fix now, or the user asks to apply them | [Fix](routes/fix.md) |
| Stage `tests-first`, or stage `build` whose latest red-check run is missing or `red-failed` | Stop: the tests come first; hand back to `dev-test`'s Write route |
| Stage `plan` or `accept` | Stop: the plan is not approved yet; hand back to `dev-plan` |
| Stage `test` or `review` | Stop: the build is done; hand on to `dev-test`'s Run route or `dev-review` |

## Core rules

- **Smallest complete change.** Take the first rung of [the ladder](#the-ladder) that fully works, and finish every part the work item needs, because a short diff that leaves a caller broken is not done.
- **Every changed line traces to the work item.** A hunk with no acceptance criterion, test-map row, or fix-now finding behind it is reverted, not justified. Tidying, renaming, and reformatting that the work item does not need stay out, also when asked in passing; offer them as a new work item instead.
- **Never cut safety.** Validation at trust boundaries, error handling that prevents data loss, security, and accessibility stay, also in code you move or merge.
- **Tests and CI are not yours to change.** `TESTING.md` files belong to `dev-test`, which rewrites them after each run, so they are not part of the build's hunks. Never edit tests, test data, test settings, thresholds, CI configuration, or lockfiles to make the gate pass, because a weakened gate hides the failure it exists to show. If the work item really needs such a change, ask, and record the approval with its `paths`.
- **No new dependency without asking.** Rung 4 means a dependency already installed; adding one is the user's call.
- **The project's own commands.** The gate runs only the commands saved in `build.gate`, through `BUILD gate`, and the tests run through `dev-test`; never ad-hoc commands.
- **Numbers from scripts.** Hunks, trace results, gate results, and test results come from `BUILD` and `dev-test`, never from your own reading of a diff or a log.
- **No commits.** The change stays uncommitted in the working tree for `dev-test`, `dev-review`, and `dev-deploy`, which commits it.

## The ladder

Both routes choose code this way, because the cheapest code to review and maintain is code that was never written. For each thing the work item or finding needs, go down the rungs and stop at the first one that fully meets it. Record the rung as a Ladder decisions row of the build record.

1. **Not needed.** No acceptance criterion, test, or finding asks for it: options, settings, flexibility, and "for later" hooks stay out. Name what you left out under Skipped or unchecked.
2. **Existing code.** A function, type, component, or pattern the repository already has. Use it the way the code around it does; search for it before writing anything, because a helper the plan does not mention is easy to miss.
3. **Standard library or platform.** What the language, runtime, or framework ships, unless the project wraps it in its own helper, which then wins (rung 2).
4. **Installed dependency.** A package the project already references. A new one is the user's decision, never a rung.
5. **One line.** A single expression a reader understands at a glance; a dense line that needs decoding does not count.
6. **New code.** The least code that meets the criteria, in the structure, layers, and naming the code already has.

While you climb:

- **Complete, not partial.** Callers, configuration, and exports the change reaches are part of it; a smaller diff that breaks one of them is not smaller.
- **No speculative structure.** No new abstraction, wrapper, interface, option, setting, or type conversion the work item does not ask for. Keep values in the form the code already passes them; removing code beats adding it.
- **Bug fixes at the cause.** Find every caller first, then fix the shared code once instead of patching each caller.
- **Equal size, correct edges.** Between two options of the same size, take the one that is right on boundaries, nulls, and empty input.
- **Comments say why.** One line, only for what the code cannot show. A deliberate shortcut gets a comment that names its limit and when to revisit it.
- **Never trimmed:** validation at trust boundaries, error handling that prevents data loss, security, accessibility, and anything the work item asks for.

## Output contract

- **Audience:** the developer running the change, and the later dev stages that read the record (`dev-test`, `dev-review`, `dev-learn`).
- **Deliverables:**
  - The code change, in the repository's working tree, in the project's own style and conventions.
  - `<change folder>/build-<n>.md`, one per build or fix run, from `dev-core`'s [build template](../dev-core/assets/templates/build.md), every section kept: Ladder decisions, Callers checked, Trace, Workbook statements applied, Gate, Skipped or unchecked, Open points. Markdown, because agents read it and git diffs it; it follows its own fixed shape, not the workspace's title and contents-list rules.
  - `<change folder>/raw/build-<n>/`: the snapshot and gate records `BUILD` writes.
- **State:** each workbook use as `append.receipts`, each approval (gate settings, a pre-existing gate failure, a protected path) as `append.approvals`, each finished run as `append.builds`, and the stage, all through `DEVCORE`.
- **Chat:** one line per step ("Gate: format and build pass; WI tests green"), every question as its own message, and a short closing report: result, the hunks and what they trace to, the gate, the skipped-or-unchecked lines, and the next stage. No raw JSON.
- **Writes outside the repository's working tree and the change folder:** none, except the gate settings in `<workspace>/.howtoai/dev/settings.json` after the user approves them, and git objects for the snapshot (no commit, branch, or index change).

## Verify the output

Before the closing report:

- `BUILD check "<change folder>" --n <n>` returns `"passed": true`: every hunk traced once, every trace ID real, no protected or test file changed without approval, every gate command passed on the final code (or failed before and after with the user's approval), and, on the Build route, a green work-item test run after the last gate run (the Fix route leaves the tests to `dev-test` at stage `test`, and the script lists that check under `skipped`).
- `build-<n>.md` has no `{placeholder}` left and at least one line under Skipped or unchecked.
- `DEVCORE state` shows the build in `builds` and the new stage.
- A stopped build (fix-round cap, a declined approval) also writes `build-<n>.md` with Result `stopped` and records the build as `stopped`, and its stage stays `build`.

## Common failures

| Symptom | Cause | Fix |
| --- | --- | --- |
| `hunk not traced` for lines you never meant to change | A formatter or an IDE-style fix touched whole files | Revert those hunks; format only your own lines, then run the gate again |
| `the last 'after' run was on other code` | Code changed after the gate ran | Run every gate command again with `--label after`, then the work item's tests |
| The format check fails on files the build did not touch | The baseline already failed | Ask the user whether to go on; on a yes, record the approval with `build` and `gate`, and list it under Skipped or unchecked |
| `--command must equal the configured command` | The command was retyped or changed | Copy it from `build.gate`; to change the gate, ask and save it through `DEVCORE setup` |
| A test still fails after 3 fix rounds | The design, the test, or the plan is wrong | Stop and report; the user decides whether the plan or the test changes |

## What it can't do

- It does not write or change tests: `dev-test` does, before the build.
- It does not commit, push, branch, or open a pull request: `dev-deploy` does.
- It checks traceability by hunk, not by meaning: a hunk can cite a criterion it does not serve, which `dev-review` checks.
- It finds callers by search; dynamic calls (reflection, string dispatch) can be missed, and are listed under Skipped or unchecked.
- The hooks run only in Claude Code with the plugin installed; in other harnesses the rules hold as instructions only.

## Feedback

Send requested changes or reported problems to the `skill-builder` skill (`/skill-builder` in Claude Code), not by file path. Lessons about a change's process go to `dev-learn`; technology facts (a linter's behaviour, a framework idiom) go to `dev-workbook`. If `skill-builder` is unavailable, agree the change with the user first, keep it as small as the problem needs, and check the skill afterwards.

## Skills and agents

- `dev-core` - settings, state, the change folder, and the build template.
- `dev-workbook` - the workbook rules and the statements that fit the step.
- `dev-test` - the stage before (Write route) and the work item's test runs (Run route).
- `dev-plan` - the plan and work items this skill builds; `dev-review` - the next stage after `dev-test`'s Run route, and the source of fix-now findings.
- `skill-builder` - changes this skill.
- Hooks from this plugin: `dev-test-first` and `dev-safe-target` (in `hooks/`).
- No agents are used.
