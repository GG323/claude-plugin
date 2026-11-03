# claude-plugin

## Contents

- [Mods](#mods)
- [Install](#install)
- [Update](#update)
- [Skills and agents](#skills-and-agents)

## Mods

This repository is the `howtoai-mods` plugin marketplace for Claude Code.

- [command-pane](command-pane/) - a star button above the prompt box that fills in "Build a skill based on our conversation, ask if the process to automate is not clear".

## Install

At the prompt of a Claude Code terminal session:

```text
/plugin install command-pane --marketplace GG323/claude-plugin
```

From a shell:

```bash
claude plugin install command-pane --marketplace GG323/claude-plugin
```

In the desktop app's Code tab: click **+** next to the prompt box, then **Plugins**, add the marketplace `GG323/claude-plugin`, then add `command-pane` at user scope.

## Update

Installed plugins run the copy made at install time. After pushing a change, raise `version` in the mod's `plugin.json`, then run `claude plugin update command-pane@howtoai-mods` and `/reload-plugins`.

## Skills and agents

None apply.
