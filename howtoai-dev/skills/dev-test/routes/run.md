# Route: run

## Contents

- [Start the run](#start-the-run)
- [Find the entry points](#find-the-entry-points)
- [Classify the targets](#classify-the-targets)
- [Throwaway target](#throwaway-target)
- [Run and read](#run-and-read)
- [Record](#record)
- [Tear down](#tear-down)
- [Skills and agents](#skills-and-agents)

## Start the run

1. The route name is `red-check` when the [Write](write.md#red-check) route called it, else `run`. The run number `<n>` is one more than the highest `n` in `test_runs`; the run ID is `<change id>-<n>`.
2. For a `run` at stage `test`, read `test-map.md` (and each `test-map-<n>.md`): every criterion there must end with a passing test. When the change has no test map (it skipped the Write route), compare against the criteria in `plan.md`'s Verification section instead, and write "no test map" under Coverage and gaps.

## Find the entry points

1. Use `testing.entry_points` from the settings. When it is empty, look them up from files only: the test steps of the CI files (`.github/workflows/`, `azure-pipelines.yml`, `.gitlab-ci.yml`), `Makefile` test targets, and `test` scripts in package files, plus the workbook's Commands statements for how results are written (for example `dotnet test --logger trx --results-directory TestResults`).
2. Show what you found as "From `<file>`: `<command>`" and ask the user to confirm, as one question with the found list as the recommendation. After a yes, save it through `dev-core`'s Setup preview and `--write`: `{"testing": {"entry_points": [{"name", "command", "cwd", "results"}]}}`. Adding a results logger to a command CI runs is a change to the command, so it is part of this question.
3. When CI calls a command the repository does not contain, say so and ask; never invent a replacement.

## Classify the targets

1. Run `TARGETS classify --workspace "<workspace>"`, adding `--ephemeral <host:port or container name>` for each container this run created.
2. Copy its targets into the Targets table of the report (key, host, database, never values). Then act on `verdict`:
   - **refused:** stop. Do not run anything. Write the report with result `refused`, record the run, and tell the user which target or marker refused it (from `reasons`) and what would fix it: a test-scope override file, an allow-list item for a real test target, or removing the production marker from the test settings. Skip to [Record](#record).
   - **ask:** show the unknown targets and ask, in one question, whether each is a test target to add to the allow list (with the evidence the allow item would match), is not used by these tests, or should be replaced by a throwaway target. Add allow items only through Setup's preview after the user's yes, then classify again.
   - **ok:** go on.
3. Scan the test settings the run will load for real side effects: email, SMS, payment, or webhook settings that point at a real provider. Ask before running when one does; recommend a catcher such as Mailpit or the provider's test mode.

## Throwaway target

Only when a test needs a service that no allowed target provides, and `testing.ephemeral` is `docker`; otherwise skip to [Run and read](#run-and-read).

1. Propose the container: the service, a pinned image tag (from the workbook or the project's compose file), the container port, and the test-only settings. Ask once; say it runs on this machine, bound to 127.0.0.1, and is removed at the end.
2. After a yes: `EPHEMERAL up --run-id <run id> --name <service> --image <image:tag> --port <port> [--env KEY=VALUE]`. Record it at once: `DEVCORE state "<change folder>" --patch '{"append": {"ephemeral": {"run_id": "<run id>", "name": "<container name>", "label": "howtoai.dev.run=<run id>", "state": "created"}}}'`.
3. Point the tests at it with environment variables for this run only (for example `ConnectionStrings__Shop=Host=127.0.0.1;Port=<port>;...`), and classify again with `--ephemeral 127.0.0.1:<port>`.
4. When Docker is missing (`"ok": false`), say so and ask for another allowed target; never fall back to an unknown one.

## Run and read

1. Run each entry point, in order, from its `cwd`, with the test environment set for the run (for example `ASPNETCORE_ENVIRONMENT=Test`, or what the workbook's Testing statements name). For a red check, add the filter for each pass where the framework has one, selecting the tests by their full names (for example `--filter "FullyQualifiedName~TenItems|FullyQualifiedName~NineItems"` for .NET, as the workbook's Commands statements describe). Each pass and each rerun writes its results to its own folder under the entry point's results folder (for example `--results-directory TestResults/<run id>-a`), so files from different passes never mix. Never use another command than the entry point, apart from the filter, that results folder, and the results options the user confirmed.
2. Read the results: `RESULTS parse "<this pass's results folder>/*.trx"` (or the entry point's `results` pattern applied inside that folder). When no results file exists, use the command's exit code and summary line, and note "no result file" in the report.
3. **Flaky tests.** For a `run` with failures, rerun only the tests still failing, with the framework's filter, up to `testing.reruns_per_test` times each and `testing.max_reruns` reruns in all, writing each rerun's results to its own folder. A test leaves the rerun list as soon as it passes once; stop when the list is empty. Then `RESULTS merge --first <first results> --rerun <rerun 1> --rerun <rerun 2> ...`: a test that passed in a rerun is flaky, and one that failed every time is failed. A red check does not rerun: a new test that passes on a rerun is broken.
   In the report and in state, Passed counts every test that passed in the end, flaky ones included; Flaky counts the flaky ones again, and Failures lists them with the reading "flaky".
4. **Read each failure:** real failure (the behaviour is wrong), expected red (a red check), flaky (with the rerun count), or environment problem (a target down, a port in use, a missing tool). An environment problem is fixed and the run repeated once; it is never reported as a test result.
5. **Coverage and gaps:** report coverage when the entry point collects it ("not collected" otherwise; never add a coverage tool on your own). Compare with the test maps: list criteria without a passing test after a `run`.

## Record

1. Copy `dev-core`'s [test-run template](../../dev-core/assets/templates/test-run.md) to `<change folder>/test-run-<n>.md` and fill it from the `TARGETS` and `RESULTS` output and your reading. The commit is `git rev-parse --short HEAD` ("no git" otherwise), the date and time from the system clock.
2. Record the run: `DEVCORE state "<change folder>" --patch '{"append": {"test_runs": {"n": <n>, "route": "<red-check or run>", "wi": <n or null>, "result": "<red, green, or refused>", "passed": <n>, "failed": <n>, "flaky": <n>, "commit": "<sha>", "report": "test-run-<n>.md"}}}'`. A red check whose new tests failed as expected is `red`; a `run` is `green` only when nothing failed in the end (a test that failed and then passed on a rerun is flaky: the run stays green and the report's Next names each flaky test for `dev-review`); a refused run records `refused` with 0 for passed, failed, and flaky.
3. **TESTING.md.** Skip for a refused run. For each test folder the run touched, write the data file (keys `run`, the run's ISO date and time from the system clock such as `2026-11-19T16:12:00+01:00`; `commit`; and `environment`, `data`, `results`, `coverage`, `flaky`, `gaps`, `untested` as short text, no secrets) to `<change folder>/raw/testing-md-<n>.json`, then `TESTINGMD update "<test folder>" --data "<that file>"`. When the folder has no `TESTING.md`, ask the user once for all such folders; after a yes, add `--create` and fill the base part (how to run, environments and data, fixtures, conventions) from what this run used, then show it. Finish with `TESTINGMD check --workspace "<workspace>" --dirs <those folders>`.
4. **Stage.** A `run` at stage `test`: `green` moves to `review` (`DEVCORE state "<change folder>" --patch '{"stage": "review"}'`), `red` back to `build` with the failures as the reason; a `refused` run keeps the stage. A progress run at stage `build` changes no stage. A red check returns to the [Write](write.md#red-check) route, which sets the stage.

## Tear down

Always, also after a refused or failed run, and in the same turn the run started:

1. `EPHEMERAL down --run-id <run id>` (without Docker it reports `docker_missing` and removes nothing, because no container can exist), then record each container this run created: the same `append.ephemeral` entry with `"state": "removed"`, or `"left"` with the error when removal failed (and tell the user the container name).
2. `EPHEMERAL sweep` removes orphans of earlier runs older than six hours. Report what it removed.
3. Remove result folders and data files the run wrote outside the change folder and the repository's ignored output folders.

## Skills and agents

- `dev-core` - settings (entry points, allow list), state, and the test-run template.
- `dev-workbook` - the Commands and Testing statements for filters, loggers, and the test environment.
- [Write](write.md) - calls this route for the red check.
- No agents are used.
