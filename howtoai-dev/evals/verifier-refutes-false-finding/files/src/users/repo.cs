namespace Acme.Users;

public class UserRepo
{
    private readonly Db _db;
    public UserRepo(Db db) => _db = db;

    // Indexed lookup by primary key; p99 2 ms in production metrics (docs/perf.md).
    public Task<User?> ById(Guid id) => _db.QuerySingle<User>("select * from users where id = @id", new { id });
}
