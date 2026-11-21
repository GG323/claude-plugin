namespace Shop.Orders;

public static class Percent
{
    // Money is rounded to cents the same way everywhere: banker's rounding, 2 decimals.
    public static decimal Of(decimal amount, decimal rate) => Math.Round(amount * rate, 2);
}
