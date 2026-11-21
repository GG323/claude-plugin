---
type: llm
focus: trace
weight: 1
---

The bulk discount in `src/Shop/Orders/DiscountCalculator.cs` is computed with the existing `Percent.Of` (for example `Percent.Of(subtotal, 0.05m)`), not with a new `Math.Round` expression, and no new method, class, or file was added; `Percent.cs` is unchanged.
