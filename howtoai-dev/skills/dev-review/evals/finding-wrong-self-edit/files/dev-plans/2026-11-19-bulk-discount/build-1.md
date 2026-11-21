# Bulk discount for large orders: build 1

Change `2026-11-19-bulk-discount` · Work item: whole plan · Route: build · Snapshot: `8407c47848c42177d1be59456e2f1581d278ef1b` · 2026-11-19 20:12 · Result: passed

Written by `dev-build`. The hunk list comes from `build.py hunks`; `build.py check` checks the Trace, Ladder decisions, and Gate tables against the hunks, the test map or review, and the gate records.

## Ladder decisions

One row per thing the work item needed. Rungs: 1 not needed, 2 existing code, 3 standard library, 4 installed dependency, 5 one line, 6 new code.

| # | Need | Rung | What was used | Source |
| --- | --- | --- | --- | --- |
| L1 | Item count for the 10-item threshold | 2 existing code | `src/Shop/Orders/Order.cs:Order.ItemCount` | plan.md Scope and size |
| L2 | Larger of coupon and bulk discount | 3 standard library | `Math.Max` | plan.md Decisions |
| L3 | 5% bulk discount, rounded like the coupons | 5 one line | `Math.Round` on the subtotal times 0.05 | plan.md Design details |

## Callers checked

| Changed symbol | Callers found | How found | Still correct |
| --- | --- | --- | --- |
| src/Shop/Orders/DiscountCalculator.cs:Calculate | tests/Shop.Tests/DiscountCalculatorTests.cs (5 calls) | grep "DiscountCalculator.Calculate" | yes: signature unchanged |

## Trace

Every hunk `build.py hunks` lists has exactly one row. Traces to: `T<n>` or `C<n>` (a test-map row), `AC<n>` (the nth acceptance criterion of the work item), or a review finding ID such as `R1-C3` (Fix route); several, comma-separated.

| Hunk | Traces to | Ladder | Why this line |
| --- | --- | --- | --- |
| src/Shop/Orders/DiscountCalculator.cs:8-8 | T2, T4 | L2 | keep the coupon discount as a value to compare |
| src/Shop/Orders/DiscountCalculator.cs:14-15 | T1, T2, T3 | L1, L2, L3 | bulk discount at 10 or more items; the larger discount wins |

## Workbook statements applied

- csharp.pitfalls: decimal for money, as the coupons use.

## Gate

| Step | Source | Baseline | After | Result |
| --- | --- | --- | --- | --- |
| format: `dotnet format src/Shop/Shop.csproj --verify-no-changes` | dotnet.commands.002 | passed | passed | pass |
| build: `dotnet build tests/Shop.Tests/Shop.Tests.csproj -c Release` | dotnet.commands.001 | passed | passed | pass |
| WI tests | `test-run-2.md` (dev-test Run route) | red check: red | green | pass |

Fix rounds used: 0 of 3.

## Skipped or unchecked

- The 10-item threshold and 5% rate stay fixed values, not settings (rung 1).
- Only prices that make whole-cent discounts are tested.

## Open points

- none
