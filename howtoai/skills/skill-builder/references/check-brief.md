# Check brief

## Contents

- [Start the checker](#start-the-checker)
- [Your role](#your-role)
- [Inputs](#inputs)
- [The checks](#the-checks)
- [Return](#return)
- [Rerun](#rerun)
- [Skills and agents](#skills-and-agents)

## Start the checker

[Test](../stages/test.md#check) runs the checks below through a **checker**: a fresh built-in general-purpose subagent (in Claude Code, the Agent tool's `general-purpose` type), not a custom agent file. It starts without this conversation, so it judges the files as they are, not what the author meant them to say. This file is the only copy of the check list; Test and the checker both read it here.

Start the checker with this prompt, filled in:

```text
You are the checker in skill-builder's Test stage. Read
<absolute path of this file>, from the section "Your role" to the end,
and follow it. Stay read-only: do not change any file.

Target: <absolute path of the target's folder, or of each of its files>
Kind: <skill | slash command | subagent | plugin | mod | hook or settings |
  MCP server or connector | procedure>
Approved plan: <absolute path of the saved plan file, or the plan pasted below>
Changed files: <for a change, each file this run changed; "new" otherwise>
Location exception: <the approved plan's reason for a location outside the
  discovery paths, or "none">
Run checks: <"all", or the numbers of the checks to run>
```

## Your role

You check a target skill or tool that `skill-builder` has just built or changed: a skill, slash command, subagent, plugin, mod, hook or settings change, MCP server or connector, or a procedure built from these. You are not its author, and you do not fix anything.

- **Read-only.** Do not edit, create, move, or delete any file, do not install anything, and do not run the target, its scripts, or its tests. Read files, list folders, search them, and read `git status` or `git diff` where the folder is in git.
- **The one exception** is a syntax check that writes nothing, named in check 14.
- Do not start subagents, and do not ask the user anything; the user is unavailable.
- Links in this file resolve relative to its own folder, the `references/` folder of `skill-builder`. Read the files they point to when a check needs them.

## Inputs

- **Target** and **Kind:** what to check, and which rules apply to it. A check that cannot apply to this kind is not checked, with the reason "does not apply".
- **Approved plan:** what the target was meant to be; checks 5, 10, 12, and 13 compare the files with it.
- **Changed files:** tells a failure in text this run wrote from one that was already there.
- **Location exception:** the reason check 1 may pass with an exception.
- **Run checks:** run only those checks, in their numbered order.

## The checks

The numbers stay fixed, so the main agent can ask for a rerun by number.

1. **Discoverable.** The target's name and location follow the discovery rules for its kind in [Deliverable kinds](skill-types.md#deliverable-kinds); for a skill, the directory name matches frontmatter `name`, and the location is discoverable by the target harness. If the approved plan puts it outside a discovery path, record the check as passed with that exception; the test copy that [Test](../stages/test.md#how-tests-run) makes is discoverable.
2. **Metadata.** The frontmatter or manifest parses; `name` is 1–64 lowercase letters, digits, and single hyphens, with no leading or trailing hyphen; the description is at most 1,024 characters and states what the target does and when to use it; a `SKILL.md` is under 500 lines ([Metadata and discovery](../stages/build.md#metadata-and-discovery)).
3. **Links and conventions.** Relative links resolve and referenced files exist, and stay within the scope [Build](../stages/build.md#instructions) allows for the target's location (its own files; for a project skill, also the workspace's files); documentation follows the target repository's conventions, except files with a fixed format (see [Core rules](../SKILL.md#core-rules)); list those exempt files in the return.
4. **Script paths.** Every bundled script is called through the skill's own folder (`${CLAUDE_SKILL_DIR}` for Claude Code), never by a bare relative path.
5. **Output contract.** The output contract separates the deliverable from its report and states audience, format, and delivery. A document-like deliverable has a fixed structure, presentation, and format per the [standardized-output defaults](../SKILL.md#output-contract), or the approved plan's reason for departing from them.
6. **Stages.** If the workflow is split into stages, the files follow [Split the workflow into stages](../stages/build.md#split-the-workflow-into-stages): `SKILL.md` holds the overview, the shared rules, and the sections that rule keeps there; each stage file owns its own instructions and handoffs; and no instructions are split across files.
7. **One name per thing.** The instructions use one name per thing, following the stage, section, and step terms in [Vocabulary](../SKILL.md#vocabulary).
8. **Feedback.** The target has the **Feedback** section, last before `Skills and agents`, sending changes to `skill-builder` by name.
9. **State and sources.** Planned `state/` has defined seeding and update/prune rules; source links and paths are reachable, or the target asks the user when they fail.
10. **Requirements.** Every requirement the plan applied from [skill-types.md](skill-types.md) is written where [Build](../stages/build.md#instructions) places it, including privacy: no credentials, tokens, or real personal data in the target's files, examples, or test cases.
11. **Test cases.** Existing test cases in `evals/` follow [test-cases.md](test-cases.md), including case and grader names.
12. **Idea generation.** If the idea-generation option is used, the count, split, model choice, and **Choose one** step match the approved plan. If not used, nothing in the target implies it.
13. **Revisions.** For a change: no stale instructions or references remain in authorized files, and related skills found during planning are still consistent.
14. **Scripts.** Existing syntax or static checks for bundled scripts pass, when practical, using only checks that write nothing: for Python, `py -3 -B -c "import ast, sys; ast.parse(open(sys.argv[1], encoding='utf-8').read())" "<script>"` (never `py_compile`, which writes `__pycache__` into the target); for shell scripts, `bash -n "<script>"`. When the target bundles a check script, its code lists every check it ran and every check it skipped, with the reason, in its output.

## Return

Return one table with a row for every check you were asked to run, then two short lists.

```text
| # | Check | Result | Evidence |
| --- | --- | --- | --- |
| 1 | Discoverable | pass | <file>:<line> "<short quote>" |
| 3 | Links and conventions | fail | <file>:<line> links to <path>, which does not exist; text already there before this run |
| 12 | Idea generation | not checked | does not apply: the plan does not use it |
```

- **Result** is exactly one of `pass`, `pass (exception: <reason>)`, `fail`, or `not checked`.
- **Evidence** is a file path with a line number and a short quote, or a command with its output. "Looks fine" is not evidence. A `not checked` gives the reason it was skipped.
- For each `fail`, say what is wrong and where, and whether the failing text is in a file or line this run changed or was already there (from Changed files, or `git diff`).
- **Exempt files:** the fixed-format files check 3 excluded, or "none".
- **Commands run:** every command you ran, in order, or "none".

## Rerun

When the main agent sends check numbers to run again after its fixes, run only those checks on the current files and return the same table for them.

## Skills and agents

- [Test](../stages/test.md#check) — starts the checker, fixes what fails, and sends failed checks back here for a rerun.
- The checker is the harness's built-in general-purpose subagent; no custom agent definition is required.
- [skill-builder](../SKILL.md), [Build](../stages/build.md), [skill-types.md](skill-types.md), and [test-cases.md](test-cases.md) — the rules the checks compare the target with.
