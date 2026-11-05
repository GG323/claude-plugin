# Commands reachable from `$.command.run`

## Contents

- [About this list](#about-this-list)
- [Built-in](#built-in)
- [Plugin](#plugin)
- [User skills](#user-skills)
- [Skills and agents](#skills-and-agents)

## About this list

What `$.command.list()` returned to the `command-pane` mod at `session.start` on 2026-11-05: Claude Code 2.1.317 in the desktop app (Code tab) on Windows, 87 commands. These are the commands `$.command.run({ command })` can run there. `$.session.surface()` was still `null` at that point.

- The list depends on the session: installed plugins, personal skills in `~/.claude/skills/`, and the Claude Code version. Probe again after an update.
- Not in the list: desktop-app commands caught by the app's own prompt box, such as `/btw` (side chat). `$.command.run` refuses those with "no command named `/<name>` in this session".
- Descriptions are cut to their first sentence.
- Back to [Claude Code mod programming](mod-programming.md).

## Built-in

60 commands.

| Command | Description |
| --- | --- |
| `deep-research` | Deep research harness — fan-out web searches, fetch sources, adversarially verify claims, synthesize a cited report. |
| `design` | Make a new Design artifact from a brief |
| `slides` | Make a new Slides deck artifact from a brief |
| `design-sync` | Push a React design system to claude.ai/design. |
| `dataviz` | Use this skill whenever you are about to create ANY chart, graph, plot, dashboard, or data visualization, in ANY output medium — an HTML or React artifact, inline SVG, plotting code in any library (matplotlib, plotly,... |
| `artifact-design` | Design guidance and fundamentals for Artifacts. |
| `artifact-diagramming` | Diagramming know-how for Artifacts - when a picture earns its place, how to draw one that shows the real mechanism, and the inline-SVG mechanics that keep it legible in both themes. |
| `artifact-capabilities` | Runtime capabilities a published Artifact page can be granted — behavior static HTML cannot provide on its own, such as the page reading live or connected data, remembering what people do on it (a poll, a sign-up shee... |
| `update-config` | Use this skill to configure the Claude Code harness via settings.json. |
| `keybindings-help` | Use when the user wants to customize keyboard shortcuts, rebind keys, add chord bindings, or modify ~/.claude/keybindings.json. |
| `verify` | Verify that a code change actually does what it's supposed to by exercising it end-to-end and observing behavior — drive the affected flow, not just tests or typecheck. |
| `debug` | Enable debug logging for this session and help diagnose issues |
| `code-review` | Review the current diff, or a PR number/branch/path target, for correctness bugs (plus reuse/simplification/efficiency cleanups where the model's recipe covers them) at the effort level given first, before any target... |
| `simplify` | Review the changed code for reuse, simplification, efficiency, and altitude cleanups, then apply the fixes. |
| `batch` | Research and plan a large-scale change, then execute it in parallel across 5–30 isolated worktree agents that each open a PR. |
| `fewer-permission-prompts` | Scan your transcripts for common read-only Bash and MCP tool calls, then add a prioritized allowlist to project .claude/settings.json to reduce permission prompts. |
| `doctor` | Health-check the user's Claude Code setup and fix issues: diagnose installation health — what the `claude doctor` terminal diagnostics cover — from local data (duplicate or leftover installs, PATH, unparseable setting... |
| `loop` | Run a prompt or slash command on a recurring interval (e.g. |
| `schedule` | Create, update, list, or run scheduled cloud agents (routines) that execute on a cron schedule. |
| `claude-api` | Reference for the Claude API / Anthropic SDK — model ids, pricing, params, streaming, tool use, MCP, agents, caching, token counting, model migration. |
| `workflow-authoring` | Reference for writing a Workflow tool script (script API and gotchas, resume, quality patterns, worked examples). |
| `run` | Launch and drive this project's app to see a change working. |
| `run-skill-generator` | Author or improve the run-<unit> skill - a per-project skill that tells agents how to build, launch, and drive this project's app. |
| `plugin-authoring` | Make a mod: a change to Claude's own interface or behaviour, such as a panel or pane that stays beside the chat and updates, a band, status line, toast, slash command, or hook on tool calls. |
| `advisor` | Let Claude consult a stronger model at key moments |
| `agents` | (removed) Ask Claude to create/manage subagents, or edit .claude/agents/ |
| `auto-mode-setup` | Teach auto mode about your environment, plus optional rule tweaks |
| `autocompact` | Configure the auto-compact window size |
| `clear` | Start a new session with empty context; previous session stays on disk (resumable with /resume) |
| `color` | Set the prompt bar color for this session |
| `compact` | Free up context by summarizing the conversation so far |
| `config` | Set a setting by key |
| `output-style` | List output styles or switch to one |
| `context` | Show current context usage |
| `effort` | Set effort level for model usage |
| `fast` | Toggle fast mode (Opus 5.5) |
| `focus` | Toggle focus view: just your prompt, summary, and response |
| `heapdump` | Dump the JS heap to the Desktop; on Linux with no Desktop folder, the home directory |
| `init` | Initialize a new CLAUDE.md file with codebase documentation |
| `mcp` | Manage MCP servers |
| `import` | Import config from another AI coding agent |
| `model` | Set the AI model for Claude Code |
| `__remote-workflow` | Run the workflow script delivered in this session environment (server-launched sessions only) |
| `workflow-launch-exec` | Execute a server-launched workflow handoff (workflow_launch event sessions only) |
| `reload-plugins` | Activate pending plugin changes in the current session |
| `reload-skills` | Pick up skills added or changed on disk during this session |
| `rename` | Rename the current conversation |
| `ultrareview` | Start a cloud agent that finds and verifies bugs in your branch (~5-15 min, $5-$25 USD) · Runs in a cloud session. |
| `security-review` | Complete a security review of the pending changes on the current branch |
| `usage-credits` | Configure usage credits or request them from your admin when you hit a limit |
| `extra-usage` | Renamed to /usage-credits |
| `usage` | Show session cost, plan usage, and what's contributing to your limits |
| `insights` | Generate a report analyzing your Claude Code sessions |
| `recap` | Generate a one-line session recap now |
| `skill-doctor` | Show which loaded skills are unused and costing context |
| `goal` | Set a goal — keep working until the condition is met |
| `design-consent` | Grant Claude agent access to your Design projects |
| `design-revoke` | Revoke Claude agent access to your Design projects |
| `list-agents` | List subagents, teammates, and other Claude sessions you can message |
| `team-onboarding` | Help teammates ramp on Claude Code with a guide from your usage |

## Plugin

19 commands.

| Command | Plugin | Description |
| --- | --- | --- |
| `anthropic-skills:built-in-browser` | `anthropic-skills` | Read this skill before the first step that uses the built-in browser, the browser pane inside the Claude desktop app (also called the in-app browser, the browser pane, Claude's browser, or "your own browser"), whose t... |
| `anthropic-skills:chrome-browser` | `anthropic-skills` | Read this skill before the first step that uses Claude in Chrome, the browser extension whose tools are named mcp__claude-in-chrome__* (also called Chrome, the browser extension, or the external browser) and which act... |
| `anthropic-skills:computer-use` | `anthropic-skills` | Read this skill before the first step of any request to do something in an app on the person's own computer (Notes, Finder, System Settings, any desktop app), to look at their screen, or for "computer use". |
| `anthropic-skills:consolidate-memory` | `anthropic-skills` | Reflective pass over your memory files — merge duplicates, fix stale facts, prune the index. |
| `anthropic-skills:deep-research` | `anthropic-skills` | Use this skill when the user's prompt requires (1) researching a topic across multiple sources, comparing options or alternatives, analyzing trends or history, understanding markets or industries, or reviewing literat... |
| `anthropic-skills:docs` | `anthropic-skills` | docs (editable docs people share and comment on; the default for any document, named as a doc or not: a document, report, proposal, resume, cover letter, letter, contract, policy, form, template, worksheet, essay, han... |
| `anthropic-skills:docx` | `anthropic-skills` | Use this skill whenever the user wants to create, read, edit, or manipulate Word documents (.docx) or Word templates (.dotx). |
| `anthropic-skills:explain-usage` | `anthropic-skills` | Explain where this session's tokens went, with one simple chart in plain language. |
| `anthropic-skills:google-workspace` | `anthropic-skills` | Read this before the first Google Drive, Docs, Sheets or Slides connector call whenever the task creates or changes a Google file. |
| `anthropic-skills:import-memory` | `anthropic-skills` | Import a memory export from another AI assistant into Claude's memory — conversationally, additively, and with the content treated as data. |
| `anthropic-skills:morning` | `anthropic-skills` | Render the user's morning brief as a styled HTML artifact, or set it up as a recurring weekday task. |
| `anthropic-skills:pdf` | `anthropic-skills` | Use this skill whenever the user wants to do anything with PDF files. |
| `anthropic-skills:pptx` | `anthropic-skills` | Use this skill any time a .pptx or .potx file is involved in any way — as input, output, or both. |
| `anthropic-skills:setup-claude` | `anthropic-skills` | Guided setup — install role-matched plugins, connect your tools, try a skill. |
| `anthropic-skills:setup-cowork` | `anthropic-skills` | Guided setup — install role-matched plugins, connect your tools, try a skill. |
| `anthropic-skills:skill-creator` | `anthropic-skills` | Create new skills, modify and improve existing skills, and measure skill performance. |
| `anthropic-skills:xlsx` | `anthropic-skills` | Use this skill any time a spreadsheet file is the primary input or output. |
| `cowork-plugin-management:cowork-plugin-customizer` | `cowork-plugin-management` | Customize a Claude Code plugin for a specific organization's tools and workflows. |
| `cowork-plugin-management:create-cowork-plugin` | `cowork-plugin-management` | Guide users through creating a new plugin from scratch in a cowork session. |

## User skills

8 commands.

| Command | Description |
| --- | --- |
| `client-follow-up` | Drafts the follow-up email to a client in the user's own voice, after an AI training session (from session notes - thanks, recap, material links, next steps, workshop offer) or after a client meeting (from the Google... |
| `course-clip-prep` | Prepares short course or training video clips for upload. |
| `downloads-organizer` | Tidies a Windows Downloads folder (including one inside OneDrive) by sorting loose files into subfolders by type and month (or year), giving them consistent clean names, and setting exact duplicates aside for review. |
| `environment-audit` | Audits the user's whole Claude environment on this computer in one run - the global ~/.claude folder and every Claude workspace found in Claude Code's session history. |
| `invoice-summary` | Turns a monthly invoice CSV export from an accounting tool (semicolon-separated, decimal commas, amounts in EUR) into an Excel summary with totals per client, paid vs unpaid (partly paid invoices split into paid and o... |
| `python-script-review` | Reviews a single Python script for bugs and style problems and suggests concrete, copy-ready fixes, without modifying the file. |
| `skill-builder` | Create, improve, or repair a focused agent skill (SKILL.md plus optional supporting files) for a repeatable technical or nontechnical task. |
| `workshop-in-a-box` | Turns a topic and an audience into a ready-to-run half-day workshop kit. |

## Skills and agents

- `plugin-authoring` - Claude Code's built-in skill for making mods.
- No agents apply.
