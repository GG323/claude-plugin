using Npgsql;

namespace Api.Data;

public sealed class Db(IConfiguration config)
{
    public NpgsqlConnection Open() => new(config.GetConnectionString("Shop"));
}
