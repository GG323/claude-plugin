# {title}: build {n}

Change `{change_id}` · Work item: {n, or "whole plan"} · Route: {build / fix} · Snapshot: `{tree id from build.py start}` · {date and time} · Result: {passed / failed / stopped}

Written by `dev-build`. The hunk list comes from `build.py hunks`; `build.py check` checks the Trace, Ladder decisions, and Gate tables against the hunks, the test map or review, and the gate records.

## Ladder decisions

One row per thing the work item needed. Rungs: 1 not needed, 2 existing code, 3 standard library, 4 installed dependency, 5 one line, 6 new code.

| # | Need | Rung | What was used | Source |
| --- | --- | --- | --- | --- |
| {L1} | {what the work item needed, in one line} | {1-6 and its name, for example "2 existing code"} | {file:symbol, API, or package; for rung 1, what was left out} | {workbook statement ID / project code file:symbol / plan.md / wi/<n>.md / general} |

## Callers checked

| Changed symbol | Callers found | How found | Still correct |
| --- | --- | --- | --- |
| {file:symbol} | {file:line, ...; or "none"} | {the search pattern or tool} | {yes / covered by test name / no: why} |

{"none: no existing function, type, or contract changed"}

## Trace

Every hunk `build.py hunks` lists has exactly one row. Traces to: `T<n>` or `C<n>` (a test-map row), `AC<n>` (the nth acceptance criterion of the work item), or a review finding ID such as `R1-C3` (Fix route); several, comma-separated.

| Hunk | Traces to | Ladder | Why this line |
| --- | --- | --- | --- |
| {path:start-end, or path:<line>d for a deletion} | {T2, AC1} | {L1} | {one line} |

## Workbook statements applied

- {statement ID}: {how it shaped the code}; "none" when no workbook applies

## Gate

| Step | Source | Baseline | After | Result |
| --- | --- | --- | --- | --- |
| {gate name}: `{command}` | {CI file and step / workbook statement ID} | {passed / failed} | {passed / failed} | {pass / pre-existing failure, continued with approval / fail} |
| WI tests | `test-run-{test run number}.md` (dev-test Run route) | {red check: red} | {green / red} | {pass / fail} |

Fix rounds used: {n} of {max_fix_rounds}.

## Skipped or unchecked

- {what this build left out on purpose, what it could not check, and any risk the reviewer must know; at least one line}

## Open points

- {a criterion the code meets only in part, a caller that needs its own WI, an out-of-scope request offered as a new WI}; "none"
