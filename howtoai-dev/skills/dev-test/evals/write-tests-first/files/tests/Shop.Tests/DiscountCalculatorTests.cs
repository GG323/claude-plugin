using Shop.Orders;

namespace Shop.Tests;

[TestClass]
public sealed class DiscountCalculatorTests
{
    private static Order OrderOf(int quantity, decimal price, string? coupon = null)
    {
        var order = new Order { Coupon = coupon };
        order.Lines.Add(new OrderLine("SKU-1", quantity, price));
        return order;
    }

    [TestMethod]
    public void Welcome10_TakesTenPercent() =>
        Assert.AreEqual(5.00m, DiscountCalculator.Calculate(OrderOf(5, 10.00m, "WELCOME10")));

    [TestMethod]
    public void NoCoupon_NoDiscount() =>
        Assert.AreEqual(0m, DiscountCalculator.Calculate(OrderOf(3, 10.00m)));
}
