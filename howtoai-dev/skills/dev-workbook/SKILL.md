---
name: dev-workbook
description: Keeps the technology documentation the howtoai-dev process uses - one workbook per language or tool (C#, .NET, Docker, Terraform, and any added later, plus one per version when code projects use different versions) with best practices, pitfalls, commands, testing, security, performance, deployment, and the user's and project's situation, in one standard format with stable statement IDs and three layers (base, user, project). Resolves the sections a dev step needs and returns a receipt, adds or corrects statements after approval, records each code project's version, finds or makes a workbook for a new technology or version, and audits workbooks for old sources and versions past their support date. Holds technology facts only, never process instructions. Use when a dev skill consults the workbook, when the user wants to add, correct, or see a technology rule or preference ("our base image is…", "we use xUnit"), when a technology has no workbook, or to audit the workbooks.
compatibility: Needs Python 3 (standard library only). Written for Claude Code; other harnesses run the script by its path relative to this skill's folder.
---

# Dev workbook

## Contents

- [What this skill keeps](#what-this-skill-keeps)
- [Before you start](#before-you-start)
- [Routes](#routes)
  - [Resolve](#resolve)
  - [Create](#create)
  - [Propose](#propose)
  - [Record a version](#record-a-version)
  - [Audit](#audit)
- [Output contract](#output-contract)
- [Verify the output](#verify-the-output)
- [Common failures](#common-failures)
- [What it can't do](#what-it-cant-do)
- [Feedback](#feedback)
- [Skills and agents](#skills-and-agents)

## What this skill keeps

A workbook is the technology documentation for one language or tool: facts and best practices, plus the user's and the project's situation with it. Every statement would still be true outside this dev process. Process instructions (when to test, what to ask, approvals, review rounds, stage order) never go in a workbook: they live in the dev skills, and changes to them go to `dev-learn`. This skill is the only reader and writer of workbook files; the other dev skills ask it for facts and send it proposals.

The format, the three layers, and the ID rules are in [references/format.md](references/format.md); read it before writing or judging a workbook. The shipped base workbooks are in [workbooks/](workbooks/).

## Before you start

1. **Python.** The script runs as `py -3 -I -B "${CLAUDE_SKILL_DIR}/scripts/workbook.py" <command>` (`python3 -I -B` outside Windows). From another dev skill, the path is `${CLAUDE_SKILL_DIR}/../dev-workbook/scripts/workbook.py`. Without Python 3, stop and say the dev skills need it. Call the chosen command `WORKBOOK` below.
2. **Workspace.** Use the workspace the caller passes; otherwise the one `dev-core` finds (`devcore.py root`). Project workbooks live in `<workspace>/.howtoai/workbooks/`, the user's own in `~/.claude/howtoai/workbooks/`.
3. Every command prints JSON (Resolve can print Markdown). `"ok": false` carries the error; report it and stop that step. Every command takes `--base-dir` and `--user-dir` to replace the default folders; tests use them so no real workbook is read or written.

## Routes

Take the route the caller names, or the one the user's request fits.

### Resolve

Called by a dev skill at each step that touches a technology.

1. Run `WORKBOOK resolve --workspace "<workspace>" --paths <paths> --topics <topics> --stage <stage>`:
   - `--paths`: the changed or planned files, relative to the workspace, separated by spaces. Include the project files next to them that name the platform (for example the `.csproj` for a C# file), or pass `--technologies dotnet`, so platform workbooks are included.
   - `--topics`: section headings or their slugs, separated by spaces, with each multi-word heading in quotes (`"Idioms and patterns" Pitfalls` or `patterns pitfalls`); leave it out for all sections.
   - `--stage`: the calling stage: `plan`, `tests-first`, `build`, `test`, `review`, or `deploy`.
   - Technologies listed in the project's dev settings (`workbooks.technologies`) are always included; add `--technologies <names>` when the step knows a technology without paths. Use `--markdown` when only the text is needed.
2. Hand the caller the matching statements (with IDs). MUST and MUST NOT statements are rules for the step; SHOULD and statements without a level are recommendations and facts the step weighs. Results are keyed by workbook. Each path gets the workbook named by its code project's Codebase versions line: a version workbook such as `dotnet@8`, or the general one. So one change can return `dotnet` for one code project and `dotnet@8` for another, and each code project follows the statements of its own version. When a code project's `support_ended` is true, say so once as an upgrade due at some point. It is not a reason to change the version within this step. Hand over the `receipt` too: when the caller has a change folder, it records it with `dev-core` (`devcore.py state "<change folder>" --patch '{"append": {"receipts": <receipt>}}'`); with no change folder, or an empty receipt, nothing is recorded.
3. **Missing:** a technology or version workbook (`dotnet@8`) in `missing` has no workbook. The other workbooks' statements are still returned and the caller goes on with them. Only the part of its step that needs the missing one pauses, while this skill runs [Create](#create) for it with the user.
4. **Unrecorded versions:** `unrecorded_paths` lists paths whose code project has no Codebase versions line for that technology, so they got the general workbook. Once per change, run [Record a version](#record-a-version) for each such code project, and go on with the general workbook until it is recorded.
5. **Conflicts:** for each entry in `conflicts` (the user's and the project's layers disagree on one ID), show both texts and ask which applies; record the answer with [Propose](#propose). Overrides of the base are normal and are only mentioned.

### Create

For a technology with no workbook, or a version workbook a code project needs (`dotnet@8`).

**Version workbook.** Ask one question, with the `grilling` skill's method: "Make a <technology> <version> workbook for <code project>?" State the default: a copy of the general workbook, checked against that version's docs. On a yes:

1. Run `WORKBOOK skeleton --tech <name> --version-key <key> --copy-base --title "<Title> <version>" --layer project --out "<workspace>/.howtoai/workbooks/<name>@<key>.md"`. The copy keeps the general workbook's statement IDs.
2. Check every statement against the official documentation for that version, opening every page cited (long pages in short ranges).
   - Keep a statement that holds, and set its confirmed part to `project, <date>`.
   - Correct a statement that differs, keeping its ID.
   - Delete one that does not apply, leaving a gap in the numbers.
   - Add statements specific to the version with `p` numbers.
3. Set Versions, and Supported until from the vendor's support policy page, listed in Sources with today's date.
4. Validate it (`WORKBOOK validate <file>`) and show the user a summary: counts per section, and statements kept, corrected, deleted, and added. Skip the rest of this section.

**New technology.** Ask the user, with the `grilling` skill's method, one crucial question: find and download a workbook, or make one. Recommend make when an official documentation site exists, because it gives current, cited statements without third-party text. State the defaults: a project workbook at `.howtoai/workbooks/<technology>.md`, about 4 to 8 statements per section. Frameworks and package managers belong to their language's workbook unless the project uses them heavily enough for their own (ask when unsure). When the user cannot be reached, return the question to the caller; never make a workbook without the answer.

- **Find:** search with `skill-finder` for skills or rule sets covering the technology. A candidate is used only after `skill-finder` vets it; convert it to the format, strip every process part (workflows, personas, stage steps, what the agent must ask), cite it as a source with its license, and keep only statements its own text supports.
- **Make:** run `WORKBOOK skeleton --tech <name> --title "<Title>" --layer project --out "<workspace>/.howtoai/workbooks/<name>.md"`, then fill each section from the technology's official documentation for the version the project uses, opening every page cited (long pages in short ranges, so a summarising read hook does not stand in for the text), and from the codebase's own conventions for Our situation. About 4 to 8 statements per section, chosen for what agents most often get wrong.
- Validate the result (`WORKBOOK validate <file>`), show the user a summary (counts per section, sources), and add the technology to `workbooks.technologies` in the dev settings through `dev-core`'s Setup preview. A base workbook (shipped with the plugin) is created only when building the plugin, never in a user's run.

### Propose

For a new or corrected fact from a dev step, a review finding, `dev-learn`, or the user.

1. Check it is technology, not process, before anything else: would it still be true outside this dev process? If it says when, in what order, or with whose approval something happens, it is process, even when it is the user's own preference ("always ask me before changing the Dockerfile"). Hand it to the `dev-learn` skill by name with the user's words, the technology, and why it is process (an enforceable one may become a hook rule in the dev settings), and tell the user where it went. When `dev-learn` is not installed, tell the user the rule was not recorded and give them its text to keep. Skip steps 2 to 4.
2. Decide the workbook and layer. The workbook is the technology the fact is about (a base image is a Docker fact, even for a .NET app). The layer is **project** for this project's choices and facts (the default) or **user** for the user's own preferences across projects. Base workbooks change only through `skill-builder` when the plugin is built.
3. Preview it: `WORKBOOK propose --workspace "<workspace>" --tech <name> --section <slug> --text "<one or two sentences>" --source "<link or file>" [--level MUST|SHOULD|"MUST NOT"] [--layer project|user] [--replaces <ID>]`. For a fact from the project's own files, the source is the file name in backticks, for example `` `Dockerfile` ``. The preview gives the new ID, likely duplicates, and process wording. For a duplicate, propose a replacement of that ID instead; for flagged wording, recheck step 1. The first write to a project or user workbook creates it with only the sections it uses.
4. Show the user the statement line (and, for a replacement, the old text) and ask "Add this to the <layer> <technology> workbook?". After a clear yes, run the same command with `--write` (and `--allow-process-wording` only when the user agrees the flagged words describe the technology). Secrets are always refused.

A fact true only for one version goes to that version's project workbook: `--tech <name>@<key>`, once [Create](#create) has made it. A choice that holds for every version goes to `--tech <name>`.

### Record a version

For each code project that uses a technology, the project's `<technology>.md` records which version it uses. A repository can hold code projects on different versions.

1. Read the version from the code project's own files, never from memory. Examples: `TargetFramework` in the `.csproj` for .NET, `LangVersion` or the target framework's default for C#, the `FROM` tag for Docker, `required_version` for Terraform.
2. Choose the workbook:
   - the general `<technology>` when its Header Versions cover the version;
   - else `<technology>@<major version>`, made through [Create](#create) when it does not exist yet.
3. Take the end-of-support date from that workbook's Supported until, or from the vendor's support page, or use `unknown`.
4. Preview: `WORKBOOK record-version --workspace "<workspace>" --tech <name> --path <code project folder> --version "<as the files state it>" --workbook <name or name@key> --supported-until <date|unknown> --source "`<file>`"`. Record each technology separately, for example both `dotnet` and `csharp` for a .NET project.
5. Show the user the line (and the line it replaces) and ask "Record this version for <code project>?". After a clear yes, run it again with `--write`.

### Audit

On the user's request, or when `environment-audit` asks.

1. Run `WORKBOOK audit --workspace "<workspace>"`. It lists format errors, sources checked more than 180 days ago, project or user statements that replace a base ID no longer there, support dates that have passed (`support_ended`) or are less than 180 days away (`support_ending`), Codebase versions lines read more than 180 days ago (in `old_sources`), and lines whose version workbook does not exist (`missing_version_workbooks`). Each `support_ended` entry carries its `meaning`:
   - A general base or user workbook: the workbook is out of date. Refresh its versions from the vendor's support page.
   - A version workbook or a code project's line: that version is out of support. Report an upgrade to plan at some point, never a fault to fix now.
2. Ask before checking installed versions, because it runs each workbook's read-only Version command (such as `dotnet --version`); with a yes, add `--run-version-commands`.
3. Report the list, with the checks it ran and the ones it skipped and why (`checks_run`, `checks_skipped`); fix project and user workbooks through [Propose](#propose) after approval. Base workbook fixes go to `skill-builder`.

## Output contract

- **Resolve:** JSON (or Markdown) for the calling skill, keyed by workbook, with the statements, each workbook's `code_projects` and `unrecorded_paths`, `missing`, `overrides`, `conflicts`, and a `receipt`. The caller tells the user only what needs them: a missing workbook, an unrecorded version, a version out of support, or a conflict.
- **Create:** a workbook file in the project layer (a new technology's `<technology>.md`, or a version workbook `<technology>@<key>.md`) that passes `validate`, and a one-line report: workbook, statements per section, sources opened.
- **Propose:** one statement line written to a project or user workbook after approval; report "Added `<ID>` to the <layer> <technology> workbook" or "Replaced `<ID>`".
- **Record a version:** one Codebase versions line written to the project's `<technology>.md` after approval; report "Recorded <version> for `<folder>` (workbook `<name>`)".
- **Audit:** a list in chat, grouped by format errors, old sources, orphan replacements, support ended or ending (each with its meaning), missing version workbooks, and versions; "none found" for an empty group.
- **Writes:** only project and user workbook files, and only after approval.

## Verify the output

- `WORKBOOK validate <file>` returns `"ok": true` for every workbook written or changed.
- After a Propose write, `resolve` for that technology returns the new statement with the expected layer.
- After any change to the script, run its tests: `py -3 -I -B "${CLAUDE_SKILL_DIR}/evals/test_workbook.py"`.

## Common failures

| Symptom | Cause | Fix |
| --- | --- | --- |
| A statement does not parse | The text contains ` · `, or the line breaks the statement syntax | Reword without the separator; follow [references/format.md](references/format.md#statements) |
| A technology the change touches is not returned | Its globs do not match, or it has no workbook | Check `missing`; add globs to the workbook's Load when through Propose or Create |
| A write refused for process wording | The statement says when or with whose approval something happens | Send it to `dev-learn`; rephrase only if it is really a technology fact |
| The same ID in two layers with different text | The user's and the project's layers disagree | Ask which applies, and record it with Propose |
| A code project gets statements for the wrong version | It has no Codebase versions line, or a parent folder's line covers it | Record a line for its own folder with Record a version; the deepest folder wins |

## What it can't do

- It does not decide process: the stage skills do, and `dev-learn` changes them.
- It does not verify that a statement is still true on the web by itself. Audit only flags sources by age and support dates by the date recorded in the Header; a check means opening the page again.
- It stores no secrets: accounts and profiles by name only.
- It does not notice by itself when a code project changes version. A recorded line stays until Record a version replaces it, and Audit flags lines read more than 180 days ago.

## Feedback

Send requested changes or reported problems to the `skill-builder` skill (`/skill-builder` in Claude Code), not by file path. If `skill-builder` is unavailable, agree the change with the user first, keep it as small as the problem needs, and check the skill afterwards.

## Skills and agents

- `dev-plan`, `dev-test`, `dev-build`, `dev-review`, `dev-deploy` - consult this skill through Resolve at each technology-touching step.
- `dev-learn` - sends technology fixes here through Propose and receives process instructions this skill refuses.
- `dev-core` - records the receipts and keeps `workbooks.technologies` in the settings.
- `skill-finder` - finds and vets a workbook source in Create.
- `grilling` - the question method in Create and for conflicts.
- `skill-builder` - changes this skill and the base workbooks.
- No agents are used.
