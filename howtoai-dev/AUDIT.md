# howtoai-dev audit

## Checks

`INSTALL.md` and `skill-audit` both run these checks, and each fix is applied only after the user's yes. The columns and kinds are defined in `skill-audit`'s `references/plugin-audit-format.md`.

| ID | Scope | Applies | Kind | Target | Expect | Fix |
| --- | --- | --- | --- | --- | --- | --- |
| D1 | workspace | `exists {workspace}/AGENTS/settings/dev/settings.json` | section | `{workspace}/AGENTS.md` | `#Workbooks text` | Add or replace the Workbooks section, before `## Installed skills` (else at the end), with its Contents entry. |
| D2 | workspace | `exists {workspace}/AGENTS/settings/dev/settings.json` | import | `{workspace}` | `@AGENTS.md` | Add the line `@AGENTS.md` to the workspace's CLAUDE.md: beside a CLAUDE.md, AGENTS.md does not load without it. |
| D3 | workspace | `exists {workspace}/AGENTS/settings/dev/settings.json` | line | `{workspace}/AGENTS.md` | `#Skills line` | Show any old howtoai-dev line and replace it, so `## Installed skills` holds this one line. |
| D4 | workspace | `exists {workspace}/AGENTS/settings/dev/settings.json` | json | `{workspace}/AGENTS/settings/dev/settings.json` | `workbooks/technologies` | Run INSTALL.md's Workbooks section. |
| D5 | workspace | `exists {workspace}/AGENTS/settings/dev/settings.json` | exists | `{workspace}/AGENTS/settings/dev/install.md` | a record | Run INSTALL.md's Write and record. |
| D6 | global | always | contains | `{plugin}/agents/goldfish-*.md` | `skills: dev-workbook` | A plugin change through skill-builder: reviewers read workbooks only through that preload. |
| D7 | global | always | absent | `{plugin}/agents/*.md` | `omitClaudeMd: true` | A plugin change through skill-builder: such an agent does not get AGENTS.md. |
| D8 | workspace | `contains {workspace}/AGENTS.md :: - **Dev mode:** on` | link | `{plugin}/skills/*` | `{global}/skills` | Run INSTALL.md's Install or link. |
| D9 | workspace | `contains {workspace}/AGENTS.md :: - **Dev mode:** on` | link | `{plugin}/agents/goldfish-*.md` | `{global}/agents` | Run INSTALL.md's Install or link. |
| D10 | workspace | `contains {workspace}/AGENTS.md :: - **Dev mode:** on` | hook | `{global}/settings.json` | `PreToolUse dev_test_first.py Edit\|Write\|MultiEdit\|NotebookEdit` | Register the hook as INSTALL.md's Install or link says. |
| D11 | workspace | `contains {workspace}/AGENTS.md :: - **Dev mode:** on` | hook | `{global}/settings.json` | `PreToolUse dev_safe_target.py ^(Bash\|PowerShell\|Edit\|Write\|MultiEdit\|mcp__.*)$` | Register the hook as INSTALL.md's Install or link says. |
| D18 | workspace | `contains {workspace}/AGENTS.md :: - **Dev mode:** on` | hook | `{global}/settings.json` | `UserPromptSubmit dev_reply_log.py *` | Register the hook as INSTALL.md's Install or link says: without it, approvals in the user's name are recorded unverified. |
| D12 | workspace | `contains {workspace}/AGENTS.md :: - **Dev mode:** on` | json | `{global}/plugins/installed_plugins.json` | `!plugins/howtoai-dev@howtoai-mods` | Skills and hooks run twice: ask before uninstalling the marketplace copy. |
| D17 | workspace | `exists {workspace}/AGENTS/settings/dev/settings.json && not contains {workspace}/AGENTS.md :: - **Dev mode:** on` | json | `{global}/plugins/installed_plugins.json` | `plugins/howtoai-dev@howtoai-mods` | Run INSTALL.md's Install or link. |
| D13 | workspace | `exists {workspace}/AGENTS/settings/dev/settings.json` | command | `py -3 -I -B "{plugin}/skills/dev-workbook/scripts/workbook.py" audit --workspace "{workspace}"` | no format errors and nothing untagged | Fix through dev-workbook's Propose or Record a version. |
| D14 | workspace | `exists {workspace}/AGENTS/settings/dev/settings.json` | command | `py -3 -I -B "{plugin}/skills/dev-core/scripts/devcore.py" settings --workspace "{workspace}"` | configured is true | Run INSTALL.md's Write and record. |
| D15 | global | always | command | `py -3 -I -B "{plugin}/scripts/install_check.py" index` | clean | Update docs/install-index.md through a plugin change. |
| D16 | global | always | command | `py -3 -I -B "{plugin}/scripts/install_check.py" deps` | deps_ok is true, and nothing a chosen option needs is missing | Install what is missing after the user's yes; a deferred step's item is recorded under Left out. |

## Workbooks text

The tool list is filled in from the workspace's dev settings.

```markdown
## Workbooks

Workbooks hold this workspace's rules and facts for {json:AGENTS/settings/dev/settings.json#workbooks/technologies}. Before you plan, write, test, review, or judge work on any of them, read the workbook through the `dev-workbook` skill, never by opening its files.
```

## Skills line

```markdown
- `howtoai-dev` - the dev process (plan, tests first, build, review, deploy, learn): start every code change here with `dev-plan`. Settings in `AGENTS/settings/dev/settings.json`, install record in `AGENTS/settings/dev/install.md`.
```
