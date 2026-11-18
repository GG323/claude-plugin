# howtoai-dev

## Contents

- [What it is](#what-it-is)
- [What is in this version](#what-is-in-this-version)
- [Where it keeps data](#where-it-keeps-data)
- [Install](#install)
- [Attribution](#attribution)
- [Skills and agents](#skills-and-agents)

## What it is

A software-development process for Claude Code: plan, user acceptance, tests first, build, test, review, human review, and deploy, with a learn loop that improves the process and a workbook per language and tool. The design is in the HowToAI plan doc "Developer plugin: requirements and plan". The stage skills arrive phase by phase; this README lists what exists now.

## What is in this version

Version 0.1.0 holds the foundations:

- `dev-core` - an internal skill with the settings and their setup, the plan folder script (`state.json` per change, `dev-plans/INDEX.md`), and the document templates.
- Plan-review agents with no conversation context ("goldfish"): `goldfish-comprehension`, `goldfish-zoom-out`, `goldfish-critic`, `goldfish-readiness`.
- `goldfish-scorer` (confidence score per finding) and `goldfish-verifier` (tries to refute Critical and Major findings).

## Where it keeps data

- `<workspace>/dev-plans/` - one folder per change and `INDEX.md`. The plugin never deletes anything there; clean up old changes yourself.
- `<workspace>/.howtoai/dev/settings.json` - project settings; `~/.claude/howtoai/dev-settings.json` - your defaults across projects. No secrets are stored.

## Install

It needs the `howtoai` plugin (for `skill-builder`, `skill-finder`, and `grilling`) and Python 3.

```bash
claude plugin install howtoai@howtoai-mods
claude plugin install howtoai-dev@howtoai-mods
```

## Attribution

The goldfish agents are adapted from [google/elephant-goldfish-model](https://github.com/google/elephant-goldfish-model) (Apache License 2.0); each adapted file names the upstream commit and states that it was changed.

## Skills and agents

- `dev-core` - shared settings, plan folder state, and templates.
- `goldfish-comprehension`, `goldfish-zoom-out`, `goldfish-critic`, `goldfish-readiness`, `goldfish-scorer`, `goldfish-verifier` - review agents.
