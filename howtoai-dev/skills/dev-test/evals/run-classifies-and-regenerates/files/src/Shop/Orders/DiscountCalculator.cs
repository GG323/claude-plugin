namespace Shop.Orders;

public static class DiscountCalculator
{
    public const int BulkThreshold = 10;

    public static decimal Calculate(Order order)
    {
        var subtotal = OrderTotals.Subtotal(order);
        var coupon = order.Coupon switch
        {
            "WELCOME10" => Math.Round(subtotal * 0.10m, 2),
            "SAVE2" => Math.Min(2.00m, subtotal),
            _ => 0m,
        };
        var bulk = order.ItemCount >= BulkThreshold ? Math.Round(subtotal * 0.05m, 2) : 0m;
        return Math.Max(coupon, bulk);
    }
}
