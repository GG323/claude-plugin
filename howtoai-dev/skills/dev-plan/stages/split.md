# Stage: split

## Contents

- [Is a split needed](#is-a-split-needed)
- [Propose the split](#propose-the-split)
- [Write the work items](#write-the-work-items)
- [Send to the tracker](#send-to-the-tracker)
- [Skills and agents](#skills-and-agents)

## Is a split needed

- **Small:** never. Skip this stage; the plan is the one unit of work.
- **Medium:** only when it does not fit one build session by [the rubric](../references/scope-rubric.md#one-session). Otherwise skip this stage.
- **Large:** always.

## Propose the split

1. Draft three splits: a default, a coarser one (fewer, bigger items), and a finer one. Rules for every work item:
   - It fits one agent session by [the rubric](../references/scope-rubric.md#one-session).
   - It can be tested on its own: its own acceptance criteria and end-to-end check, taken from the plan's Verification section.
   - Prefer vertical slices (a thin path through every layer that a user can see working) over one item per layer.
   - Its dependencies on other items are explicit, and they form no cycle.
   - At most ten items per plan. A plan that needs more is too big: propose splitting the change into two changes and ask.
2. Show the three as short tables (`#`, title, depends on, what proves it works) and ask one question, recommending the default.
3. Check coverage: every Verification criterion in `plan.md` belongs to exactly one work item. Add a "Work item" note to each criterion's row, or a list under the table.

## Write the work items

1. For each item, copy `dev-core`'s `wi.md` template to `<change folder>/wi/<n>.md` and fill every section. The **Agent prompt** must stand alone: one agent session that has not read the plan can build the item from it. It holds the context in two or three sentences, the exact files, the MUST and MUST NOT workbook statements by ID with their text, the tests to write first, the done criteria, and "Read `plan.md` sections <names> only if a detail is missing".
2. Large changes: run one `goldfish-readiness` pass on the `wi/` files, as in [review](review.md#run-a-round), saving to `raw/wi-review/` and tallying with `--kind plan --round wi --out "<change folder>/plan-review-wi.md"`. Resolve its kept findings the same way.

## Send to the tracker

Use `tracker.kind` from the settings:

- **markdown:** the `wi/` files are the tracker. Record each item: `DEVCORE state "<change folder>" --patch '{"append": {"wi": {"n": <n>, "title": "<title>", "tracker_key": "wi/<n>.md", "depends_on": [<n>, ...]}}}'`.
- **jira:** show the list (summary, issue type `tracker.jira_issue_type`, project `tracker.jira_project`, dependencies) and ask "Create these <N> Jira issues in <project>?". After a yes, create them with the Atlassian MCP's create-issue tool (search the tools for "jira create issue"), using the work item file as the description, then link the dependencies. Record each with its issue key. When the connector is missing or a call fails, keep the Markdown items, record them as `markdown`, and say what failed.
- **github:** show the list and ask "Create these <N> GitHub issues in <tracker.github_repo>?". After a yes, run `gh issue create --repo <repo> --title "<title>" --body-file "<change folder>/wi/<n>.md"` per item, add "Depends on #<number>" lines once all exist, and record each with its issue number. When `gh` is missing or not signed in, keep the Markdown items and say so.

Never edit, move, close, or comment on existing issues. Tell the user in one line where the items went.

## Skills and agents

- `dev-core` - the `wi.md` template and the work items in state.
- Agents: `goldfish-readiness` and `goldfish-scorer` for a Large split.
