# Grilling the request

## Contents

- [What grilling is for](#what-grilling-is-for)
- [Crucial items](#crucial-items)
- [Default items](#default-items)
- [What the items mean for each kind](#what-the-items-mean-for-each-kind)
- [Safest choices](#safest-choices)
- [Run the method](#run-the-method)
- [Skills and agents](#skills-and-agents)

## What grilling is for

Grilling finds the details the target skill cannot be built without, before the plan is drafted. It works the same for a skill, a tool (subagent, hook, mod, plugin, connector workflow), and an automated process. It covers the five standard questions: from where and to where, from what and to what, the goal, how much thinking is needed, and the steps with the goal of each.

This file holds `skill-builder`'s items: what is **crucial** (changes what is built, where data goes, or what happens without the user; asked unless already answered) and what is a **default** (stated under **Assumed — tell me if wrong**, not asked). The method that asks them, the `grilling` skill, is shared with other skills. "A report" does not say whether it goes to email or into a document; "send me" does not say whether the email is sent or left as a draft. An available connector makes a good recommendation, not an answer.

## Crucial items

An item is answered only when the request or the conversation says it, or the project's files state it (for example, an existing skill or an `AGENTS.md` line). Ask them in this order, because earlier items change later ones.

| Item | Ask when | Example question |
| --- | --- | --- |
| **Goal** | Always first, when not stated | "What job should this do for you? For example, sorting files, summing up a spreadsheet, or drafting replies." |
| **Output destination** (to where), and who uses the result | The goal does not name it. Who uses it defaults to "just you" and is asked here only when the result is sent or shared | "Should the finished report go to your email as a draft, or into a document? Will anyone else read it?" |
| **Send, post, overwrite, or delete** | Any step acts outside the computer or changes existing files | "Should it send the email itself, or leave a draft for you to check and send?" |
| **Input source** (from where) | The goal does not name it | "Where does the information come from: your email, a folder on this computer, or something you paste in?" |
| **Trigger** | Only for an automation, hook, or scheduled procedure. A skill or slash command runs when the user asks, stated as assumed | "Should it run only when you ask, or on its own every week, even when you are not at the computer?" |
| **Other people's personal data** leaving the computer | The target skill itself sends or stores other people's names, contacts, or messages outside the user's computer and accounts. The user pasting such text into chat does not count | "The report will list your clients' names and emails. Is it OK for those to go to a shared Google Drive folder?" |

## Default items

| Item | Default | How it is stated |
| --- | --- | --- |
| **Input and output form** (from what, to what) | Follows the source and destination; a document-like output follows the [standardized-output defaults](../SKILL.md#output-contract) | "Reads the spreadsheet; writes a one-page summary you can open in any browser." |
| **Thinking effort** | The least that does the job: a script for fixed steps, a quick model for simple sorting, full effort only for hard judgment ([Every target skill](skill-types.md#every-target-skill) item 10) | "Counting is done by a small script; only the summary uses Claude." |
| **Steps and the goal of each** | Drafted from the goal; confirmed when the plan is approved | "1. Collect last week's invoices, so nothing is missed. 2. …" |
| **Schedule** (only for a scheduled trigger) | Monday 08:00 in the user's time zone, read from the system clock | "Runs every Monday at 8:00." |
| **Name and trigger phrases** | A short hyphenated name from the goal; triggers from the user's own words | "Named `weekly-report`; starts when you say 'make my weekly report'." |
| **Language and tone** | The language of the request; the tone of the user's examples, else plain and friendly | "Written in English, plain and friendly." |
| **Placement** | The project folder when it uses this project's files; personal (`~/.claude`) otherwise; the plugin only for the HowToAI pack | "Available in this project only." |
| **Look** (HTML pages only) | The HowToAI house design from `skill-design`, unless a client's own design is found | "Uses the HowToAI page design." |

## What the items mean for each kind

| Kind | Trigger | Output destination | Actions to ask about |
| --- | --- | --- | --- |
| Skill or slash command | When the user asks | Chat, a file, or a service | Sends, posts, file changes |
| Subagent | When the main agent hands it work | Back to the main agent | What it may change |
| Hook or "whenever X" automation | The event, for example "whenever a file is saved" | Where its message or change appears | What it blocks or changes |
| Mod | Always on, or a button | A pane, the band above the prompt, or the status line | What it writes or sends |
| Plugin | Each bundled piece's own trigger | Each piece's own destination | Who installs it, and what each piece may do |
| Connector workflow | When asked or on a schedule | The service, or chat | Read only, or also write to the account |
| Automated process | On a schedule or an event | A draft, a document, or a queue | An unattended run recommends draft only |

## Safest choices

When the user will not decide a crucial item, the method recommends its safest choice and keeps it open for approval: input pasted into the chat or a file the user attaches, never a connector; draft only, never sends; runs only when asked; saved on this computer; no personal data leaves it; existing files are copied, not overwritten.

## Run the method

Run the `grilling` skill's method with the items above: look up first, ask in rounds of at most four numbered questions with recommended answers, word them for the user's technical level, and hand over answers, defaults, and open items to [Plan](../stages/plan.md#grill-the-request). When `grilling` is unavailable, follow the same rules from this summary and say so in the plan's notes.

The Reuse decision is not part of grilling; the plan asks it.

## Skills and agents

- [skill-builder](../SKILL.md) — the rules this file applies, including **Infer, then ask**.
- [Plan](../stages/plan.md#grill-the-request) — runs the method with these items and drafts the plan from the answers.
- [skill-types.md](skill-types.md) — requirements behind the thinking-effort and side-effect items.
- `grilling` — the shared question method, including the wording by technical level.
- `skill-design` — the house design behind the **Look** default.
- No dedicated agent is required.
