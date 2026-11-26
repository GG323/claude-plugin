# Safety rules

The twelve data and system safety rules of `howtoai-dev`, each held by more than one layer, because a hook alone can be bypassed and instructions alone can be missed. Your own check comes first; a hook is the second layer. CI stays the final gate.

## The rules and their layers

| Rule | What it means | Settings and scripts | Hook | Instructions |
| --- | --- | --- | --- | --- |
| Unknown is production | A target not on the allow list gets no writes; the run stops and asks | `TARGETS classify` verdict `ask` | - | [Classify the targets](../routes/run.md#classify-the-targets) |
| Allowlist by evidence | Host, connection string, environment variable, database name, or cloud profile; a name alone never counts | `environments.allow` items match one evidence key each | - | Allow items added only through Setup's preview |
| Ephemeral first | Containers made for the run, labelled with the run ID, torn down every time, orphans swept by label | `EPHEMERAL up`, `down`, `sweep` | - | [Throwaway target](../routes/run.md#throwaway-target), [Tear down](../routes/run.md#tear-down) |
| Destructive only on owned targets | Drops, truncates, down-migrations, bulk deletes, and resets only on targets this run created | Ephemeral entries in state | Second layer: `dev-safe-target` asks, except for a command naming a container whose latest state entry is `created` | Check first: only on a throwaway container this run created, otherwise ask ([Core rules](../SKILL.md#core-rules)); snapshot first on a shared dev target |
| Test-only secrets | Credentials from `.env.test` or the CI secret store; a production marker in a test file refuses the run; never in logs or docs | `TARGETS` never reads `.env` or prints values; `TESTINGMD` and `RESULTS` redact | - | [Core rules](../SKILL.md#core-rules) |
| Synthetic data | Generated data, never real personal data; production snapshots need approval and anonymisation | - | - | [Write the tests](../routes/write.md#write-the-tests) |
| Isolation per test | A rolled-back transaction per test, or a schema or database per run | - | - | [Write the tests](../routes/write.md#write-the-tests) |
| No real side effects | Email, SMS, payments, webhooks to catchers or test mode; production hosts denied | `environments.deny` | Second layer: `dev-safe-target` denies deny markers | Check first: each command and MCP call against the deny markers ([Core rules](../SKILL.md#core-rules)); side-effect scan in [Classify the targets](../routes/run.md#classify-the-targets) |
| Cost and time caps | Remote test servers get cost and time limits | Not built: only local containers | - | [Core rules](../SKILL.md#core-rules) (Local only) |
| Same entry points as CI | The project's scripts, never ad-hoc commands; CI configuration never edited to pass | `testing.entry_points` | Second layer: `dev-test-first` denies CI edits at stages `tests-first` and `test` | Check first: never edit CI configuration ([Core rules](../SKILL.md#core-rules)); [Find the entry points](../routes/run.md#find-the-entry-points) |
| No gate weakening | Skipping, deleting, or loosening a test or assertion is a Critical finding unless the plan approved it | - | - | [Core rules](../SKILL.md#core-rules); `dev-review` checks it |
| Approved production steps | Every production deploy step needs approval in chat, with the rollback planned first | `deploy.py use` refuses a used, expired, unknown, or changed approval | Second layer: `dev-safe-target` denies deny markers, except an approved step once | Check first: `dev-deploy` runs `DEPLOY use` before each step |

## Classes of targets

`TARGETS classify` gives each target the first class that matches:

| Class | Evidence | May the run use it |
| --- | --- | --- |
| production | A deny marker appears in it, or an environment variable (`APP_ENV`, `NODE_ENV`, `RAILS_ENV`, `ASPNETCORE_ENVIRONMENT`, `DOTNET_ENVIRONMENT`) names production, prod, live, or staging | Never: the run is refused |
| local, dev, test, remote-test | An `environments.allow` item matches its host, database, profile, or env | Yes |
| ephemeral | A container this run created (`--ephemeral`) | Yes, including destructive steps |
| local (file) | An in-memory or file database (SQLite, LocalDB) | Yes |
| unknown | Anything else; a loopback host not on the allow list gets a hint | No: the run stops and asks |

`environments.deny` holds production markers only. A shared target that is not production, such as a team's dev database or a staging service, belongs on neither list, so `dev-test` asks about it at each run.

Only files a test run loads decide the verdict: test settings, `.env.test`, `.runsettings`, and shared config such as `appsettings.json` unless a test settings file next to it overrides the same key. Other environments' files (`appsettings.Production.json`), `.env.example`, and CI files are listed but do not decide.

## What the hooks check

- **`dev-test-first`** (Edit, Write, MultiEdit, NotebookEdit), only while the file's workspace has a change at `tests-first`, `build`, or `test`: non-test files are denied at `tests-first` (`testing.test_first`: `block`, `warn`, or `off`); at `build` it warns when the change has no red-check run; CI files are denied at `tests-first` and `test`.
- **`dev-safe-target`** (Bash, PowerShell, MCP tools, Edit, Write, MultiEdit): deny markers are denied wherever the dev settings set them, user-level settings included; `hook_rules` block or warn. In workspaces with project dev settings, destructive commands and destructive migration edits ask first; a migration edit passes once the plan approved it and it carries the comment `howtoai-dev: destructive-confirmed`. A step `dev-deploy` approved in `AGENTS/state/approvals.json` (the exact command, unexpired and unused) passes once; `dev-deploy` checks the same approval first with `deploy.py use`.
- Neither calls a model, and both fail open on their own errors, so the scripts and instructions stay in force when a hook cannot run.

## Without hooks

Hooks run only in Claude Code with the plugin installed. These are your own checks, made first everywhere:

- **Production markers:** Before any command or MCP call, check it against the settings' `environments.deny` markers; on a match, stop and ask.
- **`hook_rules`:** before each command or edit, apply each entry yourself: on a `block` match, stop and give its reason; on a `warn` match, say it.
- **Destructive commands:** only on a throwaway container this run created; otherwise ask.
- **Destructive migrations:** a migration that drops, truncates, or renames only after the user's yes, recorded with its `paths`.
- **Tests first:** at stage `tests-first`, edit only files matching `testing.test_globs`, test data, and the change folder; `DEVCORE` refuses the move to `build` when git shows other files changed since then, and records it as unchecked without git.
- **CI files:** never edited at stages `tests-first` and `test`.
- **Reply log:** never create, read, or write `skills/dev-core/state/replies.jsonl`; an approval recorded without it is unverified, and you show it to the user in your next message.
- **Deploy steps:** `DEPLOY use` before each step, which refuses a used, expired, unknown, or changed approval.
