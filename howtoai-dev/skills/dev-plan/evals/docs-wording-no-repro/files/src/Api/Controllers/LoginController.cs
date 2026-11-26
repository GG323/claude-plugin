using Api.Services;
using Microsoft.AspNetCore.Mvc;

namespace Api.Controllers;

[ApiController]
[Route("login")]
public sealed class LoginController(AuthService auth) : ControllerBase
{
    public sealed record LoginRequest(string Email, string Password);

    [HttpPost]
    public async Task<IActionResult> Post(LoginRequest req)
    {
        var user = await auth.SignIn(req.Email, req.Password);
        return user is null ? Unauthorized() : Ok(new { token = auth.IssueToken(user) });
    }
}
