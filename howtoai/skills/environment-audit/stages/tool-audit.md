# Tool audit

## Contents

- [Entry and scope](#entry-and-scope)
- [Scripted checks](#scripted-checks)
- [Review checks](#review-checks)
- [Record the findings](#record-the-findings)
- [Skills and agents](#skills-and-agents)

## Entry and scope

Entered from [Discover](discover.md) with the run folder and the targets. Run every section below for each target in order.

A target's tool folder is the global folder itself, or a workspace's `.claude` folder. The checks cover its skills, agents, commands, output styles, rules, and `CLAUDE.md`, plus a workspace's root `CLAUDE.md` and `CLAUDE.local.md`. A skill whose folder links elsewhere (for example, one linked into a workspace) is audited once, through that entry. Global skills may link only their own files; workspace tools may also link their workspace's files ([check L4](../references/checks.md#links-and-sources)).

If a workspace has no `.claude` folder and no root `CLAUDE.md`, note "No workspace tools" for that target in the run file and go to the next target.

## Scripted checks

Run:

```bash
py -3 "${CLAUDE_SKILL_DIR}/scripts/check_md.py" --root "<tool folder>"
```

The script requests every web link for check L3; add `--no-web` when the run must stay offline, and record L3 as not run. It prints JSON: the audited, exempt, and excluded files, the findings, findings already accepted in [state/exceptions.md](../state/exceptions.md), the checks it ran, and the checks it skipped. Copy the file counts into the target's `files` entry in the run file and each skipped check into its `not_run` list. If it prints an `error`, record it under `not_run` for this target and go on with the review checks.

## Review checks

Start the review subagents described in [Rules for every stage](../SKILL.md#rules-for-every-stage):

- **Per file**, for the audited files: S5, S6, L5, L6, F1 to F4 (tool instruction files only), and G1 to G5. For exempt files, only G4. Test inputs under `evals/<case>/files/` get only G4.
- **Across tools**, when the target has two or more skills, agents, or commands: D4. With fewer, record D4 as not applicable.

## Record the findings

1. Verify every scripted and review finding against its file, as the rules require.
2. Give each one its type, its proposed fix, and its suggested action from [Suggested actions](../references/checks.md#suggested-actions). A fix that changes what a tool does, or how its workflow runs, is "Use `skill-builder`", however small the edit looks; a fix that needs a fact from the user is "Needs your decision" with a `[TO FILL: …]` placeholder.
3. Add them to the run file with status `open` and domain `tool`, except the script's I2 and I5 findings, which go in with domain `instruction`, because they check what the instructions say.

Pass the run folder to the Instruction audit stage: read [stages/instruction-audit.md](instruction-audit.md).

## Skills and agents

- [environment-audit](../SKILL.md) — the overview and rules for every stage.
- [references/checks.md](../references/checks.md) — the S, L, F, G, and D checks.
- [scripts/check_md.py](../scripts/check_md.py) — the scripted checks.
- Previous stage: [Discover](discover.md); next stage: [Instruction audit](instruction-audit.md).
