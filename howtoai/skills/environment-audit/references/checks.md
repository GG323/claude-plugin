# Audit checks

## Contents

- [How to read this file](#how-to-read-this-file)
- [Tool audit checks](#tool-audit-checks)
  - [Markdown structure](#markdown-structure)
  - [Links and sources](#links-and-sources)
  - [Instruction flow](#instruction-flow)
  - [Language and naming](#language-and-naming)
  - [Skill and agent definitions](#skill-and-agent-definitions)
- [Instruction audit checks](#instruction-audit-checks)
- [Workspace audit checks](#workspace-audit-checks)
- [Suggested actions](#suggested-actions)
- [Skills and agents](#skills-and-agents)

## How to read this file

Each check has an ID, the convention or source it enforces, and how it is verified:

- **Scripted** checks are run by a bundled script and give the same result every time.
- **Review** checks need judgment and are done by reading the file.

Every finding is a **defect** (it breaks a stated convention or check) or a **suggestion** (an improvement no convention requires). Scripted findings are defects, except W2's long-text flags, which are suggestions. When several checks catch the same problem, report it once under the most specific check (for example, I4 rather than G3 for a `CLAUDE.local.md` that repeats `CLAUDE.md`) and name the others.

**Fixed-format files** (anything under `evals/`, `state/`, or `assets/`) get only the link checks L1 to L4 and the privacy check G4. **Test inputs** (`evals/<case>/files/`) get only G4, because they can be broken on purpose. The scripts call both kinds "exempt".

## Tool audit checks

These apply to every tool and instruction file in a `.claude` folder, plus a workspace's root `CLAUDE.md` and `CLAUDE.local.md`. The conventions are in [markdown-conventions.md](markdown-conventions.md).

### Markdown structure

| ID | Check | How |
| --- | --- | --- |
| S1 | Frontmatter, when the format needs it (`SKILL.md`, agent files), comes first; the `#` title follows; `## Contents` is the next section. | Scripted |
| S2 | Exactly one `#` heading, and no heading level is skipped. | Scripted |
| S3 | Every contents entry resolves to a heading, and every `##` heading appears in the contents list. Nested entries for `###` headings are optional. | Scripted |
| S4 | The contents list has a `Skills and agents` entry, and that section is the last section of the file. | Scripted |
| S5 | Heading levels match how sections relate: each subsection sits under the section it belongs to. | Review |
| S6 | The `Skills and agents` section lists the skills and agents the file uses (a skill named anywhere in the file, including Feedback, counts as used), or states that none apply. | Review |

### Links and sources

| ID | Check | How |
| --- | --- | --- |
| L1 | Every relative link resolves to an existing file, and every `#anchor` to a heading in its target. | Scripted |
| L2 | Relative links use forward slashes. | Scripted |
| L3 | Every web link responds. A failure is reported with its status; no replacement is guessed. | Scripted |
| L4 | Links stay within the file's own scope. In the global folder, a tool links only its own files. In a workspace, the workspace is the scope. In both, other skills and outside paths are named as code. | Scripted |
| L5 | Information taken from a web page links to the live page. A local file that copies changeable web material is reported unless it is marked as the maintained artifact or a deliberate snapshot. | Review |
| L6 | Example links that only show a format are written as code, not as live links. | Review |

### Instruction flow

Applies to skill, agent, and command files.

| ID | Check | How |
| --- | --- | --- |
| F1 | No "continue to" links between consecutive sections. | Review |
| F2 | Every branch or jump (choosing a route, skipping ahead, going back, moving to another stage or skill) has an explicit go-to. A target inside the same tool is linked; another skill is named as code, with where the flow resumes afterwards. Using another skill inside a step is not a jump. | Review |
| F3 | A route that skips the sections after it says so at its end. | Review |
| F4 | Each instruction sits in the section that acts on it, and no section describes a branch it does not lead to. | Review |

### Language and naming

| ID | Check | How |
| --- | --- | --- |
| G1 | Text that sets rules for other Markdown files states them as absolute statements of how files are. Style guides for a tool's output are not covered. | Review |
| G2 | One name is used per thing, within a file and across related files, following the [Vocabulary](markdown-conventions.md#vocabulary). | Review |
| G3 | A rule is stated once, in the file that owns it; other files link to it instead of repeating it. Text that the conventions require in every tool (such as the Feedback section) is not a repeat. | Review |
| G4 | No credentials, tokens, or real personal data appear in the file. | Review |
| G5 | Names follow the [Naming](markdown-conventions.md#naming) rules. | Review |

### Skill and agent definitions

| ID | Check | How |
| --- | --- | --- |
| D1 | Frontmatter parses, has `name` and `description`, and `name` matches the folder. | Scripted |
| D2 | `SKILL.md` body is under 500 lines, and every other instruction file in the skill is linked directly from `SKILL.md` (one level deep, per the [skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)). | Scripted |
| D3 | Every user-made skill except `skill-builder` has a Feedback section that sends changes to `skill-builder`, placed last before `Skills and agents`. | Scripted |
| D4 | Across all tools of one target: duplicate or overlapping responsibilities, and gaps (work no tool covers that the others hand to it). Both are suggestions; the audit never forces a merge. Conflicting instructions are I3. | Review |

## Instruction audit checks

These cover what Claude Code's `/doctor prompt-audit` and the `CLAUDE.md` part of the `/doctor` checkup look for, as described in the [memory docs](https://code.claude.com/docs/en/memory) and the [skills docs](https://code.claude.com/docs/en/skills), so the audit does not depend on those commands being available. They apply to every instruction file of a target: `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`, `.claude/rules/`, and all tools.

| ID | Check | How |
| --- | --- | --- |
| I1 | No prompting written for older models: shouting (all-caps MUST, NEVER, IMPORTANT, CRITICAL) where a plain rule would do, threats or bribes, "think step by step" boilerplate, role-play openers ("You are an expert…") with no task content, retired model names or IDs, and features the [Claude Code docs](https://code.claude.com/docs/en/skills) no longer describe. Each finding cites the current guidance in the [prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices). | Review |
| I2 | Every file, folder, script, command, skill, or tool named in the text exists. The script checks `${CLAUDE_SKILL_DIR}/…` paths; review checks the rest against the files and the installed tools. | Scripted and review |
| I3 | No two instruction files that load together contradict each other: the global `CLAUDE.md` with each workspace's files, `CLAUDE.md` with `AGENTS.md` and rules, and tools with each other and with the always-loaded files. Each finding quotes both sides. | Review |
| I4 | `CLAUDE.md` upkeep: a `CLAUDE.local.md` that repeats the checked-in file; content Claude can work out from the files themselves (folder listings, code structure, what a README already says); always-loaded procedures that would load on demand as a skill or a nested `CLAUDE.md`; a `CLAUDE.md` of 200 lines or more. | Review |
| I5 | `settings.json` and `settings.local.json` in the `.claude` folder parse as JSON. | Scripted |

## Workspace audit checks

These apply to a workspace's `AGENTS.md`.

| ID | Check | How |
| --- | --- | --- |
| W1 | A `Markdown conventions` section exists and matches the reference's section word for word. A difference is shown side by side, and neither copy changes until the user chooses which wins. | Scripted |
| W2 | Under 200 lines, as the [Claude Code memory docs](https://code.claude.com/docs/en/memory) recommend. Paragraphs over 80 words and bullets over 50 words (outside the conventions section) are flagged for a shorter rewrite. | Scripted |
| W3 | The structure and link rules: the `#` title first, then `## Contents`; every `##` section in the contents list and every entry resolving; `Skills and agents` listed and last; one `#` heading and no skipped levels; relative links resolving, with forward slashes, inside the workspace; web links responding. | Scripted |
| W4 | The `Skills and agents` section lists every skill and agent installed in the global folder and in the workspace's `.claude` folder, named as code, and nothing that is not installed. | Scripted |
| W5 | A `Project` section gives the purpose, who the work is for, the deliverables, and the target environments, followed by a `Best-practice references` list of live links. Missing facts get `[TO FILL: …]` placeholders. | Review |
| W6 | Lean and consistent: always-needed project facts and conventions only; no rule stated twice; detailed procedures left to tools; rules written as plain statements; one name per thing. | Review |
| W7 | A `## Workspace layout` section lists every top-level folder and root Markdown file (except `AGENTS.md` and names starting with `.` or `_`), each with a relative link and a one-line purpose, and nothing that is no longer on disk. | Scripted (sync) and review (purposes) |

## Suggested actions

Every finding carries one suggested action, so the user knows who acts on it:

| Action | When | What happens |
| --- | --- | --- |
| **Fix in the audit** | Naming, formatting, headings, contents lists, links, layout entries, list entries, wording that keeps the meaning. | The audit proposes the exact change and applies it once approved. |
| **Use `skill-builder`** | A broken or contradictory procedure, missing files, a change to what a tool does or how its workflow runs, or an overlap between tools. | The audit changes nothing; the report recommends running `skill-builder` with the finding as evidence. |
| **Needs your decision** | A fact or choice only the user can give, such as a project purpose or which of two copies wins. | The report shows a `[TO FILL: …]` placeholder or the choice; the audit applies the answer once given. |

## Skills and agents

- [environment-audit](../SKILL.md) runs these checks; its scripts run the scripted ones.
- `skill-builder` — recommended in the report for findings with the action "Use `skill-builder`".
