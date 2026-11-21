# {title}: test map

Change `{change_id}` · Work item: {n, or "whole plan"} · Written by `dev-test` (Write route) · Red check: {not run / passed / failed}

Every Verification criterion and acceptance criterion has exactly one row. A criterion that cannot be tested here keeps its row with the level `manual` or `not verifiable here` and the reason.

## Criteria

| # | Criterion | Source | Level | Test file | Test name | Expected red reason | Red result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| {1} | {criterion, as the plan words it} | {plan.md Verification / wi/<n>.md / plan.md must not change / plan.md Assumptions} | {unit / integration / e2e / manual / not verifiable here} | {path} | {test name} | {assertion fails / member missing / route returns 404; "passes now and after" for must-not-change rows} | {failed as expected / passed early / failed for another reason / not run; "passed" or "failed" for must-not-change rows} |

## Characterization tests

Tests that pin today's behaviour of untested code next to the change. They must pass before the build and after it.

| # | Code | Why it is a neighbour | Test file | Test name | Result |
| --- | --- | --- | --- | --- | --- |
| {C1} | {file:symbol} | {calls or is called by the changed code} | {path} | {test name} | {passed / failed} |

{"none" when the scope facts list no untested neighbours}

## Workbook statements applied

- {statement ID}: {how it shaped a test}; "none" when no workbook applies

## Open points

- {a test passed before the build, a criterion with no observable outcome, a missing fixture}; "none"
