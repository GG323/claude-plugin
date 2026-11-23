---
tags: [handover]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Skill, ToolSearch]
---

/handover include the rejected options and why, and the git state

Setup: you are at the end of the session described in session.md; read it as this conversation so far. This is a dry run of the desktop app's session tools: treat start_session as available, never call it, and reply with the exact arguments you would pass to it as JSON, then your message to the user.

Input files: session.md
