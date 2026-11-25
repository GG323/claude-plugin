# Stage: accept

## Check before asking

Goal: the user's explicit approval, recorded in state, and the hand-on to `dev-test`.

Run [Verify the output](../SKILL.md#verify-the-output) and fix what fails. Then `DEVCORE state "<change folder>" --patch '{"stage": "accept"}'`.

## Show the plan

Show it where `plan.publish` says. `plan.md` stays the source, and approval is always asked in chat.

- **`auto`:** `artifact` when the harness can publish one (in Claude Code, the Artifact tool), else `html-file`.
- **`artifact`:** `PAGE render "<change folder>" --artifact`, publish `plan.html` as a private artifact, and give the link. When the harness cannot publish, take `html-file` and say why.
- **`html-file`:** `PAGE render "<change folder>"` (from `plan.md`, the last `plan-review-<n>.md`, and `wi/`), and give its path.
- **`markdown`:** no page; give the paths of `plan.md` and the last `plan-review-<n>.md`.
- **`tracker`:** with a `plan_item` from [split](split.md#send-to-the-tracker), give its link. Otherwise show the item (title, type `tracker.plan_item_type`, `plan.md` as description) and ask "Post this plan as a <type> in <project>?"; after a yes, create it by the tracker's route in [split](split.md#send-to-the-tracker) and record it as `plan_item`. On a failed call or a no, take `html-file` and say why.

## Ask for approval

1. In one message: the link, "Approve this plan?", and what the approval covers:
   - each open question with its recommended answer, accepted unless the user says otherwise;
   - findings left open at the round cap;
   - **found outside this change:** every finding resolved `outside:` in any round, one line per problem (with all its IDs, across rounds), its severity, its follow-up, and what happens to it: its own change later (recommended for a Blocker or Major) or left as is, accepted unless the user picks otherwise; "none" when there are none;
   - **also seen outside this change:** each bug or risk in the scope facts that this change does not fix, with its file and line;
   - **possible, not confirmed:** each ID in the tallies' `possible`, with what goes wrong; the user may have it checked, fixed, or left;
   - the tracker items created or still to create, the plan item included.
2. **Approved**, with or without conditions: set the status line to "approved on <YYYY-MM-DD>", run `DEVCORE state "<change folder>" --patch '{"append": {"approvals": {"what": "plan", "by": "user", "conditions": "<conditions, or none>", "reply": "<the user's reply, word for word>"}}, "stage": "tests-first"}'`, and render the page again. Say the next stage. Without `dev-test` installed, say so and stop; otherwise go on with `dev-test`'s Write route in the same turn, unless the user said to stop after the plan. Never ask whether to. A question that blocks nothing waits in the report as `waiting: <question>`.
3. **Changes asked:** edit a wording fix or clarification, render again, and ask again. A material change (a decision, the scope, the size, a data or contract change, a Verification criterion) goes back to [grill](grill.md) or [draft](draft.md), through [review](review.md) again (one round for Small), then here.
4. **Rejected or dropped**, on the user's word only: `DEVCORE state "<change folder>" --patch '{"stage": "dropped"}'`. The folder stays.

## Change after approval

1. An edit that alters no decision, scope, contract, or criterion (a typo, a clearer sentence) is made in place, with "Edited <YYYY-MM-DD>: <what>" under the status line. No new approval.
2. Anything else is material: `DEVCORE state "<change folder>" --patch '{"stage": "plan"}'`, say which later outputs it invalidates (tests written, work items, tracker items), rerun from the stage it affects, and return to [Ask for approval](#ask-for-approval). The earlier approval stays in the state history.
3. With a `plan_item`, after either kind of edit, show what changes in its description and ask "Update the plan item <key>?". Update only its description, only after a yes.
