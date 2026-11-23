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

Example: [command-pane](../command-pane/), whose [README](../command-pane/README.md) is a worked guide to a multi-file mod: one feature per file, one `session.start` hook, where data lives, and recipes for extending it.

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

Type-check with a `tsconfig.json` kept outside the mod folder (for example in a scratch folder), with these options:

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

Add a `files` list naming the declarations, the mod's `types/index.d.ts` (without it every `$.state` key types as `never`), and every `hooks/*.tsx`. Run `tsc -p <that folder>`.

`claude plugin validate <mod folder>` also checks the manifest and what the engine would refuse. In the desktop app `claude` is not on the PATH; run `"%APPDATA%\Claude\claude-code\<version>\<build>\claude.exe" plugin validate <mod folder>`. A Windows Store install keeps it at `%LOCALAPPDATA%\Claude-Data\claude_<id>\claude-code\<version>\<build>\claude.exe` instead; the path of the running `claude` process shows which.

Rules the validator holds: `$` is never passed through a value it cannot trace (an object of callbacks, a computed call), so dispatch with a `switch` of named calls; a pane's `requestId` matcher is a literal string; a types contract exports types only; each event is hooked at most once without a matcher per module.

## API reference

The full list is in the engine's declarations; grep them for the name at hand (`'tool.call'`, `Pane: {`, `ButtonProps`). The nouns used so far:

| Need | Call |
| --- | --- |
| Band above the prompt | `on('ui.render', { component: 'AbovePrompt' }, hook)` returning a tree |
| Side pane | `$.ui.open({ id, title })` plus a `ui.render` hook on `{ component: 'Pane', requestId: id }` |
| Status line, toast | `$.ui.status(text)`, `$.ui.toast(text)` |
| Elements | `const { Box, Text, Button } = $.ui.resolve(e)`; `e.surface` is `terminal`, `desktop`, `vscode` or `mobile` |
| Link | `Link` element with `href`; the surface opens it when clicked (a mod has no call that opens a URL itself) |
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
- Built-in rows a mod can set are listed in the Findings log (2026-11-05 settings probe). Desktop-app settings, such as archiving inactive sessions, have no `/config` row: a mod can read them from the app's `claude_desktop_config.json` and change them only by asking Claude in a prompt, which uses the app's settings tools with the user's approval. See [command-pane](../command-pane/README.md#add-a-claude-code-or-desktop-app-setting).

## What a mod cannot do

- Create or fork a session, or open a split view. Claude can, with the desktop app's session tools, when a prompt asks it to. A mod can open an independent new session in the desktop app through the deep link `claude://code/new?folder=<path>&q=<prompt>`, which only fills in the text box (see the Findings log, 2026-11-12 Handover).
- Press Enter in the prompt box, or trigger desktop-app features that live in the app's own prompt box (`/btw` side chat).
- Draw in the session info rail or the hint line under the prompt (desktop app).
- Change a desktop-app setting (such as archiving inactive sessions) or a permission rule itself. A prompt can ask Claude to, and the user approves.

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
- 2026-11-05, command-pane Settings pane archive row, desktop app:
  - The desktop app keeps its own settings in `claude_desktop_config.json` under `preferences` (archive: `ccAutoArchiveInactiveDays`, 0 = never). A mod reads it with `$.fs.read` at `%APPDATA%/Claude/` (Windows) or `~/Library/Application Support/Claude/` (macOS).
  - Windows Store install: the app's own processes (the engine, its shells) see that file at `%APPDATA%/Claude/`; a process started outside the app finds it at `%LOCALAPPDATA%/Packages/Claude_<id>/LocalCache/Roaming/Claude/`. The mod tries both.
  - Changing it from a button: `$.prompt.submit` asks Claude to use the app's settings tools; the user approves on a card. The pane shows the new value when reopened.
- 2026-11-10, command-pane Design studio button (0.5.0), engine 2.1.321 declarations; not yet pressed live:
  - No `$` call opens a URL. `Link` (`href`, `label`) is the only way: an anchor on desktop, an OSC 8 span in the terminal, opened by the surface on a click. On a remote surface only an `https:` link is drawn as a link, so a `http://127.0.0.1` link may show as plain text there. A `Button` cannot hold a `Link`, so the button opens a pane that shows the link.
  - The built-in browser pane is reached only through Claude: a `$.prompt.submit` asking Claude to open the URL there (its browser tools). `$.mcp.call` names only servers the session has, and goes through the permission check, so it was not used for this.
  - `$.http.fetch` takes `http://127.0.0.1:<port>/...`, so a mod can health-check a local server before deciding; `$.fs.read` reads its runtime file.
  - `$.process.spawn` could start a server, but the child dies when the loop ends or the module unloads (every reload), so a long-lived server is started by Claude in the background instead.
  - A new built-in reaches existing `buttons.json` layouts through `normalize()`, which appends it to its default group; saving the file once when a built-in was missing makes it last.
  - On this machine (Windows Store install) the validator was `%LOCALAPPDATA%\Claude-Data\claude_pzs8sxrjxfjjc\claude-code\2.1.321\d020ce1b5d30\claude.exe`, not under `%APPDATA%\Claude\claude-code\`, and the API declarations were in the `plugin-authoring` skill's `types/claude-code.d.ts` (23,600 lines in 2.1.321).
  - Update 2026-11-12: a mod can open a URL in the user's default browser with `$.process.run(['rundll32', 'url.dll,FileProtocolHandler', url])` on Windows (`open` on macOS, `xdg-open` on Linux); it returns at once. A server that must outlive the module starts detached through `powershell -Command Start-Process -WindowStyle Hidden ...`, which `$.process.run` waits on only briefly. Waits use `$.clock.sleep` and `$.clock.now`. command-pane's `browser.tsx` holds these; validated with 2.1.321 and pressed live in the desktop app on 2026-11-12 (both buttons open the default browser).
  - The validator lists the new pane as `requestId=command-pane-design` (a literal) and the calls through named functions (`via healthyUrl`, `via askToStart`).
- 2026-11-12, token-saving-mods: a plugin from a directory marketplace (`claude plugin marketplace add <folder>`) runs in place, so `$.plugin.root` is that folder, not a copy under `~/.claude/plugins/cache/`. Mods that derive the home folder from `$.plugin.root` cut at `/.claude/` (all of Ben AI's pack) then write their files inside their own folder and the Mods pane comes up empty. Adding the marketplace through a junction under `~/.claude/` fixes it without code changes. Each mod in the pack now also ships `hooks/paths.ts` (master copy `token-saving-mods/_shared/paths.ts`): `resolvePaths($)` runs first in its `session.start` handler and picks the first of `USERPROFILE`, `HOME`, the `paths` saved in its `$.store`, and the root cut at `/.claude/` that holds a `.claude` folder; `homeSync($)` returns it everywhere the old expression was. A new mod should do the same.
  - The validator refuses a second `on('session.start')` without a matcher in one mod, even from a helper file, so shared setup is called from the mod's one handler.
- 2026-11-12, command-pane Handover, desktop app 4.23118.1.0 (Windows Store):
  - A turn sent by `$.prompt.submit` (even `asUser: true`) does not count as the user's own words: Claude's `start_session` refuses it ("Start sessions only on the user's own words"). Sessions Claude starts from a typed prompt are linked side sessions, and the app refused a one-time scheduled task started from a mod-sent turn too (auto mode).
  - The app registers `claude://` (`HKCR\claude`). Its bundle routes `claude://code/new` with `folder` (repeatable), `file`, and `q` or `prompt` (cut at 14,336 characters); `ssh_host`, `ssh_port`, `ssh_folder` open on an SSH connection instead and refuse `folder`. Other routes: `code/continue?session=last`, `code/needs-input`, `claude.ai/new?q=`, `cowork/new?q=`.
  - Opening `claude://code/new?folder=...&q=...` (rundll32 `url.dll,FileProtocolHandler`, or `Start-Process`) opens a new, independent Code session in that folder with the prompt in its text box. It is not sent: the bundle has no auto-submit option, so the user presses Enter.
  - command-pane's Handover used this first (Claude wrote the handover to a file, the mod opened the deep link with a read-the-file prompt); pressed live on 2026-11-12, it worked, but left files behind. A refresh (`/clear`, then `$.prompt.fill` with the reply) was tried next and dropped before a live press: the user preferred the Task card a started session shows. The current version asks Claude to propose the session (`start_session`, initiation `own_initiative`), which the app allows from a mod-sent turn; one click on the card starts it, with the handover as the session's first message. No file is written. Pressed live in the desktop app on 2026-11-12: works. The brief's first line has the new session call `detach_session` with `"self"`, so the proposing session gets no turn-end notes; also works live.
  - The instructions then moved into a skill the plugin ships (`command-pane/skills/handover/SKILL.md`), and the button runs it with `$.command.run({ command: 'command-pane:handover' })`: a mod can run a plugin skill that way, and the transcript shows the short command instead of the prompt. Pressed live on 2026-11-12: works.
- 2026-11-22, command-pane Handover, Claude Code 2.1.330: the skill moved to the `howtoai` plugin (`howtoai/skills/handover/SKILL.md`). A mod that runs another plugin's skill must find its name first with `$.command.list()`: `<plugin>:<skill>` for a plugin install, the bare name with `source: 'user'` for a skill linked into `~/.claude/skills/`. Pressed live in the desktop app on 2026-11-22 with the linked skill: works.

## Skills and agents

- `plugin-authoring` - Claude Code's built-in skill for making and debugging mods; loads the engine's type declarations and examples.
- No agents apply.
