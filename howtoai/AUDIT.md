# howtoai audit

## Contents

- [Checks](#checks)
- [Skills and agents](#skills-and-agents)

## Checks

`INSTALL.md` and `skill-audit` both run these checks, and each fix is applied only after the user's yes. The columns and kinds are defined in `skill-audit`'s `references/plugin-audit-format.md`.

| ID | Scope | Applies | Kind | Target | Expect | Fix |
| --- | --- | --- | --- | --- | --- | --- |
| H1 | global | always | json | `{global}/howtoai/install.json` | `howtoai_root` | Run INSTALL.md's Record the choice. |
| H2 | workspace | `contains {workspace}/AGENTS.md :: ## Dev mode` | section | `{workspace}/AGENTS.md` | `{plugin}/skills/skill-audit/references/markdown-conventions.md#Markdown conventions` | Add the section with `devmode.py agents-md`. When the workspace's copy differs, show both and ask which wins; the reference changes only through `skill-audit`'s check W1. |
| H3 | workspace | `contains {workspace}/AGENTS.md :: ## Dev mode` | contains | `{workspace}/AGENTS.md` | `- **Dev mode:**` | Run INSTALL.md's Record the choice. |
| H4 | workspace | `contains {workspace}/AGENTS.md :: - **Dev mode:** on` | link | `{plugin}/skills/*` | `{global}/skills` | Run INSTALL.md's Dev mode on. |
| H5 | workspace | `contains {workspace}/AGENTS.md :: - **Dev mode:** on` | json | `{global}/plugins/installed_plugins.json` | `!plugins/howtoai@howtoai-mods` | Every skill shows twice: ask before `claude plugin uninstall howtoai@howtoai-mods`. |
| H6 | workspace | `contains {workspace}/AGENTS.md :: ## Dev mode` | import | `{workspace}` | `@AGENTS.md` | Add the line `@AGENTS.md` to the workspace's CLAUDE.md: beside a CLAUDE.md, AGENTS.md does not load without it. |
| H7 | workspace | `contains {workspace}/AGENTS.md :: ## Dev mode` | command | `py -3 -I -B "{plugin}/scripts/devmode.py" status --workspace "{workspace}"` | exit 0, both settings valid, links and Git are fine | Follow the fix each problem names in INSTALL.md. |
| H8 | global | `exists {global}/scheduled-tasks/skill-audit-weekly` | allow | `{global}/settings.json` | `Skill(skill-audit) or Skill(howtoai:skill-audit)` | Follow INSTALL.md's Allow the weekly audit: show the user the exact line, which the user adds. |

## Skills and agents

- `skill-audit` - runs these checks and owns the Markdown conventions text.
