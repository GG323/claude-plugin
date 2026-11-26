# Dev mode

## Contents

- [What dev mode is](#what-dev-mode-is)
- [The setting](#the-setting)
  - [The settings key](#the-settings-key)
  - [The pointer](#the-pointer)
- [Source folder layout](#source-folder-layout)
- [The script](#the-script)
  - [status](#status)
  - [set](#set)
  - [link](#link)
  - [unlink](#unlink)
  - [check-deps](#check-deps)
  - [agents-md](#agents-md)
- [Who uses it](#who-uses-it)
- [Tests](#tests)

## What dev mode is

Dev mode is one install choice for the `howtoai` plugin and the plugins built on it. The question to the user is: "Do you want to keep the skills, agents, and tools in workspace files, so they are under version control and easier to change?"

- **On:** the main files live in a workspace the user picks. The global folders, like each workspace's `.claude`, `.agents`, and `.copilot` folders, hold only links: `~/.claude/skills/<skill>` is a directory junction (Windows) or symbolic link, and `~/.claude/agents/<agent>.md` is a symbolic link. Editing the workspace file changes the installed tool at once. The files must be under Git.
- **Off:** a normal plugin install from the `howtoai-mods` marketplace; nothing is linked.

This file is the contract: [INSTALL.md](../INSTALL.md), `skill-builder`, and the `howtoai-dev` plugin's install build against the names below.

## The setting

### The settings key

The setting lives in the workspace's shared settings file, `AGENTS/settings.json`, under the `howtoai` key. The file holds one top-level key per tool (`howtoai-dev` for that plugin), and every tool keeps the other keys as they are. `devmode.py set` writes the key after the user's yes, and `devmode.py status` reads it; other tools read it only through `status`, and audits check only that the key is there and whether `dev_mode` is true.

```json
{
 "howtoai": {"dev_mode": true},
 "howtoai-dev": {"...": "..."}
}
```

- `dev_mode` is required and is `true` or `false`. A missing key, a missing file, or any other value is an error: the setting has to be made, so no tool assumes on or off.
- `source_folder` and `plugins_folder` are optional folders relative to the workspace, with forward slashes. Defaults: `AGENTS` and `<source folder>/plugins`. `set` writes a folder into the key only when it differs from its default.
- `plugins_folder` may instead be the absolute path of an existing `howtoai-mods` clone (a folder with `.claude-plugin/marketplace.json` and `howtoai/`), for a second workspace that shares the clone another workspace owns. Nothing is cloned or linked again, and the pointer stays on the owning workspace (see [The pointer](#the-pointer)).
- A harness folder (`.claude`, `.agents`, or `.copilot`) is never the source folder: harness folders, global and in a workspace, hold only links to files in an `AGENTS/` folder.
- Git is not a setting. With dev mode on, the files must be under Git before anything is linked: `status` reports that in `git`, and the install fixes what it names. The workspace's `AGENTS.md` has no dev-mode entry; it lists the `howtoai` plugin in its `## Installed skills` section, a line the plugin's `AUDIT.md` installs.

A workspace without the key has no setting, which is an error, not dev mode off: ask the user, then record the answer with `set`.

### The pointer

`~/.claude/howtoai/install.json` is a user-level pointer, not the setting. `set --write` writes it, so tools running in any workspace can find the setting and the script. With dev mode off, or with dev mode on and a plugins folder outside the workspace (a shared clone), `set` keeps the workspace an existing pointer names while that workspace still holds a valid setting:

| Key | Type | Meaning |
| --- | --- | --- |
| `workspace` | absolute path | The workspace whose `AGENTS/settings.json` holds the setting. |
| `howtoai_root` | absolute path | The `howtoai` plugin folder `devmode.py` ran from, so callers find the script without a `../..` path, which breaks through a junction. |
| `updated` | `YYYY-MM-DD` | The date of the last write. |

No pointer means the setting has not been made: callers that need it ask the user and record it with `set`; they never treat it as dev mode off.

## Source folder layout

The default layout, inside the workspace:

| Path | Holds |
| --- | --- |
| `AGENTS/skills/<skill>/` | The user's own skills, one folder each with its `SKILL.md`. |
| `AGENTS/agents/<agent>.md` | The user's own subagents. |
| `AGENTS/docs/` | Notes and references for those tools. |
| `AGENTS/plugins/` | A clone of the `howtoai-mods` marketplace (`.claude-plugin/marketplace.json`, `howtoai/`, `howtoai-dev/`), unless the setting's `plugins_folder` points elsewhere; each plugin keeps its own `skills/` and `agents/`. |
| `AGENTS/settings.json`, `AGENTS/install.md`, `AGENTS/lessons.md`, `AGENTS/workbooks/`, `AGENTS/deploy-targets.json` | Files the user reviews: the shared settings (one top-level key per tool; `howtoai-dev` for that plugin), its install record, lessons log, project workbooks, and deploy targets |
| `AGENTS/state/` | Run records the tools write for themselves (deploy approvals, deploy log, generated `cache/`), left out of Git. |

- **One home.** The workspace that the pointer names is the main development workspace: its `AGENTS/` holds the plugins' clone and the skills and agents the user wants in every workspace, and the global `~/.claude` (and `~/.agents` or `~/.copilot`, when those exist) links to them. Another workspace shares that clone through an absolute `plugins_folder`.
- **Workspace-only tools.** A skill or agent that belongs to one workspace lives in that workspace's `AGENTS/skills/` or `AGENTS/agents/` and is linked only into its own `.claude` (and `.agents` or `.copilot` when it uses them) with `link --into workspace`.
- **Git.** `AGENTS/` is under Git: covered by the workspace's repository, or, when no repository covers it, its own (`git init AGENTS`, run only after the user's yes, with no commit). Its `.gitignore` leaves out `state/` (run records and caches), and `plugins/` only when the plugins folder is a git clone of its own.

Folders are created when the first file goes into them, never empty in advance. Callers never build these paths themselves: [status](#status) prints them resolved.

A workspace can keep an existing layout instead. The HowToAI workspace's setting has the source folder `Agents` and the plugins folder `PLUGIN/claude-plugin` (the `howtoai-mods` clone), so new personal skills stay out of the public plugin repository. Moving existing files into the default layout is a separate decision for the user; no command here moves files.

## The script

`scripts/devmode.py` is standard-library Python. Run it as `py -3 -I -B "<howtoai_root>/scripts/devmode.py" [--claude-dir <dir>] <command> [options]` (`python3 -I -B` outside Windows). `--claude-dir` replaces `~/.claude` and exists for tests.

Every command prints one JSON object. Exit codes: `0` done or previewed, `1` refused or failed (the JSON has `ok: false` and an `error` that says what to do), `2` bad arguments. Every command that writes previews by default and writes only with `--write`.

### status

`status [--workspace <path>]` reads only. The workspace is the one given, else the pointer's. It returns:

- `workspace`, `settings_file`, `settings_file_exists`, and `setting`: the parsed key (`dev_mode`, `source_folder`, `plugins_folder`, with the defaults filled in), or `null` when the setting is missing or invalid.
- `dev_mode`: `true` or `false` from a valid setting, otherwise `null`. Never read `null` as off.
- `needs_setting`, only on an error: a list of `setting` and `problem`, with `ok: false`, an `error` that gives the fix, and exit 1. The other keys, `links` included, are still returned.
- `git`: `null` when the setting is not valid. Otherwise `ok`, `required` (true with dev mode on, which needs `ok` before linking), `problems` (sentences to show the user), `notes`, `repos` (the repository holding each checked path), `layout`, and `nested_repos`. It checks that Git is installed and that `AGENTS/settings.json`, and with dev mode on the `skills`, `agents`, `docs`, and `plugins` folders, are each in a repository that does not ignore them. A folder with its own repository counts. It does not check that files are committed.
  - `layout` is `multi-repo` when no repository covers the workspace root but its direct subfolders hold repositories (`nested_repos`, each with its own `.git`), for example a client folder holding several repositories. The user has set up Git there, so a checked path at the root that no repository covers is a `notes` line ("stays local"), not a problem. Otherwise `layout` is `single-repo` and such a path is a problem, as before.
- `pointer_path`, `pointer` (or `null`), and `howtoai_root`.
- `paths`: the resolved absolute `workspace`, `source`, `skills`, `agents`, `docs`, and `plugins` folders (or `null` without a setting), and `exists` for each; and `plugins_shared` (the plugins folder is outside the workspace).
- `links`: one item per entry in `~/.claude/skills/` and `~/.claude/agents/*.md` (names starting with `.` are skipped), with `name`, `kind` (`skill` or `agent`), `path`, and `state`:
  - `link-ok`: a link whose target exists, with `link` (`junction` or `symlink`), `target`, and `in_workspace` (when there is a setting).
  - `link-broken`: a link whose target is gone.
  - `real`: a real folder or file, not a link (a skill folder without `SKILL.md` gets a `note`).
- `counts`: the number of links per state.

### set

`set --dev-mode on|off --workspace <path> [--source-folder <f>] [--plugins-folder <f>] [--write]`

Builds the `howtoai` key and the pointer, and returns `settings_file`, `key`, `setting`, the `previous` setting, `changed`, a unified `diff` of `AGENTS/settings.json`, `pointer`, `pointer_changed`, `git` (as in [status](#status)), and the resolved `paths` with `exists`. The workspace must exist (exit 2); the settings file is created when missing, and a file that is not a JSON object is refused (exit 1), because writing it would lose other tools' settings. Folder options are relative to the workspace and may not contain `..` (exit 2), except that `--plugins-folder` may be the absolute path of an existing `howtoai-mods` clone (anything else absolute is exit 2); an option left out keeps the current value, and the folders otherwise get their defaults. `set` repairs an invalid key, keeping its folders. It never runs `git init`, `add`, or `commit`. With `--write`, it writes what changed (the whole file at once, every other key kept) and returns `written: true`.

### link

`link --source <skill folder or agent .md file> [--into global|workspace] [--workspace <path>] [--harness claude|agents|copilot] [--replace-link] [--write]`

Links one skill folder (it must hold `SKILL.md`) to `<root>/skills/<folder name>` or one agent file to `<root>/agents/<file name>`. `<root>` is `~/.claude` by default (`--into global`), `~/.agents` or `~/.copilot` with `--harness`, or the workspace's `.claude`, `.agents`, or `.copilot` with `--into workspace --workspace <path>`, for a tool that belongs to that workspace only; the setting is then read from that workspace. It returns `kind`, `source`, `dest`, `into`, `harness`, `link` (the link type), `in_source` (whether the source is inside the setting's source or plugins folder, when there is a setting), and `action`:

- `create`: nothing is at the destination.
- `none`: the destination already links to this source.
- `replace`: the destination is a link to somewhere else; allowed only with `--replace-link`, and the old target is not touched.

It refuses without a valid setting (exit 1 with `needs_setting`), and refuses a source inside a harness folder (`<...>/.claude/skills/<name>`, `.claude/agents/<name>.md`, or the same under `.agents` or `.copilot`; exit 1 with `in_harness_folder: true`), because harness folders hold only links and the files live in an `AGENTS/` folder. It never replaces a real folder or file at the destination (exit 1). On Windows a skill folder gets a directory junction, which needs no special rights, and an agent file a symbolic link; when Windows refuses the symbolic link, the error says to turn on Developer Mode or run as administrator. On macOS and Linux both are symbolic links.

### unlink

`unlink --dest <path> [--write]`

Removes one link directly in a harness folder's `skills/` or `agents/`: `~/.claude/skills/`, `~/.claude/agents/`, or a workspace's or the home folder's `.claude`, `.agents`, or `.copilot`; for example when dev mode is turned off. It returns `target` and `action` (`remove`, or `none` when nothing is there). It removes only the link, never its target, and refuses a real folder or file or any other path (exit 1).

### check-deps

`check-deps` reads only. It returns `deps_ok` (no required item missing) and `items`, each with `name`, `kind`, `need` (`required`, `optional`, or `required for dev mode`), `status` (`ok`, `missing`, or `unknown`), `detail`, and `fix`:

- Python 3.10 or later; `git`; `uv` or the `chromadb` package (for `skill-finder` search); whether this computer can make file links.
- The seven `howtoai` skills: `skill-builder`, `skill-finder`, `skill-audit`, `skill-design`, `brain-dump`, `grilling`, `handover`.
- Harness skills the plugin uses (`update-config`, `plugin-authoring`, `artifact-design`, `docx`, `pptx`, `schedule`), always `unknown`: a script cannot see them, so the installing agent checks its own skill list.

### agents-md

`agents-md --workspace <path> [--replace-baseline] [--write]`

Adds the baseline block, `## Markdown conventions`, to the workspace's `AGENTS.md` before `## Installed skills` (else at the end), with its `Contents` entries. The block is read by heading from `skill-audit`'s `references/markdown-conventions.md`, its one maintained copy. It returns the block's `state` (`missing`, `matches`, or `differs`), its `action` (`insert`, `replace`, `none`, or `kept`), and a unified `diff`. When the workspace's block differs, it is `kept` with that block's own `diff`, because the user chooses which copy wins (as `skill-audit`'s check W1 does); `--replace-baseline` takes the reference. It needs an existing `AGENTS.md` (exit 1).

## Who uses it

- [INSTALL.md](../INSTALL.md) runs `status`, `check-deps`, `set`, `link` or `unlink`, and `agents-md`, showing each preview before a write.
- `skill-builder` places a new skill or agent in the current workspace's `AGENTS/skills/` or `AGENTS/agents/` by default, linked into that workspace's `.claude` with `link --into workspace`. Only when the user asks for one in every workspace does it go in the main development workspace's `paths.skills` or `paths.agents`, linked globally with `link`. It reads the setting in Plan and Build, and asks the user to make it when it is missing.
- The `howtoai-dev` plugin's install reads the setting only through `status --workspace <path>`, links its own skills and agents under `paths.plugins` with `link` (with `--replace-link` when the user agrees), runs `set` when the workspace has no setting or dev mode is turned off, and removes its links with `unlink` when dev mode is turned off.

## Tests

[evals/test_devmode.py](../evals/test_devmode.py) covers every command in temporary folders only (a temporary `--claude-dir` and workspace). Run: `py -3 -I -B -m unittest discover -s "<howtoai_root>/evals" -v`.
