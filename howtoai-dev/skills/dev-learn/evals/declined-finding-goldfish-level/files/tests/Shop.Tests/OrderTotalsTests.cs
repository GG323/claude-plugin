using Shop.Orders;

namespace Shop.Tests;

[TestClass]
public sealed class OrderTotalsTests
{
    [TestMethod]
    public void Total_RoundsAwayFromZero()
    {
        var order = new Order();
        order.Lines.Add(new OrderLine("SKU-1", 1, 10.005m));
        Assert.AreEqual(10.01m, OrderTotals.Total(order, 0m));
    }

    [TestMethod]
    public void Total_NeverBelowZero()
    {
        var order = new Order();
        order.Lines.Add(new OrderLine("SKU-1", 1, 1.00m));
        Assert.AreEqual(0m, OrderTotals.Total(order, 2.00m));
    }
}
