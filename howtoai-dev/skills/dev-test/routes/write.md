# Route: write

## Contents

- [Check the start](#check-the-start)
- [Read the inputs](#read-the-inputs)
- [Map criteria to tests](#map-criteria-to-tests)
- [Write the tests](#write-the-tests)
- [Red check](#red-check)
- [Skills and agents](#skills-and-agents)

## Check the start

1. `DEVCORE state "<change folder>"` must show stage `tests-first` and an approval with `"what": "plan"`. Otherwise stop: a plan at `plan` or `accept` goes back to `dev-plan`, and a change past `build` takes the [Run](run.md) route.
2. Pick the unit of work: the work item the user names, else the first item in `wi` whose `depends_on` items already have a green run in `test_runs`, else the whole plan when there is no split. Say in one line which one, for example "Writing tests for work item 2: lockout after five failures".

## Read the inputs

1. From `plan.md`: the Verification section (criteria, end-to-end path, side effects, behaviour that must not change, cannot be verified here), the Scope and size facts marked `test` or `untested`, and the Design details for the files and interfaces. From `wi/<n>.md`: its acceptance criteria and end-to-end check.
2. Resolve the workbook statements: `WORKBOOK resolve --workspace "<workspace>" --stage tests-first --paths <the files the plan names, with their project files> --topics testing commands situation`. Record the receipt as `WORKBOOK` returned it: `DEVCORE state "<change folder>" --patch '{"append": {"receipts": <receipt>}}'`. A technology in `missing` pauses only the tests that need it while `dev-workbook` runs its Create with the user.
3. Look at the existing tests next to the touched code: framework, project layout, naming, fixtures, helpers, how they reach databases and services. New tests follow what is there; a pattern the workbook names as MUST wins over the local habit, and you say so.

## Map criteria to tests

1. Copy `dev-core`'s [test-map template](../../dev-core/assets/templates/test-map.md) to `<change folder>/test-map.md` (or `test-map-<n>.md` for a work item) and fill one row per criterion:
   - **Level:** unit for logic in one class or function; integration for a database, queue, HTTP pipeline, or file system; end-to-end for the plan's end-to-end path, driven the way the plan says (browser, terminal, or HTTP calls); `manual` or `not verifiable here` only when the plan's Verification section says so, with its reason.
   - **Expected red reason:** what failure proves the test reaches the missing behaviour, for example "returns 200 instead of 429" or "`LockoutPolicy` does not exist yet".
   - Each "Behaviour that must not change" entry is a criterion too, numbered after the plan's criteria: its test must pass now and after the build.
   - An assumption in the plan that a test can pin (for example "items are counted by quantity") may get a row with the source `plan.md Assumptions`; it is optional.
2. Add a Characterization tests row for each untested neighbour in the scope facts: code next to the change that no test covers. The test pins today's observable behaviour, with real inputs and outputs, and must pass before the build.
3. List each workbook statement that shaped a test under Workbook statements applied, by ID.

## Write the tests

1. Write the tests in the files the map names. Only test files, test data, test settings files (for example `appsettings.Test.json`, `.env.test` with test-only values), and the change folder change; the `dev-test-first` hook blocks the rest. Prefer tests that compile against today's code and fail by assertion. A test that needs a type or member that does not exist yet still references it, so it fails to compile for the expected reason; never add the type yourself.
2. Write the characterization and "must not change" tests first, so the red check's first pass runs them while the project still compiles.
3. Data: generated or hand-written synthetic data only. Isolation: a rolled-back transaction per test, or a database or schema per run. Side effects: a catcher or the provider's test mode, configured in the test settings.
4. A test that would need a real external service with no test mode or catcher gets `not verifiable here` in the map with the reason, and you tell the user.

## Red check

1. Run the tests through the [Run](run.md) route with the route name `red-check`. It classifies targets once, then runs the entry points in two passes with the framework's filter (from the workbook's Commands statements), and writes one `test-run-<n>.md`:
   - **Pass A:** the characterization tests and the "must not change" tests, written before the new ones, while the project still compiles. Skip it when there are none.
   - **Pass B:** the new tests.
2. Read each result against the map, and fill its Red result column:
   - **Failed as expected:** the failure matches the expected red reason. A compile error naming the missing type or member counts for every new test in that test project.
   - **Passed early:** the behaviour exists already, or the test asserts too little. Strengthen the test, or ask the user whether the criterion is already met; record the answer in Open points.
   - **Failed for another reason:** the test is broken (a fixture path, a missing package reference, a wrong setup). Fix the test and rerun; this is not a red.
   - A characterization test that fails is a wrong pin: fix it to match today's behaviour.
3. Set the map's Red check line to `passed` when every testable criterion failed as expected and every characterization test passed; otherwise `failed`, and stop with the open points as questions.
4. On `passed`: `DEVCORE state "<change folder>" --patch '{"stage": "build"}'` (the red check's run is already recorded by the Run route). Tell the user in one line, for example "Red check passed: 7 new tests fail as expected, 2 characterization tests pass. Next: dev-build."

## Skills and agents

- `dev-core` - state and the test-map template.
- `dev-workbook` - the Testing, Commands, and Our situation statements.
- [Run](run.md) - runs the red check.
- No agents are used.
