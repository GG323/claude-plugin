# Instruction audit

## Contents

- [Entry and scope](#entry-and-scope)
- [Collect the instruction files](#collect-the-instruction-files)
- [Run the checks](#run-the-checks)
- [Record the findings](#record-the-findings)
- [Skills and agents](#skills-and-agents)

## Entry and scope

Entered from [Tool audit](tool-audit.md) with the run folder and the targets. Run every section below for each target in order.

This stage covers what Claude Code's `/doctor prompt-audit` and the `CLAUDE.md` part of the `/doctor` checkup look for, so the audit does not depend on those commands: checks I1 to I5 in [Instruction audit checks](../references/checks.md#instruction-audit-checks). The Tool audit stage already checked how the files are built; this stage checks what they say.

## Collect the instruction files

For each target, list the files that load together:

- **Global folder:** `CLAUDE.md`, `rules/`, and every tool in `skills/`, `agents/`, `commands/`, and `output-styles/`.
- **Workspace:** its root `CLAUDE.md`, `CLAUDE.local.md`, and `AGENTS.md`; nested `CLAUDE.md` files in its folders (not in third-party folders the workspace marks as not edited); and its `.claude` folder's `rules/` and tools. The global `CLAUDE.md` also loads here, so include it for check I3.

Leave out fixed-format files (`evals/`, `state/`, `assets/`), because they hold test inputs, run state, and templates, not instructions.

## Run the checks

1. **I1, I2, and I4, per file.** The scripted parts of I2 (`${CLAUDE_SKILL_DIR}/…` paths) and I5 (settings files) are already in the run file from the Tool audit stage. Start per-file review subagents, as in [Rules for every stage](../SKILL.md#rules-for-every-stage):
   - I1: outdated prompting, with the patterns listed in the check and a link to the current guidance in each finding.
   - I2: every other file, folder, script, command, skill, or tool the text names. The subagent lists each name with its line; the main agent then checks each one against the files on disk and the installed tools.
   - I4: `CLAUDE.md` upkeep, for the target's `CLAUDE.md` and `CLAUDE.local.md` files only.
2. **I3, across files.** Start one subagent on a stronger model per target, with all of the target's instruction files, and ask for every pair of instructions that cannot both be followed, quoting both sides with file and line. Two files that say the same thing are not a contradiction; G3 covers repeats.

## Record the findings

1. Verify every finding against its files. For I2, confirm on disk that the name really is missing; for I3, read both quoted passages in context.
2. Give each one its type, proposed fix, and suggested action from [Suggested actions](../references/checks.md#suggested-actions). A contradiction (I3) is a defect; resolving it is "Use `skill-builder`" when a tool's procedure changes, otherwise "Needs your decision" (which side wins).
3. Add them to the run file with domain `instruction` and status `open`.

Pass the run folder to the Workspace audit stage: read [stages/workspace-audit.md](workspace-audit.md).

## Skills and agents

- [environment-audit](../SKILL.md) — the overview and rules for every stage.
- [references/checks.md](../references/checks.md) — checks I1 to I5.
- `/doctor` — the Claude Code command whose instruction checks this stage covers.
- Previous stage: [Tool audit](tool-audit.md); next stage: [Workspace audit](workspace-audit.md).
