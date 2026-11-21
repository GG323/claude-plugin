# Findings for scoring: plan review round 1

Plan: plan.md and wi/2.md in the repository. Impact scale for a plan: Blocker, Major, Nit.

| ID | Impact | Location | Quote | Claim |
| --- | --- | --- | --- | --- |
| P1-K1 | Blocker | plan.md, Design details 1 | "alter table users rename column email to login;" | The rename breaks running instances during a rolling deploy: `src/auth/session.cs:10` still queries `email`; no expand-and-contract step or rollback. |
| P1-K2 | Blocker | plan.md, Risks | "none" | The Risks section is a placeholder although the change renames a column and adds Redis. |
| P1-R2 | Blocker | wi/2.md, Goal and Agent prompt | "Add validation to the endpoint" | No endpoint, validation rules, or error response are named; the repository has no login endpoint file. |
| P1-Z1 | Blocker | plan.md, Design details 3 | "Add a `RedisUserCache` class wrapping `UserRepo.ById`" | The cache is not on the sign-in path (`SignIn` queries the database directly) and the lookup is already indexed at p99 2 ms. |
| P1-Z5 | Major | plan.md, Design details 3 | "Add a `RedisUserCache` class" | Missed reuse: `src/users/cache.cs` already has a generic `MemoryCache` used by the profile page. |
| P1-C2 | Major | plan.md, Architecture | "The sync job handles conflicts between old and new logins." | No sync job exists in the repository and the plan never defines it or its conflict rule. |
| P1-K7 | Major | plan.md, Decisions 1 | "Rename the `email` column to `login`" | Usernames are assumed unique, but there is no unique constraint or duplicate check; `QuerySingle` fails on duplicates. |
| P1-X1 | Major | src/auth/session.cs:11 | "if (user is null \|\| !Hash.Verify(password, user.PasswordHash)) return null;" | `SignIn` never verifies the password, so any password signs in. |
| P1-X2 | Nit | src/auth/session.cs:8 | "public async Task<Session?> SignIn(string emailInput, string password)" | The method should be named `Login` instead of `SignIn`. |
