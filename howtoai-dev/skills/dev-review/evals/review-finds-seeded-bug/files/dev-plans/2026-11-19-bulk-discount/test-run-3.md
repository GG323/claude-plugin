# Bulk discount for large orders: test run 3

Change `2026-11-19-bulk-discount` · Route: run (full suite) · Run ID: `2026-11-19-bulk-discount-3` · Commit: `3f8389f` (working tree) · 2026-11-19 20:20 · Result: green

Written by `dev-test`. The Targets table comes from `targets.py classify`, the Results table from `results.py`.

## Targets

| Target | Kind | Evidence | Class | Used |
| --- | --- | --- | --- | --- |
| localhost | database | src/Shop/appsettings.json:3 ConnectionStrings:Shop, value redacted | local | no: not loaded |
| shop-prod.postgres.database.azure.com | database | src/Shop/appsettings.Production.json:3 ConnectionStrings:Shop, value redacted | production | no: not loaded |

## Results

| Entry point | Passed | Failed | Skipped | Flaky | Duration (s) |
| --- | --- | --- | --- | --- | --- |
| unit: dotnet test tests/Shop.Tests/Shop.Tests.csproj --logger trx --results-directory TestResults | 7 | 0 | 0 | 0 | 0.02 |

Passed counts every test that passed in the end, flaky ones included; Flaky counts those again.

## Failures

| Test | Reason | Reading |
| --- | --- | --- |

none

## Coverage and gaps

- Every test-map row ran and passed: T1-T4, C1-C2.

## Next

- Stage review: dev-review is next.
