namespace Shop.Orders;

public sealed record OrderLine(string Sku, int Quantity, decimal UnitPrice);

public sealed class Order
{
    public List<OrderLine> Lines { get; } = new();
    public string? Coupon { get; set; }
    public int ItemCount => Lines.Sum(l => l.Quantity);
}
