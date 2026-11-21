# Bulk discount for large orders: review round 1

Change `2026-11-19-bulk-discount` · Diff: HEAD..working tree · Reviewers: correctness, process, spec, tests · Verdict: blocked · Result: not clean

## Summary

| Impact | Findings | AUTO-FIX | ASK |
| --- | --- | --- | --- |
| Critical | 1 | 1 | 0 |
| Major | 0 | 0 | 0 |
| Minor | 1 | 1 | 0 |
| Nit | 0 | 0 | 0 |

Counts come from the tally script. Outside this change: 0 (not counted above). Findings scored under the confidence threshold are in the appendix.

## Findings by area

### Correctness

| ID | Impact | Confidence | Mark | Location | Finding | Proposed fix | Handling | Your choice |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R1-C1 | Critical | 95 | confirmed: read DiscountCalculator.cs, plan.md line 48 and line 64, and test-map.md rows 1-3 (no test with a fractional 5%). | `src/Shop/Orders/DiscountCalculator.cs:14` | `Math.Round` has no decimals argument, so the bulk discount rounds to a whole number instead of 2 decimals. The plan says "rounded to 2 decimals as the coupons do". A 10-item order at 10.50 (subtotal 105.00) should get 5.25 but gets 5, so the customer is overcharged 0.25. A subtotal of 99.90 gives 4.995, which should be 5.00 and is 5 by luck. A subtotal of 30.00 gives 1.50, which rounds to 2 (banker's rounding) instead of 1.50, so the customer is undercharged 0.50. Any bulk order whose 5% has cents gets a wrong discount. The suite only uses round subtotals (10 items at 10.00), so it passes. Also raised by R1-S1 (spec). (quote: "var bulk = order.ItemCount >= 10 ? Math.Round(subtotal * 0.05m) : 0m;") | `Math.Round(subtotal * 0.05m, 2)`, matching the WELCOME10 branch. | AUTO-FIX | open |

### Tests

| ID | Impact | Confidence | Mark | Location | Finding | Proposed fix | Handling | Your choice |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R1-T2 | Minor | 90 | confirmed: read all test bodies; no test pairs WELCOME10 with 10 or more items. | `src/Shop/Orders/DiscountCalculator.cs:15` | No test has a coupon discount larger than the bulk discount with 10 or more items. The only coupon plus bulk test (`CouponAndBulk_LargerApplies`) has the bulk side winning (SAVE2 = 2.00 against 5.00). Code that always returned `bulk` when `ItemCount >= 10` would pass the whole suite. A WELCOME10 order with 10 items, where the 10% coupon should beat the 5% bulk, would fail it. (quote: "return Math.Max(coupon, bulk);") | Add `OrderOf(10, 10.00m, "WELCOME10")` expecting 10.00m. | AUTO-FIX | open |

## Test inspection

- **Runs:** test-run-3.md (full suite, 7 passed, 0 failed) read; one rerun with a temporary test: 7 passed, 1 failed as predicted; a final run after removing it: 7 passed, 0 failed. Targets verdict ok (localhost only).
- **Temporary tests:** `Review1_BulkRoundsToCents.TenItemsAtOddPrice_DiscountHasCents` (10 items at 1.23, expects a 0.62 discount) failed as R1-S1 predicts, which confirms it; removed after the run.
- **Coverage gaps:** no test uses a price whose 5% bulk discount has cents (criteria T1 and T2 use 10.00 only).

## Outside this change

none

## Appendix: low confidence and filtered

| ID | Severity | Confidence | Reason held back | Finding |
| --- | --- | --- | --- | --- |
| R1-T1 | Major | 72 | below threshold: Quote found at line 14 and the suite only uses a 100.00 subtotal (5% exact), so the coverage gap holds; the example is wrong because 110.00 gives 6 under banker's rounding, not 5, and the "7 passed" count cannot be checked from the files given, so part of the premise failed. | The bulk-discount calculation is only exercised with 10 items at 10.00 (subtotal 100.00, 5% = 5.00 exactly) in `TenItems_GetFivePercentBulkDiscount` and `CouponAndBulk_LargerApplies`. The 5% never has cents, so wrong rounding passes. The current code rounds to whole units (a subtotal of 110.00 gives 5 instead of 5.50) and the suite is green (7 passed). Dropping the 2-digit argument, or using a different rounding mode, also passes. |
| R1-S1 | Major | - | duplicate of R1-C1 | The plan's Design details say "5% of the subtotal, rounded to 2 decimals", and its Risks say to round "to 2 decimals as the coupons do". The code calls `Math.Round` with no digits argument, so it rounds to a whole unit. A subtotal of 110.00 gives 5 instead of 5.50. Criteria 1 and 2 still pass only because 10 items at 10.00 gives exactly 5.00. The criterion "5% bulk discount" is therefore built only in part: it is wrong for any subtotal whose 5% is not a whole number. The build record's Skipped section says "Only prices that make whole-cent discounts are tested", so no test catches this. |
