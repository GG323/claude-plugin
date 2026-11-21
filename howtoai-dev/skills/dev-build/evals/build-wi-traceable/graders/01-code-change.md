---
type: llm
focus: trace
weight: 1
---

`src/Shop/Orders/DiscountCalculator.cs` gives orders whose `ItemCount` is 10 or more a 5% discount of the subtotal rounded to 2 decimals, and returns the larger of the coupon and bulk discounts. No other file under `src/` or `tests/`, no CI file, and no project file changed (`git diff HEAD --stat` outside `dev-plans/2026-11-19-bulk-discount/` shows only that one file).
