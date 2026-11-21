namespace Acme.Auth;

public class SessionService
{
    private readonly Db _db;
    public SessionService(Db db) => _db = db;

    public async Task<Session?> SignIn(string emailInput, string password)
    {
        var user = await _db.QuerySingle<User>("select id, email, password_hash from users where email = @e", new { e = emailInput });
        if (user is null || !Hash.Verify(password, user.PasswordHash)) return null;
        return Session.For(user.Id);
    }
}
