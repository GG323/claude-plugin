# Safety rules

## Contents

- [The rules and their layers](#the-rules-and-their-layers)
- [Classes of targets](#classes-of-targets)
- [What the hooks check](#what-the-hooks-check)
- [Skills and agents](#skills-and-agents)

## The rules and their layers

The twelve data and system safety rules of the `howtoai-dev` process. Each is enforced in more than one layer, because the hook alone can be bypassed and instructions alone can be missed. CI stays the final gate: these layers never replace it.

| Rule | What it means | Settings and scripts | Hook | Instructions |
| --- | --- | --- | --- | --- |
| Unknown is production | A target not on the allow list gets no writes; the run stops and asks | `TARGETS classify` verdict `ask` | - | [Classify the targets](../routes/run.md#classify-the-targets) |
| Allowlist by evidence | Host, connection string, environment variable, database name, or cloud profile; a name alone never counts | `environments.allow` items match one evidence key each | - | Allow items added only through Setup's preview |
| Ephemeral first | Containers made for the run, labelled with the run ID, torn down every time, orphans swept by label | `EPHEMERAL up`, `down`, `sweep` | - | [Throwaway target](../routes/run.md#throwaway-target), [Tear down](../routes/run.md#tear-down) |
| Destructive only on owned targets | Drops, truncates, down-migrations, bulk deletes, and resets only on targets this run created | Ephemeral entries in state | `dev-safe-target` asks, except for a command naming a container whose latest state entry is `created` | Snapshot first and ask on a shared dev target |
| Test-only secrets | Credentials from `.env.test` or the CI secret store; a production marker in a test file refuses the run; never in logs or docs | `TARGETS` never reads `.env` or prints values; `TESTINGMD` and `RESULTS` redact | - | [Core rules](../SKILL.md#core-rules) |
| Synthetic data | Generated data, never real personal data; production snapshots need approval and anonymisation | - | - | [Write the tests](../routes/write.md#write-the-tests) |
| Isolation per test | A rolled-back transaction per test, or a schema or database per run | - | - | [Write the tests](../routes/write.md#write-the-tests) |
| No real side effects | Email, SMS, payments, webhooks to catchers or test mode; production hosts denied | `environments.deny` | `dev-safe-target` denies deny markers | Side-effect scan in [Classify the targets](../routes/run.md#classify-the-targets) |
| Cost and time caps | Remote test servers get cost and time limits | Not built: only local containers | - | [What it can't do](../SKILL.md#what-it-cant-do) |
| Same entry points as CI | The project's scripts, never ad-hoc commands; CI configuration never edited to pass | `testing.entry_points` | `dev-test-first` denies CI edits at stages `tests-first` and `test` | [Find the entry points](../routes/run.md#find-the-entry-points) |
| No gate weakening | Skipping, deleting, or loosening a test or assertion is a Critical finding unless the plan approved it | - | - | [Core rules](../SKILL.md#core-rules); `dev-review` checks it |
| Approved production steps | Every production deploy step needs approval in chat, with the rollback planned first | - | `dev-safe-target` denies deny markers | `dev-deploy` |

## Classes of targets

`TARGETS classify` gives each target one class, the first that matches:

| Class | Evidence | May the run use it |
| --- | --- | --- |
| production | A deny marker appears in it, or an environment variable (`APP_ENV`, `NODE_ENV`, `RAILS_ENV`, `ASPNETCORE_ENVIRONMENT`, `DOTNET_ENVIRONMENT`) names production, prod, live, or staging | Never: the run is refused |
| local, dev, test, remote-test | An `environments.allow` item matches its host, database, profile, or env | Yes |
| ephemeral | A container this run created (`--ephemeral`) | Yes, including destructive steps |
| local (file) | An in-memory or file database (SQLite, LocalDB) | Yes |
| unknown | Anything else; a loopback host not on the allow list gets a hint | No: the run stops and asks |

Only targets in files a test run loads count for the verdict: test settings, `.env.test`, `.runsettings`, and shared config such as `appsettings.json`, unless a test settings file next to it overrides the same key. Files for other environments (`appsettings.Production.json`), `.env.example`, and CI files are listed but do not decide.

## What the hooks check

- **`dev-test-first`** (Edit, Write, MultiEdit, NotebookEdit), only while a change is at stage `tests-first`, `build`, or `test`: non-test files are denied at `tests-first` (`testing.test_first`: `block`, `warn`, or `off`); at `build` it warns when the change has no red-check run; CI files are denied at `tests-first` and `test`.
- **`dev-safe-target`** (Bash, PowerShell, MCP tools, Edit, Write, MultiEdit): deny markers are denied anywhere they are set; `hook_rules` block or warn; in workspaces with project dev settings, destructive commands and destructive migration edits ask first. A migration edit passes once the plan approved it and the migration carries the comment `howtoai-dev: destructive-confirmed`.
- `dev-test-first` is silent unless the file's workspace has a change at one of its stages. `dev-safe-target` applies deny markers and `hook_rules` wherever the dev settings name them, including your user-level settings, which reach every workspace; its destructive-command and migration checks run only in workspaces with project dev settings.
- Neither calls a model, and both fail open on their own errors, so the scripts and instructions stay in force when a hook cannot run.
- Known limit: `dev-safe-target` denies every command that names a deny marker, so it also stops an approved production deploy step. `dev-deploy`, when it is built, needs an exception for steps approved in state; until then such steps run outside the hook, by the user.

## Skills and agents

- `dev-test` - reads this file for its core rules.
- `dev-deploy` - shares the deny list and the approved-production-steps rule.
- No agents are used.
