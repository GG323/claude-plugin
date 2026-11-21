# Partial refunds: plan

Change `2026-11-20-partial-refunds` · Size: Small · Status: waiting for approval

## Goal

Let support staff refund part of an order, because customers often return one item of several.

## Out of scope

- Refunds across several orders.

## Decisions

| # | Decision | Source | Evidence | Mark | Confirmed by you |
| --- | --- | --- | --- | --- | --- |
| 1 | Store refunded amounts in a new `refunded` column on `orders` | you | request | confirmed | yes |

## Architecture

`RefundService` gains a `RefundPart(order, amount)` method next to `Refund`.

## Tools and services

None added.

## Languages and frameworks

C# on .NET 8, xUnit.

## Design details

1. Add `RefundPart` to `src/Api/Orders/RefundService.cs`; it refuses an amount above the order total minus what was already refunded.
2. Log each partial refund with `Console.WriteLine($"partial refund {order.Id} {amount}")`.
3. Migration `src/Api/Migrations/AddRefunded.sql`: `alter table orders add column refunded numeric(12, 2) not null default 0;`
4. Tests in `src/Api/Tests/PartialRefundTests.cs`: refund part of an order, and refuse a refund above what is left.

## Verification: success and proof

| Criterion | Method | Passing result |
| --- | --- | --- |
| A partial refund of 10 on an order of 40 leaves 30 refundable | unit (xUnit) | `RefundPart` returns 10 and a second call for 31 is refused |

- **End-to-end path:** call `RefundPart` from the test.
- **Side effects to confirm:** the `refunded` column is updated.
- **Behaviour that must not change:** `Refund` still returns the full total.
- **Cannot be verified here:** none

## Risks

| Risk | Impact | Fallback |
| --- | --- | --- |
| Two partial refunds at once refund too much | Major | Update `refunded` in one statement with a check |

## Assumptions and open questions

- **Assumed:** none
- **Open:** none
