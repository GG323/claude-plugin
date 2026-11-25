---
name: grilling
description: The shared method for asking the user the decisions a task cannot go ahead without - look everything up first, then ask in short rounds of at most four numbered questions, each with a recommended answer, state the rest as defaults, word it for the user's technical level, and stop when no crucial item is open. The calling skill supplies its own list of crucial and default items; this skill supplies only the method. Used by skill-builder (building a skill or tool) and by the howtoai-dev skills (planning software, dev setup). Use when another skill says to grill, interview, or question the user with the grilling method, or when the user asks to be grilled on a plan or decision.
---

# Grilling

## Contents

- [What it does](#what-it-does)
- [What the caller supplies](#what-the-caller-supplies)
- [Look up first](#look-up-first)
- [Ask in rounds](#ask-in-rounds)
- [Agreed terms](#agreed-terms)
- [Word it for the user](#word-it-for-the-user)
- [Stop and hand over](#stop-and-hand-over)
- [Output contract](#output-contract)
- [Common failures](#common-failures)
- [Feedback](#feedback)

## What it does

Grilling finds the decisions a task cannot be done well without, before anything is planned or built, while asking the user as little as possible. It is a method, not a checklist: what counts as crucial depends on the task, so the calling skill brings its own items. The method is the same whether the task is a skill, a tool, a procedure, or a software change.

Every item is either **crucial** or a **default**:

- A **crucial** item changes what is built, where data goes, or what happens without the user. It is asked unless the user, the conversation, or the project's files already answer it. Never fill one with a guess, a common choice, or what similar work did.
- A **default** item has a sensible answer. It is stated under **Assumed — tell me if wrong**, not asked.

## What the caller supplies

The calling skill (or, when the user asks directly, the conversation) gives:

1. **The items:** each crucial item with when to ask it and an example question, in the order earlier answers change later ones; and each default item with its default. `skill-builder` keeps its items in its `references/grilling.md`; `dev-plan` keeps its layers (architecture, tools and services, languages and frameworks, details) in its own files.
2. **The safest choice** for each crucial item, used when the user will not decide (for example, "draft only, never sends").
3. **Where the answers go:** a plan, a questions record, or a settings preview.

Without items, ask the user what is being decided, then treat each open decision as a crucial item.

## Look up first

Before each round, find out everything a lookup can answer: the conversation, the project's instructions (`AGENTS.md`, `CLAUDE.md`), existing files, folders, and code, available skills and connectors (their descriptions only; no private data before the user approves), the project's stack, and the date from the system clock. When a lookup is large and the harness can start a fresh read-only subagent, use one. Only questions that depend on a running lookup wait for it.

Ask the user only for decisions. Never ask what a lookup can answer, such as whether a folder exists, which version is installed, or which connectors are on. An answered item is said back as "From your request: …" or "From `<file>`: …", so the user can correct it.

## Ask in rounds

1. **Map the items.** List the crucial items still open. An item that depends on another open item waits for a later round. When nothing names the task at all, the first round asks only the goal, because every other item depends on it.
2. **Ask at most four numbered questions per round**, in the caller's order. Each has a bold title, one plain sentence, and a recommended answer with its reason:

   > 1. **Where should the report go?** As a draft email to you, or saved as a document? *Recommended: a draft email to you, so nothing goes out without you.*

   Give a safe recommendation whenever one exists, and name its source when the caller asks for one (the user's earlier answer, the project's files, a workbook statement, industry practice, or general reasoning). Only when there is nothing to base one on, give two or three varied examples instead and say so.
3. **End the round** with "Reply 'yes' to take the recommended answers, or answer by number." when every question has a recommendation. When some have none, name them: "'yes' takes the recommendations; question 2 still needs your answer." From the first round where the task is known, add **Assumed — tell me if wrong:** with the default items that round settles, one line each.
4. **Wait for the answers.** Then recompute: an answer can open a new crucial item (a data source with clients' emails opens a personal-data item; "post it to Slack" opens a send item).
5. **Repeat** until no crucial item is open. Stop earlier when two rounds in a row change nothing in the plan: take a position, state it as a recommendation, and move on.

If the user skips a crucial item or says "just decide", ask it once more in one line with why it matters. If it is still open, recommend the caller's safest choice and keep it as an open question for the approval step; the approval must cover it.

For a change to existing work, grill only the items the change touches; the existing files answer the rest.

## Agreed terms

When the user and the task use a word in different senses (a "customer" that is an account in one place and a person in another), propose one definition in a question, and once agreed, use only that word for that meaning from then on. Hand the agreed terms to the caller, which records them where it keeps decisions, so later work does not drift.

## Word it for the user

Read the `# User settings (command-pane)` block in the system prompt, if there is one. Its first sentence gives the technical level:

| Block says | Level | Wording |
| --- | --- | --- |
| "The user is not technical." | nontechnical | Everyday words; no file paths, commands, or terms such as frontmatter, hook, or MCP; examples instead of terms ("a link to your Gmail", not "a Gmail connector"); one idea per question. |
| "The user is somewhat technical: …" | some technical | Light jargon, uncommon terms explained in a few words; file names are fine. |
| "The user is a developer." | developer | Concise and technical; paths and terms are fine. |

Without the block, infer the level from how the user writes and from the project. When unsure, use nontechnical wording.

## Stop and hand over

Stop when no crucial item is open and every default is stated. Do not ask for a separate confirmation: the user confirms everything when they approve the caller's plan or preview. Hand over:

- Each answer, as an item for the caller's plan.
- Each default, still marked **Assumed — tell me if wrong**.
- Each crucial item left open, as a numbered question with its safest recommendation.
- The agreed terms.

## Output contract

- **Deliverable:** the rounds of questions in chat, and the hand-over list above, returned to the calling skill (or, when the user asked directly, a short summary of the decisions in chat).
- **Writes:** nothing. The caller decides where answers are recorded.

## Common failures

| Symptom | Cause | Fix |
| --- | --- | --- |
| The user is asked something a file answers | The lookup was skipped or too shallow | Look up first, with a subagent for large lookups |
| A crucial item was filled with a guess | Treated as a default | Ask it; only the caller's default items may be assumed |
| Long rounds of questions | More than four per round, or items asked before what they depend on | Four at most; dependent items wait |
| The same question asked again at approval | The hand-over dropped it | Hand over open items as numbered questions; never re-ask answered ones |

## Feedback

Send requested changes or reported problems to the `skill-builder` skill (`/skill-builder` in Claude Code), not by file path. If `skill-builder` is unavailable, agree the change with the user first, keep it as small as the problem needs, and check the skill afterwards.
