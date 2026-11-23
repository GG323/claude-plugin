---
name: dev-workbook
description: The one way to read and change the technology workbooks of the howtoai-dev process (C#, .NET, Docker, Terraform, Python, and any added later, with one per version where code projects differ). On load it gives every MUST and MUST NOT rule of the workspace's workbooks and how to search the other statements by tool, section, and subject tag, so each agent gets an exact, tailored subset. Also resolves a dev step's subset with a receipt, adds or corrects statements after approval, records each code project's version, finds or makes a workbook for a new technology or version, and audits workbooks. Holds technology facts only, never process instructions. Use before planning, writing, testing, reviewing, or judging work on a technology that has a workbook, when a dev skill consults the workbook, when the user wants to add, correct, or see a technology rule or preference ("our base image is…", "we use xUnit"), when a technology has no workbook, or to audit the workbooks.
compatibility: Needs Python 3 (standard library only). Written for Claude Code, which runs the loading command below; other harnesses run `scripts/workbook.py open` from this skill's folder and read what it prints.
allowed-tools: Bash(py -3 -I -B "${CLAUDE_SKILL_DIR}/scripts/workbook.py" open) Bash(python3 -I -B "${CLAUDE_SKILL_DIR}/scripts/workbook.py" open)
---

# Dev workbook

## Contents

- [This workspace's rules](#this-workspaces-rules)
- [Read the workbooks](#read-the-workbooks)
- [Routes](#routes)
- [Output contract](#output-contract)
- [Verify the output](#verify-the-output)
- [What it can't do](#what-it-cant-do)
- [Feedback](#feedback)
- [Skills and agents](#skills-and-agents)

## This workspace's rules

!`py -3 -I -B "${CLAUDE_SKILL_DIR}/scripts/workbook.py" open || python3 -I -B "${CLAUDE_SKILL_DIR}/scripts/workbook.py" open`

## Read the workbooks

The MUST and MUST NOT rules above bind all work on their technology. Get the other statements by search:

1. For each file you work on, cite, or report about, find its workbook in the list above by the file's name, and Grep the search file (`output_mode` content) for that tag, for example `#docker`. A project file's platform counts too: C# in a .NET project needs `#csharp` and `#dotnet`.
2. When that returns too much, or you need one subject, put two tags in the pattern in file order, the tool first, for example `#docker.*#secrets`. To check a cited statement, Grep its ID; for its source, Grep the ID in the sources file.
3. Use the text as returned, and cite the ID. When a result is cut, saved to a file, or summarized, search again with a narrower pattern. Never Read the search file or a workbook file, and never state a rule from memory.

## Routes

A dev stage, or a request to change or check a workbook, takes a route. A reviewer takes none. Call `py -3 -I -B "${CLAUDE_SKILL_DIR}/scripts/workbook.py"` (`python3 -I -B` outside Windows) `WORKBOOK`; from another dev skill its path is `${CLAUDE_SKILL_DIR}/../dev-workbook/scripts/workbook.py`. Use the workspace the caller passes, otherwise the one `dev-core` finds (`devcore.py root`). A result with `"ok": false` carries the error: report it and stop that step.

| Route | When |
| --- | --- |
| [Resolve](routes/resolve.md) | A dev step needs its subset with a receipt |
| [Create](routes/create.md) | A technology or version has no workbook |
| [Propose](routes/propose.md) | A fact is new or wrong |
| [Record a version](routes/record-version.md) | A code project's version is not recorded |
| [Audit](routes/audit.md) | The user or an audit asks for a check |

The format, layers, IDs, and tags are in [references/format.md](references/format.md). Project workbooks are in `<workspace>/.howtoai/workbooks/`, the user's in `~/.claude/howtoai/workbooks/`.

## Output contract

- **Reading:** exact statements with their IDs, for the agent doing the work. Loading writes only the generated search and sources files in `<workspace>/.howtoai/cache/`.
- **Resolve:** the subset and its receipt. The user hears only of a missing workbook, an unrecorded version, a version out of support, or a conflict.
- **Create, Propose, Record a version:** project or user workbook files, written only after approval, and a one-line report of what changed.
- **Audit:** a list in chat by kind of problem, "none found" for an empty one.

## Verify the output

`WORKBOOK validate <file>` returns `"ok": true` for every workbook written, and a search finds a statement just added. After a change to the script, run `evals/test_workbook.py`.

## What it can't do

- It holds technology facts, never process: the stage skills decide that, and `dev-learn` changes them.
- It stores no secrets, and it does not check by itself that a statement is still true or that a code project changed version.

## Feedback

Send requested changes or reported problems to the `skill-builder` skill (`/skill-builder` in Claude Code), not by file path. If `skill-builder` is unavailable, agree the change with the user first, keep it as small as the problem needs, and check the skill afterwards.

## Skills and agents

- `dev-plan`, `dev-test`, `dev-build`, `dev-review`, `dev-deploy`, `dev-learn` - consult this skill at each technology-touching step.
- The goldfish agents - preload this skill.
- `dev-core` - records the receipts; `skill-finder` and `grilling` - used in Create; `skill-builder` - changes this skill.
