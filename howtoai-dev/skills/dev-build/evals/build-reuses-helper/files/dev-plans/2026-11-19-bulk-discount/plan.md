# Bulk discount for large orders

Change `2026-11-19-bulk-discount` · Size: Small · Status: approved on 2026-11-19

Workbook IDs (for example `dotnet.testing.001`) refer to statements resolved by `dev-workbook`; sources are marked confirmed or inferred. Settings: `AGENTS/settings.json`.

## Goal

Orders with 10 or more items get a 5% bulk discount. When a coupon also applies, the larger discount wins; discounts never stack.

## Out of scope

- Changing coupon values or adding coupons.
- Showing the discount in any UI.

## Scope and size

| Item | Kind | Fact | Source | Mark |
| --- | --- | --- | --- | --- |
| `DiscountCalculator.Calculate` | caller | Returns the coupon discount only (WELCOME10 10%, SAVE2 2.00 off) | `src/Shop/Orders/DiscountCalculator.cs:5` | confirmed |
| `Order.ItemCount` | reuse | Sums line quantities; use it for the threshold | `src/Shop/Orders/Order.cs:9` | confirmed |
| `OrderTotals` | untested | `Subtotal` and `Total` (rounding away from zero, never below zero) have no tests | search of `tests/` for `OrderTotals`: no hits | confirmed |
| Tests | test | MSTest, `tests/Shop.Tests`, one class per production class | `tests/Shop.Tests/DiscountCalculatorTests.cs` | confirmed |

Small: one component, in line with its existing code, reversible by a revert.

## Decisions

| Decision | Choice | Source | Evidence | Mark | Confirmed |
| --- | --- | --- | --- | --- | --- |
| Threshold | 10 items, counted by quantity | user | request | confirmed | yes, round 1 |
| Coupon and bulk | larger wins, no stacking | user | request | confirmed | yes, round 1 |

## Architecture

Unchanged (`src/Shop`).

## Tools and services

Unchanged.

## Languages and frameworks

Unchanged: C#, .NET 10, MSTest.

## Design details

- `src/Shop/Orders/DiscountCalculator.cs`: add the bulk discount (5% of the subtotal, rounded to 2 decimals) when `ItemCount >= 10`; return the larger of the coupon and bulk discounts.

## Verification: success and proof

| # | Criterion | Method | Passing result |
| --- | --- | --- | --- |
| 1 | An order of 10 items at 10.00 gets a 5.00 discount | unit | `Calculate` returns 5.00 |
| 2 | With coupon SAVE2 and 10 items at 10.00, the larger discount applies | unit | `Calculate` returns 5.00 (not 2.00, not 7.00) |

- **End-to-end path:** none; a library with no user path. `dotnet test` is the proof.
- **Side effects to confirm:** none.
- **Behaviour that must not change:** an order of 9 items gets no bulk discount (0 without a coupon); WELCOME10 alone still takes 10%.
- **Cannot be verified here:** none.

## Risks

- Rounding: 5% of odd subtotals; covered by rounding to 2 decimals as the coupons do.

## Assumptions

- Item count is the sum of quantities, not the number of lines.
