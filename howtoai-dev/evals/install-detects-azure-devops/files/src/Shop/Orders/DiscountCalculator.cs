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
