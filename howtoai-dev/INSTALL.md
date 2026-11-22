# Install howtoai-dev

## Contents

- [What this does](#what-this-does)
- [Before you start](#before-you-start)
- [Check dependencies](#check-dependencies)
- [Dev mode](#dev-mode)
- [Install or link](#install-or-link)
- [Per-user choices](#per-user-choices)
- [Look up the project](#look-up-the-project)
- [Ask the project decisions](#ask-the-project-decisions)
- [Workbooks](#workbooks)
- [Deploy target](#deploy-target)
- [Write and record](#write-and-record)
- [Verify](#verify)
- [Double check with skill-builder](#double-check-with-skill-builder)
- [Summary](#summary)
- [Change a decision later](#change-a-decision-later)
- [Output contract](#output-contract)
- [Common failures](#common-failures)
- [What it can't do](#what-it-cant-do)
- [Feedback](#feedback)
- [Skills and agents](#skills-and-agents)

## What this does

These are instructions for the agent that installs the `howtoai-dev` plugin for one user and one workspace. It checks what this computer and the workspace already have, asks the user every decision the files cannot answer, and writes the answers into settings, workbooks, deploy targets, and links. The dev skills then work the way this user and project need, and no skill file is edited for one install. A need that no setting covers is a plugin change, and [docs/install-index.md](docs/install-index.md) says which files it touches.

Run it when the user asks to install, set up, or reconfigure `howtoai-dev`, or points you at this file. It can be rerun at any time; [Change a decision later](#change-a-decision-later) says how.

## Before you start

1. **Workspace.** The workspace is the folder that holds the project's `AGENTS.md` or `CLAUDE.md`. Ask the user which folder it is when the session did not start in one. All project choices below apply to it.
2. **Python.** Call the interpreter `PY`: `py -3 -I -B` on Windows, `python3 -I -B` elsewhere. Without Python 3.10 or later, stop and say the dev skills need it.
3. **Paths.** `<plugin>` is the folder that holds this file. Call these:
   - `CHECK`: `PY "<plugin>/scripts/install_check.py"`;
   - `DEVCORE`: `PY "<plugin>/skills/dev-core/scripts/devcore.py"`;
   - `DEVMODE`: `PY "<howtoai_root>/scripts/devmode.py"`, where `<howtoai_root>` comes from [Check dependencies](#check-dependencies).
4. **Rules for the whole run:**
   - **Look first, then ask.** Read the files before asking. Ask with the `grilling` skill's method: rounds of at most four numbered questions, each with a recommended answer, worded for the user's technical level. State the rest as defaults under **Assumed — tell me if wrong**.
   - **Preview every write.** Settings, `AGENTS.md`, links, the global settings file, and workbooks are shown first and written only after the user's yes.
   - **No secrets.** Name accounts, organizations, projects, and profiles; never store a token, key, or password. When a tool needs a sign-in (`gh auth login`, `az login`), the user runs it.
   - **Install nothing silently.** A missing tool is listed with its official source and installed only after the user's yes.
   - **Never move or delete** existing files, and never replace a real folder or file with a link.

## Check dependencies

1. Run `CHECK deps`. It reads only; its probes (`gh auth status`, `az extension show`, `az account show`, `docker version`) change nothing. It prints `deps_ok`, one item per dependency with `need`, `status`, and `fix`, and `dev_links`.
2. **Required items missing** (`deps_ok` false): show them with their `fix` lines and stop. The `howtoai` plugin is one of them (`grilling` and `skill-builder`): install it with its own `INSTALL.md` first, which also writes the dev-mode pointer.
3. **Items with `status` `unknown`:** a script cannot see them, so check them yourself:
   - connectors: search your own tool list for an Atlassian (Jira) and an Azure DevOps MCP server;
   - the harness: whether you can start subagents, publish an artifact (the Artifact tool), and run hooks (Claude Code).
4. Note which choices are open. A missing optional tool only removes the choices that need it; offer to install it when the user picks such a choice. Keep `howtoai_root` and `pointer_workspace` from the output.

## Dev mode

1. When `howtoai_root` is set, run `DEVMODE status --workspace "<workspace>"`. Its `setting` is the workspace's `## Dev mode` entry in `AGENTS.md`, or `null` when there is none; `paths.plugins` is the plugins folder.
2. **The entry exists:** use its value, and say it in one line ("Dev mode is on; plugins live in `<plugins folder>`"). Go on with [Install or link](#install-or-link).
3. **No entry:** ask the user, with dev mode off as the recommendation for a client who will not change the skills: "Do you want to keep the skills, agents, and tools in workspace files, so they are under version control and easier to change?"
   - **Yes:** ask where the plugins folder is: default `AGENTS/plugins`, or an existing clone of the `howtoai-mods` repository. It must be inside the workspace, written relative to it (`devmode.py` refuses `..`), so a clone elsewhere is moved or cloned again by the user first. Then run `DEVMODE set --dev-mode on --workspace "<workspace>" --plugins-folder "<folder>"`, show its `diff`, and after a yes run it again with `--write`.
   - **No:** run `DEVMODE set --dev-mode off --workspace "<workspace>"`, show the `diff`, and write it after a yes.
4. Without `howtoai_root` (the `howtoai` INSTALL never ran), dev mode cannot be set. Say so in one line, offering to run the `howtoai` plugin's `INSTALL.md` first for a user who wants dev mode; otherwise go on with plugin mode, and record dev mode as "off (no `howtoai` install; no entry written)".

## Install or link

**Plugin mode** (dev mode off):

1. Run `claude plugin list`. When it cannot run (no `claude` CLI in this harness), ask the user whether `howtoai-dev` is installed, and record the plugin check in [Verify](#verify) as not run. When `howtoai-dev` is not installed, ask, then run `claude plugin marketplace add GG323/claude-plugin` (only when the `howtoai-mods` marketplace is missing) and `claude plugin install howtoai-dev@howtoai-mods`. The skills, agents, and hooks load from the plugin; nothing is linked.

Skip the rest of this section.

**Dev mode** (on):

1. The plugin lives in `<plugins folder>/howtoai-dev/`. When it is missing there, ask, then clone the repository into an empty plugins folder: `git clone https://github.com/GG323/claude-plugin "<plugins folder>"`. Never clone over a folder that has files.
2. **Links.** For each skill folder in `<plugins folder>/howtoai-dev/skills/` and each agent file in `<plugins folder>/howtoai-dev/agents/`, run `DEVMODE link --source "<folder or file>"` (a preview). Show one table: name, destination, `action` (`create`, `none`, or `replace`). A `replace` means the destination links somewhere else: show where, and pass `--replace-link` only after the user picks this copy. A refusal means a real folder or file is in the way: leave it, and list it under Left out. After a yes, run each `create` and approved `replace` again with `--write`.
3. **Hooks.** Plugin hooks load only from an installed plugin, so in dev mode the two hooks are registered in the user's settings by absolute path. Hand this to the `update-config` skill with this brief, after showing it to the user: add, in `~/.claude/settings.json`, two `PreToolUse` hooks, and change nothing else.
   - matcher `Edit|Write|MultiEdit|NotebookEdit`, command `F="<plugins folder>/howtoai-dev/hooks/dev_test_first.py"; if command -v py >/dev/null 2>&1; then exec py -3 -I -B "$F"; else exec python3 -I -B "$F"; fi`;
   - matcher `^(Bash|PowerShell|Edit|Write|MultiEdit|mcp__.*)$`, the same command with `dev_safe_target.py`;
   - both with `"type": "command"`, `"shell": "bash"`, `"timeout": 15`, and the path written with forward slashes.

   Read the `dev hooks` item: when `in_settings` is true, both hooks are already registered; skip this step. When `plugin_installed` is true, the installed plugin also runs its own copy of the hooks, so registering them would run each hook twice: say so, and ask whether to uninstall the plugin (`claude plugin uninstall howtoai-dev`) or keep plugin hooks and skip this step.

## Per-user choices

These are the user's defaults for every workspace. Ask them only when `~/.claude/howtoai/dev-settings.json` has no value for them (`DEVCORE settings --workspace "<workspace>"` shows `"sources"`), and in one round:

1. **Tracker** usually used: Markdown files in the change folder (recommended when the user names none), Jira, GitHub Issues, or Azure DevOps Boards, with its project. Offer only the trackers whose tool [Check dependencies](#check-dependencies) found, plus any the user agrees to install.
2. **Plan format**, where plans are shown for approval (`plan.publish`): `auto` (recommended: an artifact where the harness has one, else an HTML file), `artifact`, `html-file`, `markdown` (no page; the plan file itself), or `tracker` (the plan as one parent item, an Epic by default, with the work items as its children). `tracker` needs a tracker other than Markdown.

Show the values as a preview with `DEVCORE setup --workspace "<workspace>" --scope user --values '<json>'`, for example `{"tracker": {"kind": "azure-devops", "ado_org": "https://dev.azure.com/contoso", "ado_project": "Shop"}, "plan": {"publish": "auto"}}`, and after a yes run it again with `--write`.

## Look up the project

Read files only, never a real `.env` or other secret store. Run the lookups in step 1 of [dev-core's Setup route](skills/dev-core/SKILL.md#setup): tracker signs, technologies, deploy entry points, environments, test entry points, and gate commands. Add:

- **Code projects and versions:** for each technology, every code project with its own version (for .NET, each `*.csproj` `TargetFramework` and any `global.json`; for others, the manifest's runtime or engine field). These feed [Workbooks](#workbooks).
- **Existing settings:** `DEVCORE settings --workspace "<workspace>"`. On a rerun, every value already set is the recommendation for its question.

Say what the lookups found as "From `<file>`: …", for the user to correct.

## Ask the project decisions

Ask with the `grilling` method, crucial items first, at most four per round. Items the files answer are stated, not asked.

- **Crucial** (asked unless a file answers them):
  1. Production markers to deny: hosts, connection-string fragments, cloud profiles, and account names (`environments.deny`). Prefer names that appear only in production, such as hosts and production-only accounts. The `dev-safe-target` hook denies any command or path that contains a marker, ignoring case, so a marker that also appears in local targets, project paths, or test commands (for example a database named like the project) would block them: leave it out, and say why in the install record. The safest choice: deny every production marker the files name.
  2. Allowed test targets (`environments.allow`). The safest choice: local targets only, because any target not on the list counts as production.
  3. The project's tracker and its project, when it differs from the user's default or a sign was found: Jira project key, GitHub `owner/name`, or Azure DevOps organization URL and project, with the work item type when it is not `Task`.
  4. The plan format, when it differs from the user's default.
- **Confirmed** (shown as found, for a yes or a correction): test commands (`testing.entry_points`), gate commands (`build.gate`; when the CI has no lint, format, or build step, propose the format and build commands from each technology's workbook Commands section, with their statement IDs as `source`), and throwaway test targets (`testing.ephemeral`: `docker` when Docker runs, else `none`).
- **Deploy:** set up a deploy target now, later, or never.
- **Defaults** (stated under **Assumed — tell me if wrong**): the plan folder `dev-plans`, `testing.test_first` `block`, and the review defaults (threshold 80, at most 5 rounds, 2 clean rounds to stop).

## Workbooks

For each technology found, run steps 1 and 2; run step 3 once at the end. During install, check only the statements whose truth depends on the code project's version; the others keep the base workbook's sources and receipts.

1. Run [dev-workbook's Create route](skills/dev-workbook/SKILL.md#create): it finds the base workbook or makes one, with its own approval.
2. Run its [Record a version](skills/dev-workbook/SKILL.md#record-a-version) route for each code project. When code projects use different versions of one technology, it makes a version workbook for each version (`<tech>@<key>.md`) with its own approval. The codebase's own version decides which rules apply; an old version is an upgrade to plan, never something to fix during install.
3. Run its [Audit](skills/dev-workbook/SKILL.md#audit) route once for the whole workspace and report what it finds, including versions past or near their support date. Skip its check of the installed tool versions unless the user asks for it, and list it under Left out.

## Deploy target

When the user chose "now", run [dev-deploy's Set up a target route](skills/dev-deploy/routes/setup-target.md#find-what-exists) for each target the user names; it asks its own questions and writes `.howtoai/deploy/targets.json` after a yes. "Later" and "never" set nothing: the first deploy sets the target up.

## Write and record

1. **Project settings:** `DEVCORE setup --workspace "<workspace>" --values '<json>'` with every project decision, including the tracker and plan format when they equal the user's defaults, because the project file is what teammates share, as a preview; after a yes, again with `--write`. A refusal (an unknown key, a value that looks like a secret, or `plan.publish` `tracker` with Markdown work items) is shown to the user and the value asked again.
2. **Install record:** copy [assets/install-record.md](assets/install-record.md) to `<workspace>/.howtoai/dev/install.md` and fill every placeholder; a row with nothing to say gets "none". Read the date from the system clock (for example `Get-Date -Format yyyy-MM-dd` or `date +%F`), never from memory. On a rerun, rewrite it in full.
3. **AGENTS.md:** show this line and add it after a yes to the workspace `AGENTS.md`'s skills and agents section: "`howtoai-dev` - the dev process (plan, tests first, build, review, deploy, learn); settings in `.howtoai/dev/settings.json`, install record in `.howtoai/dev/install.md`." Skip it when this line is already there. When another `howtoai-dev` line is there, show the old and new line and replace the old one after a yes, so the section keeps one.

## Verify

Run each check, and record the result in the install record's Checks table:

1. `CHECK deps`: `deps_ok` is true, and no item a chosen option needs is `missing`. An item for a step that was deferred or left out (for example hooks not registered yet) is recorded under Left out, not as a failed check.
2. `DEVCORE settings --workspace "<workspace>"`: `configured` is true and shows the approved values.
3. `dev-workbook`'s `workbook.py validate` on each workbook written in this run is clean.
4. Dev mode: `DEVMODE status --workspace "<workspace>"`, where every link from this run is `link-ok`; plugin mode: `claude plugin list` shows `howtoai-dev`.
5. `CHECK index` is clean: the change index still matches the plugin's files.

A check that fails is fixed now when the fix stays within the user's decisions; otherwise it is reported.

## Double check with skill-builder

Hand the finished install to the `skill-builder` skill (`/skill-builder` in Claude Code) on its verification-only route, (it plans a short verification-only check and asks one approval for it) with this brief: "Verify the howtoai-dev install in `<workspace>`: compare `.howtoai/dev/install.md`, the dev settings, the `AGENTS.md` dev-mode entry, the links and hooks, and the workbooks against the decisions in the install record and `<plugin>/docs/install-index.md`. Read only; report each mismatch with its file."

1. Fix each mismatch that stays within the user's decisions, then hand it the same brief again. Stop after two rounds.
2. A mismatch that would change a decision, or needs a dev skill file changed, goes to the user first; a skill file change then runs as a `skill-builder` change to the `howtoai-dev` plugin, with its own plan.
3. When `skill-builder` is not available, say that the double check did not run, and record it so in the install record; never report it as passed. When it is available but cannot start its checker (no subagents), run its verification yourself, read-only, and record it as a **self-check**, which is weaker evidence.
4. Fill the install record's double-check row now: the record was written before this step.

## Summary

Tell the user, in one message:

1. One line: installed in plugin mode or dev mode, for which workspace.
2. A table: decision, value, where it is stored, and checked (yes, no, or not run).
3. What was left out, and why.
4. The install record's path.

## Change a decision later

Run this file again. Every value already set is the recommendation for its question, so the user changes only what they want; each write is previewed again. To change only one thing, the user can also ask a dev skill directly: `dev-core`'s Setup route for settings, `dev-workbook` for workbooks, and `dev-deploy` for targets.

Turning dev mode off, each step previewed and written only after a yes:

1. `DEVMODE set --dev-mode off --workspace "<workspace>"`, then again with `--write`.
2. For each of this plugin's links in `dev_links` (state `ok`): `DEVMODE unlink --dest "<dest>"`, then again with `--write`. The plugin's files stay where they are.
3. Hand the removal of the two hook registrations from `~/.claude/settings.json` to `update-config`, changing nothing else, so a later plugin install does not run them twice.
4. Then follow [Install or link](#install-or-link) for plugin mode.

## Output contract

- **Deliverables**, each written only after a preview and the user's yes:
  - the user's defaults in `~/.claude/howtoai/dev-settings.json` and the project's settings in `<workspace>/.howtoai/dev/settings.json`;
  - the `## Dev mode` entry in the workspace `AGENTS.md`, and one skills-and-agents line there;
  - workbooks and version workbooks, through `dev-workbook`; deploy targets in `.howtoai/deploy/targets.json`, through `dev-deploy`;
  - in dev mode, links in `~/.claude/skills` and `~/.claude/agents`, and the two hooks in `~/.claude/settings.json`; in plugin mode, the installed plugin;
  - the install record `<workspace>/.howtoai/dev/install.md`, from [assets/install-record.md](assets/install-record.md), with its fixed sections (Run, Decisions, Checks, Left out) and every row filled or "none".
- **Report:** the [Summary](#summary) message in chat, for the user: one line, the decisions table, what was left out, and the record's path. It has the same shape on every run.
- **Success check:** every check in [Verify](#verify) passed or is named as failed, and the double check ran or is named as not run.

## Common failures

| Symptom | Cause | Fix |
| --- | --- | --- |
| `devmode.py set` exits 2 on the plugins folder | The folder is outside the workspace or has `..` | Use a folder inside the workspace, written relative to it |
| `devmode.py link` refuses a destination | A real folder or file with the same name is in `~/.claude/skills` or `~/.claude/agents` | Leave it, list it under Left out, and ask the user whether it is an old copy they want to remove themselves |
| `devcore.py setup` refuses `plan.publish` `tracker` | Work items are Markdown files | Pick a tracker first, or another plan format |
| `gh`, `az`, or Docker shows `missing` although installed | The tool is not signed in, the extension is missing, or the Docker engine is stopped (see `detail`) | Show the item's `fix` line; the user signs in or starts it, then rerun `CHECK deps` |
| Hooks run twice | The plugin is installed and the hooks are also registered in `~/.claude/settings.json` | Keep one: uninstall the plugin in dev mode, or remove the registrations in plugin mode |
| `CHECK index` reports problems | The plugin changed and the index did not | Update [docs/install-index.md](docs/install-index.md) in the same plugin change |

## What it can't do

- It does not install a tool or sign in without the user; it lists the official source and the command the user runs.
- It does not edit skill files to fit one install. [docs/install-index.md](docs/install-index.md) shows what a plugin change would touch, and `skill-builder` makes it.
- It cannot see connectors or harness features from a script; the agent checks its own tools.
- Only Claude Code (CLI and desktop) is verified. Other agents need a shell, Python, and ideally subagents; without hooks, the safety rules that the hooks enforce are only in the skills' instructions.
- It creates no tracker items: `dev-plan` makes them later, after approval.

## Feedback

Send requested changes or reported problems with this procedure to the `skill-builder` skill (`/skill-builder` in Claude Code), not by file path. If `skill-builder` is unavailable, agree the change with the user first, keep it as small as the problem needs, and check this file afterwards.

## Skills and agents

- `grilling` - the question method for every decision.
- `dev-core` - its Setup route's lookups and the settings script.
- `dev-workbook` - the Create, Record a version, and Audit routes.
- `dev-deploy` - the Set up a target route.
- `update-config` - registers the two hooks in dev mode.
- `skill-builder` - the double check, and any plugin change.
- The `howtoai` plugin's `devmode.py` - the dev-mode entry and the links; its contract is the `howtoai` plugin's `docs/dev-mode.md`.
- [docs/install-index.md](docs/install-index.md) - every install requirement, where it is read, and what to change for a new option.
- No agents are started by the install itself; `skill-builder`'s checker runs in the double check.
