# Route: human review

Done: every kept and every outside finding has the user's choice in `review-<round>.md`, each choice acted on, and the change sent to `dev-build` (fixes) or recorded as accepted for `deploy`. Entered from [Review](review.md#tally-and-hand-on), or from [SKILL.md](../SKILL.md#routes) at stage `human-review` when the user answers.

## Ask for the choices

1. Read the latest `review-<round>.md`. When the user's message already gives a choice for every kept finding and every finding outside this change (a choice given before you asked covers the other IDs under its Problems number only on the same side of the change), first ask any question waiting from the test run, then skip to [Record the choices](#record-the-choices).
2. Otherwise ask in one message, worded for the user's technical level, with the `grilling` skill's method:
   - **By problem:** ask once for each number under the review's `### Problems`, naming every ID in it. One answer covers them all and is recorded on each row, unless the user splits them. When a number holds both sides of the change, name each outside ID with its location and say that fix now would include it. The recommendation follows the most severe ID in the change; with none in the change, recommend as for Found outside this change.
   - The counts line, then each kept finding in one line: ID, impact, location, what goes wrong, and the proposed fix. When two kept findings are the same problem in other words, say so and recommend one choice for both.
   - **Found outside this change:** each finding in Outside this change in one line, with why it is outside; recommend **later** for a real problem (a work item for its own change) or **decline** with evidence. Never fix it inside this change unless the user asks.
   - Recommend **fix now** for Critical and Major findings and for AUTO-FIX findings; **later** for a real ASK finding outside this work item; **decline** only with evidence that the finding is wrong.
   - **Possible, not confirmed:** each ID the tally returned in `possible`, in one line with what goes wrong.
   - Any temporary test worth keeping, as its own yes-or-no question.
   - Any question waiting from the test run (Next in the report of the latest run that started at stage `test`), as its own question. After a yes to creating `TESTING.md`, create it with `dev-test`'s `TESTINGMD update --create` from the data file the waiting line names for that folder and fill its base part, as step 3 of the Run route's Record says; run no tests.
   - "Reply with your choice for each, for example `R1-C1 fix now, R1-T2 later, R1-P1 decline: the list never holds more than 20 items`. A decline needs a reason."
3. With no kept findings, ask one question instead, plus any waiting from the test run: accept the change as reviewed, or name what still worries you.
4. Wait for the answer. A decline with no reason, or a finding left out, is asked again; never assume a choice.

## Record the choices

1. Write each choice into the finding's **Your choice** cell in `review-<round>.md`: `fix now`, `later`, or `decline: <reason>`, as the user worded it.
2. `FINDINGS check "<change folder>/review-<round>.md"` must return `"ok": true`; fix any open or invalid cell it lists.
3. Each decline: `DEVCORE state "<change folder>" --patch '{"append": {"declined": {"finding": "<ID>: <one-line finding>", "reason": "<the user'"'"'s reason>"}}}'`.
4. When the reason says a rule or a reviewer was wrong ("that is not a bug, our workbook says…", "never flag this"), also run [Self-edit](self-edit.md) after this route. The fix-now hand-on does not wait for its answer; until then the cell reads `decline: <reason>; self-edit proposed`, and `declined` in state holds the plain reason.

## Act on the choices

1. **Later.** Write one work item per problem, naming every ID in it: `wi/<next n>.md` from `dev-core`'s work-item template, with the finding as the goal, its proposed fix as the approach, and an acceptance criterion that would have caught it. Send the items as `dev-plan`'s split stage does in "Send to the tracker": Markdown items are recorded with `append.wi` at once; Jira, GitHub, or Azure DevOps items are created only after the user approves the list.
2. **Learn.** Hand the change folder and the round to `dev-learn`. The steps below go on whatever the user answers to its proposals.
3. **Fix now.** A fix-now finding whose fix is to record a version changes a workbook, not code: run `dev-workbook`'s Record a version route for it now (its Create route first when the fix names a version workbook to make), and leave it out of the hand-on to `dev-build`. When any other finding is fix now, keep the stage at `human-review` and hand on to `dev-build`'s Fix route with this review file; that route sets the stage to `build`. After the fix, `dev-test` runs at stage `test` and the [Review](review.md) route runs again on the fix's diff. Say so in one line, then skip the rest of this section.
4. **Accepted.** With no fix-now finding left for `dev-build`, run `FINDINGS stop "<change folder>" --prefix review --clean-rounds <review.clean_rounds_to_stop> --max-rounds <review.max_rounds>` (Small: `--clean-rounds 1 --max-rounds 2`). A round with no fix-now finding ends the loop whatever `stop` says, because the user accepted what is left; report its result.
5. Only after the user's reply accepts the change, record it, quoting that reply: `DEVCORE state "<change folder>" --patch '{"stage": "deploy", "append": {"approvals": {"what": "human review, round <n>", "by": "user", "conditions": "<later and declined finding IDs, or none>", "reply": "<the user's reply, word for word>"}}}'`. Never in the step that asks, never before the answer. One reply that approves several items is one approval whose `"what"` names them all.
6. Close with the short report: the choices, the work items created, the declines and versions recorded, any self-edit proposed, the learn step's result, and the next stage.
