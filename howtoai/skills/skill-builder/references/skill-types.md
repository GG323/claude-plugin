# Skill types and requirements

## Contents

- [How to use this file](#how-to-use-this-file)
- [Deliverable kinds](#deliverable-kinds)
- [Every target skill](#every-target-skill)
- [Communication](#communication)
- [Documents and files](#documents-and-files)
- [Connector workflows](#connector-workflows)
- [Media processing](#media-processing)
- [Research and reporting](#research-and-reporting)
- [Data transformation](#data-transformation)
- [Coding](#coding)
- [Scheduled and recurring](#scheduled-and-recurring)
- [Skills and agents](#skills-and-agents)

## How to use this file

[Plan](../stages/plan.md#choose-the-route) reads this file to choose the route and decide what the target skill needs, and [Build](../stages/build.md#instructions) writes those decisions into its instructions. Find the target's kind in [Deliverable kinds](#deliverable-kinds), apply [Every target skill](#every-target-skill) to every kind, then each type section that matches. A target skill can match several types; a weekly status email, for example, is research and reporting, communication, and scheduled and recurring at once.

Each type section lists:

- **Plan decides** — requirements the plan must settle.
- **Verify by** — how the target skill checks its own deliverable, and how its tests stay safe.
- **Typical failures** — starting rows for its **Common failures** section.
- **Reuse** — existing skills and connectors to depend on instead of rewriting their knowledge.

Skip a requirement that does not apply. Mention a skipped requirement in the plan only when a reader might expect it.

## Deliverable kinds

The target skill can be any of these kinds. The kind sets the route [Plan](../stages/plan.md#choose-the-route) takes and where the target lives, which Test's [check 1](check-brief.md#the-checks) compares with. Paths are Claude Code's; for another harness, check its discovery rules.

| Kind | Route | Where it lives | Docs |
| --- | --- | --- | --- |
| Skill or slash command | Main route; a slash command is built as a skill | `.claude/skills/<name>/SKILL.md` (project), `~/.claude/skills/<name>/SKILL.md` (personal), `<plugin>/skills/<name>/SKILL.md` (plugin); `.claude/commands/<name>.md` files still work | [Skills](https://code.claude.com/docs/en/skills) |
| Repeatable procedure or automation | Main route: a skill, plus [Scheduled and recurring](#scheduled-and-recurring) when it runs unattended | As a skill; its scheduled task, which Test creates after approval ([Save and deliver](../stages/test.md#save-and-deliver)) | [Skills](https://code.claude.com/docs/en/skills) |
| Subagent | Main route; Build writes an agent file | `.claude/agents/<name>.md` (project), `~/.claude/agents/<name>.md` (personal), `<plugin>/agents/<name>.md` (plugin) | [Subagents](https://code.claude.com/docs/en/sub-agents) |
| Hook or settings automation ("whenever X") | Handoff to `update-config` | The settings file `update-config` chooses (`~/.claude/settings.json`, `.claude/settings.json`, or `.claude/settings.local.json`), or a plugin's `hooks/hooks.json` | [Hooks](https://code.claude.com/docs/en/hooks) |
| Mod (a pane, the band above the prompt, a status line, a toast) | Handoff to `plugin-authoring` | A plugin with a hooks module | [Plugins](https://code.claude.com/docs/en/plugins) |
| Plugin bundle | Main route for each piece; Build writes the manifest | `<plugin>/.claude-plugin/plugin.json`, listed in a marketplace's `.claude-plugin/marketplace.json`; tested with `claude --plugin-dir <plugin-directory>` | [Plugins](https://code.claude.com/docs/en/plugins) |
| MCP server or connector | Find an existing one with `skill-finder`; building a new server is out of scope, so the plan says so and puts it under **What it can't do** | Where the found one installs | [Plugins](https://code.claude.com/docs/en/plugins) |

**Dev mode.** The setting is kept in a workspace's `AGENTS.md` (its `## Dev mode` section), and the pointer `~/.claude/howtoai/install.json` names that workspace and the `howtoai` plugin folder (`howtoai_root`). When the pointer exists, run `py -3 -I -B "<howtoai_root>/scripts/devmode.py" status`; when its `dev_mode` is true, a personal skill or subagent does not live in `~/.claude/`: its files go in the workspace's source folder, and the personal path holds only a link to them. A skill goes in `<paths.skills>/<name>/`, an agent in `<paths.agents>/<name>.md`, and a plugin's own pieces in its source under `paths.plugins`. Project targets keep their place. With no pointer, or `dev_mode` false, the paths in the table apply. The setting's contract is the `howtoai` plugin's `docs/dev-mode.md`.

## Every target skill

1. **Reuse before writing.** Check which skills and connectors the harness already offers (for example, `docx`, `pdf`, `xlsx`, `pptx`, `google-workspace`, `schedule`, `deep-research`, or an email or calendar connector). Depend on them by name and tell the main agent when to use each; do not copy their knowledge into the target skill, because copies go stale when those skills improve. The exceptions are a bundled script that must write or check the same files (for example, because the format skill's own prerequisites are missing), where the instructions say why, and the look of a page or report, which `skill-design` builds once into a template ([item 11](#every-target-skill)) instead of being called each run. State each dependency in the instructions, and in frontmatter `compatibility` where the harness supports it.
2. **Startup check.** If the workflow needs tools, access, connectors, or particular inputs, open it with a **Before you start** section that checks them, including the prerequisites of each reused skill, which can claim to be preinstalled when they are not. On a failure, stop with a message naming what is missing and how to fix it, so the user never gets a half-finished run. For bundled scripts, check the interpreter too: on Windows `python` can be Python 2.7 or a Store stub, so call `py -3` or `python3` and confirm the major version before running anything. Check libraries and external programs the same way, by trying to import them or by asking the program which features it has, which is more reliable than comparing version numbers.
3. **Side-effect safety.** Sort the workflow's actions into reads, reversible writes, and irreversible or external actions (sending, publishing, deleting, paying, writing to shared systems). Then set safe defaults:
   - Draft or dry-run first, and show the planned changes before a bulk operation.
   - Ask the user before every irreversible or external action.
   - Make reruns safe: check whether something already exists before creating it.
   - Keep a backup or a new version before overwriting.
   - Plan deletions like any other irreversible action: what is deleted, when, and what the user can no longer undo, so it goes in the plan and under **What it can't do**. Match only the files meant for deletion, and never the current run's own files. The skill's own temporary files and logs can be removed without asking.
4. **Input rules.** Say which inputs the target skill accepts (pasted text, attachments, file paths, URLs, connector items), which are required, how they are validated, and what happens when one is missing or ambiguous (ask, do not guess). For very large inputs, say how the main agent splits, samples, or summarizes them, and that it tells the user.
5. **Verification and limits.** Give the target skill three sections:
   - **Verify the output** — how the main agent checks its deliverable before delivery: re-reading it against the request, rendering it, probing it, or recounting it. Use the type section's **Verify by** entry. A bundled check script lists every check it ran and every check it skipped, with the reason, so a skipped check never reads as passed.
   - **Common failures** — a table of symptom, cause, and fix. Start with the type's **Typical failures**; later changes add rows for failures seen in real use.
   - **What it can't do** — honest limits and the alternative the main agent offers instead.
6. **Privacy and secrets.** Keep credentials, tokens, and real personal data out of skill files, examples, and test cases; use placeholders. Store personal data in `state/` only when the workflow needs it, keep it minimal, and give it a prune rule. Never send data to a service the user did not name.
7. **Platforms.** State where the target skill is meant to run (for example, Claude Code, Claude.ai, or Cowork) and what the main agent does when something is missing there, such as subagents, a shell, a display, or a connector. Lower the ambition openly instead of failing silently.
8. **Explain why.** Give each non-obvious rule its reason in a short clause, so the main agent can handle cases the rule does not name. Keep "must" and "never" for safety rules and hard limits.
9. **Dates and times.** When the workflow uses today's date, a weekday, a deadline, a time zone, or a period ("last week", "overdue"), tell the main agent to read the date and time from the system clock (for example, `date`, PowerShell `Get-Date`, or Python `datetime`) and to compute weekdays and intervals with code, never by inference. Scripts that depend on today's date take an optional "as of" date, so tests can fix it.
10. **Thinking effort.** Give each step the least that does it well: a script for deterministic work, a cheap subagent for simple sorting or lookups, the main agent for ordinary judgment, and high effort only for hard judgment, because effort costs time and usage on every run. In Claude Code, a skill sets `effort` and `model` in its frontmatter (they apply to the turn that runs it, or to the forked subagent with `context: fork`), and a subagent sets `model` in its agent file; in other harnesses, state the intent in the step.
11. **Look and design.** When the deliverable is something people look at, such as an HTML page, report, dashboard, or artifact, the target skill ships its own template, so every run looks the same and writes no styling rules of its own:
    - Build makes the template once with `skill-design`, in the house design or the client's own design, and puts it in `assets/`. A script, or a fixed step, fills it with each run's data. Runs never call `skill-design`.
    - The template carries a stamp of what it was built from, for example `built from skill-design design-reference v1 (2026-11-09)` or `built from client profile 2026-11-09` (the reference version and date, or the date the client design last changed), and the registry row's Notes repeat it.
    - `skill-design` is used again only to rebuild the template: when the design reference gets a new version, or the client's design changes. [Recall](../stages/recall.md#search-past-work) compares the stamp with the current design and offers the rebuild.

    `skill-design` applies the house design to every surface its description covers. For a surface it does not cover, use the format skill (for example, `pptx` or `docx`) and state in the plan that no design review runs.

12. **Subagent briefs.** When the target skill starts subagents (explorers, checkers, reviewers, vetting):
    - Every brief that needs exact text says to read long files in ranges of under 100 lines and about 2,000 tokens, because a mod such as Input Router can replace a large read with a summary, and a "read every file" step then silently becomes a summary.
    - A panel of context-free reviewers gives each reviewer a viewpoint to start from, never a fence: each reviews the change set it is given, reports every problem it finds in any area, and marks a problem outside the change set in a fixed column, so nothing real is dropped. Sorting, merging repeats, and taking findings outside the change to the user belong to the orchestrator, helped by a script that folds exact repeats and routes the marked findings (user direction, 2026-11-20). Test the panel with one planted flaw per viewpoint, and check that each one is reported and kept once after the orchestrator's sort; plant false findings for any scorer or verifier.
13. **Bundled scripts.** When the target skill bundles scripts or hooks:
    - Every script command and hook that reads user-level settings takes the same override (a flag such as `--user-file`, or an environment variable for a hook), because with the override on some commands only, the others silently read the real user file during tests.
    - A script that takes values a model wrote (severities, timestamps, IDs, statuses) checks them against its fixed list or format and refuses the rest, naming the expected form; the main agent sends a refused value back to the agent that wrote it instead of relabelling it. Every agent that writes such a value names the list or format in its own instructions, because a value off the scale, such as "Minor" on a Blocker/Major/Nit scale, otherwise passes through and skews the counts.
14. **Rule sets.** When the target skill enforces a set of rules (an audit, a linter, safety rules split across scripts, hooks, and instructions), check the rules against each other and against every layer that enforces them before testing, because a contradiction there, such as a deny rule that also blocks an approved step, is hit by every test run.

## Communication

Emails, chat messages, replies, posts, and announcements.

- **Plan decides:**
  - Draft only, or send after approval. Default to draft.
  - Where recipients come from; never add recipients the user did not name.
  - Voice and tone, taken from real examples, and the audience. When the user has none at plan time, make 1–3 samples a runtime input, and store samples only with the user's consent.
  - Channel conventions: subject lines, length, formatting, signatures, threading and reply-all.
  - Attachments, and any personal or confidential data the messages may contain.
- **Verify by:** re-reading the draft against the request and checking every detail against the source, not only recipients, names, and links; computing any weekday or date from the system calendar ([item 9](#every-target-skill)); checking that every mentioned attachment is attached. Include a sparse-input test (missing names, links, or a partial date) to check placeholder handling. Tests only create drafts or use a disposable test account; they never send.
- **Typical failures:** wrong recipient or accidental reply-all; tone drifting from the examples; invented facts or commitments; small invented "warmth" details (a wrong weekday, "this afternoon", an unsupported generalization); a missing attachment; replying to the wrong message in a thread.
- **Reuse:** the harness's email, chat, or calendar connectors, through their draft actions where available.

## Documents and files

Word, PDF, spreadsheets as files, slide decks, and folder organization.

- **Plan decides:**
  - Input and output formats, and the existing skill that handles each format. A new document whose file type nobody requires starts from the artifact-compatible default in [Output contract](../SKILL.md#output-contract).
  - Naming and versioning conventions, folder structure, and where templates live (`assets/`).
  - Edit in place or create a new copy; whether to use tracked changes.
  - Overwrite rules (backup first) and bulk operations (a dry-run list first).
  - Sync and locking behavior of the storage location (for example, OneDrive or SharePoint locks, and long paths on Windows).
- **Verify by:** rendering the document to page images and looking at them; reopening the file and checking its structure; comparing folder listings before and after. Tests work on copies in a disposable folder.
- **Typical failures:** the file is open or locked; OneDrive marks synced folders ReadOnly and ReparsePoint, so deleting or moving them fails with "Access denied" (report each cleanup failure, never swallow it); formatting is lost in conversion; template fields are left unfilled; duplicate files appear; the wrong version is edited.
- **Reuse:** `docx`, `pdf`, `xlsx`, `pptx`, and `google-workspace`.

## Connector workflows

Work done through connectors or APIs, such as Gmail, Calendar, Drive, Notion, or a CRM.

- **Plan decides:**
  - Which connectors and actions the workflow uses, separating reads from writes.
  - How the main agent finds and loads the tools (names can differ by platform, and some tools load on demand).
  - What happens when a connector is turned off versus not connected at all.
  - Confirmation before writes; searching before creating to avoid duplicates; editing in place so links and IDs stay stable.
  - Rate limits, pagination, and whether batch requests succeed or fail as a whole.
- **Verify by:** reading back what was written. Tests use a disposable resource, such as a test calendar or a sandbox page.
- **Typical failures:** a tool is not loaded or has a different name; permission denied; a stale revision is rejected; a partial batch; a duplicate is created instead of an edit.
- **Reuse:** existing skills for the same service before writing new connector instructions, after checking what each one covers — for example, `google-workspace` covers Google Docs, Sheets, and Slides, while Gmail and Calendar have connectors but no skill.

## Media processing

Video, audio, and image processing done with tools. Judging the creative quality of edits over several rounds is creative tuning, which [Plan](../stages/plan.md#choose-the-route) limits.

- **Plan decides:**
  - Tools (for example, `ffmpeg` or `ImageMagick`) and how the startup check finds them and the features (filters, encoders) the workflow uses.
  - Accepted input formats and codecs, and the output specification: resolution, frame rate, codec, bitrate, duration, loudness.
  - Plan the edit first (an edit list with timestamps), then render. A low-resolution preview before a long render; optional for short clips.
  - How long jobs run (in the background, with progress updates), disk space, and cleanup of temporary files.
  - Source files are never modified; outputs are always new files.
- **Verify by:** probing the output (for example, `ffprobe` for duration, streams, and resolution); extracting frames or thumbnails to look at; rendering a short preview clip. Tests use short sample clips.
- **Typical failures:** unsupported codec; audio and video out of sync; variable frame rate; running out of disk space; a render that times out.
- **Reuse:** wrapper scripts in `scripts/` for repeated commands.

## Research and reporting

Collecting information and turning it into a report, brief, or summary.

- **Plan decides:**
  - Preferred, allowed, and excluded sources; how recent the information must be.
  - Citation format, and how key claims are confirmed (for example, two independent sources).
  - How facts, estimates, and opinions are kept apart.
  - Report structure, length, audience, and where it is saved, following the [standardized-output defaults](../SKILL.md#output-contract): a fixed section order, tables and charts where the findings are data, and a self-contained HTML file unless the user or destination needs another format.
- **Verify by:** checking that every claim has a source; opening two or three cited links; confirming dates are current; opening an HTML report in a browser to check that its tables and charts render and match the underlying figures. Look at an HTML report at 320px and at desktop width, in light and dark, on a standalone file that has its viewport meta: a render without the meta lays out at about 980px under phone emulation and hides every narrow-width break.
- **Typical failures:** invented or wrong citations; outdated data; sources behind a paywall; a report far longer than needed; a structure that changes from run to run; a chart that disagrees with the table beside it; a wide table of records with long text fields that hides its last columns past a scroll edge (render each record as a card instead, and put what the reader must act on first).
- **Reuse:** `deep-research` and the harness's web search tools. An HTML report's template is built once with `skill-design` ([item 11](#every-target-skill)), and Test's design pass reviews one output, with `interfaces:better-interface` as a second opinion.

## Data transformation

Cleaning, reshaping, combining, or summarizing tabular data.

- **Plan decides:**
  - Input layout: columns, types, units, header rows, encoding, and delimiter.
  - Validation rules and how bad rows are handled: reject, flag, or fix.
  - Transformations done by a script in `scripts/`, not by the main agent reading rows, because a script is repeatable and exact.
  - Output layout and format; formulas or values; locale (decimal comma, date format); size limits.
  - Whether people read the result as well as process it. If they do, add a summary view per the [standardized-output defaults](../SKILL.md#output-contract) (key figures, summary tables, a chart), generated by the same script as the data so the figures always agree.
- **Verify by:** a script that compares row counts and totals before and after and checks the output layout; opening the output file.
- **Typical failures:** wrong encoding or delimiter; locale mix-ups; a header row offset; silent type conversion; formula errors.
- **Reuse:** `xlsx` and existing scripts in the project.

## Coding

Writing, changing, testing, or reviewing code. These take the main route with the additions in [Plan](../stages/plan.md#choose-the-route).

- **Plan decides:**
  - Languages, versions, and tools, taken from the project.
  - Whether the target skill writes code, changes it, or only reviews it, and what it may run (tests, linters) and where.
  - The deliverable: a patch, new files, or findings with locations and copy-ready fixes.
  - For a review skill: it never runs or modifies the user's code, because running unknown code can have side effects; that is its deciding test.
- **Verify by:** running the project's tests and linters on a copy, for code the skill writes; checking every finding against the line it cites, for a review. Review tests compare the reviewed file before and after and confirm nothing ran it.
- **Typical failures:** a review that runs the script; a finding with a wrong line; advice that contradicts the project's lint or format settings; a fix that does not run; edits outside the files asked for.
- **Reuse:** the project's own test, lint, and format tools and their settings.

## Scheduled and recurring

Workflows that run on a schedule or repeatedly without the user present.

- **Plan decides:**
  - Instructions that work in a fresh session with no access to this conversation.
  - Schedule and time zone.
  - Where it runs: a local scheduled task (for example, Claude Code Desktop) when inputs, outputs, or state live on local or OneDrive paths, because a cloud task works on a fresh clone and cannot reach them; a cloud task only when everything it needs is online.
  - State: what has already been processed (for example, a last-run marker in `state/`) and how duplicates are avoided.
  - What happens on failure: tell the user, retry on the next run, or stop.
  - Where each run's deliverable goes. A run with nobody present cannot get approval, so it only prepares drafts or queues for external actions (sending, posting, deleting) for the user to approve later.
- **Verify by:** running twice; the second run must not repeat the first. Also simulate a missing input.
- **Typical failures:** items processed twice; time-zone drift; failures nobody sees; state that only grows (add a prune rule).
- **Reuse:** the local scheduled-tasks tools (for example, `mcp__scheduled-tasks__*` in Claude Code Desktop) for a local task, `schedule` for a cloud routine.

## Skills and agents

- [skill-builder](../SKILL.md) — the skill this reference belongs to; read from [Plan](../stages/plan.md#decide-the-design) and applied in [Build](../stages/build.md#instructions); [check-brief.md](check-brief.md) — checks targets against it.
- `update-config` and `plugin-authoring` — receive the kinds routed to them in [Deliverable kinds](#deliverable-kinds); `skill-finder` — finds an existing MCP server or connector.
- `skill-design` — the look of pages and other surfaces it covers ([item 11](#every-target-skill)).
- Skills named under **Reuse** are dependencies a target skill may use; none is required by `skill-builder` itself.
