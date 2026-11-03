---
name: meeting-notes
description: Turns a raw meeting transcript or rough notes into concise, structured meeting notes with decisions and action items. Use when asked to summarize a meeting, write up meeting notes or minutes, or extract action items from a transcript.
---

# Meeting notes

## Contents

- [Before you start](#before-you-start)
- [Workflow](#workflow)
- [Output](#output)
- [Verify the output](#verify-the-output)
- [Common failures](#common-failures)
- [What it can't do](#what-it-cant-do)
- [Feedback](#feedback)
- [Skills and agents](#skills-and-agents)

## Before you start

- Accept a transcript or notes as pasted text, an attached file, or a file path. A `.docx` input is read with the `docx` skill and a `.pdf` with the `pdf` skill, because they handle those formats reliably.
- If no transcript or notes are provided, ask for them instead of guessing what the meeting covered.
- For a transcript too long to read in one pass, work through it in parts and tell the user you did.

## Workflow

1. Identify attendees, topics, decisions, and action items. Do not invent owners or due dates, because a wrong owner is worse than a missing one; mark missing ones as "unassigned" or "no date".
2. Write the notes in the format in [Output](#output). Keep wording neutral and close to what was said.
3. If anything is ambiguous (for example, whether something was decided), list it under **Open questions** instead of guessing.

## Output

- **Deliverable:** Markdown meeting notes returned in chat, in exactly the structure below and nothing else, even where workspace rules ask for contents lists, so every set of notes reads the same. Save them to a file only when the user asks for one: a self-contained HTML file with the same structure, unless the user names another format.
- **Audience:** the meeting's attendees and anyone who missed it, so the notes must make sense without the transcript.
- **Structure:** title and date, attendees, summary (3–5 bullets), decisions, action items as a table (task, owner, due date), open questions.
- **Success check:** every action item and decision traces to the source; nothing is invented.
- **Report:** after the notes, one line saying how many decisions and action items were found and whether any open questions remain.

## Verify the output

Before delivery, reread the source once more and confirm that each decision and action item appears in it, and that no item from the source is missing from the notes.

## Common failures

| Symptom | Cause | Fix |
| --- | --- | --- |
| An action item has an owner nobody named | The owner was inferred from context | Mark it "unassigned" and add it to open questions |
| A discussion point is listed as a decision | Tentative wording was read as agreement | Move it to open questions |

## What it can't do

- It cannot tell who said what when the transcript has no speaker labels; it says so and leaves attribution out.
- It runs anywhere it can read the user's input. On platforms without file access it returns the notes in chat only and says they were not saved.
- It does not send the notes anywhere. If the user wants them emailed, it offers to prepare a draft with the user's email connector.

## Feedback

If the user asks to change how this skill works or reports a problem with it, use the `skill-builder` skill (for example, `/skill-builder`) to plan and apply the change. If `skill-builder` is unavailable, agree the change with the user first, keep it as small as the problem needs, and check the skill afterwards.

## Skills and agents

- `skill-builder` — builds and maintains this skill; send changes there, as described in [Feedback](#feedback).
- `docx` and `pdf` — read Word and PDF inputs.
