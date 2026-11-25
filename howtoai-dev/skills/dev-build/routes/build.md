# Route: build

Done: one work item's product code passes the gate and its tests, every hunk is traced, `build-<n>.md` is written and checked, and the build is recorded with the stage at `test` (or `build` while work items remain). Entered from [SKILL.md](../SKILL.md#routes) at stage `build`, after a red check.

## Start the build

1. **The work item:** the one the user names, else the lowest-numbered item in `wi` with no `passed` entry in `builds` whose `depends_on` items all have one. A change with no work items builds as `whole`: `--wi whole` for `BUILD`, and `"wi": null` in state.
2. **The build number** `<n>` is one more than the highest `n` in `builds`, stopped builds included.
3. **Inputs:** `wi/<wi>.md`, the test map (`test-map-<wi>.md`, else `test-map.md`), the red-check report it names, and the parts of `plan.md` the work item points to. Number the acceptance criteria `AC1`, `AC2`, ... in listed order; test-map rows are `T<#>` and characterization rows `C<#>`. These are the only IDs a hunk can trace to; a `whole` build traces to `T` and `C` rows only.
4. Tell the user: "Building WI <wi>: <title> (build <n>)".

## Consult the workbook

1. `WORKBOOK resolve --workspace "<workspace>" --stage build --paths <the files the work item names or the plan's scope facts list, with their project files> --markdown`.
2. Record the receipt as returned: `DEVCORE state "<change folder>" --patch '{"append": {"receipts": <receipt>}}'`.
3. MUST and MUST NOT statements are rules for this build; the rest are weighed. Keep the IDs you apply for the record and the ladder's Source column.
4. A technology in `missing` pauses only the part of the build that needs it, while `dev-workbook` runs its Create with the user. Never write code for that technology from memory meanwhile.

## Set the gate

Skip this section when `build.gate` is not empty.

1. Find the gate commands from files only: the lint, format-check, and build or type-check steps of the CI files (`.github/workflows/`, `azure-pipelines.yml`, `.gitlab-ci.yml`), `Makefile` targets, and `lint` or `typecheck` package scripts. For a step CI lacks, take the check-mode command from the resolved Commands statements (for example `dotnet format --verify-no-changes`, `dotnet.commands.002`), pointed at the project the CI and tests use. For a compiled language, the build is the type-check. Never take a command that changes files.
2. Ask one question, "Save these as the build gate?", listing in run order "From `<file>`: `<command>`" or "From workbook `<statement ID>`: `<command>`" as the recommendation. The work item's tests are not in it; they run through `dev-test`.
3. After a yes, preview `DEVCORE setup --workspace "<workspace>" --values-file "<file>"`, with the JSON written to a temporary file outside the workspace with the Write tool (production markers in a command's text make `dev-safe-target` deny it), for example `{"build": {"gate": [{"name": "format", "command": "<command>", "source": "<.github/workflows/ci.yml: lint, or a statement ID>"}]}}` (`"cwd"`, relative to the workspace, only for a subfolder), and `--write` it after the user approves the preview. Record: `DEVCORE state "<change folder>" --patch '{"append": {"approvals": {"what": "build gate", "by": "user", "reply": "<the user's reply, word for word>"}}}'`.

## Snapshot and baseline

1. `BUILD start "<change folder>" --n <n> --wi <wi>` records the working tree as it is, the failing tests included; nothing is committed or staged.
2. Run every gate command once, exactly as `build.gate` has it: `BUILD gate "<change folder>" --n <n> --label baseline --name <name> --command "<command>"`.
3. A baseline failure was there before the build: tell the user the command and its last output lines, and ask whether to go on with it marked as failing before the build, or stop. On a yes: `DEVCORE state "<change folder>" --patch '{"append": {"approvals": {"what": "continue with pre-existing gate failure", "by": "user", "build": <n>, "gate": "<name>", "reply": "<the user's reply, word for word>"}}}'`. Never fix a baseline failure the work item does not cover.

## Find the callers

Before changing an existing function, method, type, route, schema, or other contract, search for every use (the name, its interface and overrides, string references such as route names or serialized fields) for the Callers checked table. A caller the change would break is part of the work item: fix it, or stop and ask when that reaches beyond the work item. Callers a search cannot find (reflection, dynamic dispatch) go under Skipped or unchecked.

## Climb the ladder and edit

1. For each thing the work item needs, take the first rung of [the ladder](../SKILL.md#the-ladder) that fully works, as a Ladder decisions row (`L1`, `L2`, ...) with its source: a workbook statement, the reused code (`file:symbol`), `plan.md` or `wi/<wi>.md`, or `general`.
2. Edit only product code, following the MUST and MUST NOT statements and the code's own conventions.
3. A new package or dependency: ask, with what it gives over the lower rungs; without a yes, stay lower.
4. A test, test data, CI configuration, or lockfile path the approved work item names needs no question: the plan approval covers it. Record `{"approvals": {"what": "build may change <path>, named in WI <wi>", "by": "plan", "paths": ["<path>"]}}`; the script adds `"covers"`. Never record such a path as a new `"by": "user"` approval. For such a path the work item does not name, stop and ask; on a yes, record `{"approvals": {"what": "build may change <reason>", "by": "user", "paths": ["<path>"], "reply": "<the user's reply, word for word>"}}`. One reply that approves several items is one record whose `"what"` names them all.
5. A request during the build to tidy, rename, reformat, or add what the work item does not name: don't; say so in one line, offer it as a new work item, and note it under Open points.

## Trace every hunk

1. `BUILD hunks "<change folder>" --n <n>` lists every hunk since the snapshot, with its ID and class.
2. One Trace row per hunk: the hunk ID exactly as listed, the IDs it traces to, the ladder row, and one line on why it is needed.
3. Revert a hunk you cannot trace, or a `test` or `protected` hunk without a recorded approval, then list again. A `manifest` hunk needs the user's yes.

## Run the gate

1. Every gate command, in order: `BUILD gate "<change folder>" --n <n> --label after --name <name> --command "<command>"`.
2. Then the work item's tests through `dev-test`'s Run route as a progress run; the stage stays `build`. Run them no other way, and never before that route's target check has a clear verdict (`ok`, or an answer that covers this entry point).
3. On a failure, fix only your own hunks (or add the missing ones the work item needs, with trace rows), then rerun the whole gate and the tests. Count each round: `DEVCORE state "<change folder>" --patch '{"increment": {"build-<n>-fix": 1}}'`.
4. At `build.max_fix_rounds` without a green gate, stop: write the record with Result `stopped`, record the build as `stopped`, keep the stage `build`, and report what still fails and why, for the user to decide whether the plan, the test, or the design changes. Skip the rest of this section and [Record and hand on](#record-and-hand-on).

## Record and hand on

1. When the build changed a version that a code project's files state (`TargetFramework`, a `FROM` tag, `required_version`), run `dev-workbook`'s Record a version route for that code project now, with the user's yes, before you write the build record. A recording the user declines goes under Skipped or unchecked.
2. Write `<change folder>/build-<n>.md` from `dev-core`'s [build template](../../dev-core/assets/templates/build.md) with the file tools (see `dev-core`'s [Plan folder contract](../../dev-core/SKILL.md#plan-folder-contract)): every section, the date and time from the system clock, the Gate table from the `BUILD gate` results and the test-run report, and the fix rounds used.
3. **Skipped or unchecked**, the footer `dev-review` reads: what was left out on purpose, what could not be checked, and any risk the reviewer must know. At least one line; never "none" when something was left out.
4. `BUILD check "<change folder>" --n <n>`. Fix every error and run it again (after a code change, the gate and tests again too); report its warnings.
5. Record: `DEVCORE state "<change folder>" --patch '{"stage": "test", "append": {"builds": {"n": <n>, "wi": <wi or null>, "route": "build", "result": "passed", "hunks": <hunks>, "fix_rounds": <rounds>, "report": "build-<n>.md"}}}'`. While other work items are unbuilt, keep the stage `build` and say which is next.
6. Close with the short report, then go on with the next step (the next work item, or `dev-test`'s Run route for the whole suite) in the same turn, unless a blocking question is open or the user said to stop after the build. Never ask whether to.
