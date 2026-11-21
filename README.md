# claude-plugin

## Contents

- [Plugins](#plugins)
- [Install](#install)
- [Update](#update)
- [Skills and agents](#skills-and-agents)

## Plugins

This repository is the `howtoai-mods` plugin marketplace for Claude Code. It holds these plugins:

- [command-pane](command-pane/) - a mod: one-click buttons above the prompt box, in folders each user customizes, with their own prompt buttons; a Settings pane (technical level, approval detail, output style, archiving, recommended setup); a Today pane of editable Markdown tasks, email, and calendar per workspace; a Handover button; and a Design studio button that opens the `skill-design` design studio. Its [README](command-pane/README.md) is the developer guide: files, where data lives, debugging, and how to add settings, buttons, prompts, and Today sources.
- [howtoai](howtoai/) - six skills:
  - `howtoai:skill-builder` - creates, changes, or repairs a skill, a tool (subagent, hook, mod, plugin, slash command), or an automated or scheduled procedure, after asking about the crucial details and showing the plan as a page.
  - `howtoai:skill-finder` - finds existing skills, plugins, and tools across the approved marketplaces, and vets a candidate before install.
  - `howtoai:environment-audit` - audits the Claude environment and its workspaces and publishes one HTML report.
  - `howtoai:skill-design` - builds and reviews HTML pages in the HowToAI house design or a client's, with the design studio, a local web app that keeps the house and client designs and the default design in `~/.claude/howtoai/designs.db`.
  - `howtoai:brain-dump` - sorts a brain dump into the right project and section of the workspace's plan doc (usually `TODO.md`), after a placement preview.
  - `howtoai:grilling` - the shared method for asking the user the decisions a task needs, in short rounds of numbered questions with recommended answers; used by `skill-builder` and the `howtoai-dev` skills.
- [howtoai-dev](howtoai-dev/) - the HowToAI software-development process (plan, tests first, build, test, review, human review, deploy, learn), built phase by phase. Version 0.9.0 holds `dev-plan`, the entry point that sizes, questions, drafts, reviews, splits, and gets approval for a change; `dev-test`, which writes tests first and runs them only against classified, non-production targets, with the `dev-test-first` and `dev-safe-target` hooks; `dev-build`, which builds each work item as the smallest change that passes, with every changed line traced to it and a lint, format, type-check, and test gate; `dev-review`, a goldfish code review with scored and verified findings and a human review; `dev-learn`, which finds why serious and repeated findings got through and routes the approved fixes, lowest level first; `dev-deploy`, which deploys to any target you name with its own tools, set up on first use, one approval per production step; the foundations (the internal `dev-core` skill with settings, setup, plan folder state, templates, and the findings tally; the plan-review goldfish, scorer, and verifier agents); and `dev-workbook`, the keeper of technology workbooks, with base workbooks for C#, .NET, Docker, and Terraform. It needs the `howtoai` plugin. Its [README](howtoai-dev/README.md) lists what exists now.

- [token-saving-mods](token-saving-mods/) - Ben AI's Token Saving Mods Pack (Windows build, [description](https://benai.notion.site/Token-Saving-Mods-Pack-4111124570fe81728d6cc04294a399aa)): `input-router`, `effort-optimizer`, `model-router`, `research-router`, `efficient-browser-use`, `mods` (the `/mods` switchboard, which command-pane's Mods button opens), and `savings-proof` (`/savings`). `cache-clock` and `handoff` are kept here for reference only; they are not installed and are to be merged into command-pane's Handover. Changed here: `mods` also finds mods installed with `/plugin install`, and every mod resolves its home folder through `hooks/paths.ts` (environment, then its saved paths, then its own path), so it works wherever it is installed. The folder is also its own local marketplace, `token-saving-mods`, for installing without a push. A directory marketplace runs its plugins in place, outside `~/.claude/`, so for now add it through a junction under `~/.claude/`: `mklink /J %USERPROFILE%\.claude\token-saving-mods <this repo>\token-saving-mods`, then `claude plugin marketplace add %USERPROFILE%\.claude\token-saving-mods` and `claude plugin install <mod>@token-saving-mods`. The junction is a temporary workaround: it keeps the last fallback in `paths.ts` (cutting the mod's own path at `/.claude/`) working until Init works out each machine's real paths and writes them into each mod's saved config.

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
