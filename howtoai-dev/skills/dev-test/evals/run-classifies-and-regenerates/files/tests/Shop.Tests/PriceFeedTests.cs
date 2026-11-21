namespace Shop.Tests;

[TestClass]
public sealed class PriceFeedTests
{
    // Simulates a timing-dependent test: it fails on its first run in a build folder and passes after.
    [TestMethod]
    public void PriceFeed_WarmsUp()
    {
        var marker = Path.Combine(AppContext.BaseDirectory, "price-feed.warm");
        if (!File.Exists(marker))
        {
            File.WriteAllText(marker, "warm");
            Assert.Fail("price feed not warmed up yet (timing)");
        }
    }
}
