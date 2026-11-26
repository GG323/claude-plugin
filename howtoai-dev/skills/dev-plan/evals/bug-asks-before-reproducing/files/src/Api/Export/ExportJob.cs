using Api.Data;
using Dapper;

namespace Api.Export;

public sealed class ExportJob(HttpClient http, Db db, ILogger<ExportJob> log)
{
    // The finance upload endpoint is slow for large files.
    private static readonly TimeSpan UploadTimeout = TimeSpan.FromSeconds(30);

    public async Task RunAsync(DateOnly day, CancellationToken ct)
    {
        await using var conn = db.Open();
        var rows = await conn.QueryAsync<(int Id, decimal Total, string Email)>(
            "select o.id, o.total, u.email from orders o join users u on u.id = o.user_id where o.day = @day", new { day });
        var csv = string.Join("\n", rows.Select(r => $"{r.Id};{r.Total};{r.Email}"));
        http.Timeout = UploadTimeout;
        var res = await http.PostAsync("https://finance.example.test/upload", new StringContent(csv), ct);
        res.EnsureSuccessStatusCode();
        log.LogInformation("Exported {Count} orders for {Day}", rows.Count(), day);
    }
}
