---
name: handover
description: Hands the current session's work over to a fresh session. Writes a handover of the latest work and its current state (materials, what was done, working documents, next steps), then proposes a new session in the same folder with the handover as its first message, which detaches itself so it never reports back. Use when the user presses command-pane's Handover button, types /handover, or asks to hand over, refresh, or move this work to a new session because the context is filling up.
---

# Handover

## Contents

- [Write the handover](#write-the-handover)
- [Propose the new session](#propose-the-new-session)
- [Tell the user](#tell-the-user)
- [Skills and agents](#skills-and-agents)

## Write the handover

Write a handover of this session's work for a new session that has no copy of this conversation. It has to be complete on its own.

Focus on the latest work and its current state. Earlier work that is finished and does not bear on what comes next gets one line at most.

Leave out anything this session did not do or touch:

- git status, branches, and commits;
- other uncommitted changes in the repository;
- the environment, unless something in it blocks the next step.

The handover has these parts, in Markdown, under a `# Handover: <topic>` title:

- **Supporting materials** - the files, links, sources, and tools this work used, with their paths or URLs.
- **Overall** - what the work is for and where it stands now, in two or three sentences.
- **Tasks done** - one bullet per task, with its result. The latest task comes first and is the most detailed.
- **Working documents** - for each file this session created or changed: its path, its current state, and what is unfinished.
- **Next steps and open questions** - what to do next, in order, and what still needs the user's decision.

Do not write the handover to a file.

## Propose the new session

Propose the new session with the session tools' `start_session`, called with:

- `initiation`: `"own_initiative"`. This works even when the turn was sent by a mod.
- `context`: `"fresh"`.
- `use_worktree`: `false`, so it runs in this same folder with no new worktree.
- `title`: short, starting with `Handover:`.
- `prompt`: this line first, then the handover:

  > First, before anything else: detach this session to top level by calling the session tools' `detach_session` with `session_id` `"self"` (load it with ToolSearch if needed), so the session that proposed it gets no reports from it. Never message that session.

- `background`: the Overall part.

If `start_session` is not available, show the handover in the reply so the user can paste it into a new session.

## Tell the user

Tell the user in one line to start the new session from its card, and do no more work in this session.

## Skills and agents

None apply.
