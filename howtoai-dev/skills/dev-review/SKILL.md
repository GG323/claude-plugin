---
name: dev-review
description: Reviews a built howtoai-dev change with context-free goldfish reviewers - spec compliance against the plan and work items first, then correctness, tests and gate integrity, security, performance, and compliance with the workspace's workbooks and instruction files, each reviewer searching wide - scores and verifies each finding, inspects and reruns the tests itself, and writes a ranked review doc; then records the user's fix now, later, or decline choices, sends fixes back through dev-build and dev-test, and re-reviews the changed lines. Stages 6 and 7 of the howtoai-dev process; also proposes a fix to its own rules when the user says a finding is wrong. Use when asked to review a dev change, run the code review, answer or triage review findings, or re-review after fixes.
compatibility: Needs Python 3 (standard library only), git, subagents, and the dev-core, dev-workbook, dev-test, and dev-build skills from the same plugin. The goldfish agents load by name when the howtoai-dev plugin is installed; otherwise general-purpose subagents read their files. Without subagents it halts.
---

# Dev review

## Goal

Stages 6 and 7 of `howtoai-dev`: a ranked review of the built change that the user has answered finding by finding. You are the elephant: you hold the conversation, the plan, and the change; goldfish reviewers see only what their brief names, so they catch what familiarity hides.

- `<change folder>/review-<round>.md`, written by `FINDINGS tally --kind code` in `dev-core`'s review template shape, with each kept and each outside finding carrying the user's choice.
- `<change folder>/raw/review-<round>/`: the diff, the changed lines, each reviewer's reply, the scores, the verdicts, and `findings.json`.
- Fix-later work items `wi/<n>.md` from the work-item template, plus a tracker item when the tracker is Jira, GitHub, or Azure DevOps.
- Then fix-now findings go to `dev-build`, or the accepted change goes on to `dev-deploy`; `dev-learn` runs after each human review.

## Before you start

Commands, by path from this skill's folder (`python3 -I -B` instead of `py -3 -I -B` outside Windows):

- `DEVCORE` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/../dev-core/scripts/devcore.py"`
- `FINDINGS` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/../dev-core/scripts/findings.py"`
- `WORKBOOK` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/../dev-workbook/scripts/workbook.py"`
- `REVIEW` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/scripts/review.py"`

Each prints one JSON object; on `"ok": false` report the error and stop that step. Without Python 3 or git, stop and say the dev review needs them.

- **The change:** the folder the user names, else the newest row of `<workspace>/<plan_folder>/INDEX.md` at stage `review` or `human-review`. Read it with `DEVCORE state "<change folder>"`; every state change goes through `DEVCORE`, never by editing `state.json`.
- **Settings:** `DEVCORE settings --workspace "<workspace>"`; its `review` block holds the confidence threshold and the round limits. When `configured` is false, stop: the settings come from `dev-plan`'s Setup.
- **Goldfish:** start a reviewer by its agent name (`goldfish-spec`, `goldfish-correctness`, `goldfish-tests`, `goldfish-security`, `goldfish-performance`, `goldfish-compliance`, `goldfish-scorer`, `goldfish-verifier`) when the plugin is installed; otherwise a general-purpose subagent whose brief begins "Read `${CLAUDE_SKILL_DIR}/../../agents/<name>.md` and act as that agent". Give it only what its Input section lists, never this conversation. When no fresh subagent can start, halt and say why: a review by the agent that holds the conversation is not a goldfish review.
- Goldfish search wide and fence nothing; merging repeats and taking findings outside the change to the user are yours.

## Routes

"Stage" means the `howtoai-dev` stage in `state.json`.

| State or request | Route |
| --- | --- |
| Stage `review` (after `dev-test`'s green run), or the user asks for a code review or a re-review | [Review](routes/review.md) |
| Stage `human-review`, and the user answers the findings or asks to go through them | [Human review](routes/human-review.md) |
| The user says a finding is wrong, or corrects a rule this skill or a goldfish applied | [Self-edit](routes/self-edit.md), then back to the route that was running |
| Stage `build` or `test` | Stop: the build or its test run is not finished; hand on to `dev-build` or `dev-test` |
| Stage `plan`, `accept`, or `tests-first` | Stop: there is nothing built to review yet |

## Rules

- **Production markers stop you.** Before any command or MCP call, check it against the settings' `environments.deny` markers; on a match, stop and ask.
- **Findings, not fixes.** This skill never changes product code; `dev-build` applies the fixes the user chooses. Reviewers never run or change code; only you run tests, through `dev-test`.
- **Numbers from scripts.** `FINDINGS` counts, scores, filters, and ranks findings; `REVIEW` gives the diff and missing receipts. Never count, relabel, or drop a finding yourself; a reply off the agent's scale goes back to that agent.
- **The user decides.** Every kept finding, and every finding outside this change, gets the user's choice: fix now, later, or decline with a reason. AUTO-FIX is a recommendation, never a decision.
- **Declined stays declined.** Declined findings are recorded and passed to later rounds, so they are not raised again.
- **Temporary tests leave.** A test you add to confirm a finding is removed at the end of the round, unless the user approves promoting it to the suite.
- **No outward actions.** No commits, pushes, pull-request comments, or posts.
- **Writes outside the change folder:** only temporary test files (removed at the end of the round), a new `TESTING.md` after the user's yes, and tracker items (Jira, GitHub, or Azure DevOps) for findings the user marked later, after approving the list.
- **Chat.** One line per step ("Pass 1: spec clean; pass 2: 3 reviewers"), the human-review question as its own message, and a short closing report: the counts, the kept findings in one line each, what was held back and why, and the next stage. No raw JSON.
- **An empty diff** because the change was already committed: say so, and review against the commit the plan names with the user's help, or stop.

## Verify the output

Before the closing report of a Review round:

- `review-<round>.md` exists, and its counts match the `FINDINGS tally` result.
- Test inspection has no `{filled by dev-review}` placeholder: it was filled with `--inspection`.
- Every temporary test is removed (`git status` shows none), or its promotion is approved and recorded.
- `DEVCORE state` shows the round in `loops.review` and the stage `human-review`.

After Human review: `FINDINGS check "<change folder>/review-<round>.md"` returns `"ok": true`, every decline is in `declined`, every later finding has a work item, and the stage is `build` (fixes) or `deploy` (accepted).

## Feedback

Changes to this skill go to `skill-builder` (the [Self-edit](routes/self-edit.md) route prepares a change plan for it); technology facts go to `dev-workbook`. Without `skill-builder`, agree the change with the user first and keep it small.
