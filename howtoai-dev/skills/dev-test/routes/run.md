# Route: run

Done: the tests ran only against classified, non-production targets, through the project's entry points; `test-run-<n>.md` and state record the result; affected `TESTING.md` files are regenerated; every throwaway container is gone; a green run at stage `test` hands on to `dev-review`.

## Start the run

1. The route name is `red-check` when the [Write](write.md#red-check) route called it, `repro` when `dev-plan`'s scope stage called it, else `run`. `<n>` is one more than the highest `n` in `test_runs`; the run ID is `<change id>-<n>`.
2. For a `run` at stage `test`, every criterion in `test-map.md` (and each `test-map-<n>.md`) must end with a passing test. With no test map, compare against `plan.md`'s Verification section, and write "no test map" under Coverage and gaps.
3. For a `run` at stage `test`: `WORKBOOK resolve --workspace "<workspace>" --stage test --paths <the changed files and the test projects> --markdown`, apply it, and record the receipt as returned: `DEVCORE state "<change folder>" --patch '{"append": {"receipts": <receipt>}}'`.

## Find the entry points

1. Use `testing.entry_points`. When it is empty, look them up from files only (CI test steps in `.github/workflows/`, `azure-pipelines.yml`, `.gitlab-ci.yml`; `Makefile` test targets; package `test` scripts), plus the workbook's Commands statements for how results are written.
2. Show them as "From `<file>`: `<command>`" in one question, with the found list as the recommendation. After a yes, save them through `dev-core`'s Setup preview and `--write`: `{"testing": {"entry_points": [{"name", "command", "cwd", "results"}]}}`. Adding a results logger to a command CI runs is part of this question.
3. When CI calls a command the repository does not contain, say so and ask; never invent a replacement.

## Classify the targets

1. `TARGETS classify --workspace "<workspace>"`, adding `--ephemeral <host:port or container name>` for each container this run created.
2. Copy its targets into the report's Targets table (key, host, database, never values), then act on `verdict`:
   - **refused:** stop and run nothing. Write the report with result `refused`, record the run, tell the user which target or marker refused it (from `reasons`) and the fix: a test-scope override file, an allow-list item for a real test target, or removing the production marker from the test settings. Skip to [Record](#record).
   - **ask:** in one question, ask whether each unknown target is a test target to allow (with the evidence the allow item would match), unused by these tests, or to be replaced by a throwaway target. Name the entry points it is about (at stage `test`, every configured one): an answer covers only the entry points it was given for, so ask again before running another. Add allow items only through Setup's preview after the user's yes, then classify again.
   - **ok:** go on.
3. When the loaded test settings point email, SMS, payment, or webhook settings at a real provider, ask before running; recommend a catcher such as Mailpit or the provider's test mode.

## Throwaway target

Only when a test needs a service no allowed target provides and `testing.ephemeral` is `docker`; otherwise skip to [Run and read](#run-and-read).

1. Propose the service, a pinned image tag (from the workbook or the compose file), the port, and the test-only settings. Ask once; say it runs on this machine, bound to 127.0.0.1, and is removed at the end.
2. After a yes: `EPHEMERAL up --run-id <run id> --name <service> --image <image:tag> --port <port> [--env KEY=VALUE]`, and record it at once: `DEVCORE state "<change folder>" --patch '{"append": {"ephemeral": {"run_id": "<run id>", "name": "<container name>", "label": "howtoai.dev.run=<run id>", "state": "created"}}}'`.
3. Point the tests at it with environment variables for this run only, and classify again with `--ephemeral 127.0.0.1:<port>`.
4. When Docker is missing (`"ok": false`), say so and ask for another allowed target; never fall back to an unknown one.

## Run and read

1. **What runs.** At stage `test`, run every end-to-end script the test maps name after the entry points, each by its own command, with its own row in Results. Run every configured entry point, also those of projects the change does not touch; leave one out only after the user said yes to skipping it by name. When skipping leaves no entry point to run, or leaves a criterion without its test, do not run: record the run as `refused` with that reason, tell the user, and skip to [Record](#record).
2. **How.** Each entry point in order, from its `cwd`, with the test environment set (for example `ASPNETCORE_ENVIRONMENT=Test`). A red check or repro run adds the framework's filter per pass, by full test names, as the workbook's Commands statements describe. Each pass and rerun writes to its own folder under the entry point's results folder (for example `--results-directory "TestResults/<run id>-<the entry point's position>-a"`). Never use another command than the entry point, apart from the filter, that results folder, and the results options the user confirmed.
3. `RESULTS parse "<this pass's results folder>/*.trx"` (or the entry point's `results` pattern there). With no results file, use the exit code and summary line, and note "no result file".
4. **Flaky tests.** For a `run` with failures, rerun only the still-failing tests with the filter, up to `testing.reruns_per_test` times each and `testing.max_reruns` in all, each rerun in its own folder; a test leaves the list once it passes. Then `RESULTS merge --first <first results> --rerun <rerun 1> --rerun <rerun 2> ...`: passed in a rerun is flaky, failed every time is failed. A red check or repro run never reruns. Passed counts flaky tests too; Flaky counts them again, and Failures lists them as "flaky".
5. **Read each failure** as a real failure, expected red, flaky (with its rerun count), or an environment problem (target down, port in use, missing tool). Fix an environment problem and repeat the run once; it is never reported as a test result.
6. **Coverage and gaps:** coverage only when the entry point collects it ("not collected" otherwise; never add a coverage tool on your own). After a `run`, list criteria without a passing test.

## Record

1. Copy `dev-core`'s [test-run template](../../dev-core/assets/templates/test-run.md) to `<change folder>/test-run-<n>.md` and fill it with the file tools (see `dev-core`'s [Plan folder contract](../../dev-core/SKILL.md#plan-folder-contract)) from the `TARGETS` and `RESULTS` output and your reading. For a `run` at stage `test`, Results has one row for each configured entry point, with `skipped (user's yes)` in every figure for one the user skipped; other runs have a row per entry point or pass that ran. A row starts with the entry point's configured name and a colon; write a `|` in a command as `\|`, and `ran, no counts` as Passed when it ran without counts. Commit from `git rev-parse --short HEAD` ("no git" otherwise); date and time from the system clock.
2. `DEVCORE state "<change folder>" --patch '{"append": {"test_runs": {"n": <n>, "route": "<red-check, repro, or run>", "wi": <n or null>, "result": "<red, red-failed, green, or refused>", "passed": <n>, "failed": <n>, "flaky": <n>, "commit": "<sha>", "report": "test-run-<n>.md"}}}'`. A red check is `red` only when the map's Red check is passed, else `red-failed`. A `run` is `green` only when nothing failed in the end; flaky tests keep it green, and the report's Next names each for `dev-review`. A repro run is `red` when the test failed as predicted (reproduced) and `green` when it passed. A refused run is `refused` with 0 for passed, failed, and flaky.
3. **TESTING.md.** Skip for a refused or repro run. For each test folder the run touched, write its data file with the file tools (see `dev-core`'s [Plan folder contract](../../dev-core/SKILL.md#plan-folder-contract)) to `<change folder>/raw/testing-md-<n>-<the folder's position>.json` (keys `run`, the ISO date and time from the system clock such as `2026-11-19T16:12:00+01:00`; `commit`; and `environment`, `data`, `results`, `coverage`, `flaky`, `gaps`, `untested` as short text, no secrets), then `TESTINGMD update "<test folder>" --data "<that file>"`. For folders with no `TESTING.md`, ask the user once for all of them, without waiting when [Hand on](#hand-on) follows; after a yes, add `--create`, fill the base part (how to run, environments and data, fixtures, conventions) from this run, and show it. Finish with `TESTINGMD check --workspace "<workspace>" --dirs <those folders>`.
4. **Stage.** For a `run` at stage `test`, before `green` moves the stage to `review`, check that `state.json` holds a `test` receipt for this change; when it does not, do step 3 of [Start the run](#start-the-run) now and record its receipt, also one with no statements. Then `green` moves to `review` (`DEVCORE state "<change folder>" --patch '{"stage": "review"}'`) and `red` back to `build` with the failures as the reason; `refused` keeps the stage. A progress run at `build` changes no stage. A repro run changes no stage and returns to `dev-plan`'s [Reproduce](../../dev-plan/stages/scope.md#reproduce) section. A red check returns to [Write](write.md#red-check), which sets the stage.

## Tear down

Always, also after a refused or failed run, in the same turn the run started:

1. `EPHEMERAL down --run-id <run id>` (without Docker it reports `docker_missing` and removes nothing), then record each container this run created with the same `append.ephemeral` entry and `"state": "removed"`, or `"left"` with the error, telling the user the container name.
2. `EPHEMERAL sweep` removes orphans of earlier runs older than six hours; report what it removed.
3. Remove result folders and data files the run wrote outside the change folder and the repository's ignored output folders.

## Hand on

Only for a `run` that started at stage `test` and ended `green`, and not when the user said to stop after the tests (for example "don't review yet") or asked only which targets the tests hit or for a refreshed `TESTING.md`. A plain "run the tests", or a yes to one of this route's questions, hands on.

1. Do [Verify the output](../SKILL.md#verify-the-output). When it holds, or fails only because a `TESTING.md` is stale for `uncommitted changes after the last run`, say in one line that the tests are green and the code review starts, name any such file in the report's Next, and go on with `dev-review` in the same turn. Never ask whether to. When anything else fails, say what failed and stop.
2. A question that blocks nothing, such as creating `TESTING.md`, does not hold the review up: write it in the report's Next as `waiting: <question>`, with each test folder and its data file when it is about `TESTING.md`, and act on it after the user's yes.
