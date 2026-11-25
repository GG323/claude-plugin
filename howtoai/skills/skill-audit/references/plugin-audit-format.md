# Plugin audit format

## Where the file goes

Any plugin, skill, agent, tool, or mod can ship audit checks.

- **A folder** (plugin, skill, mod, tool): `AUDIT.md` at its root.
- **An agent:** `<name>.AUDIT.md` next to the real file, with no frontmatter. When the installed entry is a link, it goes next to the link's target.
- **A command:** `audits/<name>.AUDIT.md` beside the `commands/` folder, with the same subfolders, because every Markdown file inside that folder becomes a command.

An `INSTALL.md` runs the same file, so setup requirements are written only in `AUDIT.md`.

## Checks table

A `## Checks` section holds one table with the columns ID, Scope, Applies, Kind, Target, Expect, and Fix. A pipe inside a cell is written `\|`.

- **Scope:** `global` (once per audit) or `workspace` (once per workspace).
- **Applies:** `always`, `exists <path>`, or `contains <path> :: <text>`; `not` in front negates one, and ` && ` joins several.
- **Paths** start with `{plugin}` (the folder holding the audit file), `{workspace}`, or `{global}` and cannot leave it, also through links, and never use `**`. Outside the tool's own folder only the text of the workspace's AGENTS.md and CLAUDE.md files and the global CLAUDE.md is read, and of a JSON file only whether a key or hook is there. Secret-like files are never opened.
- **Fix:** what to propose to the user. It is shown as the tool's proposal and applied only after a yes.

## Kinds

| Kind | Target | Expect | Passes when |
| --- | --- | --- | --- |
| `exists` | path or pattern | a short note | Something matches |
| `section` | file | `#<block>` or `{plugin}/<file>#<heading>` | The file has that section word for word |
| `line` | file | `#<block>` | The file has each line of the block, and no other list entry of the same name |
| `import` | `{workspace}` | `@AGENTS.md` | No CLAUDE.md is beside it, or one has the line |
| `contains` | path or pattern | literal text | Every matching file has the text |
| `absent` | path or pattern | literal text | No matching file has the text |
| `json` | JSON file | `key/key`, or `!key/key` | The key is there, or with `!` is not |
| `hook` | `{global}/settings.json` | `<event> <script file> <matcher>` | A hook of that event and exact matcher runs that script |
| `allow` | `{global}/settings.json` | `Skill(<name>)`, several joined by ` or ` | The allow list has one of those rules |
| `link` | pattern | folder | Each match is linked there under its own name |
| `command` | command | what a pass looks like | Run only on request, after the user's yes to that command |
| `review` | AGENTS.md and CLAUDE.md files, or the tool's own files | a question | The agent judges it, read-only |

## Text to install

`#<block>` names a heading in the same file, with the text in a fenced block under it. Inside the block, `{json:AGENTS/settings/<tool>/settings.json#<key/key>}` becomes that setting's list of short lowercase names; no other file or value can be filled in.

Text to install holds no word that starts with `@` (also not in backticks), and no hidden characters. `section` and `line` install only into the workspace's `AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md`, or `.claude/CLAUDE.md`.

## Limits

A check past a limit is reported as invalid, never as passed.

- A file is at most 64 KB and holds at most 64 checks.
- Text to install is at most 4 KB.
- A path has at most two wildcards, in its last part only, and is never a network path or a link to one.
- Each file gets 5 seconds in its own process. A file that runs out is stopped, and the others still run.
- One tool gets 16 files and 10 seconds in all, and the whole run 60 seconds, each tool's first file before any tool's second. The rest are reported as not run.
- In a command, put each placeholder inside double quotes, so paths with spaces, `( ) &`, or `'` work.
