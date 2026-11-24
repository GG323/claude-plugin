# Route: build

## Contents

- [Start the build](#start-the-build)
- [Consult the workbook](#consult-the-workbook)
- [Set the gate](#set-the-gate)
- [Snapshot and baseline](#snapshot-and-baseline)
- [Find the callers](#find-the-callers)
- [Climb the ladder and edit](#climb-the-ladder-and-edit)
- [Trace every hunk](#trace-every-hunk)
- [Run the gate](#run-the-gate)
- [Record and hand on](#record-and-hand-on)
- [Skills and agents](#skills-and-agents)

## Start the build

Entered from [SKILL.md](../SKILL.md#routes) at stage `build`, after a red-check run.

1. **The work item.** Build one work item per run: the one the user names, else the lowest-numbered work item in `state.json`'s `wi` list that has no `passed` entry in `builds` and whose `depends_on` items all have one. A change with no work items (a Small change) builds as `whole`: `--wi whole` for `BUILD`, and `"wi": null` in state, as `dev-test` records it.
2. **The build number** `<n>` is one more than the highest `n` in `builds`, and counts stopped builds too.
3. **Read the inputs:** `wi/<wi>.md` (Goal, Acceptance criteria, Out of scope, Agent prompt), the test map (`test-map-<wi>.md`, else `test-map.md`), the red-check report it names, and `plan.md`'s parts that the work item points to. Number the work item's acceptance criteria `AC1`, `AC2`, ... in the order they are listed; test-map rows are `T<#>` (row `1` is `T1`) and characterization rows `C<#>`. These are the only IDs a hunk can trace to; a change built as `whole` has no work item file, so its hunks trace to `T` and `C` rows only.
4. Tell the user in one line: "Building WI <wi>: <title> (build <n>)".

## Consult the workbook

1. `WORKBOOK resolve --workspace "<workspace>" --stage build --paths <the files the work item names or the plan's scope facts list, with their project files> --markdown`.
2. Record the receipt as returned: `DEVCORE state "<change folder>" --patch '{"append": {"receipts": <receipt>}}'`.
3. MUST and MUST NOT statements are rules for this build; the others are weighed. Keep the IDs you apply for the record's Workbook statements applied list and for the Source column of the ladder.
4. A technology in `missing` pauses only the part of the build that needs it, while `dev-workbook` runs its Create with the user: they choose to find a workbook or make one. Never write code for that technology from memory meanwhile.

## Set the gate

When `build.gate` in the settings is not empty, skip this section.

1. Look up the gate commands from files only: the lint, format-check, and build or type-check steps of the CI files (`.github/workflows/`, `azure-pipelines.yml`, `.gitlab-ci.yml`), `Makefile` targets, and `lint` or `typecheck` scripts in package files. For a step the CI does not have, take the check-mode command from the Commands statements resolved in [Consult the workbook](#consult-the-workbook) (for example `dotnet format --verify-no-changes`, the `dotnet.commands.002` statement), pointed at the project or solution the CI and the tests use. For a compiled language, the build is the type-check. Never take a command that changes files (a formatter without its check flag), because its edits would not trace to the work item.
2. Show them as one question ("Save these as the build gate?"), with the list as the recommendation: "From `<file>`: `<command>`" or "From workbook `<statement ID>`: `<command>`", in the order they run. The work item's tests are not part of this list; they run through `dev-test`.
3. After a yes, show the settings preview: `DEVCORE setup --workspace "<workspace>" --values '{"build": {"gate": [{"name": "format", "command": "<command>", "source": "<.github/workflows/ci.yml: lint, or a statement ID>"}]}}'`, adding `"cwd"` (relative to the workspace) only when a command must run in a subfolder, then write it with `--write` after the user approves the preview. Record the approval: `DEVCORE state "<change folder>" --patch '{"append": {"approvals": {"what": "build gate", "by": "user", "reply": "<the user's reply, word for word>"}}}'`.

## Snapshot and baseline

1. `BUILD start "<change folder>" --n <n> --wi <wi>`. It records the working tree as it is now, the failing tests included, so only the build's own changes count as hunks. Nothing is committed or staged.
2. Run every gate command once as the baseline, each exactly as `build.gate` has it: `BUILD gate "<change folder>" --n <n> --label baseline --name <name> --command "<command>"`.
3. A baseline failure was there before the build. Tell the user which command fails and its last output lines, and ask whether to go on with that command marked as failing before the build, or to stop. On a yes, record it: `DEVCORE state "<change folder>" --patch '{"append": {"approvals": {"what": "continue with pre-existing gate failure", "by": "user", "build": <n>, "gate": "<name>", "reply": "<the user's reply, word for word>"}}}'`. Never fix a baseline failure the work item does not cover, because that fix would not trace to it.

## Find the callers

Before changing an existing function, method, type, route, schema, or other contract, search for every place that uses it (the name across the repository, its interface and overrides, string references such as route names or serialized fields), and note what you found for the record's Callers checked table. A caller the change would break is part of the work item: fix it, or, when that reaches beyond the work item, stop and ask. Callers a search cannot find (reflection, dynamic dispatch) go under Skipped or unchecked.

## Climb the ladder and edit

1. For each thing the work item needs, take the first rung of [the ladder](../SKILL.md#the-ladder) that fully works, and note it as a Ladder decisions row (`L1`, `L2`, ...) with its source: the workbook statement, the existing code it reuses (`file:symbol`), `plan.md` or `wi/<wi>.md`, or `general`.
2. Edit only product code. Follow the MUST and MUST NOT statements, and the existing code's own structure and conventions.
3. A new package or dependency is the user's decision: ask, with what it gives over the rungs below it. Without a yes, stay on a lower rung.
4. When the approved work item itself names a test, test data, CI configuration, or lockfile path it changes, do not ask: the plan approval covers it. Record it as `{"approvals": {"what": "build may change <path>, named in WI <wi>", "by": "plan", "paths": ["<path>"]}}`; the script adds `"covers"`, the plan approval it rests on. Never record such a path as a new `"by": "user"` approval. When the work item needs such a change to a path it does not name, stop and ask; on a yes, record the approval with its paths: `{"approvals": {"what": "build may change <reason>", "by": "user", "paths": ["<path>"], "reply": "<the user's reply, word for word>"}}`. When one reply approves several items, record one approval whose `"what"` names them all (for example "WI 2 and WI 3"), never two records from one reply.
5. A request during the build to tidy, rename, reformat, or add something the work item does not name is out of scope. Do not do it; say so in one line and offer it as a new work item, and note it under Open points.

## Trace every hunk

1. `BUILD hunks "<change folder>" --n <n>` lists every hunk since the snapshot, with its ID and class.
2. Give each hunk one row in the record's Trace table: the hunk ID exactly as listed, the IDs it traces to (several, comma-separated), the ladder row, and one line on why the line is needed.
3. A hunk you cannot trace is not needed: revert it, then list the hunks again. A `test` or `protected` hunk without a recorded approval is reverted the same way. A `manifest` hunk needs the user's yes from the step above.

## Run the gate

1. Run every gate command with `--label after`, in order: `BUILD gate "<change folder>" --n <n> --label after --name <name> --command "<command>"`.
2. Then run the work item's tests through `dev-test`'s Run route as a progress run for this work item; the stage stays `build`. Run them no other way, and never before that route's target check has a clear verdict (`ok`, or an answer that covers this entry point); a target it asks about waits for the user's answer first.
3. On a failure, read the output lines `BUILD gate` returned or the test-run report, fix only your own hunks (or add the missing ones the failure shows the work item needs, with their trace rows), and run the whole gate and the tests again, because a fix can break an earlier step. Count each round: `DEVCORE state "<change folder>" --patch '{"increment": {"build-<n>-fix": 1}}'`.
4. At `build.max_fix_rounds` rounds without a green gate, stop: write the record with Result `stopped`, record the build as `stopped`, keep the stage `build`, and report what still fails and your reading of why, for the user to decide whether the plan, the test, or the design changes. Skip the rest of this section and [Record and hand on](#record-and-hand-on).

## Record and hand on

1. When the build changed a version that a code project's files state (`TargetFramework`, a `FROM` tag, `required_version`), run `dev-workbook`'s Record a version route for that code project now, with the user's yes, before you write the build record. A recording the user declines goes under Skipped or unchecked.
2. Write `<change folder>/build-<n>.md` from `dev-core`'s [build template](../../dev-core/assets/templates/build.md), with the date and time read from the system clock: every section, the Gate table from the `BUILD gate` results and the test-run report, and the fix rounds used.
3. **Skipped or unchecked**, the footer `dev-review` reads: what this build left out on purpose (rung 1 decisions, a smaller option not taken), what it could not check (callers a search cannot find, a platform it could not run, behaviour only an end-to-end check shows), and any risk the reviewer must know. At least one line; never "none" when something was left out.
4. `BUILD check "<change folder>" --n <n>`. Fix every error it lists and run it again; after a code change, that means the gate and the tests again. Report its warnings in the closing report.
5. Record the build and move the stage: `DEVCORE state "<change folder>" --patch '{"stage": "test", "append": {"builds": {"n": <n>, "wi": <wi or null>, "route": "build", "result": "passed", "hunks": <hunks>, "fix_rounds": <rounds>, "report": "build-<n>.md"}}}'`. When other work items are still unbuilt, keep the stage `build` and say which work item is next.
6. Close with the short report: result, the hunks and what they trace to, the gate, the Skipped or unchecked lines, and the next step: the next work item, or `dev-test`'s Run route for the whole suite. When the build passed and no blocking question is open, go on with that next step in the same turn, unless the user said to stop after the build. Never ask whether to.

## Skills and agents

- [SKILL.md](../SKILL.md) - the rules, [the ladder](../SKILL.md#the-ladder), the output contract, and the checks this route applies.
- `dev-core` - state, settings, and the build template; `dev-workbook` - Resolve and Create; `dev-test` - the Run route for the work item's tests.
- No agents are used.
