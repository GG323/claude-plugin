using Xunit;

namespace Api.Tests;

public class AuthServiceTests
{
    [Fact]
    public void IssueToken_uses_user_id() =>
        Assert.Equal("token-7", new Api.Services.AuthService(null!).IssueToken(new(7, "a@b.test", "h")));
}
