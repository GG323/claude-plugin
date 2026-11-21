using Microsoft.Extensions.Logging;

namespace Acme.Api.Orders;

public sealed class RefundService(ILogger<RefundService> log)
{
    public decimal Refund(Order order)
    {
        log.LogInformation("Refunding order {Id}", order.Id);
        return order.Total;
    }
}

public sealed record Order(int Id, decimal Total);
