using Api.Data;
using Dapper;

namespace Api.Services;

public sealed record User(int Id, string Email, string PasswordHash);

public sealed class AuthService(Db db)
{
    public async Task<User?> SignIn(string email, string password)
    {
        await using var conn = db.Open();
        var user = await conn.QuerySingleOrDefaultAsync<User>(
            "select id, email, password_hash as PasswordHash from users where email = @email", new { email });
        return user is not null && BCrypt.Verify(password, user.PasswordHash) ? user : null;
    }

    public string IssueToken(User user) => $"token-{user.Id}";
}
