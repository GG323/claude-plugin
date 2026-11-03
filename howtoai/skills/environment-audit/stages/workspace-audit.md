# Workspace audit

## Contents

- [Entry and scope](#entry-and-scope)
- [Scripted checks](#scripted-checks)
- [Describe the folders](#describe-the-folders)
- [Review checks](#review-checks)
- [Record the findings](#record-the-findings)
- [Skills and agents](#skills-and-agents)

## Entry and scope

Entered from [Instruction audit](instruction-audit.md) with the run folder and the targets. Run every section below for each workspace target in order; the global folder has no `AGENTS.md`, so it is skipped here.

Skill files elsewhere in a workspace (for example, vendored ones under `External/` or skill sources under `SKILLS/`) are ordinary workspace files: they are described in the Workspace layout and never checked as tools.

## Scripted checks

Run:

```bash
py -3 "${CLAUDE_SKILL_DIR}/scripts/check_agents.py" --workspace "<workspace>"
```

Add `--global-dir "<folder>"` when the global folder is not `~/.claude`, and `--no-web` when the run must stay offline (then record the web-link part of W3 as not run). The script prints JSON: findings for W1 to W4 and W7 with line numbers, the installed skills and agents with their descriptions, and the workspace's top-level folders and root Markdown files with hints (file counts, main file types, a README, whether it is its own Git repository). If it prints an `error`, record it under the target's `not_run` and go to the next workspace. Otherwise add 1 to the target's `files.audited` count for `AGENTS.md`.

When the workspace has no `AGENTS.md`, the script says so and still returns the installed tools and the folders. Record one finding: check W5, defect, "No `AGENTS.md`", action "Needs your decision", with the proposed fix of creating one. Draft that file in the run folder as `AGENTS-<workspace name>.md`, with these sections in this order: a `#` title naming the workspace; `## Contents`; `## Project` with `[TO FILL: …]` placeholders for the purpose, who the work is for, the deliverables, and the target environments, ending with a `### Best-practice references` subsection (a `[TO FILL: links]` placeholder); `## Workspace layout` from [Describe the folders](#describe-the-folders); `## Markdown conventions`, copied word for word from the [reference](../references/markdown-conventions.md#markdown-conventions); and `## Skills and agents`, one `` - `name` - <one line from its description> `` entry per installed skill and agent. Then skip the Review checks section for this workspace and go to [Record the findings](#record-the-findings).

## Describe the folders

For each folder and root Markdown file the script lists, in its order, write a one-line purpose from what it holds: the first sentence of its README, or of the file itself, when there is one; otherwise its file names, types, and `children`.

- Mark a folder as third-party and not edited when it is its own Git repository or holds downloaded projects (subfolders with their own README, LICENSE, or `-main`-style download names).
- An empty folder gets `empty folder: [TO FILL: purpose]`, and an unclear one `[TO FILL: purpose]`. Never guess beyond what the files show, because a wrong purpose misleads every later session.
- Folders and files whose names start with `.` or `_`, and root files that are not Markdown, are not listed.

Each W7 finding's proposed fix uses these lines, in the form `` - [<name>](<name>/) - <purpose> `` for folders and `` - [<name>](<name>) - <purpose> `` for files, with `<…>` around a link target that contains spaces.

## Review checks

Read the whole `AGENTS.md` and apply W5 and W6 from [Workspace audit checks](../references/checks.md#workspace-audit-checks):

- When W5 finds the Project section missing or thin, the proposed fix adds `[TO FILL: …]` placeholders for what is missing. Never invent project facts.
- A rewrite of long or repeated text (W2, W6) is proposed as before and after; it keeps the meaning and every rule, and cuts only wording.

## Record the findings

1. Verify every finding against the file.
2. Give each one its type, proposed fix, and suggested action from [Suggested actions](../references/checks.md#suggested-actions). A W1 difference is "Needs your decision" (which copy wins); a project fact is "Needs your decision"; layout, list, structure, and wording fixes are "Fix in the audit".
3. Add them to the run file with domain `workspace` and status `open`.

Pass the run folder to the Report stage: read [stages/report.md](report.md).

## Skills and agents

- [environment-audit](../SKILL.md) — the overview and rules for every stage.
- [references/checks.md](../references/checks.md) — checks W1 to W7; [references/markdown-conventions.md](../references/markdown-conventions.md) — the section W1 compares.
- [scripts/check_agents.py](../scripts/check_agents.py) — the scripted checks.
- Previous stage: [Instruction audit](instruction-audit.md); next stage: [Report](report.md).
