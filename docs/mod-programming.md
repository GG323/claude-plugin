# Claude Code mod programming

## Contents

- [What a mod is](#what-a-mod-is)
- [Files and layout](#files-and-layout)
- [Development workflow](#development-workflow)
  - [Edit and reload](#edit-and-reload)
  - [Type-check](#type-check)
- [API reference](#api-reference)
- [Prompt box and commands](#prompt-box-and-commands)
- [Drawing](#drawing)
  - [Where a mod can draw](#where-a-mod-can-draw)
  - [Buttons and hover text](#buttons-and-hover-text)
- [Settings and the system prompt](#settings-and-the-system-prompt)
- [What a mod cannot do](#what-a-mod-cannot-do)
- [Findings log](#findings-log)
- [Skills and agents](#skills-and-agents)

## What a mod is

A mod is a Claude Code plugin with a hooks module: TypeScript (`.tsx` or `.ts`) that the engine loads and calls on events. It can draw UI (a band above the prompt, a side pane, toasts, a status line), react to prompts and tool calls, register slash commands, and keep state. Every hook is `($, e, next)`: `$` is the engine interface, `e` the event's input, and `next(e)` runs the rest of the chain.

Mods run in Claude Code only (terminal, desktop app, VS Code, mobile), not in Cowork or claude.ai web, and only inside an open session.

Official docs: [plugins](https://code.claude.com/docs/en/plugins) and [hooks](https://code.claude.com/docs/en/hooks).

## Files and layout

Each mod is a plugin folder in this repository, listed in [marketplace.json](../.claude-plugin/marketplace.json):

- `.claude-plugin/plugin.json` - name, version, description.
- `hooks/hooks.json` - `{ "modules": ["./register.tsx"] }`.
- `hooks/register.tsx` - the module: `export const register: Register = on => { ... }`, types imported from `'claude-code'`.
- `types/index.d.ts` - only for a mod that keeps values in `$.state`; named in `plugin.json` as `"types"`.

Example: [command-pane](../command-pane/).

## Development workflow

### Edit and reload

- The installed copy runs from `~/.claude/plugins/cache/howtoai-mods/<mod>/<version>/`. Edit it there for live testing, then land the same change in this repository's folder.
- A change to the mod's files reloads it when the current turn ends. Each reload adds a "This mod reloaded after a change to its files" notice to the chat; a mod cannot hide it.
- A reload runs `register` and `session.start` again. `$.state` (session) and `$.store` (across sessions) survive; the module's own variables start over.
- Repository files use CRLF line endings; the installed cache copy uses LF.
- Bump `version` in `plugin.json` when a change should reach other users through the marketplace.
- Hook failures show as one dim line in the transcript, `<plugin>: <event> hook skipped: <reason>`. A rejected `$` call shows only if the mod catches it; show it with `$.ui.toast` while testing.

### Type-check

The engine writes the API declarations (`claude-code.d.ts`, about 14,000 lines with doc comments and examples) for its own version. The `plugin-authoring` skill names their path when it loads. Once the engine has loaded a mod from a folder the user owns, the same types sit in `<mod>/.claude-plugin/types/`.

Type-check with a `tsconfig.json` kept outside the mod folder (for example in a scratch folder), whose `files` list names the declarations and `hooks/register.tsx`:

```json
{
  "compilerOptions": {
    "target": "es2023", "lib": ["es2023"], "types": [],
    "module": "esnext", "moduleResolution": "bundler",
    "strict": true, "noUncheckedIndexedAccess": true,
    "noEmit": true, "skipLibCheck": true,
    "jsx": "react", "jsxFactory": "h", "jsxFragmentFactory": "Fragment"
  }
}
```

Run `tsc -p <that folder>`. `claude plugin validate <mod folder>` also checks the manifest and what the engine would refuse, where the `claude` command is on the PATH.

## API reference

The full list is in the engine's declarations; grep them for the name at hand (`'tool.call'`, `Pane: {`, `ButtonProps`). The nouns used so far:

| Need | Call |
| --- | --- |
| Band above the prompt | `on('ui.render', { component: 'AbovePrompt' }, hook)` returning a tree |
| Side pane | `$.ui.open({ id, title })` plus a `ui.render` hook on `{ component: 'Pane', requestId: id }` |
| Status line, toast | `$.ui.status(text)`, `$.ui.toast(text)` |
| Elements | `const { Box, Text, Button } = $.ui.resolve(e)`; `e.surface` is `terminal`, `desktop`, `vscode` or `mobile` |
| Link | `Link` element with `href`; the surface opens it |
| Prompt box | `$.prompt.read()`, `$.prompt.fill({ text, mode })`, `$.prompt.submit({ text })` |
| Slash commands | `$.command.list()`, `$.command.run({ command, args })`, `$.command.register({ name, description })` |
| Settings menu | `$.config.list()`, `$.config.set(...)` |
| System prompt | `on('prompt.compose', hook)` |
| Model calls | `$.model.complete(...)`, `$.model.fork({ prompt })` (one tool-less reply over the current transcript) |
| Connectors | `$.mcp.call(server, tool, args)` |
| Files, timers, HTTP | `$.fs`, `$.clock`, `$.http.fetch` |
| State | `$.state` (session, typed in `types/index.d.ts`), `$.store` (across sessions) |
| Session facts | `$.session.messages()`, `$.session.cwd()`, `$.session.surface()` |

## Prompt box and commands

- `$.prompt.fill` only writes the prompt box; the user still sends it.
- `$.prompt.submit` sends a prompt to the model as its own turn (queued until the session is idle). `asUser: true` drops the "plugin sent a message" frame. It refuses text starting with `/`: commands go through `$.command.run`.
- `$.command.run({ command })` runs a slash command the engine knows in this session. Desktop-app commands that the app catches in its own prompt box (such as `/btw`, which opens the desktop side chat) are not engine commands there: the run fails with "no command named /btw in this session". `$.command.list()` shows what is reachable; [command-run-list.md](command-run-list.md) records the 87 commands it returned in the desktop app on 2026-11-05 (none opens a side chat or forks a session).

## Drawing

### Where a mod can draw

Tested 2026-10-26 in the desktop app:

- Band above the prompt (`AbovePrompt`): works, buttons press.
- Side pane (`Pane`): works; opens beside the session's info rail, like the browser or diff pane.
- Status line (`$.ui.status`): plain text only, no buttons. A value stays until the mod clears it.
- Hint line (`PromptHint`): the desktop app never asks a mod to draw it.
- Session info rail (Environment, Changes, Context, Connectors, Outputs): no mod slot.
- Transcript items: drawable, but they scroll away.

### Buttons and hover text

- A `Button` holds text and `Text` children only, so an icon is a character (★, ⇥), not a picture. An `Svg` can sit beside a button but cannot be pressed.
- `plain` draws a button without chrome. `key` gives each button a stable address.
- There is no tooltip prop. Hover text is a hidden `Box` (`display: "none"`, `position: "absolute"`) with `hover: { display: "flex" }`, inside the button's keyed `Box`.

## Settings and the system prompt

- `$.config.set` changes a `/config` row as if the user did it in the menu; `$.config.list` reads current values.
- A `prompt.compose` hook can add a system prompt section (for example the user's technical level), so every prompt carries it without a hidden instruction file.
- `userConfig` in `plugin.json` gives a mod its own settings in `/config`. A `string` field with `options` is a picker; its row key is `<plugin>.<field>` (for example `command-pane.techLevel`), and `$.config.set` on it writes `settings.json` under `pluginConfigs."<plugin>@<marketplace>".options` and reloads the module with the new `options`.
- Built-in rows a mod can set are listed in the Findings log (2026-11-05 settings probe). Desktop-app settings, such as archiving inactive sessions, have no `/config` row.

## What a mod cannot do

- Create or fork a session, or open a split view. Claude can, with the desktop app's session tools, when a prompt asks it to.
- Press Enter in the prompt box, or trigger desktop-app features that live in the app's own prompt box (`/btw` side chat).
- Draw in the session info rail or the hint line under the prompt (desktop app).

## Findings log

- 2026-11-05, command-pane Side chat button, desktop app:
  - `$.prompt.submit` with a fork-and-split prompt: the fork was created, but Claude did not open it beside the chat.
  - `$.prompt.fill` with `/btw `: the side chat opened once the user pressed Enter.
  - `$.command.run({ command: 'btw' })`: "no command named /btw in this session".
  - `$.prompt.submit` with `/btw`: refused, text starting with `/` must go through `$.command.run`.
  - `$.command.list()` at `session.start`: 87 commands (60 built-in, 19 plugin, 8 user skills), no `/btw` and no fork command; see [command-run-list.md](command-run-list.md). `$.session.surface()` was `null` there.
  - Outcome: the Side chat button was dropped; command-pane stays at 0.3.0 with the star button only.
- 2026-11-05, command-pane Today pane, desktop app:
  - A module hooks `session.start` (and any other event) once without a matcher: `claude plugin validate` refuses a second one. A feature in its own file exports a start function that the one `session.start` hook calls.
  - A feature file is imported with a plain `import` from `register.tsx`; `hooks.json` still names one module.
  - A pane can redraw from module variables plus `$.ui.invalidate('ui.render')`, with no `$.state` contract; `$.store` keeps the last results across reloads.
  - `$.mcp.call` reached the desktop app's Gmail connector, and `$.fs.read` read an absolute Windows path (`C:/Users/...`).
  - The validator: `"%APPDATA%\Claude\claude-code\<version>\<build>\claude.exe" plugin validate <mod folder>`, where `claude` is not on the PATH.
  - Forms in a pane: `Input` (`onInput` on each change, `onSubmit` on Enter) and `Select` (`onSelect`) exist on terminal, desktop and VS Code, not on mobile; check with `'Input' in $.ui.resolve(e)`. A form keeps its working copy in module variables and redraws with `$.ui.invalidate('ui.render')`.
  - The type-check `tsconfig` must list `types/index.d.ts` too, or every `$.state` key reads as `never`.
- 2026-11-05, command-pane Settings pane, desktop app:
  - `$.config.list()` at `session.start` returned 46 rows: the engine's own, plus each plugin's `userConfig` fields. Choice rows a client setup may use: `outputStyle` (default, Proactive, Concise, Explanatory, Learning), `permissionMode` (default, plan, acceptEdits, auto, dontAsk), `model`, `theme`, `askUserQuestionTimeout`, `dialogExpiry`, `remoteControl`. `thinking` was locked. No row for archiving inactive sessions.
  - `$.config.set` on the mod's own `userConfig` rows and on `outputStyle` worked from a pane button.
  - `plugin.json` `types` names one contract file; a contract file exports types only (`export {}` is refused), so every feature's `$.state` keys go under the one `'command-pane'` entry there.
  - A pane that reads `$.config.list()` while drawing does not redraw by itself after a change; a `$.state` counter (`atom`) bumped after each `$.config.set` redraws it.
  - `$.store` for the plugin is `~/.claude/plugins/store/<plugin>_<marketplace>-<hash>.json`; it is written a while after `$.store.set`, not at once.
- 2026-11-05, command-pane band folders and Customize pane, desktop app:
  - The validator refuses passing `$` through a value it cannot trace: an object of callbacks (`actions.star($)`), or a computed call (`actions[id]($)`). A named function, declared or imported, called as `fn($)` is fine, so built-in buttons go through a `switch` that calls each one by name.
  - A `ui.render` matcher's `requestId` should be a literal: an imported constant shows as `requestId=?` in `claude plugin validate`.
  - A layout kept in a `$.state` atom redraws the band and the pane together after each change; the same layout is written to a per-user JSON file (`~/.claude/command-pane/buttons.json`) so it lasts across sessions and can be shared.
  - Folders in the band: there is no pop-up menu, so a folder button opens its buttons in place, in a round-bordered `Box`, and closes again on a second press.
  - A form field's key carries a counter (`cz-f-label-${formSeq}`): bumping it draws fresh fields with new values, for example when Edit loads another button into the form.

- 2026-11-05, command-pane Today rework, desktop app:
  - The desktop app's connectors are MCP servers named by ID, not by name (Gmail `12b5f882-...`, Calendar `b28c84ff-...`): their tools show as `mcp__<id>__<tool>`. A mod finds a connector by its tools in `$.tool.list()`, which is empty at `session.start` and filled a little later.
  - `$.mcp.call` from a mod goes through Claude Code's permission check: in auto mode the classifier stopped `search_threads` ("gave no verdict"). An allow rule for that one read-only tool (`mcp__<id>__search_threads`) in `~/.claude/settings.json` lets it through. The mod does not add rules itself: its Fix connection button asks Claude, who shows the rule and asks the user first.
  - Keep every error when trying several servers or tools: keeping only the last one hid the real cause.
  - A multi-line `Input` grows with its text by drawing it with `rows` set from the line count; redrawing only when the row count changes keeps typing smooth.
  - `$.model.complete({ model: 'haiku', effort: 'low' })` from a hook makes the summaries with no agent turn; results are cached in `$.store` by item.

## Skills and agents

- `plugin-authoring` - Claude Code's built-in skill for making and debugging mods; loads the engine's type declarations and examples.
- No agents apply.
