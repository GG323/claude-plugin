# Install howtoai

## Contents

- [Before you start](#before-you-start)
- [Check dependencies](#check-dependencies)
- [Ask the install questions](#ask-the-install-questions)
- [Record the choice](#record-the-choice)
- [Install or link](#install-or-link)
  - [Dev mode off](#dev-mode-off)
  - [Dev mode on](#dev-mode-on)
- [Update AGENTS.md](#update-agentsmd)
- [Summarize](#summarize)
- [Skills and agents](#skills-and-agents)

## Before you start

These are instructions for the agent installing the `howtoai` plugin (`skill-builder`, `skill-finder`, `environment-audit`, `skill-design`, `brain-dump`, and `grilling`). Follow them top to bottom. They are safe to run again: each step checks what is already set up and changes only what differs.

- **Ask, never assume.** Every install decision is the user's. Word each question for the user's technical level (the `# User settings (command-pane)` block in the system prompt, when there is one), one short message at a time, with your recommendation.
- **Preview, then write.** Every write to `~/.claude/` or to an `AGENTS.md` is shown first (the script's preview without `--write`), and runs only after the user's yes. Never move, delete, or overwrite the user's files; the script refuses to replace a real folder or file, and you do not work around it.
- **The script.** `devmode.py` does every check and write; its contract is [docs/dev-mode.md](docs/dev-mode.md). Call the folder holding this file `<howtoai>`, and run the script as `py -3 -I -B "<howtoai>/scripts/devmode.py" <command>` (`python3 -I -B` outside Windows). Each command prints JSON; read `ok` and `error`.
- **No local copy yet.** If you read this file from the web and have no copy on disk, check Python (`py -3 --version`) and git (`git --version`) by hand now, and run `check-deps` once [Install or link](#install-or-link) has put the files on disk.

Run `status` first (with `--workspace "<path>"` when the user names a workspace). When it shows a `setting`, this is a rerun: tell the user the current setting (dev mode, workspace, folders) and the link counts, and ask whether to keep it or change it. Keeping it still runs every section below, which repairs what is missing.

## Check dependencies

Run `check-deps` and show the user each item that is `missing`, with its `fix`:

- A missing `required` item stops the install until it is fixed; offer to run its fix command, and run it only after the user's yes.
- A missing `optional` item is reported and the install goes on (for example, without `uv` or `chromadb`, `skill-finder` cannot search).
- `file links` is needed only for dev mode; carry it into the dev-mode question.
- For each `unknown` harness skill, look in your own skill list and report any that is missing; `update-config` and `plugin-authoring` ship with Claude Code.

## Ask the install questions

1. **Dev mode.** Ask: "Do you want to keep the skills, agents, and tools in workspace files, so they are under version control and easier to change?" Explain in one line each: yes keeps the files in a workspace and links them into Claude's global folders; no is a normal plugin install that updates from the marketplace. Recommend no for someone who will not change the tools, yes for someone who builds or edits them. If `file links` was missing, say that yes needs Windows Developer Mode for agent links.
2. **Workspace.** The setting is kept in a workspace's `AGENTS.md`, in a `## Dev mode` section. For yes: which workspace holds the files (an absolute folder path; suggest the current one). For no: which workspace's `AGENTS.md` should record the setting and get the conventions block, or none.
3. **Folders**, for yes only. The source folder for the user's own skills, agents, and docs (default `AGENTS`, relative to the workspace), and the plugins folder for plugin sources (default `AGENTS/plugins`). When the workspace already holds a clone of the `howtoai-mods` marketplace (a folder with `.claude-plugin/marketplace.json` and a `howtoai/` folder), recommend it as the plugins folder, so nothing moves. Moving existing files into a new layout is a separate decision; do not offer to do it here.

## Record the choice

Skip this section when the user chose dev mode off and no workspace: nothing is recorded, and no entry means off.

If the workspace has no `AGENTS.md`, say so and offer `environment-audit`'s workspace audit to draft one. Without one, the setting cannot be recorded: stop the install and tell the user it waits for an `AGENTS.md`.

Run `set` with the answers and without `--write`, for example `set --dev-mode on --workspace "<workspace>" --source-folder AGENTS --plugins-folder AGENTS/plugins`. Show the user its `diff` (the `## Dev mode` entry in `AGENTS.md`), the `previous` setting when there is one, and the `pointer` it writes to `~/.claude/howtoai/install.json` (which workspace holds the entry, and where the plugin is). After their yes, run it again with `--write`.

When the files are not on disk yet (dev mode on with no `howtoai/` in the plugins folder), run `set --write` now and again after the clone, from the clone's own `devmode.py`, so the pointer's `howtoai_root` points at the clone.

## Install or link

Take the route for the user's dev-mode answer.

### Dev mode off

1. Run `claude plugin list` (or `/plugin` in a session). If `howtoai@howtoai-mods` is installed, say so and skip to step 3.
2. Show the user the install commands and run them after their yes: `claude plugin marketplace add GG323/claude-plugin`, then `claude plugin install howtoai@howtoai-mods` (in a session: `/plugin marketplace add GG323/claude-plugin` and `/plugin install howtoai@howtoai-mods`; in the desktop app: **+** next to the prompt box, **Plugins**). Tell the user to run `/reload-plugins` or start a new session afterwards.
3. Run `status`. A `link-ok` entry whose name is one of the six `howtoai` skills is left from dev mode and makes each skill show twice. List them, and after the user's yes remove each with `unlink --dest "<path>" --write`, which removes only the link.

Skip the Dev mode on section.

### Dev mode on

1. **Get the source.** Run `status` and read `paths.plugins`. If `<paths.plugins>/howtoai/` exists, use it. Otherwise, if the plugins folder is missing or empty, show the user `git clone https://github.com/GG323/claude-plugin "<paths.plugins>"` and run it after their yes, then run `set --write` again from the clone (see [Record the choice](#record-the-choice)) and run `check-deps` from it. If the folder exists with other files, stop and ask the user where the clone should go.
2. **Plan the links.** The links to make are each folder in `<paths.plugins>/howtoai/skills/`, plus each skill folder in `paths.skills` and each agent file in `paths.agents` that `status` does not show as `link-ok`. Run `link --source "<path>"` for each, without `--write`, and show the user one list: what will be created, what is already linked (`none`), and what is refused.
3. **Refusals.** A real folder or file in the way is never replaced: name it, and say the user can move it aside (for example, into the source folder or a backup folder) and rerun this step. A link to somewhere else is replaced only when the user says so, with `--replace-link`.
4. **Create.** After the user's yes, run each planned `link` with `--write`. A Developer Mode error stops the agent links only: report it with its fix and go on.
5. **Duplicates.** Run `claude plugin list`. If `howtoai@howtoai-mods` is also installed from the marketplace, every skill shows twice; ask whether to uninstall it (`claude plugin uninstall howtoai@howtoai-mods`), and run it only after the user's yes.

## Update AGENTS.md

Skip this section when the user chose no workspace. The `## Dev mode` entry is already written by [Record the choice](#record-the-choice); this section adds the baseline block.

1. Run `agents-md --workspace "<workspace>"` and show the user its `diff`: the `## Markdown conventions` block, with its `Contents` entries, or nothing when it already matches.
2. When the conventions block is `kept` because it `differs`, show that block's own `diff` side by side and ask which copy wins. For the reference (`environment-audit`'s copy), add `--replace-baseline` in step 3. For the workspace's copy, leave it, and offer to update the reference through `environment-audit` (its check W1), because the reference is the one maintained copy.
3. After the user's yes, run it again with `--write`.

## Summarize

End with one short chat message in this shape, with "none" for an empty line:

```text
howtoai install
- Dev mode: on, source folder `<source>`, plugins `<plugins>` (or: off, marketplace install)
- Links: <n> created, <n> already fine, <n> refused (<names>)
- AGENTS.md: <what changed in which workspace>
- Missing: <dependencies or steps still open, with their fix>
```

When something stays open, end with the one step the user should take next.

## Skills and agents

- `environment-audit` - owns the Markdown conventions block (its `references/markdown-conventions.md`) and drafts a missing `AGENTS.md`.
- `skill-builder` - after the install, places new personal skills and agents in the source folder when dev mode is on.
- `howtoai-dev` - its own install needs this one first and calls the same `devmode.py`.
