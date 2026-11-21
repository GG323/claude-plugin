# Stage: grill

## Contents

- [Find the open decisions](#find-the-open-decisions)
- [Ask top-down](#ask-top-down)
- [Record](#record)
- [Skills and agents](#skills-and-agents)

## Find the open decisions

1. Walk [the items](../references/grill-items.md) layer by layer: architecture, tools and services, languages and frameworks, details. For each item, decide whether this change touches it.
2. An item is answered, not open, when one of these settles it: a scope fact, a MUST or MUST NOT workbook statement, the dev settings, a lesson, or a convention the code follows in every place the explorers looked. Write it down as a stated default with that source (for example "Logging: Serilog, as in `src/Api/Program.cs:14`").
3. The rest are open. Keep the crucial ones as questions; take the default ones at their default, stated under **Assumed — tell me if wrong**. For a Small change most layers are usually unchanged: state them as defaults, and ask only what is still crucial, often nothing.
4. For a Large change, leave the overall architecture open here: the three architect proposals in [draft](draft.md) put it to the user. Ask only what the architects need first (for example, a constraint such as "must run on the existing database").

## Ask top-down

1. Run the `grilling` skill's method with these items in layer order, at most four numbered questions per round, one layer per round unless a layer has only one or two questions. Each recommendation names its source (user, project, tool with the workbook ID, industry, or general) and its evidence, for example "Recommended: Testcontainers for the database tests (tool: `dotnet.testing.004`)".
2. Use the safest choice from [the items](../references/grill-items.md) when the user will not decide, and keep that item as an open question for the approval.
3. Stop when no crucial item is open, or when a round's answers changed nothing in the plan. Agreed terms go into the plan's Decisions table.

## Record

1. Fill `questions.md`: one row per question, in the order asked, with round, number, layer, question, recommended answer, source and evidence, and the answer (the user's words, or "recommended" when they accepted it). Write every stated default into its Stated defaults table. Questions asked later (the architecture choice in draft, a finding only the user can decide in review, the split choice) are added to the same table, continuing the round numbering, so the record stays in the order asked.
2. Tell the user nothing more than the rounds themselves; the plan shows the result.

## Skills and agents

- `grilling` - the question method.
- No agents are used in this stage.
