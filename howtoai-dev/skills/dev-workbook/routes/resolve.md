# Resolve

## Contents

- [Steps](#steps)
- [Common failures](#common-failures)
- [Skills and agents](#skills-and-agents)

## Steps

`WORKBOOK` is the command [SKILL.md](../SKILL.md#routes) defines.

Called by a dev skill at each step that touches a technology.

1. Run `WORKBOOK resolve --workspace "<workspace>" --paths <paths> --stage <stage>`:
   - `--paths`: the changed or planned files, relative to the workspace, separated by spaces. Include the project files next to them that name the platform (for example the `.csproj` for a C# file), or pass `--technologies dotnet`, so platform workbooks are included.
   - **What comes back:** every MUST and MUST NOT of every workbook in the settings, and every other statement of the workbooks the paths match or `--technologies` names. When that is more than the step needs, narrow it with `--tags` (a tag from [format.md](../references/format.md#tags) or a section slug); the MUST rules stay. A result too long to print exact comes in parts: run the same command with each `--part N` it names and record each receipt. `--topics` is never for a dev step.
   - `--stage`: the calling stage: `plan`, `tests-first`, `build`, `test`, `review`, or `deploy`.
   - Technologies listed in the project's dev settings (`workbooks.technologies`) always bring their MUST rules. When the step knows a technology that no path shows, add `--technologies <names>` to get all of its statements. Use `--markdown` for the text to work from: its last line is the receipt. `--versions` returns the versions alone, without statements.
2. Hand the caller the returned statements, exact, with their IDs. MUST and MUST NOT statements are rules for the step; SHOULD and statements without a level are recommendations and facts the step weighs. Results are keyed by workbook. Each path gets the workbook named by its code project's Codebase versions line: a version workbook such as `dotnet@8`, or the general one. So one change can return `dotnet` for one code project and `dotnet@8` for another, and each code project follows the statements of its own version. When a code project's `support_ended` is true, say so once as an upgrade due at some point. It is not a reason to change the version within this step. Hand over the `receipt` too: when the caller has a change folder, it records it with `dev-core` (`devcore.py state "<change folder>" --patch '{"append": {"receipts": <receipt>}}'`); with no change folder, or an empty receipt, nothing is recorded.
3. **Missing:** a technology or version workbook (`dotnet@8`) in `missing` has no workbook. The other workbooks' statements are still returned and the caller goes on with them. Only the part of its step that needs the missing one pauses, while this skill runs [Create](create.md#steps) for it with the user.
4. **Unrecorded versions:** `unrecorded_paths` lists paths whose code project has no Codebase versions line for that technology, so they got the general workbook. Once per change, run [Record a version](record-version.md#steps) for each such code project, and go on with the general workbook until it is recorded. A code project the caller's change moves to another version is the exception: record nothing for the version it leaves; the caller records the new one after its change.
5. **Conflicts:** for each entry in `conflicts` (the user's and the project's layers disagree on one ID), show both texts and ask which applies; record the answer with [Propose](propose.md#steps). Overrides of the base are normal and are only mentioned.

## Common failures

| Symptom | Cause | Fix |
| --- | --- | --- |
| A statement does not parse | The text contains ` · `, or the line breaks the statement syntax | Reword without the separator; follow [references/format.md](../references/format.md#statements) |
| A technology the change touches is not returned | Its globs do not match, or it has no workbook | Check `missing`; add globs to the workbook's Load when through Propose or Create |
| A write refused for process wording | The statement says when or with whose approval something happens | Send it to `dev-learn`; rephrase only if it is really a technology fact |
| The same ID in two layers with different text | The user's and the project's layers disagree | Ask which applies, and record it with Propose |
| A code project gets statements for the wrong version | It has no Codebase versions line, or a parent folder's line covers it | Record a line for its own folder with Record a version; the deepest folder wins |

## Skills and agents

- `dev-workbook` - this route's skill; the stage skills call it at each step that touches a technology.
