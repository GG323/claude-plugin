# Stage: grill

## Find the open decisions

Goal: every crucial decision this change needs is answered by the user or by a stated source, and recorded in `questions.md`.

- Walk [the items](../references/grill-items.md) layer by layer and keep those the change touches.
- An item is settled, not open, when a scope fact, a MUST or MUST NOT statement, the settings, a lesson, or a convention the code follows everywhere the explorers looked answers it. State it as a default with that source ("Logging: Serilog, as in `src/Api/Program.cs:14`").
- Ask the crucial open items. Take the rest at their default under **Assumed — tell me if wrong**. A Small change often needs no question.
- Large: leave the overall architecture to the architect proposals in [draft](draft.md); ask only what the architects need first (a constraint such as "must run on the existing database").

## Ask top-down

- Use the `grilling` method in layer order: at most four numbered questions per round, one layer per round unless a layer has only one or two. Each recommendation names its source and evidence ("Recommended: Testcontainers for the database tests (tool: `dotnet.testing.004`)").
- When the user will not decide, use the item's safest choice and keep it as an open question for the approval.
- Stop when no crucial item is open, or a round changed nothing. Agreed terms go into the plan's Decisions table.

## Record

`questions.md` has one row per question in the order asked: round, number, layer, question, recommended answer, source and evidence, and the answer (the user's words, or "recommended"). Every stated default goes in its Stated defaults table. Later questions (the architecture in draft, a review finding only the user can decide, the split) join the same table, continuing the round numbering. Say nothing beyond the rounds themselves.
