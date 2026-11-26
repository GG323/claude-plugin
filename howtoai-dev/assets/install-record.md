# howtoai-dev install record

/// Written by the howtoai-dev INSTALL. Rerun INSTALL to change a decision; it rewrites this file in full.

## Contents

- [Run](#run)
- [Decisions](#decisions)
- [Checks](#checks)
- [Left out](#left-out)

## Run

- **Date:** {YYYY-MM-DD}
- **Workspace:** `{workspace}`
- **Plugin:** howtoai-dev {version}, {plugin mode / dev mode from `{plugins folder}`}
- **Harness:** {Claude Code CLI / Claude Code desktop / other}, subagents {yes / no}, artifacts {yes / no}, hooks {yes / no}

## Decisions

| Decision | Value | Stored in | Source |
| --- | --- | --- | --- |
| Dev mode | {on / off} | `AGENTS/settings.json` `howtoai` | {asked / already set} |
| Tracker | {markdown / jira PROJ / github owner/name / azure-devops org project} | {user / project} settings `tracker` | {asked / sign found in ...} |
| Plan format | {auto / artifact / html-file / markdown / tracker} | {user / project} settings `plan.publish` | {asked / default} |
| Plan folder | {dev-plans} | {schema default / project settings `plan_folder`} | {default / asked} |
| Allowed test targets | {names, or "local only"} | project settings `environments.allow` | {asked} |
| Production markers | {markers, or "none named"; any left out and why} | project settings `environments.deny` | {asked / found in ...} |
| Test commands | {commands, or "found on the first run"} | project settings `testing.entry_points` | {CI file / confirmed} |
| Throwaway targets | {docker / none} | project settings `testing.ephemeral` | {confirmed} |
| Test-first hook | {block / warn / off} | {schema default / project settings `testing.test_first`} | {default / asked} |
| Build gate | {commands, or "proposed on the first build"} | project settings `build.gate` | {CI file / confirmed} |
| Deploy | {target names, later, or never} | `AGENTS/deploy-targets.json` | {asked} |
| Deny rules for secret env files | {rules / declined / none found / not written, and why} | `.claude/settings.json` `permissions.deny` | {asked / already set} |
| Workbooks | {technology: base / user / project / version workbook, separated by "; "} | workbook folders | {manifests} |
| Codebase versions | {folder: version, separated by "; ", or "none recorded"; a version implied by another, as "C# 14 (default for net10.0)"} | project `<tech>.md` Header | {manifest file} |
| Support dates | {versions past or near their support date, each an upgrade to plan, or "none"} | workbook audit | {audit} |
| Hooks | {plugin / user settings / not registered} | {`hooks.json` / `~/.claude/settings.json` / not stored} | {plugin mode / asked} |
| Review defaults | {80, 5, 2} | {defaults / project settings `review`} | {default} |

## Checks

| Check | Result |
| --- | --- |
| {one row per check ID in this plugin's AUDIT.md (D) and howtoai's (H)} | {pass / fail / not applicable / not run, with why} |
| approved values, Git problems, and deny rules | {as approved / differences} |
| `skill-builder` double check | {passed after N rounds / findings left / not run, and why} |

## Left out

{Every step skipped or not checked, with the reason, or "none".}
