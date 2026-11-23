# Stage: accept

## Contents

- [Check before asking](#check-before-asking)
- [Show the plan](#show-the-plan)
- [Ask for approval](#ask-for-approval)
- [Change after approval](#change-after-approval)
- [Skills and agents](#skills-and-agents)

## Check before asking

1. Run the checks in [Verify the output](../SKILL.md#verify-the-output). Fix what fails before going on.
2. Set the stage: `DEVCORE state "<change folder>" --patch '{"stage": "accept"}'`.

## Show the plan

1. Show the plan where `plan.publish` in the settings says. `plan.md` stays the source in every case, and approval is always asked in chat:
   - **`auto`:** `artifact` when the harness can publish one (in Claude Code, the Artifact tool), else `html-file`.
   - **`artifact`:** run `PAGE render "<change folder>" --artifact`, publish `plan.html` as a private artifact, and give the user the link. When the harness cannot publish one, take `html-file` and say why.
   - **`html-file`:** run `PAGE render "<change folder>"` for a full HTML file from `plan.md`, the last `plan-review-<n>.md`, and the `wi/` files, and give the user its path.
   - **`markdown`:** render no page; give the user the path of `plan.md` and of the last `plan-review-<n>.md`.
   - **`tracker`:** when state has a `plan_item` (made in [split](split.md#send-to-the-tracker)), give the user its link. Otherwise show the item (title, type `tracker.plan_item_type`, `plan.md` as its description) and ask "Post this plan as a <type> in <project>?"; after a yes, create it with the tracker's own route in [split](split.md#send-to-the-tracker) and record it as `plan_item`. When the tracker call fails or the user says no, take `html-file` and say why.

## Ask for approval

1. Ask in chat, in one message: the link, then "Approve this plan?", followed by what the approval covers:
   - each open question, with its recommended answer, which the approval accepts unless the user says otherwise;
   - any findings left open at the round cap;
   - **found outside this change:** every finding resolved `outside:` in any plan-review round, one line per problem (with every ID in it, across rounds too) with its severity and follow-up, and what happens to it - planned later as its own change (recommended for a Blocker or Major) or left as is - which the approval accepts unless the user picks otherwise; "none" when there are none;
   - **also seen outside this change:** each bug or risk among the explorers' scope facts that this change does not fix, one line each with its file and line;
   - **possible, not confirmed:** each ID the rounds' tally returned in `possible`, one line each with what goes wrong; the user may have it checked, fixed, or left;
   - the tracker items already created, or still to create, including the plan item.
2. **Approved** (with or without conditions): set the status line in `plan.md` to "approved on <YYYY-MM-DD>", then run `DEVCORE state "<change folder>" --patch '{"append": {"approvals": {"what": "plan", "by": "user", "conditions": "<conditions, or none>"}}, "stage": "tests-first"}'` and render the page again. Tell the user the next stage: `dev-test` writes the tests first from the Verification section. When `dev-test` is not installed, say so and stop here. Otherwise go on with `dev-test`'s Write route in the same turn, unless the user said to stop after the plan; a question that blocks nothing waits in the report as `waiting: <question>`. Never ask whether to.
3. **Changes asked:** a wording fix or a clarification is edited in `plan.md`, the page is rendered again, and the question asked again. A material change (a decision, the scope, the size, a data or contract change, or a Verification criterion) goes back to the stage it affects ([grill](grill.md) or [draft](draft.md)), then through [review](review.md) again (one round for Small), then here.
4. **Rejected or dropped:** on the user's word only, run `DEVCORE state "<change folder>" --patch '{"stage": "dropped"}'`. The folder stays.

## Change after approval

When the user changes an approved plan:

1. A change that alters no decision, scope, contract, or criterion (a typo, a clearer sentence) is edited in place, with a line under the status line: "Edited <YYYY-MM-DD>: <what>". No new approval.
2. Anything else is material: run `DEVCORE state "<change folder>" --patch '{"stage": "plan"}'`, say which later outputs it invalidates (tests already written, work items, tracker items), rerun from the stage it affects, and come back to [Ask for approval](#ask-for-approval). The earlier approval stays in the state history.
3. With a `plan_item`, after either kind of edit, show what changes in its description and ask "Update the plan item <key>?"; update only its description, and only after a yes. It is the one existing tracker item a dev skill may edit.

## Skills and agents

- `dev-core` - the stage and the approval in state.
- `dev-test` - the next stage.
- No agents are used in this stage.
