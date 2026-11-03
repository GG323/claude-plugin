# Report

## Contents

- [Entry and inputs](#entry-and-inputs)
- [Find recurring findings](#find-recurring-findings)
- [Render and publish](#render-and-publish)
- [Update the log](#update-the-log)
- [Propose and fix](#propose-and-fix)
- [Summarize in chat](#summarize-in-chat)
- [Skills and agents](#skills-and-agents)

## Entry and inputs

Entered from [Workspace audit](workspace-audit.md) with the run folder, whose `report.json` now holds every verified finding.

## Find recurring findings

Read the last two rows of [state/run-log.md](../state/run-log.md). A check ID that is open in both and again in this run is recurring: three runs in a row. For each one, add an entry to the run file's `recurring` list with a proposal: a change to the conventions in [references/markdown-conventions.md](../references/markdown-conventions.md), or a lesson for `skill-builder`, instead of fixing the same thing again. The conventions change only with the user's approval, in a later on-request run.

## Render and publish

1. Render the report:

   ```bash
   py -3 "${CLAUDE_SKILL_DIR}/scripts/render_report.py" render "<run folder>/report.json" --log "${CLAUDE_SKILL_DIR}/state/run-log.md" --out "<run folder>/environment-audit-YYYY-MM-DD.html"
   ```

   It validates the run file first. If it stops with errors, fix the named findings in the run file and render again. It numbers the findings in the run file (`n`), so the chat, the page, and later fix requests use the same numbers. Text fields may use `code` spans and `[text](https://…)` links.
2. Publish the HTML file as a **new** private artifact (no `url`), with the icon `checklist` and a one-sentence description naming the date and the targets. Where the harness asks for its page-design skill before a publish (in Claude Code, `artifact-design`), load it; the page already follows its contract, so do not restyle it. Keep the artifact's link for the summary and the log.
3. Without an Artifact tool, or when the publish fails, render again with `--standalone` (so the file opens on its own in a browser) straight to the folder the run started in, as `environment-audit-YYYY-MM-DD.html` (with `-2`, `-3` when the name is taken), and use its path instead of a link.

## Update the log

Add this run's row to the run log, with the link or path from [Render and publish](#render-and-publish):

```bash
py -3 "${CLAUDE_SKILL_DIR}/scripts/render_report.py" log "<run folder>/report.json" --log "${CLAUDE_SKILL_DIR}/state/run-log.md" --report "<artifact link or file path>"
```

It appends one row and keeps the newest 26 (about six months of weekly runs); run again for the same report, it replaces that row, so the log always shows the run's latest state even when the user never answers the proposal. This is the only state file a scheduled run writes. If it cannot be written (for example, OneDrive has it locked), put the row in the chat summary and say it was not saved.

In a scheduled run, skip the Propose and fix section and go to [Summarize in chat](#summarize-in-chat).

## Propose and fix

1. **Propose.** In one message, give the chat summary described in [Summarize in chat](#summarize-in-chat) and ask which findings to fix (by number), which to defer, and which to accept as exceptions. Findings marked "Use `skill-builder`" are not offered as fixes: name them and recommend running `skill-builder` with those findings as evidence. Findings marked "Needs your decision" need the user's answer first. Then wait for the answer; if none comes, every finding stays open and the log already shows it.
2. **Fix.** Apply only the approved fixes, and leave everything else in each file as it is:
   - Mechanical fixes (an anchor, a contents entry, a heading level, a link turned into code, a missing Feedback section with the standard text and a `skill-builder` entry under Skills and agents) are applied directly.
   - **W1:** a difference is resolved only in the direction the user chose. If the reference should change, change [references/markdown-conventions.md](../references/markdown-conventions.md) only with that approval.
   - **W4:** a missing skill or agent is added as `` - `name` - <one line from its description> ``; a listed one that is not installed is removed only with approval.
   - **W5 without `AGENTS.md`:** with a yes, copy the draft from the run folder into the workspace as `AGENTS.md`, then list its placeholders as open.
   - **W7:** layout entries are added, updated, or removed as approved.
   - When an approved and a deferred finding touch the same lines, apply only the approved part and say so.
   - No file or folder is deleted, merged, or renamed without approval for that exact path; removing a line that an approved finding names is part of that fix. Preserve changes the user made meanwhile.
   - For each finding accepted as an exception, add an item to [state/exceptions.md](../state/exceptions.md) in its format.
3. **Re-check.** Rerun the scripts on what changed (`check_md.py --files <changed files and the files that link to them>`, `check_agents.py` for a changed `AGENTS.md`) and repeat the review checks on the changed parts yourself (a subagent is worth starting only for whole files). Set each finding's status in the run file (`fixed`, `deferred`, `accepted`, or `open`), and update the line numbers of open and deferred findings that a fix moved. Once proposed, a finding keeps its number, check, and domain, because the user answers by number. Add any new finding at the end, and ask the user only about new ones. Stop when nothing new is found, or after three rounds that applied fixes.
4. **Republish.** Repeat [Render and publish](#render-and-publish) with the same file names, publishing to the same artifact link (or overwriting the same saved file), so the run has one report that shows its final state. Then run the command in [Update the log](#update-the-log) again with the same link or path, which replaces the run's row.

## Summarize in chat

End the run with the summary in the shape [Output](../SKILL.md#output) gives: date, mode, and targets; defects, suggestions, fixed, and open; up to three headline items; the reminder to run `/skill-doctor`; the link or path. In an on-request run that applied fixes, it reports the final state. In a scheduled run it is the final message of the session, and it asks no questions.

## Skills and agents

- [environment-audit](../SKILL.md) — the overview, rules, and output contract.
- [scripts/render_report.py](../scripts/render_report.py) — renders the report and updates the run log; [assets/report-template.html](../assets/report-template.html) — the page it fills.
- `skill-builder` — recommended for findings with the action "Use `skill-builder`".
- `artifact-design` — loaded before publishing where the harness asks for it.
- `/skill-doctor` and `/doctor` — recommended in the report and the summary.
- Previous stage: [Workspace audit](workspace-audit.md). This is the last stage.
