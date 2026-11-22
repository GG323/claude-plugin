# Route: human review

## Contents

- [Ask for the choices](#ask-for-the-choices)
- [Record the choices](#record-the-choices)
- [Act on the choices](#act-on-the-choices)
- [Skills and agents](#skills-and-agents)

## Ask for the choices

Entered from the [Review](review.md#tally-and-hand-on) route, or from [SKILL.md](../SKILL.md#routes) at stage `human-review` when the user answers.

1. Read the latest `review-<round>.md`. When the user's message already gives a choice for every kept finding and every finding outside this change, skip to [Record the choices](#record-the-choices).
2. Otherwise ask in one message, worded for the user's technical level, with the `grilling` skill's method:
   - The counts line, then each kept finding in one line: ID, impact, location, what goes wrong, and the proposed fix. When two kept findings are the same problem in other words, say so and recommend one choice for both.
   - **Found outside this change:** each finding in the review's Outside this change section in one line, with why it is outside; recommend **later** for a real problem (it becomes a work item for its own change) or **decline** with evidence. Never fix it inside this change unless the user asks.
   - Your recommendation for each: **fix now** for Critical and Major findings and for AUTO-FIX findings; **later** for an ASK finding that is real but outside this work item; **decline** only with evidence that the finding is wrong.
   - Any temporary test worth keeping, as its own yes-or-no question.
   - "Reply with your choice for each, for example `R1-C1 fix now, R1-T2 later, R1-P1 decline: the list never holds more than 20 items`. A decline needs a reason."
3. With no kept findings, ask one question instead: accept the change as reviewed, or name what still worries you.
4. Wait for the answer. A choice with no reason for a decline, or a finding left out, is asked again; never assume a choice.

## Record the choices

1. Write each choice into the finding's **Your choice** cell in `review-<round>.md`: `fix now`, `later`, or `decline: <reason>`, as the user worded it.
2. `FINDINGS check "<change folder>/review-<round>.md"` must return `"ok": true`; fix any open or invalid cell it lists.
3. Each decline: `DEVCORE state "<change folder>" --patch '{"append": {"declined": {"finding": "<ID>: <one-line finding>", "reason": "<the user'"'"'s reason>"}}}'`. Later rounds pass these to the reviewers, so they are not raised again.
4. When the user's reason says a rule or a reviewer was wrong ("that is not a bug, our workbook says…", "never flag this"), also run the [Self-edit](self-edit.md) route after this one. The fix-now hand-on below does not wait for the answer to its proposal; until the user answers, the cell reads `decline: <reason>; self-edit proposed`, and `declined` in state holds the plain reason.

## Act on the choices

1. **Later.** Write each later finding as a work item: `wi/<next n>.md` from `dev-core`'s [work-item template](../../dev-core/assets/templates/wi.md), with the finding as the goal, its proposed fix as the approach, and an acceptance criterion that would have caught it. Send the items to the tracker as `dev-plan`'s split stage does in its "Send to the tracker" section: Markdown items are recorded with `append.wi` at once; Jira, GitHub, or Azure DevOps items are created only after the user approves the list.
2. **Learn.** Hand the change folder and the round to `dev-learn` for the learn step. The steps below go on whatever the user answers to its proposals, so it never holds up the fix or the deploy.
3. **Fix now.** A fix-now finding whose fix is to record a version with `dev-workbook` changes a workbook, not code. Run `dev-workbook`'s Record a version route for it now (and its Create route first when the fix names a version workbook to make), and leave it out of the hand-on to `dev-build`. When at least one other finding is fix now, keep the stage at `human-review` and hand on to `dev-build`'s Fix route with this review file; that route sets the stage to `build` itself. After the fix, `dev-test` runs at stage `test` and this skill runs its [Review](review.md) route again on the fix's diff. Say so in one line, then skip the rest of this section.
4. **Accepted.** With no fix-now finding left for `dev-build`, check the loop: `FINDINGS stop "<change folder>" --prefix review --clean-rounds <review.clean_rounds_to_stop> --max-rounds <review.max_rounds>` (for a Small change `--clean-rounds 1 --max-rounds 2`). A round with no fix-now finding ends the loop whatever `stop` says, because the user has accepted what is left; report its result in the closing report.
5. Record the acceptance: `DEVCORE state "<change folder>" --patch '{"stage": "deploy", "append": {"approvals": {"what": "human review, round <n>", "by": "user", "conditions": "<later and declined finding IDs, or none>"}}}'`.
6. Close with the short report: the choices, the work items created, the declines recorded, the versions recorded, any self-edit proposed, the learn step's result, and the next stage.

## Skills and agents

- [SKILL.md](../SKILL.md) - the rules; [Review](review.md) and [Self-edit](self-edit.md) - the routes this one leads to.
- `dev-core` - `findings.py check` and `stop`, state, and the work-item template.
- `dev-plan` - its split stage's "Send to the tracker" section; `dev-build` - the Fix route; `dev-workbook` - its Record a version and Create routes, for fix-now version findings.
- `grilling` - the question method.
- No agents are used.
