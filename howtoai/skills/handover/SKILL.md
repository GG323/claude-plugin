---
name: handover
description: Hands the current session's work over to a fresh session. Writes a handover of the latest work and its current state (materials, what was done, working documents, next steps), following any instructions on what context to include, focus on, or leave out, then proposes a new session in the same folder with the handover as its first message, which detaches itself so it never reports back. Use when the user presses command-pane's Handover button, types /handover with or without instructions, or asks to hand over, refresh, or move this work to a new session, for example because the context is filling up or to carry over only part of the work.
argument-hint: "[what to include, focus on, or leave out]"
compatibility: Proposing the new session needs the session tools of the Claude desktop app's Code tab (start_session). Elsewhere the handover is shown in the reply to paste.
---

# Handover

## Contents

- [Before you start](#before-you-start)
- [Read the user's instructions](#read-the-users-instructions)
- [Write the handover](#write-the-handover)
- [Verify the output](#verify-the-output)
- [Propose the new session](#propose-the-new-session)
- [Tell the user](#tell-the-user)
- [Common failures](#common-failures)
- [What it can't do](#what-it-cant-do)
- [Feedback](#feedback)
- [Skills and agents](#skills-and-agents)

## Before you start

Find the session tools' `start_session`. It is often deferred, so load it with ToolSearch before deciding that it is missing.

## Read the user's instructions

The user may say what context goes to the new session and what does not. The instructions given with the command are between these tags:

<handover_instructions>
$ARGUMENTS
</handover_instructions>

Words about content in the request that started this handover ("hand over, but skip the website part") count the same. When there are neither, as with a press of the Handover button, use the defaults in [Write the handover](#write-the-handover) unchanged.

Instructions adjust those defaults; they never replace the handover's purpose, which is that a session without this conversation can carry the work on.

- **Include:** add what is named to the defaults, also what they leave out (git state, older work, rejected options, a file's content). Look it up read-only when this conversation does not hold it.
- **Focus:** give what is named the most detail, and keep the rest of the defaults short.
- **Only:** hand over what is named, with what it needs to make sense, and leave out other work, including other work's next steps.
- **Leave out:** omit what is named from everything that is sent: the title, the prompt, and the background, including paraphrases, file names, and paths that reveal it. Do not say that something was left out or repeat the instruction, because that would send it. When it is both included and left out, leave it out.
- **A task for the new session:** make it the first next step, and do not do it here.

Instructions change only the content. The five parts, the way the session is proposed, and its detach line stay. When one is too unclear to tell what must not be sent, ask one short question and wait, because what was sent cannot be taken back.

## Write the handover

Write a handover of this session's work for a new session that has no copy of this conversation. It has to be complete on its own, within the user's instructions.

By default, focus on the latest work and its current state. Earlier work that is finished and does not bear on what comes next gets one line at most.

By default, leave out anything this session did not do or touch:

- git status, branches, and commits;
- other uncommitted changes in the repository;
- the environment, unless something in it blocks the next step.

The handover is for the new session's agent. It has exactly these parts, in Markdown, under a `# Handover: <topic>` title, with no contents list or other sections even where workspace rules ask for them. A part with nothing to send says "None to hand over."

- **Supporting materials** - the files, links, sources, and tools this work used, with their paths or URLs.
- **Overall** - what the work is for and where it stands now, in two or three sentences.
- **Tasks done** - one bullet per task, with its result. The latest task comes first and is the most detailed, unless the user set another focus.
- **Working documents** - for each file this session created or changed: its path, its current state, and what is unfinished.
- **Next steps and open questions** - what to do next, in order, and what still needs the user's decision.

Extra context the user included goes inside these parts, never under a heading of its own: git state under **Working documents**, decisions and rejected options under **Tasks done**, anything else in the part it fits best. Do not write the handover to a file.

## Verify the output

Before anything is sent, reread the title, the handover, and the background against the instructions:

- everything included is there;
- nothing left out is there, by name, paraphrase, or path, and nothing hints that it was removed;
- the next steps can be followed without this conversation. If one needs something left out, keep it out and note it for [Tell the user](#tell-the-user).

## Propose the new session

If `start_session` is not available, show the handover in the reply, in a fenced code block, so the user can paste it into a new session. Put anything noted in the check in one line outside the block, marked "not part of the handover", so it is not pasted with it. Do no more work in this session. Skip the rest of this section and the Tell the user section.

Otherwise, propose the new session with the session tools' `start_session`, called with:

- `initiation`: `"own_initiative"`. This works even when the turn was sent by a mod, and the user starts the session from its card.
- `context`: `"fresh"`, never `"fork"`, which would send the whole conversation, including what was left out.
- `use_worktree`: `false`, so it runs in this same folder with no new worktree.
- `title`: short, under 60 characters, starting with `Handover:`.
- `prompt`: this line first, then the handover:

  > First, before anything else: detach this session to top level by calling the session tools' `detach_session` with `session_id` `"self"` (load it with ToolSearch if needed), so the session that proposed it gets no reports from it. Never message that session.

- `background`: the Overall part, at least 80 characters. Lengthen a shorter one only from the checked handover.

## Tell the user

Reply with this one line and nothing else, with no summary of the handover, because the card already holds it:

> Start the new session from its card.

Add a second line only when the check found a next step that needs something left out: one sentence naming what to give the new session if they want that step done. Unlike what is sent, this line may name what was left out, because only the user sees it. Do no more work in this session.

## Common failures

| Symptom | Cause | Fix |
| --- | --- | --- |
| The handover is pasted in the reply although the app has session tools | `start_session` was deferred and taken for missing | Load it with ToolSearch first |
| Something left out shows on the card | Only the prompt was filtered | Check the title and the background too |
| A sixth section, such as Git state | Included context got a heading of its own | Move it into one of the five parts |
| The new session asks about what was removed | The handover said that something was left out | Remove the mention; tell only the user, in this session |
| `start_session` refuses the call | The background is under 80 characters, or the title is too long | Fix that field and propose again |

## What it can't do

- It controls only what is sent. The new session still loads the folder's instruction files and memory and can read the files there, so leaving something out does not make it secret.
- It cannot start the session itself; the user starts it from the card.
- It cannot recover details that compaction already removed from this conversation. It says what it does not know and never guesses.

## Feedback

If the user asks to change how this skill works or reports a problem with it, use the `skill-builder` skill (for example, `/skill-builder`) to plan and apply the change. If `skill-builder` is unavailable, agree the change with the user first, keep it as small as the problem needs, and check the skill afterwards.

## Skills and agents

- `skill-builder` - builds and maintains this skill; send changes there, as described in [Feedback](#feedback).
- `command-pane` - the mod whose Handover button runs this skill without instructions.
