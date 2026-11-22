---
name: dev-review
description: Reviews a built howtoai-dev change with context-free goldfish reviewers - spec compliance against the plan and work items first, then correctness, tests and gate integrity, security, performance, and compliance with the workspace's workbooks and instruction files, each reviewer searching wide - scores and verifies each finding, inspects and reruns the tests itself, and writes a ranked review doc; then records the user's fix now, later, or decline choices, sends fixes back through dev-build and dev-test, and re-reviews the changed lines. Stages 6 and 7 of the howtoai-dev process; also proposes a fix to its own rules when the user says a finding is wrong. Use when asked to review a dev change, run the code review, answer or triage review findings, or re-review after fixes.
compatibility: Needs Python 3 (standard library only), git, subagents, and the dev-core, dev-workbook, dev-test, and dev-build skills from the same plugin. The goldfish agents load by name when the howtoai-dev plugin is installed; otherwise general-purpose subagents read their files. Without subagents it halts.
---

# Dev review

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

`dev-review` is stages 6 and 7 of the `howtoai-dev` process. You are the **elephant**: you hold the conversation, the plan, and the change, and you drive **goldfish** reviewers that see only the diff, the plan, the test output, and the files you name, so they catch what familiarity hides. The **Review** route runs the goldfish in two passes, scores and verifies their findings, inspects the tests yourself, and writes `review-<round>.md` through a script. The **Human review** route records the user's choice for each finding and sends the change on. The **Self-edit** route turns a correction from the user into a proposed fix of the rule that caused it.

## Before you start

1. **Commands.** Call these by their paths relative to this skill's folder (`python3 -I -B` instead of `py -3 -I -B` outside Windows):
   - `DEVCORE` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/../dev-core/scripts/devcore.py"`
   - `FINDINGS` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/../dev-core/scripts/findings.py"`
   - `WORKBOOK` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/../dev-workbook/scripts/workbook.py"`
   - `REVIEW` = `py -3 -I -B "${CLAUDE_SKILL_DIR}/scripts/review.py"`

   Each prints one JSON object; `"ok": false` carries the error, which you report before stopping that step. Without Python 3 or git, stop and say the dev review needs them.
2. **The change.** The change folder the user names, else the newest row of `<workspace>/<plan_folder>/INDEX.md` at stage `review` or `human-review`. Read it with `DEVCORE state "<change folder>"`; never edit `state.json` by hand.
3. **Settings.** `DEVCORE settings --workspace "<workspace>"`; the `review` block holds the confidence threshold and the round limits. When `configured` is false, stop: the settings come from `dev-plan`'s Setup.
4. **Goldfish agents.** Start a reviewer by its agent name (`goldfish-spec`, `goldfish-correctness`, `goldfish-tests`, `goldfish-security`, `goldfish-performance`, `goldfish-compliance`, `goldfish-scorer`, `goldfish-verifier`) when the `howtoai-dev` plugin is installed. When it is not, start a general-purpose subagent whose brief begins "Read `${CLAUDE_SKILL_DIR}/../../agents/<name>.md` and act as that agent". Either way, give it only what its Input section lists, never this conversation. Goldfish search wide and fence nothing; merging repeats and taking findings outside the change to the user are yours.

## Routes

Each route is one file in `routes/`. "Stage" always means a stage of the `howtoai-dev` process, as `state.json` records it.

| State or request | Route |
| --- | --- |
| Stage `review` (after `dev-test`'s green run), or the user asks for a code review or a re-review | [Review](routes/review.md) |
| Stage `human-review`, and the user answers the findings or asks to go through them | [Human review](routes/human-review.md) |
| The user says a finding is wrong, or corrects a rule this skill or a goldfish applied | [Self-edit](routes/self-edit.md), then back to the route that was running |
| Stage `build` or `test` | Stop: the build or its test run is not finished; hand on to `dev-build` or `dev-test` |
| Stage `plan`, `accept`, or `tests-first` | Stop: there is nothing built to review yet |

## Core rules

- **Goldfish stay goldfish.** A reviewer brief holds only what the agent's Input section lists. When no fresh subagent can start, halt and say why: a review by the agent that holds the conversation is not a goldfish review.
- **Findings, not fixes.** This skill never changes product code; `dev-build` applies the fixes the user chooses. Reviewers never run or change code; only you run tests, through `dev-test`.
- **Numbers from scripts.** Findings are counted, scored, filtered, and ranked by `FINDINGS`; the diff and missing receipts come from `REVIEW`. Never count, relabel, or drop a finding yourself; a reply off the agent's scale goes back to that agent.
- **The user decides.** Every kept finding, and every finding outside this change, gets the user's choice: fix now, later, or decline with a reason. AUTO-FIX is a recommendation, never a decision.
- **Declined stays declined.** Declined findings are recorded and passed to later rounds, so they are not raised again.
- **Temporary tests leave.** A test you add to confirm a finding is removed at the end of the round, unless the user approves promoting it to the suite.
- **No outward actions.** No commits, pushes, pull-request comments, or posts. Tracker items (Jira, GitHub, or Azure DevOps) only for findings the user marked later, after approving the list.

## Output contract

- **Audience:** the user deciding on the findings, and the stages that read the review: `dev-build` (fix-now findings), `dev-learn` (each round), `dev-deploy` (the acceptance).
- **Deliverables:**
  - `<change folder>/review-<round>.md`, written by `FINDINGS tally --kind code` in `dev-core`'s [review](../dev-core/assets/templates/review.md) shape: the counts by impact first, then the kept findings by area, ranked by impact, each AUTO-FIX or ASK with a Your choice cell, then Test inspection, Outside this change (verified Critical and Major findings outside the change, each with a Your choice cell), and the appendix of held-back findings with their reasons. Markdown, because agents read it and git diffs it; it keeps its own fixed shape.
  - `<change folder>/raw/review-<round>/`: the diff, the changed lines, each reviewer's reply, the scores, the verdicts, and `findings.json`.
  - Fix-later work items: `wi/<n>.md` from the [work-item template](../dev-core/assets/templates/wi.md), and the tracker item when the tracker is Jira, GitHub, or Azure DevOps.
- **State:** each round as `increment.review`, each workbook use as `append.receipts`, each declined finding as `append.declined`, each new work item as `append.wi`, the acceptance as `append.approvals`, and the stage, all through `DEVCORE`.
- **Chat:** one line per step ("Pass 1: spec clean; pass 2: 3 reviewers"), the human-review question as its own message, and a short closing report: the counts, the kept findings in one line each, what was held back and why, and the next stage. No raw JSON.
- **Writes outside the change folder:** temporary test files (removed at the end of the round), and tracker items after approval.

## Verify the output

Before the closing report of a Review round:

- `review-<round>.md` exists, and its counts match the `FINDINGS tally` result.
- Test inspection has no `{filled by dev-review}` placeholder: it was filled from your inspection notes with `--inspection`.
- Every temporary test is removed (`git status` shows none of them), or its promotion is approved and recorded.
- `DEVCORE state` shows the round in `loops.review` and the stage `human-review`.

After Human review: `FINDINGS check "<change folder>/review-<round>.md"` returns `"ok": true`, every decline is in `declined`, every later finding has a work item, and the stage is `build` (fixes) or `deploy` (accepted).

## Common failures

| Symptom | Cause | Fix |
| --- | --- | --- |
| A goldfish agent name is not found | The plugin is not installed | Use the general-purpose fallback in [Before you start](#before-you-start) |
| `FINDINGS collect` refuses a reply | An impact off the agent's scale, or a duplicate ID | Send the error to that reviewer and ask for its table again; never relabel |
| A finding the change causes lands in Outside this change as "unchanged line" | Its location points at an unchanged line the change now reaches | Ask that reviewer to cite the changed line it depends on, then collect and tally again |
| The diff is empty | Nothing changed since HEAD or the fix build, or the change was already committed | Say so; review against the commit the plan names with the user's help, or stop |
| A temporary test stays in the suite | The round stopped before clean-up | Remove it, run the tests again, and note it in Test inspection |

## What it can't do

- It does not fix code; `dev-build` does.
- It cannot prove the code right: reviewers read and reason, and the tests run only what exists.
- It reviews the working tree since HEAD or the last fix; a change that was already committed needs the base named.
- Without subagents it does not review at all.
- `dev-learn` runs the learn step after each human review; this skill hands it the change folder and the round.

## Feedback

Send requested changes or reported problems to the `skill-builder` skill (`/skill-builder` in Claude Code), not by file path; the [Self-edit](routes/self-edit.md) route prepares a supplied change plan for it. Technology facts go to `dev-workbook`. If `skill-builder` is unavailable, agree the change with the user first, keep it as small as the problem needs, and check the skill afterwards.

## Skills and agents

- `dev-core` - state, settings, `findings.py`, the review and work-item templates, and the [self-edit method](../dev-core/references/self-edit.md).
- `dev-workbook` - the Pitfalls, Idioms and patterns, Security, and Performance statements, and proposals after a correction.
- `dev-test` - reruns the tests for the inspection; `dev-build` - applies the fix-now findings.
- `dev-plan` - creates tracker items for fix-later work items; `dev-learn` - the learn step after each human review.
- `grilling` - the question method for the human review.
- `skill-builder` - applies a supplied change plan from the Self-edit route.
- Agents: `goldfish-spec`, `goldfish-correctness`, `goldfish-tests`, `goldfish-security`, `goldfish-performance`, `goldfish-compliance`, `goldfish-scorer`, `goldfish-verifier`, from this plugin.
