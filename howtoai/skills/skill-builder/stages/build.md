# Build the skill

## Contents

- [Before writing](#before-writing)
- [Metadata and discovery](#metadata-and-discovery)
- [Instructions](#instructions)
- [Split the workflow into stages](#split-the-workflow-into-stages)
- [Supporting files](#supporting-files)
- [Placement and saving](#placement-and-saving)
- [Skills and agents](#skills-and-agents)

## Before writing

- Confirm the user explicitly approved the final plan. If approval is missing or the plan changed materially, return to [Plan](plan.md).
- Build exactly what the plan approved, following the [core rules](../SKILL.md#core-rules) and the recall-note lessons the plan applied. Use [the example](../examples/example-target-skill.md) as a shape reference.
- When revising an existing skill, first copy its current version to `_sandbox/<name>/baseline/` in the user's working directory. [Test](test.md#design-candidate-tests) uses the copy as the baseline and deletes it after delivery.
- When revising, leave only current behavior: remove obsolete instructions and stale references, consolidate overlap, update or remove supporting material that no longer matches, regenerate examples that mislead about the new behavior, and update the target skill's `state/` according to its own rules. When the change comes from a failure in real use, add it as a row in the target skill's **Common failures** section. Preserve unrelated files and behavior.

## Metadata and discovery

- YAML frontmatter with `name` and `description`, in the format the target harness supports.
- `name`: 1–64 characters of lowercase letters, digits, and single hyphens; no leading, trailing, or consecutive hyphens; matches the target skill's directory.
- `description`: non-empty, at most 1,024 characters. Say what the target skill does and when to use it, including phrases users actually say.
- Add optional, harness-specific fields only when the target harness supports them (for Claude Code, check the [skills documentation](https://code.claude.com/docs/en/skills)).

## Instructions

Write the workflow, decision points, and meaningful edge cases without spelling out steps the main agent can infer. Keep `SKILL.md` well under 500 lines; move detail into supporting files.

- Technical tasks: environment assumptions, commands, permissions, and safe checks.
- Nontechnical tasks: audience, sources, tone, format, and quality criteria.
- Make consequential permissions and side effects explicit, including what the target skill must not do.
- Write the [output contract](../SKILL.md#output-contract) as its own section, including the audience and the deliverable's own format, so the main agent does not add workspace documentation rules (titles, contents lists) to it. For a standardized output, write the fixed structure (or link its template in `assets/`), which data goes in tables or charts, and the default format with the cases that change it.
- If the plan uses the [idea-generation option](../SKILL.md#idea-generation-option), write the agreed count, split, model choice, and an explicit **Choose one** step into the workflow.
- If the plan uses `state/` or external sources, write their update/prune rules and failure handling into the workflow, per [Working memory and sources](../SKILL.md#working-memory-and-sources).
- **Requirements:** write each requirement the plan applied from [references/skill-types.md](../references/skill-types.md) where it acts:
  - The startup check and input rules in a **Before you start** section at the top of the workflow.
  - Side-effect defaults inside the steps they govern, such as "create a draft; send only after the user approves it".
  - Dependencies on other skills and connectors in the steps that use them, quoted as code.
  - **Verify the output**, **Common failures**, and **What it can't do** sections after the output contract.
  - The supported platforms: in frontmatter `compatibility` where the harness supports it, in **Before you start** for what the workflow needs, and in **What it can't do** for what happens on platforms where it is missing.
  - Privacy and explain-why ([Every target skill](../references/skill-types.md#every-target-skill) items 6 and 8) apply to how every instruction and example is written.
- **Vocabulary:** use one name per thing. For the target skill's structure, use the terms in [Vocabulary](../SKILL.md#vocabulary): a **stage** is one part of a split workflow and one file in `stages/`, a **section** is a heading inside a file, and a **step** is a numbered action inside a section. Use **route** for a branch at a decision and **handoff** for passing work to another skill.
- **Flow:** write instructions to be read top to bottom. Add an explicit link to the next section only where the flow branches or jumps — choosing between routes, skipping ahead, returning to an earlier section, or moving to another file. Do not add "continue to" links between consecutive sections. When a route skips the sections that follow it, say so explicitly at the end of that route, for example "Skip the Hand off section". Keep each instruction in the section that acts on it; a section must not describe a branch it does not lead to.
- **References:** what the target skill may link depends on where it lives.
  - Every target skill links its own files and sections with relative Markdown links, for example to `stages/review.md` or to `#output` in the same file.
  - A project skill (in a workspace's `.claude/skills/`) may also link that workspace's files, such as `../../../Job posts/`, because they belong to the same workspace.
  - A personal or plugin skill runs in every workspace, so it names workspace paths as code instead of linking them.
  - Other skills, tools, commands, and infrastructure artifacts are always quoted as code, for example `skill-creator`, `ffmpeg`, or `.claude/skills/`.
- **Bundled scripts:** a relative `scripts/...` path fails when the user's working directory is elsewhere, so call every bundled script through the skill's own folder. For Claude Code, write `${CLAUDE_SKILL_DIR}`, which Claude Code replaces with the folder holding the skill's `SKILL.md`, quoted and with the interpreter from the startup check, for example `py -3 "${CLAUDE_SKILL_DIR}/scripts/tidy.py" plan "<folder>"`. A matching frontmatter rule such as `allowed-tools: Bash(py -3 "${CLAUDE_SKILL_DIR}/scripts/tidy.py" *)` lets those exact commands run without a permission prompt; add it only for scripts that are safe to run unprompted. For other harnesses, add one sentence saying that paths under `scripts/` are relative to the skill's folder. Scripts force UTF-8 output (on Windows the default console encoding crashes on names like "Jānis"), and scripts that use today's date take an optional "as of" date, so tests can fix it.
- Place the **Feedback** section last before `Skills and agents`, as described in [Feedback note for target skills](../SKILL.md#feedback-note-for-target-skills).

## Split the workflow into stages

When the approved plan splits the workflow into stages, write one stage file per stage under `stages/`:

- `SKILL.md` gives the overview: the stage order, when each stage is entered, and the rules that apply to every stage (such as the output contract). It holds no stage-specific instructions.
- Each stage file owns its instructions completely: inputs, sections and steps, decisions, moves to other stages, handoffs to other skills, and what it passes on. Other files link to it instead of repeating or partly describing it.
- A decision and how to act on it live in the stage that makes it. Do not create shared sections that several stages use; if two stages need similar instructions, each states its own version for its own case.
- Each stage file says where it is entered from and where it goes next.
- Name files after their stage (for example, `stages/gather.md`, `stages/review.md`) and tell the main agent to read only the file for the current stage.

## Supporting files

Start with `SKILL.md`. Add only the folders the plan approved:

- `stages/` — one file per stage, when the workflow is [split into stages](#split-the-workflow-into-stages).
- `references/` — documentation and domain knowledge read on demand.
- `examples/` — complete representative samples.
- `scripts/` — executable utilities for deterministic work. Document prerequisites and failure messages; keep tiny one-off operations inline instead.
- `assets/` — templates, images, or boilerplate copied into outputs.
- `state/` — persistent working memory, when planned.

[Test](test.md#run-and-deliver) adds `evals/` for saved test cases; Build does not create it.

Link each supporting file from `SKILL.md` with a relative path and a note on when to use it. Keep each piece of reference information (facts, templates, domain knowledge) in one place; stage instructions follow the stage rules above. For material shared by several skills, follow the target repository's convention and keep one copy in a stable project-level location.

## Placement and saving

- Use project scope for a target skill meant for the repository or team and personal scope for reuse across projects. For Claude Code: `.claude/skills/<name>/SKILL.md` (project), `~/.claude/skills/<name>/SKILL.md` (personal), or `<plugin>/skills/<name>/SKILL.md` (plugin; test with `claude --plugin-dir <plugin-directory>`). Check other harnesses' discovery rules.
- If the approved plan stores the target skill outside a discovery path, [Test](test.md#how-tests-run) syncs a copy into the personal skills folder for testing, and the delivery says where that copy is.
- Change only authorized files. If the destination conflicts with an existing skill or file, stop, leave it untouched, and return to [Plan](plan.md).
- Move existing reference files only as the approved plan specifies.
- Keep package-level documentation outside the target skill's folder, and create it only when requested or required by the target repository.

## Skills and agents

- [skill-builder](../SKILL.md) — rules and vocabulary this stage applies; [skill types](../references/skill-types.md) — the requirements it writes.
- [Plan](plan.md) — source of the approved plan; [Test](test.md) — the next stage.
- No dedicated build agent is required.
