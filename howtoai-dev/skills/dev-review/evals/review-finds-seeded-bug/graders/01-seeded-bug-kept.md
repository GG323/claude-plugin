---
type: llm
focus: trace
weight: 1
---

`dev-plans/2026-11-19-bulk-discount/review-1.md` keeps a finding that the bulk discount `Math.Round(subtotal * 0.05m)` in `src/Shop/Orders/DiscountCalculator.cs` rounds to whole units instead of 2 decimals, with impact Critical or Major, confidence 80 or more, and it is the first or second finding listed under Findings by area.
