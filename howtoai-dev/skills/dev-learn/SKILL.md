---
name: dev-learn
description: Learns from each howtoai-dev code-review round - collects the Critical and Major findings, the declined ones with the user's reasons, and the ones that repeat an earlier lesson; names the stage that let each through (plan, tests, workbook, build, review) with quoted evidence; writes a learn record with the smallest fix at the lowest level that resolves it (a workbook or reference file first, then a goldfish reviewer, then a skill file only with proof); keeps the project lessons log that dev-plan reads; lists drift between docs and code; and, after the user approves each fix, hands it to dev-workbook, the project's hook rules, or skill-builder. Stage 8 of the howtoai-dev process, run after each human review. Use when asked to run the learn step, learn from a review, find why a bug got through, root-cause review findings, or update the dev lessons.
compatibility: Needs Python 3 (standard library only) and the dev-core, dev-workbook, and dev-review skills from the same plugin; process fixes need skill-builder. No subagents.
---

# Dev learn

## Goal

Stage 8 of `howtoai-dev`, after each human review: find why the round's Critical, Major, declined, and repeated findings got through, and fix each cause once, where it lives, so the next change does not repeat it.

- `<change folder>/learn-<round>.md`, from `dev-core`'s [learn template](../dev-core/assets/templates/learn.md) in its own fixed shape: one row per collected finding, then a Drift section with at least one bullet ("none found" when clean).
- Lesson lines in `<workspace>/AGENTS/lessons.md` (the [lesson](../dev-core/assets/templates/lesson.md) format), which `dev-plan` reads at setup.
- Each fix the user approves, handed to its owner: `dev-workbook`, `dev-core`'s Setup (hook rules), or `skill-builder`.

## Before you start

1. **Commands**, by path from this skill's folder (`python3 -I -B` instead of `py -3 -I -B` outside Windows):
   - `DEVCORE` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/../dev-core/scripts/devcore.py"`
   - `WORKBOOK` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/../dev-workbook/scripts/workbook.py"` (workbooks are read through its `resolve`, never by path)
   - `LEARN` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/scripts/learn.py"`
   - `TESTINGMD` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/../dev-test/scripts/testing_md.py"`

   `"ok": false` carries the error, which you report before stopping that step. Without Python 3, stop and say the learn step needs it.
2. **The change and round:** the change folder `dev-review` hands on, or the one the user names; the round is the highest `review-<n>.md` in it unless the user names one. Read it with `DEVCORE state "<change folder>"`; never edit `state.json` by hand.
3. **The workspace and log:** `DEVCORE root --cwd "<change folder>"` gives the workspace; the lessons log is `<workspace>/AGENTS/lessons.md`, created by the first lesson.
4. **The method:** read `dev-core`'s [self-edit and root-cause method](../dev-core/references/self-edit.md). Its stage table, fix levels, and change plan are the rules this skill applies.

## Routes

| State or request | Route |
| --- | --- |
| `dev-review` hands on after a human review, or the user asks to run the learn step for a change | [Learn](routes/learn.md) |
| No `review-<n>.md` in the change folder | Stop: there is no review round to learn from; hand on to `dev-review` |
| The user asks only to see or tidy the lessons log | Show it; remove a lesson only when the user says it is settled, with `LEARN lesson remove` |

## Rules

- **Lowest level first.** A fix lands at the lowest level that resolves it: a workbook or another reference file, then a goldfish, then a skill file. A skill file change needs evidence, in the record and the change plan, that neither lower level can resolve it; without that evidence, propose the lower level. Technology facts always go to `dev-workbook`.
- **Evidence, not opinion.** Every root cause quotes the instruction, statement, or test that let the problem through, with its file and line, or names where the missing one belongs.
- **The user approves each fix.** Records (the learn record and lesson lines) are written without asking. Every fix is proposed with a recommendation and goes to its owner only after the user's yes for that fix. This skill edits no workbook, skill, agent, or settings file itself; without `skill-builder`, a process change stays in the learn record as proposed.
- **One problem, one cause.** The IDs under one number of the review's Problems list are one cause: one root cause, one lesson, and one repeat, with a record row for each ID.
- **Settled lessons leave the log.** A lesson whose fix is applied or declined is removed with its copies; lesson lines are written only by `LEARN lesson`. The learn record keeps the history, and `LEARN collect` reads earlier records, so a problem that comes back after its fix is still found.
- **Repeats come first.** A finding that matches an open lesson raises its count; one that matches an applied fix means the fix did not hold. Both are listed first, with the stronger fix recommended.
- **Stay in your lane.** Never change product code or docs, or the change's stage: drift items and fix-later findings become work items through `dev-review` and `dev-plan`. Never judge a finding again: the review's scores and the user's choices stand. The only write outside the change folder is the lessons log.
- **Never blocks the change.** The fix-now hand-on and the deploy do not wait for the learn step's approvals.

## Verify the output

- `LEARN check "<change folder>/learn-<round>.md" --review "<change folder>/review-<round>.md" --lessons "<lessons log>" --state "<change folder>/state.json"` returns `"ok": true`.
- Every row's evidence is a quote with a file and line, or the place a missing statement belongs; every level 3 row says why levels 1 and 2 cannot resolve it.
- Nothing was handed on without the user's yes for that fix, and each applied fix's lesson is gone from the log.

## Common failures

| Symptom | Fix |
| --- | --- |
| Every root cause is `build` | Ask which stage's rules or facts would have caught it; `build` only when the plan, tests, and workbooks were right |
| A skill file change is proposed for a technology fact | It goes to `dev-workbook`; the skill step already consults the workbook |
| `collect` finds no repeats although the problem is familiar | The lesson was settled and removed: read `applied_fixes` in its output; a match there means the fix did not hold |
| `check` says a settled lesson is still in the log | `LEARN lesson remove` with that ID, then check again |

## Feedback

Changes to this skill go to `skill-builder`, not by file path; technology facts go to `dev-workbook`. Without `skill-builder`, agree the change with the user first and keep it small.
