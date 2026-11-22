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

Use `tracker.kind` and `plan.publish` from the settings. When `plan.publish` is `tracker` and state has no `plan_item` yet, the list starts with the plan's parent item (the plan title, type `tracker.plan_item_type`, `plan.md` as its description), and every work item is created as its child; record the parent with `DEVCORE state "<change folder>" --patch '{"plan_item": {"tracker_key": "<key>", "kind": "<tracker.kind>", "url": "<url>"}}'`. [Accept](accept.md#show-the-plan) then shows that item.

- **markdown:** the `wi/` files are the tracker. Record each item: `DEVCORE state "<change folder>" --patch '{"append": {"wi": {"n": <n>, "title": "<title>", "tracker_key": "wi/<n>.md", "depends_on": [<n>, ...]}}}'`.
- **jira:** show the list (summary, issue type `tracker.jira_issue_type`, project `tracker.jira_project`, dependencies) and ask "Create these <N> Jira issues in <project>?". After a yes, create them with the Atlassian MCP's create-issue tool (search the tools for "jira create issue"), using the work item file as the description and, with a plan item, that item as each issue's parent (the tool's parent field), then link the dependencies. Record each with its issue key. When the connector is missing or a call fails, keep the Markdown items, record them as `markdown`, and say what failed.
- **github:** show the list and ask "Create these <N> GitHub issues in <tracker.github_repo>?". After a yes, run `gh issue create --repo <repo> --title "<title>" --body-file "<change folder>/wi/<n>.md"` per item, add "Depends on #<number>" lines once all exist, and record each with its issue number. With a plan item, add a task list of the work item numbers to it once all exist. When `gh` is missing or not signed in, keep the Markdown items and say so.
- **azure-devops:** show the list (title, type `tracker.ado_work_item_type`, project `tracker.ado_project` in `tracker.ado_org`, dependencies) and ask "Create these <N> Azure DevOps work items in <project>?". After a yes, create them with the Azure DevOps MCP server's work item tools when it is connected (search the tools for "work item create"); otherwise run `az boards work-item create --org <org> --project <project> --type "<type>" --title "<title>" --description "<text>"` per item, then `az boards work-item relation add --org <org> --id <id> --relation-type parent --target-id <plan item id>` for children and `--relation-type predecessor` for dependencies. Send the description as Markdown where the tool lets you mark the field as Markdown (the work item's `multilineFieldsFormat`); otherwise convert the work item file to simple HTML (headings, lists, code blocks), because Azure Boards reads an unmarked description as HTML. Record each with its work item ID. When neither the connector nor `az` with the `azure-devops` extension signed in (`az account show`) is there, or a call fails, keep the Markdown items and say what failed.

Never edit, move, close, or comment on existing issues or work items. The one exception is the plan item this change created: this section may add its children (the GitHub task list) in the same approved step, and [Accept](accept.md#change-after-approval) may update its description after a yes. Tell the user in one line where the items went.

## Skills and agents

- `dev-core` - the `wi.md` template and the work items in state.
- Agents: `goldfish-readiness` and `goldfish-scorer` for a Large split.
