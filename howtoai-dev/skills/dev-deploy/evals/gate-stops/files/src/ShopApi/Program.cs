using System.Collections.Concurrent;

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();
var items = new ConcurrentDictionary<int, Item>();
var nextId = 0;

app.MapGet("/health", () => Results.Text("ok"));
app.MapGet("/items", () => items.Values.OrderBy(i => i.Id));
app.MapGet("/items/{id:int}", (int id) => items.TryGetValue(id, out var item) ? Results.Ok(item) : Results.NotFound());
app.MapPost("/items", (ItemInput input) =>
{
    var item = new Item(Interlocked.Increment(ref nextId), input.Name);
    items[item.Id] = item;
    return Results.Created($"/items/{item.Id}", item);
});
app.MapPut("/items/{id:int}", (int id, ItemInput input) =>
{
    if (!items.ContainsKey(id)) return Results.NotFound();
    items[id] = new Item(id, input.Name);
    return Results.Ok(items[id]);
});
app.MapDelete("/items/{id:int}", (int id) => items.TryRemove(id, out _) ? Results.NoContent() : Results.NotFound());

app.Run();

public record Item(int Id, string Name);
public record ItemInput(string Name);
