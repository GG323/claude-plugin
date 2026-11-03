# Skill types and requirements

## Contents

- [How to use this file](#how-to-use-this-file)
- [Every target skill](#every-target-skill)
- [Communication](#communication)
- [Documents and files](#documents-and-files)
- [Connector workflows](#connector-workflows)
- [Media processing](#media-processing)
- [Research and reporting](#research-and-reporting)
- [Data transformation](#data-transformation)
- [Scheduled and recurring](#scheduled-and-recurring)
- [Skills and agents](#skills-and-agents)

## How to use this file

[Plan](../stages/plan.md#decide-the-design) reads this file to decide what the target skill needs, and [Build](../stages/build.md#instructions) writes those decisions into its instructions. Apply [Every target skill](#every-target-skill) to all target skills, then each type section that matches. A target skill can match several types; a weekly status email, for example, is research and reporting, communication, and scheduled and recurring at once.

Each type section lists:

- **Plan decides** — requirements the plan must settle.
- **Verify by** — how the target skill checks its own deliverable, and how its tests stay safe.
- **Typical failures** — starting rows for its **Common failures** section.
- **Reuse** — existing skills and connectors to depend on instead of rewriting their knowledge.

Skip a requirement that does not apply. Mention a skipped requirement in the plan only when a reader might expect it.

## Every target skill

1. **Reuse before writing.** Check which skills and connectors the harness already offers (for example, `docx`, `pdf`, `xlsx`, `pptx`, `google-workspace`, `schedule`, `deep-research`, or an email or calendar connector). Depend on them by name and tell the main agent when to use each; do not copy their knowledge into the target skill, because copies go stale when those skills improve. State each dependency in the instructions, and in frontmatter `compatibility` where the harness supports it.
2. **Startup check.** If the workflow needs tools, access, connectors, or particular inputs, open it with a **Before you start** section that checks them. On a failure, stop with a message naming what is missing and how to fix it, so the user never gets a half-finished run. For bundled scripts, check the interpreter too: on Windows `python` can be Python 2.7 or a Store stub, so call `py -3` or `python3` and confirm the major version before running anything. Check libraries and external programs the same way, by trying to import them or by asking the program which features it has, which is more reliable than comparing version numbers.
3. **Side-effect safety.** Sort the workflow's actions into reads, reversible writes, and irreversible or external actions (sending, publishing, deleting, paying, writing to shared systems). Then set safe defaults:
   - Draft or dry-run first, and show the planned changes before a bulk operation.
   - Ask the user before every irreversible or external action.
   - Make reruns safe: check whether something already exists before creating it.
   - Keep a backup or a new version before overwriting.
   - Plan deletions like any other irreversible action: what is deleted, when, and what the user can no longer undo, so it goes in the plan and under **What it can't do**. Match only the files meant for deletion, and never the current run's own files. The skill's own temporary files and logs can be removed without asking.
4. **Input rules.** Say which inputs the target skill accepts (pasted text, attachments, file paths, URLs, connector items), which are required, how they are validated, and what happens when one is missing or ambiguous (ask, do not guess). For very large inputs, say how the main agent splits, samples, or summarizes them, and that it tells the user.
5. **Verification and limits.** Give the target skill three sections:
   - **Verify the output** — how the main agent checks its deliverable before delivery: re-reading it against the request, rendering it, probing it, or recounting it. Use the type section's **Verify by** entry.
   - **Common failures** — a table of symptom, cause, and fix. Start with the type's **Typical failures**; later changes add rows for failures seen in real use.
   - **What it can't do** — honest limits and the alternative the main agent offers instead.
6. **Privacy and secrets.** Keep credentials, tokens, and real personal data out of skill files, examples, and test cases; use placeholders. Store personal data in `state/` only when the workflow needs it, keep it minimal, and give it a prune rule. Never send data to a service the user did not name.
7. **Platforms.** State where the target skill is meant to run (for example, Claude Code, Claude.ai, or Cowork) and what the main agent does when something is missing there, such as subagents, a shell, a display, or a connector. Lower the ambition openly instead of failing silently.
8. **Explain why.** Give each non-obvious rule its reason in a short clause, so the main agent can handle cases the rule does not name. Keep "must" and "never" for safety rules and hard limits.
9. **Dates and times.** When the workflow uses today's date, a weekday, a deadline, a time zone, or a period ("last week", "overdue"), tell the main agent to read the date and time from the system clock (for example, `date`, PowerShell `Get-Date`, or Python `datetime`) and to compute weekdays and intervals with code, never by inference. Scripts that depend on today's date take an optional "as of" date, so tests can fix it.

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
- **Typical failures:** the file is open or locked; formatting is lost in conversion; template fields are left unfilled; duplicate files appear; the wrong version is edited.
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

Video, audio, and image processing done with tools. Judging the creative quality of edits over several rounds is creative tuning, which [Plan](../stages/plan.md#choose-the-route) routes to `skill-creator`.

- **Plan decides:**
  - Tools and minimum versions (for example, `ffmpeg` or `ImageMagick`) and how the startup check finds them.
  - Accepted input formats and codecs, and the output specification: resolution, frame rate, codec, bitrate, duration, loudness.
  - Plan the edit first (an edit list with timestamps), then render. Use a low-resolution preview before the full render.
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
- **Verify by:** checking that every claim has a source; opening two or three cited links; confirming dates are current; opening an HTML report in a browser to check that its tables and charts render and match the underlying figures.
- **Typical failures:** invented or wrong citations; outdated data; sources behind a paywall; a report far longer than needed; a structure that changes from run to run; a chart that disagrees with the table beside it.
- **Reuse:** `deep-research`, the harness's web search tools, and its page-design or chart skills where available.

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

## Scheduled and recurring

Workflows that run on a schedule or repeatedly without the user present.

- **Plan decides:**
  - Instructions that work in a fresh session with no access to this conversation.
  - Schedule and time zone.
  - Where it runs: a local scheduled task (for example, Claude Code Desktop) when inputs, outputs, or state live on local or OneDrive paths, because a cloud task works on a fresh clone and cannot reach them; a cloud task only when everything it needs is online.
  - State: what has already been processed (for example, a last-run marker in `state/`) and how duplicates are avoided.
  - What happens on failure: tell the user, retry on the next run, or stop.
  - Where each run's deliverable goes.
- **Verify by:** running twice; the second run must not repeat the first. Also simulate a missing input.
- **Typical failures:** items processed twice; time-zone drift; failures nobody sees; state that only grows (add a prune rule).
- **Reuse:** `schedule`, or the harness's scheduled-task tools.

## Skills and agents

- [skill-builder](../SKILL.md) — the skill this reference belongs to; read from [Plan](../stages/plan.md#decide-the-design) and applied in [Build](../stages/build.md#instructions).
- Skills named under **Reuse** are dependencies a target skill may use; none is required by `skill-builder` itself.
