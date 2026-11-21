# Bulk discount for large orders: test map

Change `2026-11-19-bulk-discount` · Work item: whole plan · Written by `dev-test` (Write route) · Red check: passed

Every Verification criterion and acceptance criterion has exactly one row. A criterion that cannot be tested here keeps its row with the level `manual` or `not verifiable here` and the reason.

## Criteria

| # | Criterion | Source | Level | Test file | Test name | Expected red reason | Red result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | An order of 10 items at 10.00 gets a 5.00 discount | plan.md Verification | unit | tests/Shop.Tests/DiscountCalculatorTests.cs | TenItems_GetFivePercentBulkDiscount | returns 0 instead of 5.00 | failed as expected |
| 2 | With coupon SAVE2 and 10 items at 10.00, the larger discount applies | plan.md Verification | unit | tests/Shop.Tests/DiscountCalculatorTests.cs | CouponAndBulk_LargerApplies | returns 2.00 instead of 5.00 | failed as expected |
| 3 | An order of 9 items gets no bulk discount | plan.md must not change | unit | tests/Shop.Tests/DiscountCalculatorTests.cs | NineItems_KeepTodaysDiscount | passes now and after | passed |
| 4 | WELCOME10 alone still takes 10% | plan.md must not change | unit | tests/Shop.Tests/DiscountCalculatorTests.cs | Welcome10_TakesTenPercent | passes now and after | passed |

## Characterization tests

| # | Code | Why it is a neighbour | Test file | Test name | Result |
| --- | --- | --- | --- | --- | --- |
| C1 | src/Shop/Orders/OrderTotals.cs:Total | called with the discount | tests/Shop.Tests/OrderTotalsTests.cs | Total_RoundsAwayFromZero | passed |
| C2 | src/Shop/Orders/OrderTotals.cs:Total | called with the discount | tests/Shop.Tests/OrderTotalsTests.cs | Total_NeverBelowZero | passed |

## Workbook statements applied

- dotnet.commands.004: the red check filtered the passes with `--filter`.

## Open points

- none
