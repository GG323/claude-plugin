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
- [Plugin audit checks](#plugin-audit-checks)
- [Suggested actions](#suggested-actions)

## How to read this file

Each check has an ID, the convention or source it enforces, and how it is verified:

- **Scripted** checks are run by a bundled script and give the same result every time.
- **Review** checks need judgment and are done by reading the file.

Every finding is a **defect** (it breaks a stated convention or check) or a **suggestion** (an improvement no convention requires). Scripted findings are defects, except W2's long-text flags and the findings that I5 to I9 mark as suggestions (names the docs do not list, which may be newer than the lists, and risks that still load, such as a package or image not pinned to one version in the user's own configuration). When several checks catch the same problem, report it once under the most specific check (for example, I4 rather than G3 for a `CLAUDE.local.md` that repeats `CLAUDE.md`) and name the others.

**Fixed-format files** (anything under `evals/`, `state/`, or `assets/`) get only the link checks L1 to L4 and the privacy check G4. **Test inputs** (`evals/<case>/files/`) get only G4, because they can be broken on purpose. The scripts call both kinds "exempt".

**Candidates.** In a candidate run, the target is one isolated copy of a third-party skill, tool, or procedure. Every check below applies to it as to a tool folder, with these differences: its instruction files are found wherever its layout puts them, including dot-folders it ships such as `.claude/` (only `.git/` is left out); its other Markdown files are exempt; its links must stay inside the candidate (L4); its web links are never requested, so L3 does not run, because a request would tell whoever controls the URL that the candidate is being vetted; and a package or image it runs that is not pinned to one version is a defect (I7, I5, I9). `skill-finder` decides which findings fail the candidate.

## Tool audit checks

These apply to every tool and instruction file in a `.claude` folder, plus a workspace's root `CLAUDE.md` and `CLAUDE.local.md`. The conventions are in [markdown-conventions.md](markdown-conventions.md).

### Markdown structure

| ID | Check | How |
| --- | --- | --- |
| S1 | Frontmatter, when the format needs it (`SKILL.md`, agent files), comes first; the `#` title follows; `## Contents` is the next section, except in an agent-read file of a skill or agent (a `SKILL.md`, its routes, stages, and references, or an agent definition) under 100 lines, which needs none. | Scripted |
| S2 | Exactly one `#` heading, and no heading level is skipped. | Scripted |
| S3 | Every contents entry resolves to a heading, and every `##` heading appears in the contents list. Nested entries for `###` headings are optional. | Scripted |
| S5 | Heading levels match how sections relate: each subsection sits under the section it belongs to. | Review |

S4 and S6 were retired on 2026-11-24 and are no longer run.

### Links and sources

| ID | Check | How |
| --- | --- | --- |
| L1 | Every relative link resolves to an existing file, and every `#anchor` to a heading in its target. | Scripted |
| L2 | Relative links use forward slashes. | Scripted |
| L3 | Every web link responds. A failure is reported with its status; no replacement is guessed. Not run for a candidate. | Scripted |
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
| D1 | Frontmatter parses, has `name` and `description`, `name` matches the folder, and `description` is at most 1,024 characters, the [Agent Skills specification](https://agentskills.io/specification) limit. | Scripted |
| D2 | `SKILL.md` body is under 500 lines, and every other instruction file in the skill is linked directly from `SKILL.md` (one level deep, per the [skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)). | Scripted |
| D3 | Every user-made skill except `skill-builder` has a Feedback section that sends changes to `skill-builder`, placed as the last section. | Scripted |
| D4 | Across all tools of one target: duplicate or overlapping responsibilities, and gaps (work no tool covers that the others hand to it). Both are suggestions; the audit never forces a merge. Conflicting instructions are I3. | Review |

## Instruction audit checks

I1 to I4 cover what Claude Code's `/doctor prompt-audit` and the `CLAUDE.md` part of the `/doctor` checkup look for, as described in the [memory docs](https://code.claude.com/docs/en/memory) and the [skills docs](https://code.claude.com/docs/en/skills), so the audit does not depend on those commands being available. They apply to every instruction file of a target: `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`, `.claude/rules/`, and all tools. I5 to I9 check the configuration files that tell Claude Code what to run and allow: the target's settings files and the hooks in its skills' and agents' frontmatter, and in a workspace or candidate also every plugin and marketplace manifest, hooks file, `.mcp.json`, and `.lsp.json` outside third-party folders. Wherever a command runs a package or image through `npx`, `bunx`, `pnpx`, `npm exec`, `pnpm dlx`, `yarn dlx`, `uvx`, `uv tool run`, `uv run --with`, `pipx run`, or `docker`, also inside `cmd /c`, `sh -c`, `bash -c`, or `pwsh -c`, it must name one exact version (`name@1.2.3` or `name==1.2.3`; for an image, an `@sha256:` digest in a candidate, because a tag can be moved, and a tag other than `latest` or a digest in the user's own configuration); otherwise the finding is a defect in a candidate, which cannot be pinned without editing it, and a suggestion in the user's own configuration. `docker compose` in a candidate is a defect, because its images are set in a compose file. Their known keys, events, and forms come from the [settings](https://code.claude.com/docs/en/settings-reference), [permissions](https://code.claude.com/docs/en/permissions), [hooks](https://code.claude.com/docs/en/hooks), [plugin manifest](https://code.claude.com/docs/en/plugins/manifest-reference), and [marketplace](https://code.claude.com/docs/en/plugins/marketplace-reference) references.

| ID | Check | How |
| --- | --- | --- |
| I1 | No prompting written for older models: shouting (all-caps MUST, NEVER, IMPORTANT, CRITICAL) where a plain rule would do, threats or bribes, "think step by step" boilerplate, role-play openers ("You are an expert…") with no task content, retired model names or IDs, and features the [Claude Code docs](https://code.claude.com/docs/en/skills) no longer describe. Each finding cites the current guidance in the [prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices). | Review |
| I2 | Every file, folder, script, command, skill, or tool named in the text exists. The script checks `${CLAUDE_SKILL_DIR}/…` paths; review checks the rest against the files and the installed tools. | Scripted and review |
| I3 | No two instruction files that load together contradict each other: the global `CLAUDE.md` with each workspace's files, `CLAUDE.md` with `AGENTS.md` and rules, and tools with each other and with the always-loaded files. Each finding quotes both sides. | Review |
| I4 | `CLAUDE.md` upkeep: a `CLAUDE.local.md` that repeats the checked-in file; content Claude can work out from the files themselves (folder listings, code structure, what a README already says); always-loaded procedures that would load on demand as a skill or a nested `CLAUDE.md`; a `CLAUDE.md` of 200 lines or more. | Review |
| I5 | `settings.json` and `settings.local.json` parse as JSON; every top-level and `permissions` key is a documented one (an unknown key is a suggestion); `permissions.defaultMode` is a permission mode, and `auto` or `bypassPermissions` is set only in user settings, where it takes effect; every `enabledPlugins` entry is `plugin@marketplace` with a marketplace that is added; the programs and scripts a `statusLine` or `subagentStatusLine` command runs exist, as in I7, and any package it runs is pinned. A candidate that ships a settings file is a defect. | Scripted |
| I6 | Every permission rule is `Tool` or `Tool(specifier)` and names a documented tool (an unknown name is a suggestion), and no rule is one Claude Code skips or never matches: an `mcp__` rule with parentheses, an allow rule with a tool-name wildcard outside `mcp__<server>__`, a `Write`, `Glob`, `Grep`, or `NotebookEdit` path rule, `:*` before the end of a pattern, a `WebFetch` rule without `domain:`, and a Bash allow rule with `*` before the subcommand. | Scripted |
| I7 | Every hook, in settings files, a plugin's `hooks/hooks.json`, a manifest, or a skill's or agent's frontmatter, uses a documented event, sits in a matcher group with a `hooks` list, has a documented type with its required fields, and runs programs and scripts that exist: on `PATH` and on disk for the user's own hooks, inside the candidate for a candidate (programs it needs are listed instead), and any package or image it runs is pinned. A hooks file wraps its events in `hooks`, or lists the modules of a mod, which exist; a hooks file that a manifest also names is checked once. | Scripted |
| I8 | Every `.claude-plugin/plugin.json` parses, has a `name` with no spaces, `@`, `:`, or separators that does not pass as Anthropic's own (kebab-case and known fields are suggestions), an `author` object with a `name`, a `homepage` that is a URL, and component paths that start with `./`, contain no `..`, and exist. Every `marketplace.json` has a valid `name`, an `owner` with a `name`, and `plugins` entries with a unique valid `name` and a `source` that is a `./` folder that exists or a documented source type with its required fields. | Scripted |
| I9 | Every MCP server in `.mcp.json` or a manifest has a `command` (that exists, as in I7) or an absolute `url`, and no literal credential in its `headers` or `env`; every LSP server in `.lsp.json` or a manifest has a `command` that exists. A package or image a server runs that is not pinned to one version is a defect in a candidate and a suggestion otherwise; unencrypted `http` or `ws` to a non-loopback host is a suggestion. | Scripted |

## Workspace audit checks

These apply to a workspace's `AGENTS.md`.

| ID | Check | How |
| --- | --- | --- |
| W1 | A `Markdown conventions` section exists and matches the reference's section word for word. A difference is shown side by side, and neither copy changes until the user chooses which wins. | Scripted |
| W2 | Under 200 lines, as the [Claude Code memory docs](https://code.claude.com/docs/en/memory) recommend. Paragraphs over 80 words and bullets over 50 words (outside the conventions section) are flagged for a shorter rewrite. | Scripted |
| W3 | The structure and link rules: the `#` title first, then `## Contents`; every `##` section in the contents list and every entry resolving; one `#` heading and no skipped levels; relative links resolving, with forward slashes, inside the workspace; web links responding. | Scripted |
| W4 | When the workspace keeps an `Installed skills` section, it lists every skill and agent installed in the global folder and in the workspace's `.claude` folder, named as code, and nothing that is not installed. The section is optional. | Scripted |
| W5 | A `Project` section gives the purpose, who the work is for, the deliverables, and the target environments, followed by a `Best-practice references` list of live links. Missing facts get `[TO FILL: …]` placeholders. | Review |
| W6 | Lean and consistent: always-needed project facts and conventions only (a section a tool's `AUDIT.md` installs counts as one); no rule stated twice; detailed procedures left to tools; rules written as plain statements; one name per thing. | Review |
| W7 | A `## Workspace layout` section lists every top-level folder and root Markdown file (except `AGENTS.md` and names starting with `.` or `_`), each with a relative link and a one-line purpose, and nothing that is no longer on disk. | Scripted (sync) and review (purposes) |

## Plugin audit checks

These apply to each target, for every tool that ships an [audit file](plugin-audit-format.md).

| ID | Check | How |
| --- | --- | --- |
| P1 | Every check the tool's `AUDIT.md` declares for this target passes. The finding names the tool and its check ID. | Scripted; commands after a yes, questions by review |
| P2 | The `AUDIT.md` follows the format and its paths stay inside their roots. | Scripted |

## Suggested actions

Every finding carries one suggested action, so the user knows who acts on it:

| Action | When | What happens |
| --- | --- | --- |
| **Fix in the audit** | Naming, formatting, headings, contents lists, links, layout entries, list entries, wording that keeps the meaning. | The audit proposes the exact change and applies it once approved. |
| **Use `skill-builder`** | A broken or contradictory procedure, missing files, a change to what a tool does or how its workflow runs, or an overlap between tools. | The audit changes nothing; the report recommends running `skill-builder` with the finding as evidence. |
| **Needs your decision** | A fact or choice only the user can give, such as a project purpose or which of two copies wins. | The report shows a `[TO FILL: …]` placeholder or the choice; the audit applies the answer once given. |

