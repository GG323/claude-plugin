#!/usr/bin/env bash
set -eu
cp -R "$(dirname "$0")/files/." .
# Commit the change as it was before the build, then restore the built code, so the build is
# the uncommitted diff dev-review reviews.
cp src/Shop/Orders/DiscountCalculator.cs .built-DiscountCalculator.cs
cat > src/Shop/Orders/DiscountCalculator.cs <<'CS'
namespace Shop.Orders;

public static class DiscountCalculator
{
    public static decimal Calculate(Order order)
    {
        var subtotal = OrderTotals.Subtotal(order);
        return order.Coupon switch
        {
            "WELCOME10" => Math.Round(subtotal * 0.10m, 2),
            "SAVE2" => Math.Min(2.00m, subtotal),
            _ => 0m,
        };
    }
}
CS
git init -q
git add -A -- . ':!.built-DiscountCalculator.cs'
git -c user.name=fixture -c user.email=fixture@example.invalid commit -q -m "bulk discount: plan and failing tests"
mv .built-DiscountCalculator.cs src/Shop/Orders/DiscountCalculator.cs
