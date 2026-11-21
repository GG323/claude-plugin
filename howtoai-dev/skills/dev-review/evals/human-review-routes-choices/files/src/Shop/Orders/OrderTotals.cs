namespace Shop.Orders;

public static class OrderTotals
{
    public static decimal Subtotal(Order order) => order.Lines.Sum(l => l.Quantity * l.UnitPrice);

    public static decimal Total(Order order, decimal discount)
    {
        var total = Subtotal(order) - discount;
        return Math.Round(total < 0 ? 0 : total, 2, MidpointRounding.AwayFromZero);
    }
}
