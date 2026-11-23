# Workbook format

## Contents

- [What a workbook is](#what-a-workbook-is)
- [File and layers](#file-and-layers)
  - [Version workbooks](#version-workbooks)
- [Layout](#layout)
- [Header](#header)
- [Load when](#load-when)
- [Topic sections](#topic-sections)
- [Statements](#statements)
  - [Tags](#tags)
- [Overrides and conflicts](#overrides-and-conflicts)
- [What does not belong](#what-does-not-belong)
- [Skills and agents](#skills-and-agents)

## What a workbook is

A workbook is the technology documentation for one language or tool: facts, best practices, commands, and the user's and the project's situation with it. Every statement would still be true outside the dev process. `scripts/workbook.py` parses this format, so the headings, table rows, and statement syntax below are exact.

## File and layers

One Markdown file per technology, named `<technology>.md`, where `<technology>` is lowercase letters, digits, and hyphens (`csharp`, `dotnet`, `docker`, `terraform`). The same name in the dev settings' `workbooks.technologies` refers to it.

| Layer | Folder | Holds | ID numbers |
| --- | --- | --- | --- |
| base | the skill's `workbooks/` | The full workbook, shipped with the plugin | `001`, `002`, … |
| user | `~/.claude/howtoai/workbooks/` | The user's own preferences across projects | `u001`, `u002`, … |
| project | `<workspace>/.howtoai/workbooks/` | The project's choices, kept in its git | `p001`, `p002`, … |

A user or project file uses the same layout but holds only the sections it adds to; it may leave the others out. Project wins over user, and user wins over base.

### Version workbooks

Code projects can use different versions of one technology, for example one on .NET 8 and one on .NET 10, and each version gets its own workbook file.

- **Name.** `<technology>@<version key>.md`, for example `dotnet@8.md` or `csharp@12.md`. The key is lowercase letters, digits, dots, and hyphens, and the Header repeats it as `Version key`.
- **Content.** It is a full workbook for that one version, with every section and its own Versions and Supported until. Its statement IDs are the technology's own (`dotnet.patterns.001`). A copy of the general workbook keeps its IDs, so the user's and project's overrides still match.
- **Place.** It goes in the base folder when the plugin ships it, or in the project folder when it is made for a codebase. It never goes in the user folder. New statements in a project copy use `p` numbers.
- **When it is used.** The general `<technology>.md` covers the versions in its Header. A version workbook is used only for the code projects whose [Codebase versions](#header) line names it. In `resolve` it takes the base's place, and the user's and project's `<technology>.md` overlays still apply on top, because their choices hold for every version.

## Layout

In this order, with these exact headings:

1. `# <Title> workbook`
2. `## Contents` - links to every section below.
3. `## Header`
4. `## Load when`
5. The ten topic sections, in the order of [Topic sections](#topic-sections).
6. `## Skills and agents` - "`dev-workbook` - keeps this workbook; the dev skills read it through `workbook.py resolve`."

## Header

A two-column table, then a Sources list, and in the project's `<technology>.md` a Codebase versions list:

```markdown
## Header

| Key | Value |
| --- | --- |
| Technology | `csharp` |
| Title | C# |
| Versions | C# 14 and 15 (.NET 10 and 11) |
| Supported until | 2028-11-14 |
| Version command | `dotnet --version` |
| Layer | base |
| Updated | 2026-11-18 |

Sources:

- [C# documentation, Microsoft Learn](https://learn.microsoft.com/dotnet/csharp/) · checked 2026-11-18
- [dotnet/skills](https://github.com/dotnet/skills) · checked 2026-11-18 · MIT, secondary source
```

- **Supported until** is optional: `YYYY-MM-DD`, the earliest end-of-support date among the versions in Versions, from the vendor's support policy page listed in Sources. Audit reports it once it has passed or is near. A passed date in the general base or user workbook means that workbook is out of date. In a version workbook, it means that version is out of support: an upgrade is due at some point, and the workbook stays as long as code projects use the version.
- **Version key** appears only in a [version workbook](#version-workbooks).
- **Codebase versions** appear only in the project's `<technology>.md`, with one line per code project that uses the technology:

  ```markdown
  Codebase versions:

  - `src/Api/` · .NET 8 · workbook: `dotnet@8` · supported until 2026-11-10 · source: `src/Api/Api.csproj` · checked 2026-11-20
  - `src/Worker/` · .NET 10 · workbook: `dotnet` · supported until 2028-11-14 · source: `src/Worker/Worker.csproj` · checked 2026-11-20
  ```

  Each line gives:
  - the code project's folder, or `./` for the whole repository;
  - the version as the project's files state it;
  - the workbook that covers it: the general one, or a version workbook;
  - its end-of-support date, or `unknown`;
  - the file that states the version;
  - the date it was read.

  A path belongs to the deepest folder that holds it. The codebase's version decides which statements apply, so a passed date means an upgrade is due at some point, not that the code is wrong. `record-version` writes these lines.
- **Version command** is optional: a read-only command that prints the installed version. Audit runs it only with the user's go-ahead.
- **Updated** is the date the file last changed, from the system clock.
- Every source a statement cites is listed here with the date it was last opened. A secondary source names its license.

## Load when

A one-column table of file globs that mark the technology in a change. `resolve` matches changed paths against them.

```markdown
## Load when

| Glob |
| --- |
| `**/*.cs` |
| `**/*.csproj` |
```

## Topic sections

Exactly these ten, in this order. The slug is the middle part of a statement ID.

| Section heading | Slug | Holds |
| --- | --- | --- |
| `## Overview` | `overview` | What the technology is for, its strengths and limits, when it fits |
| `## Setup and configuration` | `setup` | Installation, project configuration, recommended settings |
| `## Idioms and patterns` | `patterns` | Recommended practices, as MUST, SHOULD, or MUST NOT |
| `## Pitfalls` | `pitfalls` | Common mistakes and anti-patterns, each with how to spot it |
| `## Commands` | `commands` | Lint, format, type-check, build, test-runner, and CLI commands with flags |
| `## Testing` | `testing` | Test frameworks, fixtures, mocking, container support |
| `## Security` | `security` | Secure-use practices and risky APIs |
| `## Performance` | `performance` | Known costs and tuning |
| `## Deployment and operations` | `deploy` | Packaging, release, rollback, runtime practices |
| `## Our situation` | `situation` | The user's and the project's choices: versions, conventions, approved packages, environments, accounts by name only, never secrets |

A section with no statements holds one bullet: `- none yet`.

## Statements

One statement per bullet, on one line:

```markdown
- **csharp.patterns.004** · MUST · Use `await using` for `IAsyncDisposable` resources. · tags: lifecycle, async · source: [Implement DisposeAsync](https://learn.microsoft.com/dotnet/standard/garbage-collection/implementing-disposeasync) · confirmed: base, 2026-11-18
```

- **ID:** `<technology>.<slug>.<number>`, with the number from the file's layer (`004`, `u004`, `p004`). IDs are never reused or renumbered; a removed statement leaves a gap.
- **Level:** optional; `MUST`, `SHOULD`, or `MUST NOT`. Use it in Idioms and patterns and Security; leave it out where it adds nothing.
- **Tags:** one to three subject [tags](#tags), comma-separated, after the text. Required in base workbooks.
- **Text:** one or two plain sentences, with commands and code in backticks. It never contains ` · `, the separator.
- **Source:** a Markdown link to the page the fact comes from, listed in the Header's Sources. For the project's own facts, the file that shows it (`` `Dockerfile` ``) or "user, <date>".
- **Confirmed:** who confirmed it and when: `base, <date>` for the shipped layer, `user, <date>` or `project, <date>` for facts the user approved.

### Tags

A search finds a statement by tool (from the ID), section, level, and subject tag, so a tag never repeats the tool. The list is closed, and `validate` refuses any other:

`access`, `async`, `build`, `caching`, `cli`, `config`, `data`, `dependencies`, `di`, `errors`, `formatting`, `health`, `http`, `image`, `lifecycle`, `linting`, `logging`, `modules`, `nullability`, `performance`, `secrets`, `state`, `strings`, `style`, `tests`, `versions`.

A new tag changes this list and `TAGS` in `scripts/workbook.py` together. A statement that replaces another keeps that one's tags and level unless it states its own. Give `MUST` or `MUST NOT` to a statement that must never be missed: only those load whatever the search.

## Overrides and conflicts

- A user or project statement with the same ID as a lower layer's replaces it in `resolve`'s output.
- To withdraw a lower statement, a higher layer repeats its ID with the text `withdrawn: <reason>`.
- When two layers hold the same ID with different text and the higher one does not say why, `resolve` reports a conflict; `dev-workbook` shows it to the user instead of choosing silently.
- New user and project statements use their own numbers (`u…`, `p…`), so a later base update never collides with them.

## What does not belong

Process instructions never go in a workbook: when to test, what to ask the user, approvals, review rounds, stage order, or what a skill does next. They live in the skills; `dev-learn` routes changes to them through `skill-builder`. A statement that only makes sense inside this dev process is a process instruction.

## Skills and agents

- `dev-workbook` - owns this format and every workbook; `scripts/workbook.py` parses it.
- `dev-learn` - receives process instructions that do not belong here.
