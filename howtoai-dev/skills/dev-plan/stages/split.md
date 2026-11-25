# Stage: split

## Is a split needed

Small: never; skip this stage. Medium: only when it does not fit [one session](../references/scope-rubric.md#one-session); otherwise skip. Large: always.

## Propose the split

Goal: standalone work items, each buildable and testable in one agent session.

1. Draft three splits: a default, a coarser, and a finer one. Every item fits [one session](../references/scope-rubric.md#one-session), has its own acceptance criteria and end-to-end check from Verification, prefers a vertical slice over one layer, and names its dependencies, with no cycle. At most ten items; a plan that needs more is two changes, so propose that and ask.
2. Show the three as short tables (`#`, title, depends on, what proves it works) and ask one question, recommending the default.
3. Every Verification criterion belongs to exactly one work item; note it on the criterion's row or in a list under the table.

## Write the work items

1. Copy `dev-core`'s `wi.md` template to `<change folder>/wi/<n>.md` per item and fill every section. The **Agent prompt** stands alone for a session that never read the plan: two or three sentences of context, the exact files, the MUST and MUST NOT statements by ID with their text, the tests to write first, the done criteria, and "Read `plan.md` sections <names> only if a detail is missing".
2. Large: one `goldfish-readiness` pass on the `wi/` files, briefed as in [review](review.md#run-a-round), saved to `raw/wi-review/`, scored by `goldfish-scorer` as in [review](review.md#score-and-verify), tallied with `--kind plan --round wi --out "<change folder>/plan-review-wi.md"`, and resolved the same way.

## Send to the tracker

Use `tracker.kind` and `plan.publish`. When `plan.publish` is `tracker` and state has no `plan_item`, the list starts with the plan's parent item (the plan title, type `tracker.plan_item_type`, `plan.md` as description) and every work item is its child; record it with `DEVCORE state "<change folder>" --patch '{"plan_item": {"tracker_key": "<key>", "kind": "<tracker.kind>", "url": "<url>"}}'`.

Outside `markdown`, show the list first and create nothing before the user's yes. Record each item with its key. When the connector or CLI is missing or not signed in, or a call fails, keep the Markdown items, record them as `markdown`, say what failed, and ask whether to retry later.

- **markdown:** the `wi/` files are the tracker. Record each: `DEVCORE state "<change folder>" --patch '{"append": {"wi": {"n": <n>, "title": "<title>", "tracker_key": "wi/<n>.md", "depends_on": [<n>, ...]}}}'`.
- **jira:** show summary, issue type `tracker.jira_issue_type`, project `tracker.jira_project`, and dependencies; ask "Create these <N> Jira issues in <project>?". Create with the Atlassian MCP's create-issue tool (search the tools for "jira create issue"), the work item file as description and the plan item, when there is one, as parent; then link the dependencies.
- **github:** ask "Create these <N> GitHub issues in <tracker.github_repo>?". Per item `gh issue create --repo <repo> --title "<title>" --body-file "<change folder>/wi/<n>.md"`; once all exist, add "Depends on #<number>" lines and, with a plan item, a task list of the work item numbers on it.
- **azure-devops:** show title, type `tracker.ado_work_item_type`, project `tracker.ado_project` in `tracker.ado_org`, and dependencies; ask "Create these <N> Azure DevOps work items in <project>?". Use the Azure DevOps MCP server's work item tools when connected (search "work item create"); otherwise `az boards work-item create --org <org> --project <project> --type "<type>" --title "<title>" --description "<text>"` per item, then `az boards work-item relation add --org <org> --id <id> --relation-type parent --target-id <plan item id>` for children and `--relation-type predecessor` for dependencies. The `az` path needs the `azure-devops` extension, signed in (`az account show`). Send the description as Markdown where the field can be marked so (`multilineFieldsFormat`); otherwise as simple HTML (headings, lists, code blocks), because Azure Boards reads an unmarked description as HTML.

Never edit, move, close, or comment on existing issues or work items. The one exception is the plan item this change created: its children here, in the same approved step, and its description in [Accept](accept.md#change-after-approval) after a yes. Tell the user in one line where the items went.
