namespace Api.Export;

public sealed class ExportScheduler(IServiceProvider services) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken ct)
    {
        while (!ct.IsCancellationRequested)
        {
            await Task.Delay(TimeSpan.FromHours(24), ct);
            using var scope = services.CreateScope();
            await scope.ServiceProvider.GetRequiredService<ExportJob>().RunAsync(DateOnly.FromDateTime(DateTime.UtcNow.AddDays(-1)), ct);
        }
    }
}
