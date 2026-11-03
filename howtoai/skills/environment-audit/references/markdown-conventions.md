# Markdown conventions reference

## Contents

- [Markdown conventions](#markdown-conventions)
  - [Markdown structure](#markdown-structure)
  - [Links and sources](#links-and-sources)
  - [Instruction flow](#instruction-flow)
- [Extended conventions](#extended-conventions)
  - [Naming](#naming)
  - [Vocabulary](#vocabulary)
  - [Rules with reasons and examples](#rules-with-reasons-and-examples)
- [Which version applies](#which-version-applies)
- [Skills and agents](#skills-and-agents)

## Markdown conventions

These conventions apply to every Markdown file in this workspace, including `AGENTS.md`, skills, agents, and tool documentation, both when reading and when writing them.

### Markdown structure

Every Markdown file starts with its title, followed by a `## Contents` section before the main body. Where the format requires frontmatter (for example, a Claude Code `SKILL.md`), the frontmatter comes first, then the title and the contents list.

- The contents list links every major section and stays in sync with the headings. In short documents it is short, but it is never omitted.
- The contents list includes a `Skills and agents` entry. That section is the last section of the file and lists the relevant skills and agents, or states that none apply.
- Heading levels show how sections relate: one `#` title, each subsection nested one level under its parent, and no skipped levels.

### Links and sources

- Information that comes from a web page (official docs, specifications, vendor guides) is linked to that live page, not copied into a local file. A local copy exists only when it is the maintained artifact or a deliberate snapshot.
- A source is checked for access when it is needed. If it fails, the user is asked for a working source; a stale copy or a guessed replacement is never used.
- Files and sections that belong to the same workspace, skill, or tool are linked with relative Markdown links and forward slashes, for example `[AGENTS](AGENTS.md)` or `[Links and sources](#links-and-sources)`.
- Everything outside it, such as other skills, tools, commands, and infrastructure paths, is quoted as code, not linked, for example `skill-creator`, `ffmpeg`, or `.claude/skills/`.

### Instruction flow

Free-text instructions in skill and agent files run from top to bottom. The flow may jump to another section, stage, or skill; instructions that a jump passes over are ignored.

- Sections run in order. There are no "continue to" links between consecutive sections; a go-to link appears only where the flow branches or jumps.
- A route that skips the sections after it says so at its end, for example "Skip the Hand off section".
- Each instruction sits in the section that acts on it. A section never describes a branch it does not lead to.

## Extended conventions

`AGENTS.md` carries only the section above. These rules complete it, and the audit applies them everywhere, so a workspace whose `AGENTS.md` is missing or damaged is still checked against the full set.

### Naming

- Skill, agent, command, and file names use lowercase letters, digits, and single hyphens, for example `client-follow-up`. A skill's folder name equals the `name` in its frontmatter.
- A name says what the thing does in the user's domain: an object and an action or role, such as `invoice-summary` or `skill-builder`. An audit, and each stage of one, is named after the domain it checks: `<domain>-audit`, such as `tool-audit` or `workspace-audit`.
- One term per thing across all files:
  - **workspace** — a folder Claude Code works in, with its own `AGENTS.md` and an optional `.claude` folder; never "project folder".
  - **global folder** — `~/.claude`, which applies in every workspace.
  - **tool** — a skill, agent, slash command, or output style.
  - **instruction file** — any file that tells an agent what to do: `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`, rules, and tools.
- Headings are in sentence case and name what the section does or holds, such as "Before you start" or "Verify the output".

### Vocabulary

Instruction files that describe a procedure use these words, one meaning each:

| Term | Meaning |
| --- | --- |
| **process** | A tool's whole procedure from start to delivery. |
| **stage** | One part of a split procedure; one file in `stages/`. |
| **section** | A heading inside a file. |
| **step** | A numbered action inside a section. |
| **route** | A branch chosen at a decision. "Path" means only a file or folder path. |
| **handoff** | Passing work to another skill, which is named as code. |
| **deliverable** / **report** | The main output / the short status message about it. |

### Rules with reasons and examples

| Rule | Reason | Example |
| --- | --- | --- |
| Title, then `## Contents` | A reader and an agent see the structure before the detail. | `# Invoice summary`, then `## Contents` |
| `Skills and agents` is the last section | One fixed place shows every dependency. | "- `xlsx` — reads the workbook back." |
| Web information links to the live page | A local copy goes stale without warning. | `[skills docs](https://code.claude.com/docs/en/skills)` |
| Own files are linked; everything else is code | A global skill runs in every workspace, so a link to another folder breaks. | `[Plan](stages/plan.md)`, but `` `skill-creator` `` |
| A jump has a link; consecutive sections have none | Agents read in order; an unlinked jump is missed, and a needless link invites skipping. | `If no AGENTS.md exists, go to [Create AGENTS.md](#create-agentsmd).` |
| A skipping route says so at its end | Without it, the agent also runs the sections it should pass over. | "Skip the Meeting route section." |
| Files under `evals/`, `state/`, or `assets/` keep their own format | Test inputs, run state, and templates break if a title or contents list is added. | `state/run-log.md` stays a table in its own format. |

## Which version applies

- In a workspace, the `Markdown conventions` section of its `AGENTS.md` is the primary source; the Init procedure adds it. When it is missing or differs from the section above, the audit applies the section above and proposes the fix (check W1).
- For the global folder, which has no `AGENTS.md`, the section above applies.
- The extended conventions apply in both cases, because `AGENTS.md` does not carry them.

## Skills and agents

- [environment-audit](../SKILL.md) owns this file and checks files against it; [checks.md](checks.md) says how. Its workspace audit copies the `Markdown conventions` section into `AGENTS.md`.
