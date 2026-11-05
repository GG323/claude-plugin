# command-pane

## Contents

- [What it does](#what-it-does)
- [Files](#files)
- [Where data lives](#where-data-lives)
  - [User files](#user-files)
  - [Session state and store](#session-state-and-store)
  - [Settings](#settings)
- [Debugging](#debugging)
  - [Check and reload](#check-and-reload)
  - [Reading what went wrong](#reading-what-went-wrong)
  - [Connector problems](#connector-problems)
- [Extending](#extending)
  - [Rules the validator holds](#rules-the-validator-holds)
  - [Add a setting](#add-a-setting)
  - [Add a Claude Code or desktop app setting](#add-a-claude-code-or-desktop-app-setting)
  - [Add a built-in button](#add-a-built-in-button)
  - [Add a default prompt button](#add-a-default-prompt-button)
  - [Add a slash command](#add-a-slash-command)
  - [Add a Today source](#add-a-today-source)
- [Release](#release)
- [Skills and agents](#skills-and-agents)

## What it does

A Claude Code mod that puts one-click buttons above the prompt box, in folders each user customizes, plus three side panes:

- **Band** - the Main group drawn inline, every other group as a folder (`▸ Name`) that opens in place; ✎ opens the Customize pane.
- **Customize pane** (`/buttons`) - show, hide, reorder, and move buttons; add, rename, and delete folders; add prompt buttons (fill the box or send at once; text starting with `/` runs a slash command).
- **Settings pane** (⚙) - technical level, approval detail, Handover levels, output style, archive inactive sessions, and Apply recommended.
- **Today pane** (☰, `/today`) - tabs per source: editable Markdown files, Gmail and Google Calendar (read only, with optional summaries), + to add a source, ⚙ for the sources editor, and Fix connection for a failing connector.
- **Handover** (⇄) - writes a handover and starts a new session with it; the button turns yellow, then red, as the context fills.

General mod programming (API, workflow, what has been tested) is in [mod-programming.md](../docs/mod-programming.md); this file covers only command-pane.

## Files

| File | Owns |
| --- | --- |
| [.claude-plugin/plugin.json](.claude-plugin/plugin.json) | Name, version, description, `types`, and the `userConfig` settings fields. |
| [hooks/hooks.json](hooks/hooks.json) | Names the one module, `register.tsx`. |
| [hooks/register.tsx](hooks/register.tsx) | `register`: calls each feature's register function, the one `session.start` hook, the `prompt.compose` hook (user settings section of the system prompt), and the Settings pane. |
| [hooks/customize.tsx](hooks/customize.tsx) | The band, the Customize pane, `/buttons`, built-in button defaults (`BUILTINS`), the default layout, and what each built-in does (`press`). |
| [hooks/today.tsx](hooks/today.tsx) | The Today pane, `/today`, source readers, Markdown editing, connector lookup, summaries, the sources editor, and the + and Fix connection prompts. |
| [hooks/handover.tsx](hooks/handover.tsx) | The Handover prompt, its colour levels, and the `turn.complete` redraw. |
| [types/index.d.ts](types/index.d.ts) | The `$.state` contract: every `$.state` key of every feature, under the one `'command-pane'` entry. |
| [today.example.json](today.example.json) | An example `today.json`. |

A feature lives in its own file and exports `register<Feature>(on)` (hooks) and, if it needs start-up work, `start<Feature>($)`, which the one `session.start` hook in `register.tsx` calls. A module may hook each event only once without a matcher, so a feature never adds its own `session.start`.

## Where data lives

### User files

Per user, in `~/.claude/command-pane/`; the panes write them, so users never edit JSON:

- `buttons.json` - the band layout: `{ version: 1, groups: [{ id, name, items }] }`. Loaded at session start by `normalize()`, which puts Main first, adds any missing built-in with its default visibility, and drops duplicate ids. A file that fails to read falls back to the defaults with a toast.
- `today.json` - Today sources: `{ default: { sources, refreshMinutes }, workspaces: { "<folder>": { ... } } }`. The longest workspace folder that holds the session's folder wins, else `default`. Example: [today.example.json](today.example.json).

### Session state and store

`$.state` atoms (session; declared in [types/index.d.ts](types/index.d.ts)):

| Key | File | Holds |
| --- | --- | --- |
| `settingsRev` | register.tsx | Counter bumped after each settings change, so the Settings pane redraws. |
| `layout` | customize.tsx | The band layout (`null` until loaded). |
| `bandOpen` | customize.tsx | The folder open in the band, `''` for none. |
| `customizeRev` | customize.tsx | Counter that redraws the Customize form. |

`$.store` keys (across sessions; file `~/.claude/plugins/store/command-pane_howtoai-mods-<hash>.json`, written a little after each set):

| Key | Holds |
| --- | --- |
| `today.lastResults` | `{ snapshot, sources }`: the last read of every Today source, including each error. |
| `today.folders` | Folder id to open or closed; absent means lowest-level folders closed, others open. |
| `today.snoozed` | Snoozed items, until midnight. |
| `today.summaries` | Summary text by item key, the newest 400. |
| `today.tab` | The open Today tab. |

The Today pane and the Customize form also keep working copies in module variables and redraw with `$.ui.invalidate('ui.render')`; these start over on every reload.

### Settings

- The mod's own settings are `userConfig` fields in `plugin.json`: `techLevel`, `approvalLevel`, `handoverWarn`, `handoverAlert`. Each is a row in `/config` keyed `command-pane.<field>`, saved in `~/.claude/settings.json` under `pluginConfigs`, and passed to `register` as `options`. Changing one reloads the module.
- `outputStyle` is Claude Code's own `/config` row; the pane reads it with `$.config.list()` and sets it with `$.config.set`.
- Archive inactive sessions is a desktop app setting with no `/config` row. The pane reads it from the app's `claude_desktop_config.json` (`preferences.ccAutoArchiveInactiveDays`) and changes it by sending Claude a prompt; Claude sets it with the app's settings tools and the user approves.

## Debugging

### Check and reload

1. Edit the installed copy in `~/.claude/plugins/cache/howtoai-mods/command-pane/<version>/`. It reloads when the turn that changed it ends; the module's variables start over, `$.state` and `$.store` stay.
2. Validate: `"%APPDATA%\Claude\claude-code\<version>\<build>\claude.exe" plugin validate <folder>` (`claude` is not on the PATH in the desktop app). It lists every hook, `$` call, and pane `requestId`; `requestId=?` means a non-literal id.
3. Type-check: a `tsconfig.json` outside the mod folder whose `files` list names the engine's `claude-code.d.ts`, this mod's `types/index.d.ts`, and every `hooks/*.tsx` (see [Type-check](../docs/mod-programming.md#type-check)). Without `types/index.d.ts` every `$.state` key types as `never`.
4. Land the change in this folder with CRLF line endings, and check that the two copies match.

### Reading what went wrong

- A hook that throws or returns a tree the surface refuses shows one dim line in the transcript: `command-pane: <event> hook skipped: <reason>`.
- A refused `$` call is silent unless caught. The mod shows refusals with `$.ui.toast` (for example "Setting not changed: ...", "Not sent: ..."); do the same in new code.
- Today errors are kept per source in the store file under `today.lastResults` (`sources[i].error`), so they can be read after the fact. A connector error lists every server and tool tried, not just the last.
- `buttons.json` or `today.json` that fails to parse shows a toast and falls back to the defaults.

### Connector problems

- The desktop app names connectors by ID, not by name: Gmail and Calendar tools show as `mcp__<id>__search_threads`, `mcp__<id>__list_events`. The mod finds them by their tools in `$.tool.list()` (`CONNECTOR_TOOLS` in today.tsx), which is empty at `session.start` and filled a little later.
- A `$.mcp.call` from the mod passes Claude Code's permission check. In auto mode it can be stopped ("gave no verdict"). The fix is an allow rule for exactly the one read-only tool in `~/.claude/settings.json` `permissions.allow`. The mod never adds it: Fix connection sends Claude the error and the `CONNECT_STEPS` procedure, and Claude shows the rule and asks first.

## Extending

### Rules the validator holds

- Never pass `$` through something it cannot trace: no object of callbacks (`actions.star($)`) and no computed call (`actions[id]($)`). Call named functions, declared or imported, as `fn($)`; dispatch with a `switch`.
- A pane's `ui.render` matcher takes a literal `requestId` string, not an imported constant.
- `types/index.d.ts` exports types only (no `export {}`), and every `$.state` key goes under the one `'command-pane'` entry.
- `Input` and `Select` do not exist on mobile: guard with `'Input' in $.ui.resolve(e)`.
- A value kept in an atom needs a `shape` string; change it when the value's type changes, so an old value is not read as the new type.

### Add a setting

A setting of the mod's own, shown in `/config` and the Settings pane:

1. `plugin.json` `userConfig`: add the field (`type: "string"`, `title`, `description`, `options`, `default`).
2. `register.tsx`: add `const <NAME>_KEY = 'command-pane.<field>'` and the options list next to `TECH_LEVELS`.
3. Settings pane: add a section with `choiceRow(<NAME>_KEY, '<prefix>', <LEVELS>, value(<NAME>_KEY, <default>))`. `choose` sets it and bumps `settingsRev`.
4. Use it: `options.<field>` in `register`, or `value(...)` while drawing. If it changes Claude's behaviour, add its text to the `prompt.compose` hook, as `TECH_TEXT` and `APPROVAL_TEXT` do.
5. If it belongs in the recommended setup, add it to `RECOMMENDED` and to the loop in `applyRecommended`.

### Add a Claude Code or desktop app setting

- A Claude Code `/config` row (find the key with `$.config.list()`; the 2026-11-05 list is in the [Findings log](../docs/mod-programming.md#findings-log)): read the row with `findRow(rows, KEY)` and draw `choiceRow(KEY, ..., row.options, String(row.value))`, as the output style section does. Show the value as text when `row.isLocked`.
- A desktop app setting (no `/config` row): read its value from `claude_desktop_config.json` like `readArchiveDays`, and change it with a button that sends Claude a prompt (`$.prompt.submit({ text, asUser: true })`) naming the setting and value, asking it to use the app's settings tools so the user approves, like `askArchive`. The pane does not see the change until it is reopened.

### Add a built-in button

A button whose action is code, not a prompt:

1. `types/index.d.ts`: add the id to `BuiltinId`.
2. `customize.tsx` `BUILTINS`: add `{ label, icon, color?, group, visible }`. The group is `main`, `session`, or another default folder id. `normalize()` adds it to existing users' layouts with this visibility.
3. `customize.tsx` `press`: add a `case` that calls the action by name, for example `case 'mine': return void runMine($)`. Put the function in its feature's file and import it.
4. A slash command already known to the session needs only `runCommand($, '<name>')`; [command-run-list.md](../docs/command-run-list.md) lists what can run.

### Add a default prompt button

A button that fills or sends a prompt needs no code for a single user: they add it in the Customize pane. To ship it to every new user, add an item to the `prompts` group in `defaultLayout()` (`customize.tsx`): `{ id: 'prompt-<name>', kind: 'prompt', label, icon, text, mode: 'fill' | 'send', visible }`. Existing users keep their saved layout; only a new or reset layout gets it.

### Add a slash command

In the feature's `start<Feature>($)`, call `$.command.register({ name, description })`, then answer it in a `command.run` hook with a matcher for that name. `startToday` (`/today`) and `startCustomize` (`/buttons`) are the examples.

### Add a Today source

All in `today.tsx`:

1. Add a `<Kind>Source` type and add it to `Source`.
2. Write `read<Kind>($, src, index): Promise<SourceResult>`, returning `items` (or `error`), and add it to the dispatch in `refresh` next to `readGmail` and `readCalendar`.
3. A connector source: add its tools to `CONNECTOR_TOOLS`, its read-only tool to `READ_TOOL`, likely server names to `CONNECTOR_NAMES`, and read through `callConnector` so errors and Fix connection work.
4. The sources editor: add the kind to the add-source `Select`, and its fields to `DraftSource`, `toDraft`, and `fromDraft`.
5. Summaries: give it an ask text like `EMAIL_ASK` and include its kind in `summarizeAll`.
6. Add an example to [today.example.json](today.example.json) and to the + prompt in `askToAddSource`.

## Release

1. Raise `version` in [plugin.json](.claude-plugin/plugin.json) when a change should reach other users.
2. Update this file, the Findings log in [mod-programming.md](../docs/mod-programming.md), and the repository [README](../README.md) where the change shows.
3. Validate the repository folder, commit, and push. Users get it with `claude plugin update command-pane@howtoai-mods` and `/reload-plugins`.

## Skills and agents

- `plugin-authoring` (bundled with Claude Code) - loads the engine's API types and the mod rules; load it before changing a hooks module.
- No agents apply.
