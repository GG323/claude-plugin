# {title}: test run {n}

Change `{change_id}` · Route: {red check / run} · Run ID: `{run_id}` · Commit: `{commit}` · {date and time} · Result: {green / red / red-failed / refused}

Written by `dev-test`. The Targets table comes from `targets.py classify`, the Results table from `results.py`.

## Targets

| Target | Kind | Evidence | Class | Used |
| --- | --- | --- | --- | --- |
| {name} | {database / queue / api / server / cloud} | {file:line and key, value redacted} | {local / dev / test / remote-test / ephemeral / unknown / production} | {yes / no: not loaded / no: overridden / refused} |

{When the run was refused: which target, which rule, and what the user can change.}

## Results

| Entry point | Passed | Failed | Skipped | Flaky | Duration (s) |
| --- | --- | --- | --- | --- | --- |
| {name: command} | {n} | {n} | {n} | {n} | {seconds, from the first pass} |

Passed counts every test that passed in the end, flaky ones included; Flaky counts those again. For a refused run, one row per entry point with "not run (refused)" in every figure. At stage test, an entry point the user said yes to skipping has "skipped (user's yes)" in every figure.

## Failures

| Test | Reason | Reading |
| --- | --- | --- |
| {test name} | {first assertion or error line} | {real failure / expected red / flaky after N reruns / environment problem} |

{"none"}

## Coverage and gaps

- **Coverage:** {figure and tool; "not collected"; "not run" for a refused run}
- **Criteria without a passing test:** {test-map rows; "none"}
- **Untested neighbours:** {"none"}

## Created and removed

| Resource | Label | Created | Removed |
| --- | --- | --- | --- |
| {container or file} | `howtoai.dev.run={run_id}` | {time} | {time / "left: reason"} |

{"none"}

## Next

{review (green), plus "waiting: <question>" for one that did not hold the review up / back to build with the failures above (red) / the question the user must answer (refused)}
