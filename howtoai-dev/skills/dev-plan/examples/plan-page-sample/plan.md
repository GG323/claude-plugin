# Login rate limit: plan

Change `2026-11-19-login-rate-limit` · Size: Medium · Status: waiting for approval

Every decision names its source and is marked **confirmed** (file and line, or doc link) or **inferred** (with the reason). Workbook statements are cited by ID, for example `csharp.patterns.004`.

## Goal

Stop password guessing on `/login` by limiting failed attempts per account and per IP, without locking out users who type their password right.

## Out of scope

- Captcha and multi-factor sign-in.

## Scope and size

| Item | Kind | Fact | Evidence | Mark |
| --- | --- | --- | --- | --- |
| Login handler | caller | `LoginController.Post` is the only caller of `AuthService.SignIn` | searched `src/` for `SignIn(` | confirmed |
| Attempts store | data | No table records failed attempts | searched `db/migrations/` for `attempt` | confirmed |

**Size:** Medium - one subsystem (`src/auth/`), a new reversible table.

## Decisions

| # | Decision | Source | Evidence | Mark | Confirmed by you |
| --- | --- | --- | --- | --- | --- |
| 1 | Use ASP.NET Core rate limiting middleware for the per-IP limit | tool | `dotnet.patterns.012` | confirmed | yes, round 1 |
| 2 | Five failures in 15 minutes lock the account for 15 minutes | industry | OWASP Authentication Cheat Sheet | inferred: no project rule | not yet |

## Architecture

Unchanged except `src/auth/`: the controller calls a new `AttemptTracker` before `SignIn`.

## Tools and services

None added.

## Languages and frameworks

C# 12 on .NET 8 (`csharp`, `dotnet` workbooks).

## Design details

- `src/auth/AttemptTracker.cs` (new): counts failures per account in table `login_attempts`.
  - Reset on success.
- `db/migrations/013_login_attempts.sql` (new): the table, with a down migration.

## Verification: success and proof

| Criterion | Method | Passing result |
| --- | --- | --- |
| Sixth failed login in 15 minutes is refused | integration | HTTP 429 with `Retry-After` |
| A right password after four failures signs in | integration | HTTP 200 and the counter is 0 |

- **End-to-end path:** HTTP calls to `/login` against the local test server.
- **Side effects to confirm:** rows in `login_attempts`.
- **Behaviour that must not change:** a first-try login still returns 200.
- **Cannot be verified here:** none

## Risks

| Risk | Impact | Fallback |
| --- | --- | --- |
| Attackers lock out real users on purpose | Major | Lock for 15 minutes only, and per IP as well |

## Assumptions and open questions

- **Assumed:** the load balancer forwards the client IP in `X-Forwarded-For`.
- **Open:** Should support staff be able to unlock an account by hand?
