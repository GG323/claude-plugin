---
name: dev-learn
description: Learns from each howtoai-dev code-review round - collects the Critical and Major findings, the declined ones with the user's reasons, and the ones that repeat an earlier lesson; names the stage that let each through (plan, tests, workbook, build, review) with quoted evidence; writes a learn record with the smallest fix at the lowest level that resolves it (a workbook or reference file first, then a goldfish reviewer, then a skill file only with proof); keeps the project lessons log that dev-plan reads; lists drift between docs and code; and, after the user approves each fix, hands it to dev-workbook, the project's hook rules, or skill-builder. Stage 8 of the howtoai-dev process, run after each human review. Use when asked to run the learn step, learn from a review, find why a bug got through, root-cause review findings, or update the dev lessons.
compatibility: Needs Python 3 (standard library only) and the dev-core, dev-workbook, and dev-review skills from the same plugin; process fixes need skill-builder. No subagents.
---

# Dev learn

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

`dev-learn` is stage 8 of the `howtoai-dev` process. After each review round it asks why the round's serious, declined, and repeated findings got through, and fixes the cause once, where the cause lives, so the next change does not repeat it. It writes `learn-<round>.md` in the change folder, keeps the project lessons log that `dev-plan` reads at setup, and hands each fix the user approves to the skill that owns that file. It never changes product code, and it does not change the change's stage.

## Before you start

1. **Commands.** Call these by their paths relative to this skill's folder (`python3 -I -B` instead of `py -3 -I -B` outside Windows):
   - `DEVCORE` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/../dev-core/scripts/devcore.py"`
   - `WORKBOOK` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/../dev-workbook/scripts/workbook.py"` (workbooks are read through its `resolve`, never by path)
   - `LEARN` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/scripts/learn.py"`
   - `TESTINGMD` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/../dev-test/scripts/testing_md.py"`

   Each prints one JSON object; `"ok": false` carries the error, which you report before stopping that step. Without Python 3, stop and say the learn step needs it.
2. **The change and round.** The change folder `dev-review` hands on, or the one the user names; the round is the highest `review-<n>.md` in it unless the user names one. Read the state with `DEVCORE state "<change folder>"`; never edit `state.json` by hand.
3. **The workspace and the log.** `DEVCORE root --cwd "<change folder>"` gives the workspace; the lessons log is `<workspace>/.howtoai/dev/lessons.md`, created by the first lesson. The plan folder is the change folder's parent.
4. **The method.** Read `dev-core`'s [self-edit and root-cause method](../dev-core/references/self-edit.md): its stage table, its fix levels, and its change plan are the rules this skill applies.

## Routes

| State or request | Route |
| --- | --- |
| `dev-review` hands on after a human review, or the user asks to run the learn step for a change | [Learn](routes/learn.md) |
| No `review-<n>.md` in the change folder | Stop: there is no review round to learn from; hand on to `dev-review` |
| The user asks only to see or tidy the lessons log | Show it; remove a lesson only when the user says it is settled, with `LEARN lesson remove` |

## Core rules

- **Workbook rules load as `dev-workbook` says.** Before the first `WORKBOOK resolve`, read `${CLAUDE_SKILL_DIR}/../dev-workbook/references/loading.md` and follow it; every resolve prints that rule again.
- **Lowest level first.** A fix lands at the lowest level that resolves it: a workbook or another reference file, then a goldfish, then a skill file. A skill file change needs evidence, in the record and the change plan, that neither lower level can resolve it; without that evidence, propose the lower level.
- **Evidence, not opinion.** Every root cause quotes the instruction, statement, or test that let the problem through, with its file and line, or names where the missing one belongs.
- **The user approves each fix.** Records (the learn record and lesson lines) are written without asking; every fix is proposed with a recommendation and goes to its owner only after the user's yes for that fix. This skill edits no workbook, skill, agent, or settings file itself.
- **Settled lessons leave the log.** A lesson whose fix is applied, or whose fix is declined, is removed from the log with its copies. The learn record keeps the history, and `LEARN collect` reads earlier learn records, so a problem that comes back after its fix is still found.
- **Repeats come first.** A finding that matches an open lesson raises its count; one that matches an applied fix means the fix did not hold. Both are listed first in the proposal, with the stronger fix recommended.
- **Never blocks the change.** The fix-now hand-on and the deploy do not wait for the learn step's approvals.

## Output contract

- **Audience:** the developer running the change; `dev-plan` reads the lessons log at its next setup.
- **Deliverables:**
  - `<change folder>/learn-<round>.md`, copied from `dev-core`'s [learn template](../dev-core/assets/templates/learn.md) and kept in its shape (exempt from the workspace's title and contents rules): one table row per collected finding, then a Drift section with at least one bullet ("none found" when clean).
  - Lines in `<workspace>/.howtoai/dev/lessons.md` in the [lesson](../dev-core/assets/templates/lesson.md) format, written only by `LEARN lesson`.
- **Report:** one chat message: "Learn round <n>: <c> findings collected (<r> repeats), <p> fixes proposed, <d> drift items", then the proposal list, then what the user approves. After the hand-ons, one line per fix with where it landed.
- **Writes outside the change folder:** the lessons log only. Fixes are written by `dev-workbook`, `dev-core`'s Setup, or `skill-builder`.

## Verify the output

- `LEARN check "<change folder>/learn-<round>.md" --review "<change folder>/review-<round>.md" --lessons "<lessons log>" --state "<change folder>/state.json"` returns `"ok": true`.
- Every row's evidence is a quote with a file and line, or the place a missing statement belongs; every level 3 row says why levels 1 and 2 cannot resolve it.
- Nothing was handed on without the user's yes for that fix, and each applied fix's lesson is gone from the log.

## Common failures

| Symptom | Cause | Fix |
| --- | --- | --- |
| Every root cause is `build` | The build is the last stage that touched the code, so it looks guilty | Ask which stage's rules or facts would have caught it; `build` only when the plan, tests, and workbooks were right |
| A skill file change is proposed for a technology fact | The fact was found in a skill's step | Technology facts go to `dev-workbook`; the step already consults the workbook |
| `collect` finds no repeats although the problem is familiar | The earlier lesson was settled and removed | Read `applied_fixes` in its output: a match there means the fix did not hold |
| `check` says a settled lesson is still in the log | The row was set to applied before the lesson was removed | `LEARN lesson remove` with that ID, then check again |

## What it can't do

- It does not fix product code or docs: drift items and fix-later findings become work items through `dev-review` and `dev-plan`.
- It does not judge a finding again: the review round's scores and the user's choices stand.
- A process change runs through `skill-builder`; without it, the change plan stays in the learn record as proposed.

## Feedback

Send requested changes or reported problems to the `skill-builder` skill (`/skill-builder` in Claude Code), not by file path. Technology facts go to `dev-workbook`. If `skill-builder` is unavailable, agree the change with the user first, keep it as small as the problem needs, and check the skill afterwards.

## Skills and agents

- [Learn](routes/learn.md) - the route; [scripts/learn.py](scripts/learn.py) - collect, lesson, and check.
- `dev-core` - state, Setup for hook rules, the learn and lesson templates, and the self-edit and root-cause method.
- `dev-workbook` - takes technology facts through Propose; `skill-builder` - takes process changes as a supplied change plan.
- `dev-review` - hands on after each human review; `dev-plan` - reads the lessons log at setup.
- No agents are used.
