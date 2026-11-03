---
name: environment-audit
description: Audits the user's whole Claude environment on this computer in one run - the global ~/.claude folder and every Claude workspace found in Claude Code's session history. Tool audit checks skills, agents, commands, output styles, rules, and CLAUDE.md against the Markdown conventions; instruction audit finds outdated prompting, dead references, contradictions, CLAUDE.md upkeep problems, and broken settings files; workspace audit checks each AGENTS.md and its Workspace layout. Publishes one HTML report for all targets as an artifact, proposes fixes, and applies only approved ones; runs weekly as a report-only scheduled task. Use when asked to audit, check, validate, or lint skills, agents, commands, CLAUDE.md, AGENTS.md, or a workspace's instruction files, to find contradictions between them, or to run the weekly environment audit. Not for fixing one skill's workflow (skill-builder), installation health (/doctor), or skill usage and context cost (/skill-doctor).
compatibility: Claude Code (the desktop app for the scheduled run); needs Python 3, file access to ~/.claude and the workspaces, and subagents for the review checks. Publishing the report needs the Artifact tool; without it the report is saved as an HTML file.
allowed-tools: Bash(py -3 "${CLAUDE_SKILL_DIR}/scripts/*" *) Bash(py -3 --version) Bash(python3 --version) Bash(date) PowerShell(Get-Date*) Read Glob Grep Agent Artifact
---

# Environment audit

## Contents

- [The process](#the-process)
- [Before you start](#before-you-start)
- [Rules for every stage](#rules-for-every-stage)
- [Output](#output)
- [Verify the output](#verify-the-output)
- [Common failures](#common-failures)
- [What it can't do](#what-it-cant-do)
- [Feedback](#feedback)
- [Skills and agents](#skills-and-agents)

## The process

One run audits every target: the global folder and each workspace. The stages run in this order, each over all targets. Read only the file for the current stage.

1. **Discover** — [stages/discover.md](stages/discover.md). Entered after [Before you start](#before-you-start). Lists the targets and starts the run file.
2. **Tool audit** — [stages/tool-audit.md](stages/tool-audit.md). Checks each target's tools and instruction files against the Markdown conventions.
3. **Instruction audit** — [stages/instruction-audit.md](stages/instruction-audit.md). Checks what the instructions say: outdated prompting, dead references, contradictions, `CLAUDE.md` upkeep, and settings files.
4. **Workspace audit** — [stages/workspace-audit.md](stages/workspace-audit.md). Checks each workspace's `AGENTS.md` and its Workspace layout.
5. **Report** — [stages/report.md](stages/report.md). Publishes one report for all targets. In an on-request run it also proposes fixes, applies the approved ones, and re-checks.

## Before you start

1. Read today's date with `date` or PowerShell `Get-Date`; the run file, the report, and the run log use it.
2. Confirm Python 3 with `py -3 --version` (or `python3 --version` outside Windows), because `python` on Windows can be Python 2 or a Store stub. If it is missing, stop and say that the scripts need Python 3; the audit is not done by hand, because the scripted checks are its backbone.
3. Read [references/markdown-conventions.md](references/markdown-conventions.md) and [references/checks.md](references/checks.md). If either is missing, stop and ask the user to restore it; never audit from memory.
4. Decide the mode:
   - **Scheduled** — the run was started by the weekly scheduled task, or the request says "scheduled mode". Nobody is present, so the run asks nothing and fixes nothing.
   - **On request** — every other run. If the user names targets (the global folder, a workspace, or a folder), audit only those; otherwise audit all of them.

## Rules for every stage

- **Read-only until approval.** Discover and the three audit stages change no audited file. Only [Report](stages/report.md) applies fixes, only in an on-request run, and only the approved ones. A scheduled run writes only the run file, the report, and [state/run-log.md](state/run-log.md).
- **The run file.** Every finding goes into the run file, `report.json` in the run folder that Discover creates, in the shape [scripts/render_report.py](scripts/render_report.py) describes in its header. A finding has its target, domain (`tool`, `instruction`, or `workspace`), check ID, type (defect or suggestion), file, line, a short quote as evidence, the proposed fix, and one suggested action from [Suggested actions](references/checks.md#suggested-actions).
- **Verified findings only.** Open each cited file and confirm a finding before it enters the run file; drop what you cannot confirm, and drop findings that earlier runs accepted in [state/exceptions.md](state/exceptions.md). Nothing enters the report on a subagent's word alone.
- **One finding per problem.** Findings of one check in one file and section that share one fix are merged into one finding (for example, eight unlisted skills under W4). A problem that several checks catch is reported once, under the most specific check, naming the others in the evidence.
- **File paths in findings.** Global-folder files start with `~/.claude/`; workspace files are written relative to the workspace (`AGENTS.md`, `.claude/skills/x/SKILL.md`), because the target's section heading already names the workspace.
- **Review subagents.** Review checks run in read-only subagents (in Claude Code, the Explore type, which cannot edit): per-file checks on a fast, low-cost model (Haiku), up to eight files each, because each file is a short, bounded read; checks that compare files (D4, I3) on a stronger model (Sonnet or Opus), because they need the whole set in view. Each brief names the files, both reference files, the checks to apply, and asks for check ID, file, line, a short quote, and defect or suggestion, editing nothing. If subagents are unavailable, do the review checks yourself and say so in the report.
- **Exclusions.** Paths and workspaces listed in [state/exclusions.md](state/exclusions.md) are left out and named in the report as excluded.
- **Never audited:** official skills synced by the Claude app, installed marketplace plugins, Claude Code's own data (projects, sessions, caches), and third-party folders a workspace marks as not edited.

## Output

- **Deliverable:** one HTML report for all targets, rendered by [scripts/render_report.py](scripts/render_report.py) from the run file into the page in [assets/report-template.html](assets/report-template.html), and published as a new private artifact every run. Its fixed structure:
  1. Header: date, mode, and the targets with links to their sections.
  2. Key figures: targets, files audited, defects, suggestions, fixed, open.
  3. Work for `skill-builder`: findings whose action is "Use `skill-builder`", grouped by tool.
  4. One section per target, headed by the target's name, with Tool audit, Instruction audit, and (for workspaces) Workspace audit findings as numbered tables (number, check, type, file and line, evidence, proposed fix, action, status), then the checks that did not run. A domain with no findings says "No findings".
  5. Recurring findings, with the proposed convention change.
  6. Built-in checks to run: `/skill-doctor` for each skill's usage and context cost, and `/doctor` for installation health, which this audit cannot see.
  7. Run log: the last ten runs.
- **Audience:** the user, who maintains the tools and workspaces and decides on each fix.
- **Delivery:** the artifact's link in chat. Without the Artifact tool, or when publishing fails, the HTML file is saved as `environment-audit-YYYY-MM-DD.html` in the folder the run started in (with `-2`, `-3` when taken), and its path is given instead.
- **Chat summary:** after publishing, always the same shape, three to six lines: date, mode, and targets; defects, suggestions, fixed, and open (deferred findings count as open, with their number named); up to three headline items (the most serious defects or `skill-builder` work); the reminder to run `/skill-doctor`; the link or path. In a scheduled run this summary is the final message of the session.
- **Success check:** every finding is confirmed against its file, cites a check from [references/checks.md](references/checks.md), and has a suggested action; every applied fix was approved; the report names every check that did not run.

## Verify the output

Before publishing, `render_report.py render` validates the run file and stops on a finding that lacks a field, so fix the run file and render again. Compare the report's counts with the scripts' JSON and the verified review findings. When fixes were applied, reopen two or three fixed files to confirm each fix is in place and broke no link (the re-check covers the rest). Never report a check as passed if it did not run.

## Common failures

| Symptom | Cause | Fix |
| --- | --- | --- |
| Many L3 failures in one run | No network, or a site blocking the checker | Report them as not verified rather than broken; the next run checks again |
| A workspace is missing from the targets | It was never opened in Claude Code, or its folder moved | Name it in an on-request run; a moved folder is listed under skipped targets |
| A scheduled run made no report | The app was closed or the computer asleep at the scheduled time | The desktop app runs one catch-up run on the next launch; the report shows the real run date |
| A scheduled run stalled | It needed a tool that `allowed-tools` does not cover, or `Skill(environment-audit)` is missing from the allow rules in `~/.claude/settings.json` | Approve the prompt in the run's session; for a tool the skill always needs, add it to `allowed-tools` |
| Publishing the artifact fails | No Artifact tool in this harness, or the publish was refused | Save the HTML file as described in [Output](#output) and give its path |
| The run log cannot be written | OneDrive has the file locked | Put the row in the chat summary and say it was not saved |

## What it can't do

- It checks conventions and instruction quality, not whether a skill works; testing a skill belongs to `skill-builder`.
- It cannot see how often skills are used or what they cost in context, or check the installation, hooks timing, or plan usage; the report points to `/skill-doctor` and `/doctor` for those.
- It finds workspaces only from Claude Code's session history on this computer. A workspace never opened in Claude Code, or one on another computer, is audited only when the user names it.
- Settings files are only checked to parse; their keys and permission rules are not validated.
- Web link checks can fail for reasons unrelated to the link (rate limits, blocked automated requests); those are reported as not verified.
- Scheduled runs need the Claude Code desktop app open and the computer awake.

## Feedback

If the user asks to change how this skill works or reports a problem with it, use the `skill-builder` skill (for example, `/skill-builder`) to plan and apply the change. If `skill-builder` is unavailable, agree the change with the user first, keep it as small as the problem needs, and check the skill afterwards.

## Skills and agents

- [stages/discover.md](stages/discover.md), [stages/tool-audit.md](stages/tool-audit.md), [stages/instruction-audit.md](stages/instruction-audit.md), [stages/workspace-audit.md](stages/workspace-audit.md), [stages/report.md](stages/report.md) — this skill's stages.
- [references/markdown-conventions.md](references/markdown-conventions.md) and [references/checks.md](references/checks.md) — the conventions and the checks.
- [scripts/find_workspaces.py](scripts/find_workspaces.py), [scripts/check_md.py](scripts/check_md.py), [scripts/check_agents.py](scripts/check_agents.py), [scripts/render_report.py](scripts/render_report.py) — the bundled scripts; [assets/report-template.html](assets/report-template.html) — the report page.
- [state/run-log.md](state/run-log.md), [state/exceptions.md](state/exceptions.md), [state/exclusions.md](state/exclusions.md) — run state.
- `skill-builder` — recommended in the report for findings that need it, and maintains this skill, as described in [Feedback](#feedback).
- `/skill-doctor` and `/doctor` — Claude Code's built-in commands, recommended in the report.
- `artifact-design` — loaded before publishing where the harness asks for it.
- No custom agent definition is needed; the review subagents are task-scoped.
