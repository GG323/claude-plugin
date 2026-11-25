# Install howtoai

## Contents

- [Before you start](#before-you-start)
- [Check dependencies](#check-dependencies)
- [Ask the install questions](#ask-the-install-questions)
- [Record the choice](#record-the-choice)
- [Install or link](#install-or-link)
  - [Dev mode off](#dev-mode-off)
  - [Dev mode on](#dev-mode-on)
- [Allow the weekly audit](#allow-the-weekly-audit)
- [Run the audit](#run-the-audit)
- [Summarize](#summarize)

## Before you start

These are instructions for the agent installing the `howtoai` plugin (`skill-builder`, `skill-finder`, `skill-audit`, `skill-design`, `brain-dump`, `grilling`, and `handover`). Follow them top to bottom. They are safe to run again: each step checks what is already set up and changes only what differs.

- **Ask, never assume.** Every install decision is the user's. Word each question for the user's technical level (the `# User settings (command-pane)` block in the system prompt, when there is one), one short message at a time, with your recommendation.
- **Preview, then write.** Every write to `~/.claude/` or to an `AGENTS.md` is shown first (the script's preview without `--write`), and runs only after the user's yes. Never move, delete, or overwrite the user's files; the script refuses to replace a real folder or file, and you do not work around it.
- **The script.** `devmode.py` does every check and write; its contract is [docs/dev-mode.md](docs/dev-mode.md). Call the folder holding this file `<howtoai>`, and run the script as `py -3 -I -B "<howtoai>/scripts/devmode.py" <command>` (`python3 -I -B` outside Windows). Each command prints JSON; read `ok` and `error`.
- **No local copy yet.** If you read this file from the web and have no copy on disk, check Python (`py -3 --version`) and git (`git --version`) by hand now, and run `check-deps` once [Install or link](#install-or-link) has put the files on disk.

Run `status` first (with `--workspace "<path>"` when the user names a workspace). Exit 1 with `needs_setting` means a setting is missing or invalid, as on a first install: tell the user which, and have them make it on or off in [Ask the install questions](#ask-the-install-questions); never assume a value. When it shows a `setting`, this is a rerun: tell the user the current setting (Git version control and its `git` problems, dev mode, workspace, folders) and the link counts, and ask whether to keep it or change it. Keeping it still runs every section below, which repairs what is missing.

## Check dependencies

Run `check-deps` and show the user each item that is `missing`, with its `fix`:

- A missing `required` item stops the install until it is fixed; offer to run its fix command, and run it only after the user's yes.
- A missing `optional` item is reported and the install goes on (for example, without `uv` or `chromadb`, `skill-finder` cannot search).
- `file links` is needed only for dev mode; carry it into the dev-mode question.
- `git` is needed for Git version control, and so for dev mode: dev mode cannot be turned on until it is installed. Carry it into the questions.
- For each `unknown` harness skill, look in your own skill list and report any that is missing; `update-config` and `plugin-authoring` ship with Claude Code.

## Ask the install questions

1. **Dev mode.** Ask: "Do you want to keep the skills, agents, and tools in workspace files, so they are under version control and easier to change?" Explain in one line each: yes keeps the files in the workspace's `AGENTS/` folder (a clone of the plugins, the user's own skills and agents, and the settings folder, all under Git) and puts only links in Claude's folders; no is a normal plugin install that updates from the marketplace. Recommend no for someone who will not change the tools, yes for someone who builds or edits them. Say that yes also turns Git version control on, because dev mode needs it. If `file links` was missing, say that yes needs Windows Developer Mode for agent links.
2. **Workspace.** The setting is kept in a workspace's `AGENTS.md`, in a `## Dev mode` section. For yes: which workspace holds the files (an absolute folder path; suggest the current one). For no: which workspace's `AGENTS.md` records the setting and gets the conventions block. A workspace is required either way, because both settings must be recorded.
3. **Git version control.** With dev mode on it is on, so do not ask; if the user does not want it, dev mode is off. With dev mode off, ask: "Should Git version control be enabled for this workspace: on or off?" Recommend on: changes to the instructions and tools can then be reviewed and undone. On a rerun, recommend the current value.
   - **Multi-repo workspace:** when the workspace root is not a repository but its direct subfolders are (for example a client folder holding several repositories), the user has set up Git: recommend Git version control on and dev mode on, and say that the files at the root (such as `AGENTS.md`) stay local, outside those repositories. `status` reports this layout as `git.layout` `multi-repo`.
4. **Folders**, for dev mode on only. Recommend the defaults: the source folder `AGENTS` (the user's own skills in `AGENTS/skills/`, agents in `AGENTS/agents/`, docs in `AGENTS/docs/`) and the plugins folder `AGENTS/plugins` (a clone of the plugins). A harness folder (`.claude`, `.agents`, `.copilot`) is never the source folder: those folders, global and in the workspace, hold only links.
   - **Main development workspace:** the workspace whose `AGENTS/plugins` holds the clone is the main one, and the global links point to it. Recommend making the workspace being installed the main one with its own clone. When the user wants to keep another workspace as the main one, pass that workspace's clone (the folder above the pointer's `howtoai_root`) as an absolute `--plugins-folder`: nothing is cloned or linked again, and the pointer stays there.
   - **Clone source:** the public repository `https://github.com/GG323/claude-plugin`, or a local development clone the user names (for example, the folder where they build the plugins), cloned with `git clone "<local path>"` so its committed history comes along. Only committed changes are cloned: when that folder has uncommitted changes, say so and ask whether the user commits them first.
   - Moving existing files into a new layout is a separate decision; do not offer to do it here.

## Record the choice

If the workspace has no `AGENTS.md`, say so and offer `skill-audit`'s workspace audit to draft one. Without one, the setting cannot be recorded: stop the install and tell the user it waits for an `AGENTS.md`.

Run `set` with both answers (`--dev-mode` and `--git-version-control`, each on or off) and without `--write`, for example `set --dev-mode on --workspace "<workspace>" --source-folder AGENTS --plugins-folder AGENTS/plugins --git-version-control on`. Show the user its `diff` (the `## Dev mode` entry in `AGENTS.md`), the `previous` setting when there is one, and the `pointer` it writes to `~/.claude/howtoai/install.json` (which workspace holds the entry, and where the plugin is). After their yes, run it again with `--write`.

When the files are not on disk yet (dev mode on with no `howtoai/` in the plugins folder), run `set --write` now and again after the clone, from the clone's own `devmode.py`, so the pointer's `howtoai_root` points at the clone.

With Git version control on, show the user each of the `problems` in `git`, and fix one only after their yes. Show its `notes` too: in a multi-repo workspace they name the root files that stay local, and need no fix.

- **`AGENTS/` not in a repository** (the `skills`, `agents`, or `docs` problem, or a multi-repo `notes` line for them): offer `git init "<workspace>/AGENTS"`, so `AGENTS/` is a repository of its own, and a `.gitignore` in it with the two lines `plugins/` (the clone is its own repository) and `settings/cache/` (generated). Write the `.gitignore` with the file tools after showing it.
- **The workspace itself not in a repository:** offer `git init "<workspace>"` only when the user wants the whole workspace under one repository, never in a multi-repo workspace, where it would nest the user's repositories in a new one.
- Never add, commit, create a remote, or push: the first commit can hold private files, so it is the user's.
- **Ignored:** show which folder, and ask whether to change that `.gitignore` or leave it.
- **Anything else:** show the message and list it under Missing in [Summarize](#summarize).

Dev mode needs working Git version control. With dev mode on, go on to linking only when Git is installed and `git.problems` is empty (a multi-repo workspace counts); if the user declines a fix, offer dev mode off and run `set` again.

## Install or link

Take the route for the user's dev-mode answer.

### Dev mode off

1. Run `claude plugin list` (or `/plugin` in a session). If `howtoai@howtoai-mods` is installed, say so and skip to step 3.
2. Show the user the install commands and run them after their yes: `claude plugin marketplace add GG323/claude-plugin`, then `claude plugin install howtoai@howtoai-mods` (in a session: `/plugin marketplace add GG323/claude-plugin` and `/plugin install howtoai@howtoai-mods`; in the desktop app: **+** next to the prompt box, **Plugins**). Tell the user to run `/reload-plugins` or start a new session afterwards.
3. Run `status`. A `link-ok` entry whose name is one of the seven `howtoai` skills is left from dev mode and makes each skill show twice. List them, and after the user's yes remove each with `unlink --dest "<path>" --write`, which removes only the link.

Skip the Dev mode on section.

### Dev mode on

1. **Get the source.** Run `status` and read `paths.plugins`. If `<paths.plugins>/howtoai/` exists, use it; with `paths.plugins_shared` true it is another workspace's clone, already linked from there, so step 2 normally finds every plugin link as `none`. Otherwise, if the plugins folder is missing or empty, show the user `git clone <clone source> "<paths.plugins>"` (the source from [Ask the install questions](#ask-the-install-questions), item 4) and run it after their yes, then run `set --write` again from the clone (see [Record the choice](#record-the-choice)) and run `check-deps` from it. If the folder exists with other files, stop and ask the user where the clone should go.
2. **Plan the links.** Run each `link` below without `--write`, and show the user one list: what will be created, what already links there (`none`), what links elsewhere (`replace`), and what is refused.
   - **Plugin skills, global:** each folder in `<paths.plugins>/howtoai/skills/`, with `link --source "<path>"`, plus `--harness agents` or `--harness copilot` for `~/.agents` or `~/.copilot` when those folders exist.
   - **The workspace's own skills and agents:** each skill folder in `paths.skills` and each agent file in `paths.agents`, linked into this workspace only, with `link --source "<path>" --into workspace --workspace "<workspace>"` (and `--harness agents` or `copilot` when the workspace has those folders). Link one globally as well only when the user wants it in every workspace.
   - A source inside a harness folder is refused: harness folders hold only links. Offer to move such a skill into `AGENTS/skills/` first, after the user's yes.
3. **Refusals.** A real folder or file in the way is never replaced: name it, and say the user can move it aside (for example, into the source folder or a backup folder) and rerun this step. A link to somewhere else is replaced only when the user says so, with `--replace-link`; when this workspace becomes the main development workspace, its links replace the ones that point to the old main workspace's clone.
4. **Create.** After the user's yes, run each planned `link` with `--write`. A Developer Mode error stops the agent links only: report it with its fix and go on.
5. **Duplicates.** A marketplace copy beside the links is found and fixed in [Run the audit](#run-the-audit).

## Allow the weekly audit

Only when the user has, or wants, the weekly `skill-audit` scheduled task: nobody is present in that run, so without an allow rule in `~/.claude/settings.json` it stalls on a permission prompt. Otherwise skip this section.

1. Read `permissions.allow` in `~/.claude/settings.json`. The rule is `Skill(skill-audit)` with dev mode on and `Skill(howtoai:skill-audit)` with dev mode off, because a plugin's skills carry the plugin's name. When it is there, go on.
2. Show the user the exact edit, with the file's path and the line:
   - **`Skill(environment-audit)` is there** (the skill's former name): replace it with the rule.
   - **An allow list without either:** add the rule as one more entry.
   - **No file, or no allow list:** merge in `{"permissions": {"allow": ["<rule>"]}}`, keeping everything else.
3. The user makes the edit, because permission rules are theirs: never write it yourself or through another skill. When they say it is done, read the file again and confirm that it is valid JSON with the rule in it. When they leave it, put it under Missing in [Summarize](#summarize).

## Run the audit

[AUDIT.md](AUDIT.md) holds everything this install must leave true, so it is checked the same way here and in every later audit.

1. Run `py -3 -I -B "<howtoai root>/skills/skill-audit/scripts/check_plugins.py" --audit "<howtoai root>/AUDIT.md" --workspace "<workspace>"`.
2. For each `fail`, show the check's fix and any `text` as a preview, and apply it after the user's yes. For each `needs-approval`, show the command, run it after the user's yes, and judge it by its `pass_when`. Judge a `review` from its listed files. An `invalid` is a broken check: report it, never count it as passed.
3. Run it again until the only failures are the ones the user declined. Those go under Missing in [Summarize](#summarize).

## Summarize

End with one short chat message in this shape, with "none" for an empty line:

```text
howtoai install
- Git version control: on, working (or: on, with <problems>; or: off)
- Dev mode: on, source folder `<source>`, plugins `<plugins>` (or: off, marketplace install)
- Links: <n> created, <n> already fine, <n> refused (<names>)
- AGENTS.md: <what changed in which workspace>
- Settings: allow rule for the weekly audit in place (or: not needed; or: waits for the user's edit)
- Missing: <dependencies or steps still open, with their fix>
```

When something stays open, end with the one step the user should take next.
