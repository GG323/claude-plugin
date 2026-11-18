---
name: brain-dump
description: Turns a brain dump (loose thoughts, ideas, tasks, voice-note text) into clean plan items and files each one under the right project and section of that project's plan doc, usually the workspace's TODO.md. Reads the workspace's project map in AGENTS.md or CLAUDE.md and the existing plan first, so items land next to related work, merge with duplicates, and match the plan's wording. Shows a placement preview and writes only after approval; asks when an item's project is not stated or is unclear. Use when the user says "brain dump", "braindump", "dump my thoughts", "add these ideas to the TODO", "put this in the plan", or pastes a messy list of ideas to sort into the plan.
compatibility: Needs file read and edit access to the workspace (Claude Code, Claude desktop Code tab, Cowork with a folder). Elsewhere it returns the sorted items in chat only.
---

# Brain dump

## Contents

- [Before you start](#before-you-start)
- [Workflow](#workflow)
  - [Read the context](#read-the-context)
  - [Sort the dump](#sort-the-dump)
  - [Preview and ask](#preview-and-ask)
  - [Write the plan docs](#write-the-plan-docs)
- [Output](#output)
- [Verify the output](#verify-the-output)
- [Common failures](#common-failures)
- [What it can't do](#what-it-cant-do)
- [Feedback](#feedback)
- [Skills and agents](#skills-and-agents)

## Before you start

- **Input:** the brain dump as pasted text, dictated text, or a file path (a `.docx` is read with the `docx` skill). If there is no dump in the request, ask for it.
- **Project map:** read the workspace's `AGENTS.md` (or `CLAUDE.md`), looking for a projects table or Project section that names each project, its scope, and its plan doc. With no map, take the workspace's `TODO.md` as the only plan doc and the Project section as its scope, and say so in the preview. With no `TODO.md` either, ask where the plan should live before writing anything.
- **Project named in the request:** if the user names a project ("for SEO: …"), every item goes to it unless an item plainly says otherwise.
- **Large dumps:** above about 40 items, sort them all but show the preview grouped by project, so it stays readable.

## Workflow

### Read the context

1. Read each plan doc the map names that this dump could touch, in full: its sections, subsections, wording style (for example `Next:`, `Open:`, `Possible:`, `Test:` prefixes), and existing items. Items should land next to related work, so the existing plan is the main guide to placement.
2. Note the plan doc's own conventions: title, `## Contents` list, and a last `Skills and agents` section, if it has them. New sections go before that last section. If the plan doc already breaks them (for example a section after `Skills and agents`, or a heading missing from `## Contents`), list that under **Plan doc issues** in the preview and offer to fix it as its own change; do not fix it silently, because the user may have left it there on purpose.

### Sort the dump

1. Split the dump into separate items: one idea or task each. Keep the user's meaning; fix spelling and grammar, and make each item short and actionable in the plan's own style. Do not add detail, owners, or dates that the user did not give, because a made-up detail reads like a decision. Drop chat-export noise such as `[23:56, 11/7/2026] Name:` prefixes, but use their times in the next step.
2. Link items to their neighbours. A dump is written over time, so an item often continues, answers, or qualifies the one just before or after it: a label followed by its link ("Best of plugins", then a video URL), a follow-up message a minute later, an answer to an open question raised earlier in the dump, or a "Regarding X" note about an existing plan item. Read the items in order, with their timestamps where given; messages close in time are more likely to belong together than ones hours apart. Then:
   - Merge linked items into one plan item, or place them next to each other, and keep what links them (for example "Idea: …" under the open question it answers).
   - Treat a "Regarding X" note, or an item that answers an existing plan item, as a change to that plan item, not a new one.
   - When it is unclear whether two neighbours belong together, show them linked in the preview with a question, because a wrong split loses meaning and a wrong merge hides an item.
3. Give each item a project, using the map's scope rules and the existing plan. Rate it:
   - **clear** - the item names the project, or its subject plainly matches one project's scope or an existing section.
   - **unclear** - it fits more than one project, or none. Never guess these; they go to the question in [Preview and ask](#preview-and-ask).
4. Give each clear item a place: an existing section or subsection, or a new section when nothing fits (name it in the plan's style).
5. Check for duplicates: an item that repeats an existing one is merged into it (adding only what is new) or dropped as already planned, never added twice.
6. An item that says something in the plan is done or no longer wanted is a change, not an addition. List it as such; do not delete anything without the user's approval.

### Preview and ask

Show the preview in [Output](#output) and, in the same message, ask:

- For each unclear item: which project it belongs to, with your best guess first.
- Approval to write the listed changes, including any new section, any new plan doc file, and any change or removal of an existing item.

Write nothing until the user answers. If they change a placement, update the preview and ask again only when the change is large; otherwise apply it.

### Write the plan docs

1. Apply only the approved changes, editing each plan doc in place. A git-tracked or OneDrive file keeps its history, so no backup copy is needed; for a file in neither, copy it to `<name>.bak` first.
2. Add each item as a bullet under its section, after related items. Keep the plan doc's conventions: when a new section is added, add it to the `## Contents` list at the matching level; keep heading levels nested without skips.
3. A plan doc that does not exist yet (a separate project's `TODO.md` the map says is created on first use) is created only with approval, with a title, a `## Contents` list, the new sections, and a last `## Skills and agents` section saying none apply, when the workspace's Markdown conventions ask for that shape.
4. Never write a separate project's items into another project's plan doc, because mixed plans are hard to untangle later.

## Output

- **Deliverable:** the updated plan doc or docs, edited in place.
- **Preview (before writing):** a Markdown table in chat, in this shape so every run reads the same:

  | # | Item | Project | Where | Action |
  | --- | --- | --- | --- | --- |
  | 1 | short item text | project name | plan doc › section | add / merge / new section / change / already planned |

  Then a short list headed **Unclear** with each unclear item and the question for it, or "Unclear: none". Add **Plan doc issues** only when [Read the context](#read-the-context) found any.
- **Report (after writing):** one short block: items added, merged, and skipped as already planned, per plan doc; new sections; anything not written and why. Link each changed plan doc.

## Verify the output

Before the report, reread each changed plan doc: every approved item appears once, in its approved section; the `## Contents` list matches the headings; no existing item was lost or changed without approval; and no item from the dump is missing from the preview.

## Common failures

| Symptom | Cause | Fix |
| --- | --- | --- |
| A link or a follow-up is filed apart from the item it belongs to | Items were sorted one by one, without reading their neighbours | Read the dump in order with its timestamps and merge or group linked items before placing them |
| An item lands in the wrong project | Its subject touched two scopes, and it was rated clear | Rate it unclear and ask; add the scope rule to the project map if the user wants it to stick |
| The same idea appears twice in the plan | The existing item used different words | Search the plan for the idea's key terms, not the exact wording, before adding |
| A new section is missing from Contents | The heading was added but the list was not updated | Update the `## Contents` list in the same edit |
| A done item is removed, but its sub-bullets still refer to it | The sub-bullets were dropped or left unchanged | Reword each sub-bullet so it stands alone (for example an `Open:` decision), and show that in the preview |
| The item reads more decided than the user said | Detail was added while cleaning up the wording | Keep only what the dump says; use `Possible:` or `Open:` for tentative ideas when the plan uses them |

## What it can't do

- It does not do the planned work, research the items, or prioritize them; it files them. It can hand a single item to the right skill afterwards if the user asks (for example `skill-builder` for a new skill idea).
- It does not write to task tools such as Jira, Linear, or Notion; it uses the workspace's Markdown plan docs only.
- Without file access it returns the preview table in chat and says nothing was saved.

## Feedback

If the user asks to change how this skill works or reports a problem with it, use the `skill-builder` skill (for example, `/skill-builder`) to plan and apply the change. If `skill-builder` is unavailable, agree the change with the user first, keep it as small as the problem needs, and check the skill afterwards.

## Skills and agents

- `skill-builder` - builds and maintains this skill; send changes there, as described in [Feedback](#feedback).
- `docx` - reads a brain dump given as a Word file.
- No agents are required.
