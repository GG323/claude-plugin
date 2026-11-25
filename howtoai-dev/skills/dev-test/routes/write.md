# Route: write

Done: a test map with one row per criterion, the tests written in the repository before any product code, and a red check that proves each new test fails for its expected reason, after which the stage is `build`.

## Check the start

1. `DEVCORE state "<change folder>"` must show stage `tests-first` and an approval with `"what": "plan"`. Otherwise stop: a plan at `plan` or `accept` goes back to `dev-plan`, and a change past `build` takes the [Run](run.md) route.
2. The unit of work: the work item the user names, else the first item in `wi` whose `depends_on` items already have a green run in `test_runs`, else the whole plan when there is no split. Say which in one line.

## Read the inputs

1. From `plan.md`: the Verification section (criteria, end-to-end path, side effects, behaviour that must not change, cannot be verified here), the scope facts marked `test` or `untested`, and the Design details. From `wi/<n>.md`: its acceptance criteria and end-to-end check.
2. `WORKBOOK resolve --workspace "<workspace>" --stage tests-first --paths <the files the plan names, with their project files> --markdown`, and record the receipt as `WORKBOOK` returned it: `DEVCORE state "<change folder>" --patch '{"append": {"receipts": <receipt>}}'`. A technology in `missing` pauses only the tests that need it while `dev-workbook` runs its Create with the user.
3. New tests follow the existing tests next to the touched code (framework, layout, naming, fixtures, how they reach services); a pattern the workbook names as MUST wins over the local habit, and you say so.

## Map criteria to tests

1. Copy `dev-core`'s [test-map template](../../dev-core/assets/templates/test-map.md) to `<change folder>/test-map.md` (or `test-map-<n>.md` for a work item) with the file tools (see `dev-core`'s [Plan folder contract](../../dev-core/SKILL.md#plan-folder-contract)), and fill one row per criterion:
   - **Level:** unit, integration (database, queue, HTTP pipeline, file system), or end-to-end for the plan's end-to-end path, driven the way the plan says and written as a script file next to the tests, so the path is repeatable and its Test column names that file; when no script can fail before the code exists, the Expected red reason says why. `manual` or `not verifiable here` only when the plan's Verification section says so, with its reason.
   - **Expected red reason:** the failure that proves the test reaches the missing behaviour, for example "returns 200 instead of 429".
   - Each "Behaviour that must not change" entry is a criterion, numbered after the plan's criteria; its test must pass now and after the build.
   - A plan assumption a test can pin may get a row sourced `plan.md Assumptions` (optional).
2. A Characterization tests row for each untested neighbour in the scope facts. It pins today's observable behaviour with real inputs and outputs, and must pass before the build.
3. List each workbook statement that shaped a test under Workbook statements applied, by ID.
4. Resolve again with the new test files' paths added, record its receipt as in step 2 of [Read the inputs](#read-the-inputs), and add the statements that shaped a test. A test file in a technology in `missing` pauses as code does. Write an end-to-end script only in a language or tool that has a workbook; otherwise drive the path from the project's own test framework.

## Write the tests

1. Only test files, test data, test settings files (for example `appsettings.Test.json`, `.env.test` with test-only values), and the change folder change. Prefer tests that compile against today's code and fail by assertion; a test that needs a missing type or member still references it, and never add the type yourself.
2. Write the characterization and "must not change" tests first.
3. Data is synthetic only. Isolation is a rolled-back transaction per test, or a database or schema per run. Side effects go to a catcher or the provider's test mode, set in the test settings.
4. A test that would need a real external service with no test mode or catcher gets `not verifiable here` with the reason, and you tell the user.

## Red check

1. Run the tests through the [Run](run.md) route with the route name `red-check`: targets classified once, then the entry points in two passes with the framework's filter, into one `test-run-<n>.md`:
   - **Pass A:** the characterization and "must not change" tests, while the project still compiles. Skip it when there are none.
   - **Pass B:** the new tests.
2. Fill each Red result against the map:
   - **Failed as expected:** matches the expected red reason. A compile error naming the missing type or member counts for every new test in that test project.
   - **Passed early:** strengthen the test, or ask the user whether the criterion is already met; record the answer in Open points.
   - **Failed for another reason** (a fixture path, a missing package): the test is broken, not red. Fix it and rerun.
   - A failing characterization test is a wrong pin: fix it to match today's behaviour.
3. The map's Red check is `passed` when every testable criterion failed as expected and every characterization test passed; otherwise `failed`, and stop with the open points as questions.
4. On `passed`: `DEVCORE state "<change folder>" --patch '{"stage": "build"}'` (Run already recorded the run), say so in one line, and go on with `dev-build` in the same turn unless the user said to stop after the tests or a blocking question is open. Never ask whether to.
