# howtoai audit

## Contents

- [Checks](#checks)
- [Skills line](#skills-line)

## Checks

`INSTALL.md` and `skill-audit` both run these checks, and each fix is applied only after the user's yes. The columns and kinds are defined in `skill-audit`'s `references/plugin-audit-format.md`.

| ID | Scope | Applies | Kind | Target | Expect | Fix |
| --- | --- | --- | --- | --- | --- | --- |
| H1 | global | always | json | `{global}/howtoai/install.json` | `howtoai_root` | Run INSTALL.md's Record the choice. |
| H2 | workspace | `json {workspace}/AGENTS/settings.json :: howtoai` | section | `{workspace}/AGENTS.md` | `{plugin}/skills/skill-audit/references/markdown-conventions.md#Markdown conventions` | Add the section with `devmode.py agents-md`. When the workspace's copy differs, show both and ask which wins; the reference changes only through `skill-audit`'s check W1. |
| H3 | workspace | `json {workspace}/AGENTS/settings.json :: howtoai` | json | `{workspace}/AGENTS/settings.json` | `howtoai/dev_mode` | Run INSTALL.md's Record the choice. |
| H4 | workspace | `json {workspace}/AGENTS/settings.json :: howtoai/dev_mode` | link | `{plugin}/skills/*` | `{global}/skills` | Run INSTALL.md's Dev mode on. |
| H5 | workspace | `json {workspace}/AGENTS/settings.json :: howtoai/dev_mode` | json | `{global}/plugins/installed_plugins.json` | `!plugins/howtoai@howtoai-mods` | Every skill shows twice: ask before `claude plugin uninstall howtoai@howtoai-mods`. |
| H6 | workspace | `json {workspace}/AGENTS/settings.json :: howtoai` | import | `{workspace}` | `@AGENTS.md` | Add the line `@AGENTS.md` to the workspace's CLAUDE.md: beside a CLAUDE.md, AGENTS.md does not load without it. |
| H7 | workspace | `json {workspace}/AGENTS/settings.json :: howtoai` | command | `py -3 -I -B "{plugin}/scripts/devmode.py" status --workspace "{workspace}"` | exit 0, the setting is valid, links are fine, and when `git.required` is true `git.problems` is empty | Follow the fix each problem names in INSTALL.md. |
| H8 | global | `exists {global}/scheduled-tasks/skill-audit-weekly` | allow | `{global}/settings.json` | `Skill(skill-audit) or Skill(howtoai:skill-audit)` | Follow INSTALL.md's Allow the weekly audit: show the user the exact line, which the user adds. |
| H9 | workspace | `json {workspace}/AGENTS/settings.json :: howtoai` | line | `{workspace}/AGENTS.md` | `#Skills line` | Show any old howtoai line and replace it, so `## Installed skills` holds this one line. |

## Skills line

```markdown
- `howtoai` - the HowToAI skill tools (skill-builder, skill-finder, skill-audit, skill-design, brain-dump, grilling, handover): build or change any skill, agent, or tool with `skill-builder`. Tools live in `AGENTS/`, harness folders hold only links, settings in `AGENTS/settings.json`.
```
