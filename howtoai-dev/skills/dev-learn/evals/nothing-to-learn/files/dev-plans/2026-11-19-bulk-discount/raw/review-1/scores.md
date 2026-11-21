| ID | Score | Reason |
| --- | --- | --- |
| R1-C1 | 95 | Quote found at `src/Shop/Orders/DiscountCalculator.cs:14`; `Math.Round(decimal)` with no decimals argument rounds to whole units (5.25 gives 5, 1.50 gives 2 under banker's rounding), which contradicts the 2-decimal rule in `plan.md` Design details. The cited R1-S1 is not in the findings list. |
| R1-T1 | 72 | Quote found at line 14 and the suite only uses a 100.00 subtotal (5% exact), so the coverage gap holds; the example is wrong because 110.00 gives 6 under banker's rounding, not 5, and the "7 passed" count cannot be checked from the files given, so part of the premise failed. |
| R1-T2 | 90 | Quote found at `src/Shop/Orders/DiscountCalculator.cs:15`; `CouponAndBulk_LargerApplies` only covers the bulk-wins case (SAVE2 2.00 against 5.00), so a code path that always returned bulk with 10+ items would pass, and WELCOME10 at 10 items (10.00 against 5.00) is the uncovered case. |
