# Dev mode

## Contents

- [What dev mode is](#what-dev-mode-is)
- [The setting](#the-setting)
  - [The AGENTS.md entry](#the-agentsmd-entry)
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

- **On:** the main files live in a workspace the user picks. The global folders, like each workspace's `.claude`, `.agents`, and `.copilot` folders, hold only links: `~/.claude/skills/<skill>` is a directory junction (Windows) or symbolic link, and `~/.claude/agents/<agent>.md` is a symbolic link. Editing the workspace file changes the installed tool at once. Dev mode needs Git version control on.
- **Off:** a normal plugin install from the `howtoai-mods` marketplace; nothing is linked.

This file is the contract: [INSTALL.md](../INSTALL.md), `skill-builder`, and the `howtoai-dev` plugin's install build against the names below.

## The setting

### The AGENTS.md entry

The setting lives in the workspace's `AGENTS.md`, in a `## Dev mode` section: the entry. It is the source of truth, under version control with the workspace. `devmode.py set` writes it after the user's yes, and `devmode.py status` reads it; no other tool parses it. Its shape is fixed:

```markdown
## Dev mode

Dev mode is on: the installed and created skills, agents, and tools are kept in this workspace's files, under version control, and the global folders `~/.claude/skills/` and `~/.claude/agents/`, like this workspace's `.claude`, `.agents`, and `.copilot` folders, hold only links to them (a directory junction or symbolic link per skill, a symbolic link per agent). Git version control should be enabled.

- **Git version control:** on
- **Dev mode:** on
- **Source folder:** [Agents/](Agents/)
- **Plugins folder:** [PLUGIN/claude-plugin/](PLUGIN/claude-plugin/)
```

- The section goes after `## Workspace layout` (else before `## Markdown conventions` or `## Installed skills`), with a `- [Dev mode](#dev-mode)` entry in `Contents`.
- Labelled lines are `- **<Label>:** <value>`, each on one line. **Git version control** (first) and **Dev mode** are both required and each is `on` or `off`. A missing line, a missing section, or any other value is an error: the setting has to be made, so no tool assumes on or off. **Dev mode** on needs **Git version control** on; with dev mode off, Git version control can be either.
- **Source folder** and **Plugins folder** are folders relative to the workspace, written as a relative link (`[Agents/](Agents/)`, or `[My tools/](<My tools/>)` with spaces). The parser also accepts a code span (`` `Agents/` ``). Defaults when a line is missing: `AGENTS` and `<source folder>/plugins`. With dev mode off, `set` writes only the **Git version control** and **Dev mode** lines.
- **Plugins folder** may instead be the absolute path of an existing `howtoai-mods` clone (a folder with `.claude-plugin/marketplace.json` and `howtoai/`), for a second workspace that shares the clone another workspace owns. Nothing is cloned or linked again, and the pointer stays on the owning workspace (see [The pointer](#the-pointer)).
- A harness folder (`.claude`, `.agents`, or `.copilot`) is never the **Source folder**: harness folders, global and in a workspace, hold only links to files in an `AGENTS/` folder.
- The paragraph above is the default description with dev mode on. With it off, the default is: "Dev mode is off: the installed skills, agents, and tools come from normal plugin installs, and created ones are saved in this workspace's `AGENTS/` folder, with links in its `.claude`, `.agents`, and `.copilot` folders. Git version control should be enabled." With Git version control off, which only dev mode off allows, it drops the last sentence. The description stays plain: how the script works is documented here, not in `AGENTS.md`.
- `set` restores the default description on every run and shows the change in its `diff`, so a new default is changed in `scripts/devmode.py`, here, and in the tests. Edit the labelled lines by rerunning `set`.

A workspace with no entry has no setting, which is an error, not dev mode off: ask the user, then record the answer with `set`.

### The pointer

`~/.claude/howtoai/install.json` is a user-level pointer, not the setting. `set --write` writes it, so tools running in any workspace can find the entry and the script. With dev mode off, or with dev mode on and a plugins folder outside the workspace (a shared clone), `set` keeps the workspace an existing pointer names while that workspace still holds a valid setting:

| Key | Type | Meaning |
| --- | --- | --- |
| `workspace` | absolute path | The workspace whose `AGENTS.md` holds the entry. |
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
| `AGENTS/plugins/` | A clone of the `howtoai-mods` marketplace (`.claude-plugin/marketplace.json`, `howtoai/`, `howtoai-dev/`), unless the entry's **Plugins folder** points elsewhere; each plugin keeps its own `skills/` and `agents/`. |
| `AGENTS/howtoai/` | The howtoai state folder: `dev/` (settings, install record, reply log, lessons), `workbooks/`, `deploy/`, and the generated `cache/`. |

- **One home.** The workspace that the pointer names is the main development workspace: its `AGENTS/` holds the plugins' clone and the skills and agents the user wants in every workspace, and the global `~/.claude` (and `~/.agents` or `~/.copilot`, when those exist) links to them. Another workspace shares that clone through an absolute **Plugins folder**.
- **Workspace-only tools.** A skill or agent that belongs to one workspace lives in that workspace's `AGENTS/skills/` or `AGENTS/agents/` and is linked only into its own `.claude` (and `.agents` or `.copilot` when it uses them) with `link --into workspace`.
- **Git.** `AGENTS/` is under Git: covered by the workspace's repository, or, when no repository covers it, its own (`git init AGENTS`, run only after the user's yes, with no commit). Its `.gitignore` leaves out `plugins/` (a repository of its own) and `howtoai/cache/` (generated).

Folders are created when the first file goes into them, never empty in advance. Callers never build these paths themselves: [status](#status) prints them resolved.

A workspace can keep an existing layout instead. The HowToAI workspace's entry has the source folder `Agents/` and the plugins folder `PLUGIN/claude-plugin/` (the `howtoai-mods` clone), so new personal skills stay out of the public plugin repository. Moving existing files into the default layout is a separate decision for the user; no command here moves files.

## The script

`scripts/devmode.py` is standard-library Python. Run it as `py -3 -I -B "<howtoai_root>/scripts/devmode.py" [--claude-dir <dir>] <command> [options]` (`python3 -I -B` outside Windows). `--claude-dir` replaces `~/.claude` and exists for tests.

Every command prints one JSON object. Exit codes: `0` done or previewed, `1` refused or failed (the JSON has `ok: false` and an `error` that says what to do), `2` bad arguments. Every command that writes previews by default and writes only with `--write`.

### status

`status [--workspace <path>]` reads only. The workspace is the one given, else the pointer's. It returns:

- `workspace`, `agents_md`, `agents_md_exists`, and `setting`: the parsed entry (`git_version_control`, `dev_mode`, `source_folder`, `plugins_folder`, and `line`, its heading's line number), or `null` when the setting is missing or invalid.
- `dev_mode`: `true` or `false` from a valid setting, otherwise `null`. Never read `null` as off.
- `needs_setting`, only on an error: a list of `setting` and `problem`, with `ok: false`, an `error` that gives the fix, and exit 1. The other keys, `links` included, are still returned.
- `git`: `null` when the setting is not valid or Git version control is off. Otherwise `ok`, `problems` (sentences to show the user), `notes`, `repos` (the repository holding each checked path), `layout`, and `nested_repos`. It checks that Git is installed and that `AGENTS.md`, and with dev mode on the `skills`, `agents`, `docs`, and `plugins` folders, are each in a repository that does not ignore them. A folder with its own repository counts. It does not check that files are committed.
  - `layout` is `multi-repo` when no repository covers the workspace root but its direct subfolders hold repositories (`nested_repos`, each with its own `.git`), for example a client folder holding several repositories. The user has set up Git there, so a checked path at the root that no repository covers is a `notes` line ("stays local"), not a problem. Otherwise `layout` is `single-repo` and such a path is a problem, as before.
- `pointer_path`, `pointer` (or `null`), and `howtoai_root`.
- `paths`: the resolved absolute `workspace`, `source`, `skills`, `agents`, `docs`, and `plugins` folders (or `null` without an entry), and `exists` for each; and `plugins_shared` (the plugins folder is outside the workspace).
- `links`: one item per entry in `~/.claude/skills/` and `~/.claude/agents/*.md` (names starting with `.` are skipped), with `name`, `kind` (`skill` or `agent`), `path`, and `state`:
  - `link-ok`: a link whose target exists, with `link` (`junction` or `symlink`), `target`, and `in_workspace` (when there is an entry).
  - `link-broken`: a link whose target is gone.
  - `real`: a real folder or file, not a link (a skill folder without `SKILL.md` gets a `note`).
- `counts`: the number of links per state.

### set

`set --dev-mode on|off --workspace <path> [--source-folder <f>] [--plugins-folder <f>] [--git-version-control on|off] [--write]`

Builds the entry and the pointer, and returns `setting`, the `previous` setting, `entry_action` (`insert`, `replace`, or `none`), `changed`, a unified `diff` of `AGENTS.md`, `pointer`, `pointer_changed`, `git` (as in [status](#status)), and the resolved `paths` with `exists`. The workspace must exist (exit 2) and have an `AGENTS.md` (exit 1). Folder options are relative to the workspace and may not contain `..` (exit 2), except that `--plugins-folder` may be the absolute path of an existing `howtoai-mods` clone (anything else absolute is exit 2); an option left out keeps the entry's current value, and the folders otherwise get their defaults. `--git-version-control` has no default: without a current value it is required. A result with dev mode on and Git version control off is refused, never corrected silently (exit 1 with `needs_setting`). `set` repairs a broken entry when both values are given, keeping its folders. It records Git version control and never runs `git init`, `add`, or `commit`. With `--write`, it writes what changed and returns `written: true`. Line endings in `AGENTS.md` are kept.

### link

`link --source <skill folder or agent .md file> [--into global|workspace] [--workspace <path>] [--harness claude|agents|copilot] [--replace-link] [--write]`

Links one skill folder (it must hold `SKILL.md`) to `<root>/skills/<folder name>` or one agent file to `<root>/agents/<file name>`. `<root>` is `~/.claude` by default (`--into global`), `~/.agents` or `~/.copilot` with `--harness`, or the workspace's `.claude`, `.agents`, or `.copilot` with `--into workspace --workspace <path>`, for a tool that belongs to that workspace only; the setting is then read from that workspace. It returns `kind`, `source`, `dest`, `into`, `harness`, `link` (the link type), `in_source` (whether the source is inside the entry's source or plugins folder, when there is an entry), and `action`:

- `create`: nothing is at the destination.
- `none`: the destination already links to this source.
- `replace`: the destination is a link to somewhere else; allowed only with `--replace-link`, and the old target is not touched.

It refuses without a valid setting (exit 1 with `needs_setting`), and refuses a source inside a harness folder (`<...>/.claude/skills/<name>`, `.claude/agents/<name>.md`, or the same under `.agents` or `.copilot`; exit 1 with `in_harness_folder: true`), because harness folders hold only links and the files live in an `AGENTS/` folder. It never replaces a real folder or file at the destination (exit 1). On Windows a skill folder gets a directory junction, which needs no special rights, and an agent file a symbolic link; when Windows refuses the symbolic link, the error says to turn on Developer Mode or run as administrator. On macOS and Linux both are symbolic links.

### unlink

`unlink --dest <path> [--write]`

Removes one link directly in a harness folder's `skills/` or `agents/`: `~/.claude/skills/`, `~/.claude/agents/`, or a workspace's or the home folder's `.claude`, `.agents`, or `.copilot`; for example when dev mode is turned off. It returns `target` and `action` (`remove`, or `none` when nothing is there). It removes only the link, never its target, and refuses a real folder or file or any other path (exit 1).

### check-deps

`check-deps` reads only. It returns `deps_ok` (no required item missing) and `items`, each with `name`, `kind`, `need` (`required`, `optional`, `required for dev mode`, or `required for Git version control and dev mode`), `status` (`ok`, `missing`, or `unknown`), `detail`, and `fix`:

- Python 3.10 or later; `git`; `uv` or the `chromadb` package (for `skill-finder` search); whether this computer can make file links.
- The seven `howtoai` skills: `skill-builder`, `skill-finder`, `skill-audit`, `skill-design`, `brain-dump`, `grilling`, `handover`.
- Harness skills the plugin uses (`update-config`, `plugin-authoring`, `artifact-design`, `docx`, `pptx`, `schedule`), always `unknown`: a script cannot see them, so the installing agent checks its own skill list.

### agents-md

`agents-md --workspace <path> [--replace-baseline] [--write]`

Adds the baseline block, `## Markdown conventions`, to the workspace's `AGENTS.md` before `## Installed skills` (else at the end), with its `Contents` entries. The block is read by heading from `skill-audit`'s `references/markdown-conventions.md`, its one maintained copy. It returns the block's `state` (`missing`, `matches`, or `differs`), its `action` (`insert`, `replace`, `none`, or `kept`), and a unified `diff`. When the workspace's block differs, it is `kept` with that block's own `diff`, because the user chooses which copy wins (as `skill-audit`'s check W1 does); `--replace-baseline` takes the reference. It needs an existing `AGENTS.md` (exit 1).

## Who uses it

- [INSTALL.md](../INSTALL.md) runs `status`, `check-deps`, `set`, `link` or `unlink`, and `agents-md`, showing each preview before a write.
- `skill-builder` places a new skill or agent in the current workspace's `AGENTS/skills/` or `AGENTS/agents/` by default, linked into that workspace's `.claude` with `link --into workspace`. Only when the user asks for one in every workspace does it go in the main development workspace's `paths.skills` or `paths.agents`, linked globally with `link`. It reads the setting in Plan and Build, and asks the user to make it when it is missing.
- The `howtoai-dev` plugin's install reads the setting only through `status --workspace <path>`, links its own skills and agents under `paths.plugins` with `link` (with `--replace-link` when the user agrees), runs `set` when the workspace has no entry or dev mode is turned off, and removes its links with `unlink` when dev mode is turned off.

## Tests

[evals/test_devmode.py](../evals/test_devmode.py) covers every command in temporary folders only (a temporary `--claude-dir` and workspace). Run: `py -3 -I -B -m unittest discover -s "<howtoai_root>/evals" -v`.
