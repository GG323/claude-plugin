# Install howtoai-dev

## Contents

- [Goal](#goal)
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
- [Troubleshooting](#troubleshooting)
- [Feedback](#feedback)

## Goal

Install `howtoai-dev` for one user and one workspace, so the dev skills work the way this user and project need without any skill file edited for this install. Done means these are written, each only after a preview and the user's yes, and checked:

- the user's defaults in `~/.claude/howtoai/dev-settings.json` and the project's settings in `<workspace>/AGENTS/settings.json`;
- the `## Dev mode` entry in the workspace `AGENTS.md` (Git version control and dev mode, each on or off), and this plugin's one line under its `## Installed skills` section ([AUDIT.md](AUDIT.md#skills-line));
- deny rules for secret env files in `<workspace>/.claude/settings.json`, through `update-config`;
- workbooks and version workbooks in `AGENTS/workbooks/` through `dev-workbook`, and deploy targets in `AGENTS/deploy-targets.json` through `dev-deploy`;
- in dev mode, links in `~/.claude/skills` and `~/.claude/agents` and the three hooks in `~/.claude/settings.json`; in plugin mode, the installed plugin;
- the install record `<workspace>/AGENTS/install.md`, from [assets/install-record.md](assets/install-record.md), every row filled or "none";
- the [Summary](#summary) message in chat.

**Where things are kept.** What the user reviews sits at the `<workspace>/AGENTS/` root, a plain folder they can open and track in the `AGENTS/` repository: `settings.json` (shared by the workspace's tools, one top-level key each; this plugin's project settings are its `"howtoai-dev"` key), `install.md` (the install record), `lessons.md` (`dev-learn`'s log), `workbooks/` (project and version workbooks), and `deploy-targets.json`. Run records go in `AGENTS/state/`, left out of Git: `approvals.json` and `deploy-log.md` (from `dev-deploy`) and the generated `cache/`. The dev-reply-log hook's hashes are not workspace files: they go in dev-core's own `state/replies.jsonl` inside the plugin, shared by every workspace that uses this copy, and only that hook writes them. The user's own defaults stay in `~/.claude/howtoai/`. Files from an older layout (`.howtoai/`, `AGENTS/howtoai/`, `AGENTS/settings/`) are not read, and [Look up the project](#look-up-the-project) offers to move them. For a nontechnical user, say that the project's choices for the dev tools are kept in one folder they can open and check, and name the files only when they ask.

A need no setting covers is a plugin change through `skill-builder`; [docs/install-index.md](docs/install-index.md) says which files it touches. The install creates no tracker items (`dev-plan` makes them after approval). Only Claude Code (CLI and desktop) is verified; without hooks, the hooks' rules hold only through the skills' instructions. Rerun this file at any time ([Change a decision later](#change-a-decision-later)).

## Before you start

1. **Workspace:** the folder that holds the project's `AGENTS.md` or `CLAUDE.md`. Ask the user which folder it is when the session did not start in one; for a nontechnical user, ask which folder holds their project, by its name.
2. **Python:** call the interpreter `PY`: `py -3 -I -B` on Windows, `python3 -I -B` elsewhere. Without Python 3.10 or later, stop and say the dev skills need it; for a nontechnical user, say a one-time Python install is needed, which whoever looks after this computer can do.
3. **Paths.** `<plugin>` is the folder that holds this file.
   - `CHECK`: `PY "<plugin>/scripts/install_check.py"`;
   - `DEVCORE`: `PY "<plugin>/skills/dev-core/scripts/devcore.py"`;
   - `DEVMODE`: `PY "<howtoai_root>/scripts/devmode.py"`, with `<howtoai_root>` from [Check dependencies](#check-dependencies).
4. **Rules for the whole run:**
   - **Look first, then ask.** Read the files before asking. Ask with the `grilling` skill's method: rounds of at most four numbered questions, each with a recommended answer, worded for the user's technical level. State the rest as defaults under **Assumed — tell me if wrong**.
   - **Word everything for the level**, findings, previews, and reports as much as questions: for a nontechnical user, say what a file, folder, or tool is for ("the shop's live settings") in place of its name or path, and explain any term that has to stay. A write preview also keeps the exact path, beside that meaning.
   - **Reread for a nontechnical user.** Before sending a message to a nontechnical user, reread it, and replace each path, file name, command, host name, and rule syntax with what it is for; only a write preview keeps the exact path, beside that meaning.
   - **The nontechnical form wins.** For a nontechnical user, the nontechnical form wins over any step's wording that gives a command, path, or file name: name the step, what it is for, and who can do it. In messages, only a write preview keeps the exact text; the install record and other files you write keep it as usual.
   - **Preview every write.** Settings, `AGENTS.md`, links, the global settings file, and workbooks are shown first and written only after the user's yes.
   - **Write files with the file tools.** Create and edit `AGENTS.md`, the install record, and every other file you write yourself with the file tools (Write, Edit), never through a shell redirect, heredoc, or here-string: `dev-safe-target` denies a command whose text names a production marker, and the install record names them.
   - **A blocked step is reported.** When a hook, the harness, or a permission rule blocks a command, say so in your next message with what it would have done. Never report that step as done, and never do it another way. List it under Left out with the command for the user to run; for a nontechnical user, name the step and who can do it ("ask whoever looks after this computer to install the dev tools"), and keep the command in the install record.
   - **No secrets.** Name accounts, organizations, projects, and profiles; never store a token, key, or password. When a tool needs a sign-in (`gh auth login`, `az login`), the user runs it; for a nontechnical user, say which account needs a sign-in and who does it, with no command.
   - **Install nothing silently.** A missing tool is listed with its official source and installed only after the user's yes.
   - **Never move or delete** existing files, and never replace a real folder or file with a link.

## Check dependencies

1. Run `CHECK deps` (it reads only; its probes change nothing). In your first message to the user, show every entry of `missing`, the dev hooks too, with its `need` (what it blocks), also when no choice needs it yet or step 2 stops the install. For a nontechnical user, name each item by what it does and who can install it, with no command or `fix` line.
2. **Required items missing** (`deps_ok` false): show them with their `fix` lines and stop. The `howtoai` plugin (`grilling`, `skill-builder`) is installed with its own `INSTALL.md` first, which also writes the dev-mode pointer. Stop the same way when `howtoai_root` is empty, even with `deps_ok` true: without its `devmode.py` the [Dev mode](#dev-mode) settings can be neither read nor recorded, so never go on as if dev mode were off. For a nontechnical user, name each missing item by what it does and who can install it, with no `fix` line; the `fix` lines go in the install record.
3. **Items with `status` `unknown`** a script cannot see: check your own tool list for an Atlassian (Jira) and an Azure DevOps MCP server, and whether you can start subagents, publish an artifact (the Artifact tool), and run hooks (Claude Code).
4. A missing optional tool only removes the choices that need it; offer to install it when the user picks such a choice. Keep `howtoai_root` and `pointer_workspace`.

## Dev mode

The workspace's `## Dev mode` entry in `AGENTS.md` holds two required settings, **Git version control** and **Dev mode**, each `on` or `off`. Dev mode on needs Git version control on. A missing or invalid value is an error to resolve with the user, never a default.

1. Run `DEVMODE status --workspace "<workspace>"`:
   - **Exit 0:** `setting` holds both values, and `paths.plugins` is the plugins folder.
   - **Exit 1 with `needs_setting`:** tell the user each `problem` and go to step 3; `dev_mode` is then `null`, which never means off. When `agents_md_exists` is false, first ask to create `AGENTS.md`, where the setting is kept (`skill-audit`'s workspace audit drafts one), and stop if the user declines. For a nontechnical user, call `AGENTS.md` the folder's notes file, say what it is for, and say each `problem` as what is missing and who decides it.
   - **Any other failure:** show its `error` and stop.
2. **A valid setting:** say both values in one line ("Git version control and dev mode are on; plugins live in `<plugins folder>`"); for a nontechnical user, without the folder path. When the user wants to change one, go to step 3. When dev mode is on and `pointer.workspace` is another workspace, check `paths.plugins_shared`: when it is true, this workspace shares that workspace's clone and the pointer stays there by design, so go to step 5. When it is false, go to step 4 with the current values (`DEVMODE link` reads the pointer's workspace). Otherwise go to step 5.
3. **Ask.** A value already set is the recommendation.
   - **Dev mode:** "Do you want to keep the skills, agents, and tools in workspace files, so they are under version control and easier to change?" Recommend no for a client who will not change the skills. Say that yes also turns Git version control on.
   - **Yes:** Git version control is on, so do not ask it separately; a user who does not want Git gets dev mode off. Ask where the plugins folder is, recommending the default `AGENTS/plugins`: a clone in this workspace's `AGENTS/`, which makes it the main development workspace that the global links point to (the howtoai plugin's `INSTALL.md`, Ask the install questions, item 4, has the clone source and the main-workspace choice). Other choices: an existing clone of the `howtoai-mods` repository inside the workspace, written relative to it (`devmode.py` refuses `..`), or another workspace's clone, kept as the main one, given as its absolute path (the folder above the pointer's `howtoai_root`), so nothing is cloned or linked again and the pointer stays there.
   - **No:** ask "Should Git version control be enabled for this workspace: on or off?", recommending on, because changes to the instructions and tools can then be reviewed and undone.
4. **Record both values**, always with both flags:
   - dev mode on: `DEVMODE set --dev-mode on --git-version-control on --workspace "<workspace>" --plugins-folder "<folder>"`;
   - dev mode off: `DEVMODE set --dev-mode off --git-version-control <on or off> --workspace "<workspace>"`.

   Show its `diff` and, when `pointer_changed` is true, what the pointer will hold; after a yes, run it again with `--write`. When it refuses, show the `error` and ask again; never change an answer to make it pass. When the user does not approve the write, stop: the install cannot go on without both settings.
5. **Git problems.** With Git version control on, run `DEVMODE status` again, show every sentence in `git.problems`, and fix one only after the user's yes; for a nontechnical user, say each problem in plain words, and who can fix it:
   - **Git is not installed:** give the official install source.
   - **`AGENTS/` not in a repository:** offer `git init "<workspace>/AGENTS"` and a `.gitignore` there with `state/` (and `plugins/` only when the plugins folder is a git clone of its own), written with the file tools after showing it; this works in a multi-repo workspace too. For a nontechnical user, offer to start change history for the AI tools folder, with no command.
   - **The workspace not in a repository:** offer `git init "<workspace>"` only when the user wants the whole workspace in one repository, never when `git.layout` is `multi-repo` (the root holds the user's own repositories; its root files are `git.notes`, not problems). Never add, commit, create a remote, or push. For a nontechnical user, offer to start change history for this folder, with no command.
   - **Ignored:** show the folder, and ask whether to change that `.gitignore` or leave it. For a nontechnical user, say a folder is set to be left out of the change history, and ask whether to keep it that way.

   With dev mode off, these problems do not stop the install: list what stays under Left out.

## Install or link

**Plugin mode** (dev mode off): run `claude plugin list`. When `howtoai-dev` is not installed, ask, then run `claude plugin marketplace add GG323/claude-plugin` (only when the `howtoai-mods` marketplace is missing) and `claude plugin install howtoai-dev@howtoai-mods`; nothing is linked. When the CLI cannot run here, ask the user whether it is installed and record the plugin check in [Verify](#verify) as not run. For a nontechnical user, when you cannot run the install yourself, say the dev tools still need a one-time install that whoever looks after this computer can do, with no command; the commands go under Left out in the install record. Skip the rest of this section.

**Dev mode** (on):

1. The plugin lives in `<plugins folder>/howtoai-dev/`. When it is missing there, ask, then clone into an empty plugins folder: `git clone <clone source> "<plugins folder>"`, where the source is `https://github.com/GG323/claude-plugin` or a local development clone the user names (only its committed changes come along). Never clone over a folder that has files.
2. **Git before links.** Run `DEVMODE status --workspace "<workspace>"` and show any `git.problems`. Create no link while `git.problems` is not empty (Git not installed, or a checked path in no repository); a multi-repo workspace's `git.notes` do not block linking. When the user declines that fix, offer dev mode off (step 4 of [Dev mode](#dev-mode), then Plugin mode); when they decline that too, stop. An ignored folder the user chose to leave does not block linking: list it under Left out.
3. **Links.** For each skill folder in `<plugins folder>/howtoai-dev/skills/` and each agent file in `<plugins folder>/howtoai-dev/agents/`, run `DEVMODE link --source "<folder or file>"` (and again with `--harness agents` or `--harness copilot` when `~/.agents` or `~/.copilot` exists) and show one table: name, destination, `action` (`create`, `none`, or `replace`). A `replace` links elsewhere: show where, and pass `--replace-link` only after the user picks this copy. A refusal means a real folder or file is in the way: leave it, and list it under Left out. After a yes, run each `create` and approved `replace` again with `--write`.
4. **Hooks.** Plugin hooks load only from an installed plugin, so in dev mode the three hooks are registered by absolute path. Show this brief to the user, then hand it to the `update-config` skill: add, in `~/.claude/settings.json`, two `PreToolUse` hooks and one `UserPromptSubmit` hook, and change nothing else.
   - matcher `Edit|Write|MultiEdit|NotebookEdit`, command `F="<plugins folder>/howtoai-dev/hooks/dev_test_first.py"; if command -v py >/dev/null 2>&1; then exec py -3 -I -B "$F"; else exec python3 -I -B "$F"; fi`;
   - matcher `^(Bash|PowerShell|Edit|Write|MultiEdit|mcp__.*)$`, the same command with `dev_safe_target.py`;
   - under `UserPromptSubmit`, matcher `*`, the same command with `dev_reply_log.py` (it records a hash of each user prompt, never its text, so an approval in the user's name can be checked against a real reply);
   - all three with `"type": "command"`, `"shell": "bash"`, `"timeout": 15`, and the path written with forward slashes.

   Read the `dev hooks` item: when `in_settings` is true, all three are registered; skip this step. When `plugin_installed` is true, the installed plugin runs its own copy, so each hook would run twice: say so, and ask whether to uninstall the plugin (`claude plugin uninstall howtoai-dev`) or keep plugin hooks and skip this step.

## Per-user choices

These are the user's defaults for every workspace. Ask them only when `~/.claude/howtoai/dev-settings.json` has no value for them (`DEVCORE settings --workspace "<workspace>"` shows `"sources"`), in one round:

1. **Tracker** usually used: Markdown files in the change folder (recommended when the user names none), Jira, GitHub Issues, or Azure DevOps Boards, with its project. Offer only the trackers whose tool [Check dependencies](#check-dependencies) found, plus any the user agrees to install.
2. **Plan format** (`plan.publish`): `auto` (recommended: an artifact where the harness has one, else an HTML file), `artifact`, `html-file`, `markdown` (no page; the plan file itself), or `tracker` (one parent item, an Epic by default, with the work items as children; needs a tracker other than Markdown). For a nontechnical user, ask how they want to see plans ("a page in this app" or "a file on this computer"), with no setting names.

Show the values as a preview with `DEVCORE setup --workspace "<workspace>" --scope user --values-file "<file>"` (write the JSON to a temporary file outside the workspace with the Write tool: production markers in a command's text make `dev-safe-target` deny it), for example `{"tracker": {"kind": "azure-devops", "ado_org": "https://dev.azure.com/contoso", "ado_project": "Shop"}, "plan": {"publish": "auto"}}`, and after a yes run it again with `--write`.

## Look up the project

Read files only, never a real `.env` or other secret store: `.env.production` and every other environment's env file stay closed. Application settings files such as `appsettings.Production.json` are no env file: always look in them, with a command that prints only host, database, and account names, never the value of a password, key, or token. Run the lookups in step 1 of [dev-core's Setup route](skills/dev-core/SKILL.md#setup), and add:

- **Code projects and versions:** for each technology, every code project with its own version (for .NET, each `*.csproj` `TargetFramework` and any `global.json`; for others, the manifest's runtime or engine field), for [Workbooks](#workbooks).
- **Existing settings:** `DEVCORE settings --workspace "<workspace>"`. On a rerun, every value already set is the recommendation for its question.
- **Files from an older layout:** when `<workspace>/.howtoai/`, `<workspace>/AGENTS/howtoai/`, or `<workspace>/AGENTS/settings/` exists, its settings, record, workbooks, and deny markers are not read any more, so production markers in it no longer block anything. Say so, and offer to move each file to its place: `dev/settings.json` into the `"howtoai-dev"` key of `AGENTS/settings.json` (through `DEVCORE setup` with the file as `--values-file`), `dev/install.md` to `AGENTS/install.md`, `dev/lessons.md` to `AGENTS/lessons.md`, `workbooks/` to `AGENTS/workbooks/`, `deploy/targets.json` to `AGENTS/deploy-targets.json`, `deploy/approvals.json` and `deploy/log.md` to `AGENTS/state/` (as `deploy-log.md`), and `dev/replies.jsonl` to dev-core's `state/` in the plugin; `cache/` is regenerated. Move only after the user's yes, never over a file that already exists (list it and ask), and then run `DEVCORE settings` again. For a nontechnical user, say the earlier setup is stored in an old place and offer to move it, with no folder names.

Say what the lookups found as "From `<file>`: …", for the user to correct. For a nontechnical user, name each source by what it is ("the shop's live settings"), with no file name.

## Ask the project decisions

Ask with the `grilling` method, crucial items first; items the files answer are stated, not asked.

- **Crucial** (asked unless a file answers them):
  1. Production markers to deny (`environments.deny`): hosts, connection-string fragments, cloud profiles, and account names, preferring names that appear only in production. The `dev-safe-target` hook denies any command or connector (MCP) call whose text contains a marker anywhere, ignoring case; file edits are not checked. A marker that also appears in local targets, project paths, or test commands (for example a database named like the project) would block them: leave it out, and say why in the install record. Its block message names the marker, the settings file that lists it (the project's `AGENTS/settings.json`, the user's `~/.claude/howtoai/dev-settings.json`, or both), that matching rule, and that the list is changed with dev-core's Setup route or by rerunning this INSTALL; tell the user so when you ask. The safest choice: deny every production marker the files name, and nothing else; a shared target that is not production, such as a team's dev database, goes on neither list, so `dev-test` asks. For a nontechnical user, ask which live systems must never be touched, by what they are, with no setting name.
  2. Allowed test targets (`environments.allow`). The safest choice: local targets only, because any target not on the list counts as production.
  3. The project's tracker and its project, when it differs from the user's default or a sign was found: Jira project key, GitHub `owner/name`, or Azure DevOps organization URL and project, with the work item type when it is not `Task`.
  4. The plan format, when it differs from the user's default.
- **Confirmed** (shown as found, for a yes or a correction): test commands (`testing.entry_points`), gate commands (`build.gate`; when the CI has no lint, format, or build step, propose the format and build commands from each technology's workbook Commands section, with their statement IDs as `source`), and throwaway test targets (`testing.ephemeral`: `docker` when Docker runs, else `none`). For a nontechnical user, describe each check by what it does ("the shop's tests"), with no command.
- **Deploy:** set up a deploy target now, later, or never.
- **Defaults** (under **Assumed — tell me if wrong**): the plan folder `dev-plans`, `testing.test_first` `block`, and the review defaults (threshold 80, at most 5 rounds, 2 clean rounds to stop). For a nontechnical user, state each default in plain words, with no setting name.

## Workbooks

For each technology found, run steps 1 and 2; run step 3 once at the end. During install, check only the statements whose truth depends on the code project's version.

1. Run [dev-workbook's Create route](skills/dev-workbook/routes/create.md#steps): it finds the base workbook or makes one, with its own approval.
2. Run its [Record a version](skills/dev-workbook/routes/record-version.md#steps) route for each code project; projects on different versions of one technology get a version workbook each (`<tech>@<key>.md`), with its own approval. The codebase's own version decides which rules apply; an old version is an upgrade to plan, never something to fix during install.
3. Run its [Audit](skills/dev-workbook/routes/audit.md#steps) route once and report what it finds, including versions past or near their support date. Skip its check of the installed tool versions unless the user asks for it, and list it under Left out.

## Deploy target

When the user chose "now", run [dev-deploy's Set up a target route](skills/dev-deploy/routes/setup-target.md#find-what-exists) for each target the user names; it asks its own questions and writes after a yes. "Later" and "never" set nothing: the first deploy sets the target up.

## Write and record

1. **Project settings:** `DEVCORE setup --workspace "<workspace>" --values-file "<file>"` with every project decision (write the JSON to a temporary file outside the workspace with the Write tool: production markers in a command's text make `dev-safe-target` deny it), including the tracker and plan format when they equal the user's defaults, because the project file is what teammates share; preview first, and after a yes run it again with `--write`. A refusal (an unknown key, a value that looks like a secret, or `plan.publish` `tracker` with Markdown work items) is shown to the user and the value asked again. Then run step 5 of [dev-core's Setup route](skills/dev-core/SKILL.md#setup): the deny rules for secret env files, with their own yes.
2. **Install record:** copy [assets/install-record.md](assets/install-record.md) to `<workspace>/AGENTS/install.md` and fill every placeholder (with the file tools, see Rules for the whole run); a row with nothing to say gets "none". Read the date from the system clock (`Get-Date -Format yyyy-MM-dd` or `date +%F`), never from memory. On a rerun, rewrite it in full.

## Verify

[AUDIT.md](AUDIT.md) holds what every install must leave true, so the install and every later audit check it the same way.

1. Run `py -3 -I -B "<howtoai_root>/skills/skill-audit/scripts/check_plugins.py" --audit "<plugin>/AUDIT.md" --workspace "<workspace>"`, and again with `--audit "<howtoai_root>/AUDIT.md"` (both dev-mode settings, Git, and the `howtoai` links).
2. For each `fail`, show the check's fix and any `text` as a preview, and apply it after the user's yes. For each `needs-approval`, show the command, run it after the user's yes, and judge it by its `pass_when`. Judge a `review` from its listed files. An `invalid` is a broken check: report it, never count it as passed. For a nontechnical user, say what each check looks at and that it changes nothing, with no command.
3. Check what only this install knows: each approved value is the one in the settings and the dev-mode entry, `DEVMODE status` exits 0 and each of its `git.problems` is fixed or under Left out, and `<workspace>/.claude/settings.json` holds each approved deny rule for secret env files. A check for a deferred step goes under Left out, not as a failed check.
4. Run step 1 again and record every result in the install record's Checks table.

Fix a failing check now when the fix stays within the user's decisions; otherwise report it.

## Double check with skill-builder

Hand the finished install to the `skill-builder` skill (`/skill-builder` in Claude Code) on its verification-only route, with this brief: "Verify the howtoai-dev install in `<workspace>`: compare `AGENTS/install.md`, the dev settings, the results of `<plugin>/AUDIT.md`, the `AGENTS.md` dev-mode entry, the links and hooks, and the workbooks against the decisions in the install record and `<plugin>/docs/install-index.md`. Read only; report each mismatch with its file."

1. Fix each mismatch that stays within the user's decisions, then hand it the same brief again. Stop after two rounds.
2. A mismatch that would change a decision, or needs a dev skill file changed, goes to the user first; a skill file change then runs as a `skill-builder` change to the `howtoai-dev` plugin, with its own plan.
3. When `skill-builder` is not available, say that the double check did not run, and record it so; never report it as passed. When it cannot start its checker (no subagents), run its verification yourself, read-only, and record it as a **self-check**, which is weaker evidence.
4. Fill the install record's double-check row now.

## Summary

Tell the user, in one message:

1. One line: installed in plugin mode or dev mode, for which workspace.
2. A table: decision, value, where it is stored, and checked (yes, no, or not run). For a nontechnical user, the place is named by what it is ("this folder's dev settings"), with no path.
3. What was left out, and why. For a nontechnical user, each item names the step and who can do it, with no command.
4. Where the install record is: for a developer, its path; for a nontechnical user, what it is ("your setup notes, saved in this folder"), with no path.

The message has the same shape on every run: one line, the decisions table, the left-out items, and where the record is (its path for a developer only).

## Change a decision later

Run this file again: every value already set is the recommendation, and each write is previewed again. To change one thing, the user can also ask a dev skill directly: `dev-core`'s Setup route for settings, `dev-workbook` for workbooks, `dev-deploy` for targets.

Turning dev mode off, each step previewed and written only after a yes:

1. Ask whether Git version control is on or off, recommending its current value, or on when it has none. Then run `DEVMODE set --dev-mode off --git-version-control <on or off> --workspace "<workspace>"`, and again with `--write`.
2. When the pointer names another workspace, say that the links serve that workspace too, and ask before removing any. For each of this plugin's links in `dev_links` (state `ok`): `DEVMODE unlink --dest "<dest>"`, then again with `--write`. The plugin's files stay where they are.
3. Hand the removal of the three hook registrations from `~/.claude/settings.json` to `update-config`, changing nothing else, so a later plugin install does not run them twice.
4. Then follow [Install or link](#install-or-link) for plugin mode.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `devmode.py` exits 1 with `needs_setting` | A value is missing or invalid, or dev mode is on with Git off (for `link`, in the pointer's workspace): ask the user and record both values, as [Dev mode](#dev-mode) says; never assume one |
| `install_check.py deps` gives no `howtoai_root` | Stop: the `howtoai` plugin's `INSTALL.md` runs first; for a nontechnical user, say the HowToAI tools need installing first, by whoever looks after this computer |
| `devmode.py set` exits 2 on the plugins folder | Use a folder inside the workspace, written relative to it, with no `..`, or the absolute path of an existing `howtoai-mods` clone (with `.claude-plugin/marketplace.json` and `howtoai/`) to share it |
| `devmode.py link` refuses a destination | A real folder or file is in the way: leave it, list it under Left out, and ask the user whether it is an old copy they want to remove themselves |
| `devcore.py setup` refuses `plan.publish` `tracker` | Work items are Markdown files: pick a tracker first, or another plan format |
| `gh`, `az`, or Docker shows `missing` although installed | Not signed in, extension missing, or engine stopped (see `detail`): show the item's `fix` line, the user acts, then rerun `CHECK deps`. For a nontechnical user, say which tool needs attention and who can do it, with no command |
| Hooks run twice | Keep one: uninstall the plugin in dev mode, or remove the registrations in plugin mode |
| `CHECK index` reports problems | Update [docs/install-index.md](docs/install-index.md) in the same plugin change |

## Feedback

Send requested changes or reported problems with this procedure to the `skill-builder` skill (`/skill-builder` in Claude Code), not by file path. If `skill-builder` is unavailable, agree the change with the user first, keep it as small as the problem needs, and check this file afterwards.
