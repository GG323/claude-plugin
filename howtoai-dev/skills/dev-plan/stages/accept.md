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

1. Render the page from `plan.md`, the last `plan-review-<n>.md`, and the `wi/` files into `<change folder>/plan.html`:
   - **The harness can publish an artifact** (in Claude Code, the Artifact tool): run `PAGE render "<change folder>" --artifact`, publish `plan.html` as a private artifact, and give the user the link.
   - **It cannot:** run `PAGE render "<change folder>"` for a full HTML file and give the user its path.

## Ask for approval

1. Ask in chat, in one message: the link, then "Approve this plan?", followed by what the approval covers:
   - each open question, with its recommended answer, which the approval accepts unless the user says otherwise;
   - any findings left open at the round cap;
   - **found outside this change:** every finding resolved `outside:` in any plan-review round, one line each with its severity and follow-up, and what happens to it - planned later as its own change (recommended for a Blocker or Major) or left as is - which the approval accepts unless the user picks otherwise; "none" when there are none;
   - the tracker issues already created, or still to create.
2. **Approved** (with or without conditions): set the status line in `plan.md` to "approved on <YYYY-MM-DD>", then run `DEVCORE state "<change folder>" --patch '{"append": {"approvals": {"what": "plan", "by": "user", "conditions": "<conditions, or none>"}}, "stage": "tests-first"}'` and render the page again. Tell the user the next stage: `dev-test` writes the tests first from the Verification section. When `dev-test` is not installed, say so and stop here.
3. **Changes asked:** a wording fix or a clarification is edited in `plan.md`, the page is rendered again, and the question asked again. A material change (a decision, the scope, the size, a data or contract change, or a Verification criterion) goes back to the stage it affects ([grill](grill.md) or [draft](draft.md)), then through [review](review.md) again (one round for Small), then here.
4. **Rejected or dropped:** on the user's word only, run `DEVCORE state "<change folder>" --patch '{"stage": "dropped"}'`. The folder stays.

## Change after approval

When the user changes an approved plan:

1. A change that alters no decision, scope, contract, or criterion (a typo, a clearer sentence) is edited in place, with a line under the status line: "Edited <YYYY-MM-DD>: <what>". No new approval.
2. Anything else is material: run `DEVCORE state "<change folder>" --patch '{"stage": "plan"}'`, say which later outputs it invalidates (tests already written, work items, tracker issues), rerun from the stage it affects, and come back to [Ask for approval](#ask-for-approval). The earlier approval stays in the state history.

## Skills and agents

- `dev-core` - the stage and the approval in state.
- `dev-test` - the next stage.
- No agents are used in this stage.
