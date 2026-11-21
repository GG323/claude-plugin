# Login by username: plan

Change `2026-11-18-login-by-username` · Size: Medium · Status: waiting for approval

## Goal

Let users sign in with a username instead of an email address, because enterprise customers asked for it.

## Out of scope

- none

## Decisions

| # | Decision | Source | Evidence | Mark | Confirmed by you |
| --- | --- | --- | --- | --- | --- |
| 1 | Rename the `email` column to `login` | general | none | inferred: simpler than a new column | not yet |
| 2 | Add a Redis cache in front of user lookups | general | none | inferred: faster sign-in | not yet |

## Architecture

Unchanged, plus a Redis cache between `UserRepo` and PostgreSQL. The sync job handles conflicts between old and new logins.

## Tools and services

Redis (new).

## Languages and frameworks

C# on .NET 8, ASP.NET Core.

## Design details

1. Migration: `alter table users rename column email to login;` deployed with the code change.
2. `SessionService.SignIn` queries `login` instead of `email`.
3. Add a `RedisUserCache` class wrapping `UserRepo.ById`.

## Verification: success and proof

| Criterion | Method | Passing result |
| --- | --- | --- |
| A user signs in with a username | e2e | Sign-in succeeds |

- **End-to-end path:** sign in through the web form.
- **Side effects to confirm:** none
- **Behaviour that must not change:** none
- **Cannot be verified here:** none

## Risks

| Risk | Impact | Fallback |
| --- | --- | --- |
| none | | |

## Assumptions and open questions

- **Assumed:** none
- **Open:** none
