using Api.Data;
using Api.Export;
using Api.Services;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddControllers();
builder.Services.AddSingleton<Db>();
builder.Services.AddScoped<AuthService>();
builder.Services.AddHttpClient<ExportJob>();
builder.Services.AddHostedService<ExportScheduler>();

var app = builder.Build();
app.MapControllers();
app.Run();
