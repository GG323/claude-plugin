# claude-plugin

## Contents

- [Plugins](#plugins)
- [Install](#install)
- [Update](#update)
- [Skills and agents](#skills-and-agents)

## Plugins

This repository is the `howtoai-mods` plugin marketplace for Claude Code. It holds two plugins:

- [command-pane](command-pane/) - a mod: a star button above the prompt box that fills in "Build a skill based on our conversation, ask if the process to automate is not clear".
- [howtoai](howtoai/) - two skills:
  - `howtoai:skill-builder` - creates, improves, or repairs a skill.
  - `howtoai:environment-audit` - audits the Claude environment and its workspaces and publishes one HTML report.

Each skill keeps its run state in its own `state/` folder. The folders are ignored by git, so the state stays on the machine that made it and never reaches this repository.

[Claude Code mod programming](docs/mod-programming.md) is the developer reference for the mods: workflow, the API used so far, and what has been tested.

## Install

At the prompt of a Claude Code terminal session (repeat with `howtoai`):

```text
/plugin install command-pane --marketplace GG323/claude-plugin
```

From a shell:

```bash
claude plugin install command-pane --marketplace GG323/claude-plugin
claude plugin install howtoai@howtoai-mods
```

In the desktop app's Code tab: click **+** next to the prompt box, then **Plugins**, add the marketplace `GG323/claude-plugin`, then add `command-pane` and `howtoai` at user scope.

## Update

Installed plugins run the copy made at install time. After pushing a change, raise `version` in that plugin's `plugin.json`, then run `claude plugin update <plugin>@howtoai-mods` and `/reload-plugins`.

## Skills and agents

None apply.
