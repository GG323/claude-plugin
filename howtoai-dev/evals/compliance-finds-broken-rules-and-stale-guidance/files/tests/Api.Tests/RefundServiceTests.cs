using Acme.Api.Orders;
using Microsoft.Extensions.Logging.Abstractions;
using Xunit;

public class RefundServiceTests
{
    [Fact]
    public void Refund_returns_the_order_total()
    {
        var service = new RefundService(NullLogger<RefundService>.Instance);
        Assert.Equal(40m, service.Refund(new Order(1, 40m)));
    }
}
