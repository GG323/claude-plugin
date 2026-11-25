# howtoai-dev install index

## Contents

- [How to use this index](#how-to-use-this-index)
- [Requirements at a glance](#requirements-at-a-glance)
- [Dev mode](#dev-mode)
- [Settings folder](#settings-folder)
- [Dependencies and harness](#dependencies-and-harness)
- [Tracker](#tracker)
- [Plan format](#plan-format)
- [Plan folder](#plan-folder)
- [Test targets and production markers](#test-targets-and-production-markers)
- [Test commands](#test-commands)
- [Throwaway test targets](#throwaway-test-targets)
- [Test-first hook](#test-first-hook)
- [Build gate](#build-gate)
- [Deploy](#deploy)
- [Workbooks and versions](#workbooks-and-versions)
- [Hooks and hook rules](#hooks-and-hook-rules)
- [Review defaults](#review-defaults)
- [Add an option no setting covers](#add-an-option-no-setting-covers)
- [Keep this index current](#keep-this-index-current)

## How to use this index

Every install requirement of `howtoai-dev` has one section here. Each section says:

- **Setting:** the key in dev-core's [settings schema](../skills/dev-core/assets/settings.schema.json), or the file that holds the choice. An install changes only these, never a skill file.
- **Set by:** the [INSTALL](../INSTALL.md) step that asks it.
- **Read by:** every skill file and section that acts on it.
- **Signs:** what the install's lookups read to suggest an answer.
- **New option:** the files to change when a client needs a value the setting does not offer yet. That is a plugin change: it goes through `skill-builder` with its own plan, never an edit made during one install.
- **Search:** a text search that finds every place, for checking that nothing was missed. Run it from the plugin folder, for example `rg -n "<pattern>" skills agents hooks`.

## Requirements at a glance

| Requirement | Setting | Asked at install | Default |
| --- | --- | --- | --- |
| Git version control | `## Dev mode` entry in the workspace `AGENTS.md` | yes, once per workspace; on without a separate question when dev mode is chosen | none: must be set on or off |
| Dev mode | `## Dev mode` entry in the workspace `AGENTS.md` | yes, once per workspace | none: must be set on or off |
| Tracker | `tracker.kind` and its keys | yes, when a sign is found or the user wants one | `markdown` |
| Plan format | `plan.publish` | yes | `auto` |
| Plan folder | `plan_folder` | stated as a default | `dev-plans` |
| Test targets | `environments.allow`, `environments.deny` | yes, crucial | only local targets |
| Test commands | `testing.entry_points` | confirmed from CI | none, found on the first run |
| Throwaway targets | `testing.ephemeral` | confirmed | `docker` |
| Test-first hook | `testing.test_first` | stated as a default | `block` |
| Build gate | `build.gate` | confirmed from CI | none, found on the first build |
| Deploy | `deploy.entry_points`, `AGENTS/settings/deploy/targets.json` | yes: now, later, or never | none |
| Workbooks | `workbooks.technologies`, workbook files, codebase versions | yes, per technology and version | found in manifests |
| Hooks | `hook_rules`; registration of the three hooks | dev mode only | plugin hooks |
| Review | `review.confidence_threshold`, `review.max_rounds`, `review.clean_rounds_to_stop` | stated as defaults | 80, 5, 2 |

## Dev mode

- **Setting:** the `## Dev mode` entry in the workspace's `AGENTS.md`: **Git version control** and **Dev mode**, both required and each on or off (dev mode on needs Git version control on; a missing or invalid value is an error, never off), plus the source and plugins folders. It is read and written only by the `howtoai` plugin's `devmode.py`; the user-level pointer `~/.claude/howtoai/install.json` says which workspace holds it. The contract is the `howtoai` plugin's `docs/dev-mode.md`.
- **Set by:** [INSTALL: Dev mode](../INSTALL.md#dev-mode) and [Install or link](../INSTALL.md#install-or-link).
- **Read by:** INSTALL only; the dev skills run the same from a link or from a plugin install. `scripts/install_check.py deps` reports each skill and agent link as `dev_links`.
- **Signs:** the existing entry; `devmode.py status`'s `needs_setting` (ask) and `git.problems` (show before linking); junctions in `~/.claude/skills` and symbolic links in `~/.claude/agents` that point into a workspace.
- **New option:** a different link layout is a change to the `howtoai` plugin's `devmode.py` and its `docs/dev-mode.md`, not to this plugin.
- **Search:** `rg -n "devmode|Dev mode|Git version control|git-version-control" INSTALL.md docs assets`.

## Settings folder

- **Setting:** none; the location is fixed: `<workspace>/AGENTS/settings/`, found in any letter case (`Agents/` counts). It holds `dev/` (`settings.json`, `install.md`, `replies.jsonl`, `lessons.md`), `workbooks/`, `deploy/` (`targets.json`, `approvals.json`, `log.md`), and the generated `cache/`. The user's defaults are in `~/.claude/howtoai/`.
- **Set by:** [INSTALL: The settings folder](../INSTALL.md#goal), and the move of an older install's folder in [Look up the project](../INSTALL.md#look-up-the-project).
- **Read by:** one helper per script, `state_dir()` and `agents_dir()` with `STATE_FOLDER`: [devcore.py](../skills/dev-core/scripts/devcore.py) (also used by both hooks), [workbook.py](../skills/dev-workbook/scripts/workbook.py), and [deploy.py](../skills/dev-deploy/scripts/deploy.py). The whole `AGENTS/` folder is tooling: the root-only skips in [build.py](../skills/dev-build/scripts/build.py), [targets.py](../skills/dev-test/scripts/targets.py), [testing_md.py](../skills/dev-test/scripts/testing_md.py), and `deploy.py`, and the `agents/` prefix checks in `devcore.py` and [dev_test_first.py](../hooks/dev_test_first.py).
- **Signs:** an existing `AGENTS/settings/`; a leftover `.howtoai/` or `AGENTS/howtoai/` from an older install, which nothing reads.
- **New option:** a different folder name is one change to `STATE_FOLDER` in the three scripts, the eval fixtures under `skills/*/evals/*/files/AGENTS/`, and every text this section's search finds.
- **Search:** `rg -n "AGENTS/settings|STATE_FOLDER|state_dir|agents_dir|settings/cache" skills hooks scripts INSTALL.md AUDIT.md docs assets README.md`.

## Dependencies and harness

- **Setting:** none; checked on every run by `scripts/install_check.py deps`.
- **Set by:** [INSTALL: Check dependencies](../INSTALL.md#check-dependencies).
- **Read by:** each skill's **Before you start** section: [dev-core](../skills/dev-core/SKILL.md#before-you-start), [dev-plan](../skills/dev-plan/SKILL.md#before-you-start), [dev-test](../skills/dev-test/SKILL.md#before-you-start), [dev-build](../skills/dev-build/SKILL.md#before-you-start), [dev-review](../skills/dev-review/SKILL.md#before-you-start), [dev-deploy](../skills/dev-deploy/SKILL.md#before-you-start), [dev-workbook](../skills/dev-workbook/SKILL.md#routes).
- **Required:** Python 3.10 or later, `git`, and the `howtoai` plugin's `grilling`, `skill-builder`, and `devmode.py` (found through its pointer; INSTALL stops without it), and `skill-audit`, which runs `AUDIT.md`. Per choice: `gh` signed in (GitHub tracker), `az` with the `azure-devops` extension signed in or the Azure DevOps MCP server (Azure DevOps tracker), the Atlassian MCP server (Jira), Docker (throwaway targets and Docker deploys), and `kubectl` (Kubernetes deploys).
- **Harness:** a shell and Python are required. Subagents run the goldfish reviewers in parallel; without them, [dev-plan's review](../skills/dev-plan/stages/review.md#run-a-round) and [dev-review's passes](../skills/dev-review/routes/review.md#pass-2-quality) stop and say why. The Artifact tool serves `plan.publish` `artifact`. Hooks need Claude Code. Claude Code (CLI and desktop) is verified; Cowork, claude.ai, and other agents are not.
- **New option:** a new required tool goes into `install_check.py` (`check_deps`) and the **Before you start** section of the skill that uses it.
- **Search:** `rg -n "compatibility:|Before you start" skills`.

## Tracker

- **Setting:** `tracker.kind` (`markdown`, `jira`, `github`, `azure-devops`), with `tracker.jira_project`, `tracker.jira_issue_type`, `tracker.github_repo`, `tracker.ado_org`, `tracker.ado_project`, `tracker.ado_work_item_type`, and `tracker.plan_item_type`. The user's default goes in `~/.claude/howtoai/dev-settings.json`, the project's choice in `AGENTS/settings/dev/settings.json`.
- **Set by:** [INSTALL: Per-user choices](../INSTALL.md#per-user-choices) and [Ask the project decisions](../INSTALL.md#ask-the-project-decisions).
- **Read by:**
  - [dev-plan split: Send to the tracker](../skills/dev-plan/stages/split.md#send-to-the-tracker), which holds every tracker's route;
  - [dev-plan accept: Show the plan](../skills/dev-plan/stages/accept.md#show-the-plan) and [Ask for approval](../skills/dev-plan/stages/accept.md#ask-for-approval);
  - [dev-review human review: Act on the choices](../skills/dev-review/routes/human-review.md#act-on-the-choices), for fix-later work items;
  - [dev-learn: Hand on and settle](../skills/dev-learn/routes/learn.md#hand-on-and-settle);
  - the [work item template](../skills/dev-core/assets/templates/wi.md) Tracker line, and the `append.wi` and `plan_item` keys in [dev-core: Record state](../skills/dev-core/SKILL.md#record-state).
- **Signs:** in [dev-core: Setup](../skills/dev-core/SKILL.md#setup): Jira keys such as `ABC-123`; `.github/ISSUE_TEMPLATE/`; `AB#123` mentions or a `dev.azure.com` or `visualstudio.com` remote for Azure DevOps.
- **New option** (for example GitLab or Linear):
  1. Add the value to `tracker.kind` and its keys to the schema, and a test in `skills/dev-core/evals/test_devcore.py`.
  2. Add its route to [Send to the tracker](../skills/dev-plan/stages/split.md#send-to-the-tracker): the tool (connector or CLI), the create and link calls, and what happens when it fails.
  3. Add its signs to [dev-core: Setup](../skills/dev-core/SKILL.md#setup), its name to the template's Tracker line, and its tool to `install_check.py`.
  4. Update the tracker lists in `skills/dev-plan/SKILL.md`, `skills/dev-review/SKILL.md`, `routes/human-review.md`, and `README.md`.
- **Search:** `rg -n "tracker|Jira|GitHub Issues|Azure DevOps|gh issue|az boards" skills README.md`.

## Plan format

- **Setting:** `plan.publish`: `auto` (an artifact where the harness has one, else an HTML file), `artifact`, `html-file`, `markdown` (no page), or `tracker` (a parent item with the work items as children; needs a tracker other than `markdown`, which `devcore.py setup` checks). `plan.md` is always the source, and approval is always asked in chat.
- **Set by:** [INSTALL: Per-user choices](../INSTALL.md#per-user-choices) and [Ask the project decisions](../INSTALL.md#ask-the-project-decisions).
- **Read by:** [dev-plan accept: Show the plan](../skills/dev-plan/stages/accept.md#show-the-plan) and [Change after approval](../skills/dev-plan/stages/accept.md#change-after-approval); [dev-plan split: Send to the tracker](../skills/dev-plan/stages/split.md#send-to-the-tracker) for the parent item. The page script `skills/dev-plan/scripts/plan_page.py` does not read the setting: accept calls it only for `artifact` and `html-file`.
- **Signs:** whether the harness has the Artifact tool; the tracker choice.
- **New option** (for example a Confluence page or a Word file): add the value to `plan.publish` in the schema, its route to [Show the plan](../skills/dev-plan/stages/accept.md#show-the-plan), its update rule to [Change after approval](../skills/dev-plan/stages/accept.md#change-after-approval), and its tool to `install_check.py`.
- **Search:** `rg -n "plan.publish|plan.html|PAGE render|plan_item" skills`.

## Plan folder

- **Setting:** `plan_folder`.
- **Set by:** stated as a default in [Ask the project decisions](../INSTALL.md#ask-the-project-decisions).
- **Read by:** [dev-core: Plan folder contract](../skills/dev-core/SKILL.md#plan-folder-contract), and every stage through `devcore.py`; the hooks allow it in [dev_test_first.py](../hooks/dev_test_first.py).
- **New option:** a plan folder outside the workspace is not supported; `devcore.py` refuses anything but a plain folder name.
- **Search:** `rg -n "plan_folder|dev-plans" skills hooks`.

## Test targets and production markers

- **Setting:** `environments.allow` (named targets tests may use) and `environments.deny` (production markers). Any target not on the allow list counts as production.
- **Set by:** [INSTALL: Ask the project decisions](../INSTALL.md#ask-the-project-decisions), as crucial items.
- **Read by:** [dev-test run: Classify the targets](../skills/dev-test/routes/run.md#classify-the-targets), the [safety rules](../skills/dev-test/references/safety-rules.md#the-rules-and-their-layers), `skills/dev-test/scripts/targets.py`, and the [dev_safe_target.py](../hooks/dev_safe_target.py) hook.
- **Also writes:** after a separate yes, deny rules for secret env files in the workspace's `.claude/settings.json` ([dev-core: Setup](../skills/dev-core/SKILL.md#setup), through `update-config`).
- **Signs:** `.env.example`, compose files, CI variables, and comments that name production or test hosts ([dev-core: Setup](../skills/dev-core/SKILL.md#setup)).
- **New option:** a new kind of match (besides host, database, profile, env) goes into the `environments.allow` description in the schema, `targets.py`, and the hook, with tests in `skills/dev-test/evals/` and `hooks/`.
- **Search:** `rg -n "environments\.|deny|allow list" skills hooks`.

## Test commands

- **Setting:** `testing.entry_points` and `testing.test_globs`.
- **Set by:** confirmed in [INSTALL: Ask the project decisions](../INSTALL.md#ask-the-project-decisions); otherwise [dev-test run: Find the entry points](../skills/dev-test/routes/run.md#find-the-entry-points) asks on the first run.
- **Read by:** [dev-test run](../skills/dev-test/routes/run.md#find-the-entry-points), [dev-test write](../skills/dev-test/routes/write.md#write-the-tests), `skills/dev-test/scripts/testing_md.py`, and the [dev_test_first.py](../hooks/dev_test_first.py) hook.
- **Signs:** test steps in CI files, `Makefile` test targets, and `test` scripts in package files.
- **New option:** a new result format besides TRX and JUnit XML goes into `skills/dev-test/scripts/results.py` with its tests.
- **Search:** `rg -n "entry_points|test_globs|TRX|JUnit" skills hooks`.

## Throwaway test targets

- **Setting:** `testing.ephemeral` (`docker` or `none`), with `testing.reruns_per_test` and `testing.max_reruns`.
- **Set by:** confirmed in [INSTALL: Ask the project decisions](../INSTALL.md#ask-the-project-decisions), from whether Docker runs.
- **Read by:** [dev-test run: Throwaway target](../skills/dev-test/routes/run.md#throwaway-target) and [Tear down](../skills/dev-test/routes/run.md#tear-down), `skills/dev-test/scripts/ephemeral.py`.
- **New option** (for example Podman or Testcontainers Cloud): add the value to `testing.ephemeral`, its commands to `ephemeral.py` with tests, and its tool to `install_check.py`.
- **Search:** `rg -n "ephemeral|EPHEMERAL|docker" skills/dev-test`.

## Test-first hook

- **Setting:** `testing.test_first` (`block`, `warn`, or `off`).
- **Set by:** stated as a default in [Ask the project decisions](../INSTALL.md#ask-the-project-decisions).
- **Read by:** the [dev_test_first.py](../hooks/dev_test_first.py) hook and [dev-test write: Check the start](../skills/dev-test/routes/write.md#check-the-start).
- **Search:** `rg -n "test_first|tests-first" skills hooks`.

## Build gate

- **Setting:** `build.gate`, with `build.max_fix_rounds`, `build.gate_timeout_seconds`, and `build.protected_globs`.
- **Set by:** confirmed in [INSTALL: Ask the project decisions](../INSTALL.md#ask-the-project-decisions); otherwise [dev-build: Set the gate](../skills/dev-build/routes/build.md#set-the-gate) proposes it on the first build.
- **Read by:** [dev-build: Set the gate](../skills/dev-build/routes/build.md#set-the-gate) and [Run the gate](../skills/dev-build/routes/build.md#run-the-gate), `skills/dev-build/scripts/build.py`.
- **Signs:** lint, format-check, and build or type-check steps in CI files, `Makefile` targets, and package scripts; workbook Commands statements second.
- **New option:** none needed; any command is allowed once the user confirms it.
- **Search:** `rg -n "build\.gate|protected_globs|max_fix_rounds" skills`.

## Deploy

- **Setting:** `deploy.entry_points` in the settings, and one entry per target in `AGENTS/settings/deploy/targets.json` (steps, rollback, health checks).
- **Set by:** [INSTALL: Deploy target](../INSTALL.md#deploy-target), which runs [dev-deploy: Set up a target](../skills/dev-deploy/routes/setup-target.md#find-what-exists) when the user wants it now.
- **Read by:** [dev-deploy: Check the gate](../skills/dev-deploy/routes/deploy.md#check-the-gate) through [Record and close](../skills/dev-deploy/routes/deploy.md#record-and-close), `skills/dev-deploy/scripts/deploy.py`, and the [dev_safe_target.py](../hooks/dev_safe_target.py) hook for production approvals.
- **Signs:** CI deploy jobs, `Makefile` targets, container files, Kubernetes manifests, Helm charts, Terraform folders, and the CLIs' current contexts ([dev-deploy: Find what exists](../skills/dev-deploy/routes/setup-target.md#find-what-exists)).
- **New option:** a new platform needs no skill change: its steps live in the target entry and its facts in a workbook ([Get the workbooks](../skills/dev-deploy/routes/setup-target.md#get-the-workbooks)).
- **Search:** `rg -n "targets.json|deploy\.entry_points|rollback" skills hooks`.

## Workbooks and versions

- **Setting:** `workbooks.technologies`; the Workbooks section of the workspace's `AGENTS.md`, whose text and check are in [AUDIT.md](../AUDIT.md#workbooks-text); the workbook files (base in `skills/dev-workbook/workbooks/`, user in `~/.claude/howtoai/workbooks/`, project in `<workspace>/AGENTS/settings/workbooks/`); the "Codebase versions" lines in each project `<tech>.md`; and version workbooks `<tech>@<key>.md`.
- **Set by:** [INSTALL: Workbooks](../INSTALL.md#workbooks), which runs [dev-workbook: Create](../skills/dev-workbook/routes/create.md#steps), [Record a version](../skills/dev-workbook/routes/record-version.md#steps), and [Audit](../skills/dev-workbook/routes/audit.md#steps).
- **Read by:** every agent through [dev-workbook: Read the workbooks](../skills/dev-workbook/SKILL.md#read-the-workbooks) (the goldfish preload it with `skills: dev-workbook`; loading writes `AGENTS/settings/cache/workbook-search.md` and `workbook-sources.md`, kept out of Git); [dev-workbook: Resolve](../skills/dev-workbook/routes/resolve.md#steps), called by [dev-build: Consult the workbook](../skills/dev-build/routes/build.md#consult-the-workbook), [dev-review: Consult the workbook](../skills/dev-review/routes/review.md#consult-the-workbook), dev-plan, dev-test, and dev-deploy; the `goldfish-compliance` agent checks the recorded versions against the code.
- **Signs:** manifests such as `*.csproj`, `global.json`, `package.json`, `pyproject.toml`, `Dockerfile`, and `*.tf`, with the version each declares.
- **New option:** a new technology needs no skill change: Create makes its workbook. A new subject tag, or a new section in every workbook, is a change to `skills/dev-workbook/references/format.md` and `scripts/workbook.py`.
- **Search:** `rg -n "workbook.py resolve|Codebase versions|record-version" skills agents`.

## Hooks and hook rules

- **Setting:** `hook_rules`; in dev mode, the three hooks registered in `~/.claude/settings.json` by absolute path (two `PreToolUse`, and `dev_reply_log.py` under `UserPromptSubmit`); in plugin mode, the plugin's [hooks.json](../hooks/hooks.json).
- **Set by:** [INSTALL: Install or link](../INSTALL.md#install-or-link); `hook_rules` are added later by dev-learn, after approval.
- **Read by:** [dev_test_first.py](../hooks/dev_test_first.py), [dev_safe_target.py](../hooks/dev_safe_target.py), and their shared [common.py](../hooks/common.py). [dev_reply_log.py](../hooks/dev_reply_log.py) writes `AGENTS/settings/dev/replies.jsonl` (a hash and time per user prompt, never the text), which `devcore.py`'s state patch reads to check an approval `"by": "user"`; without it, such approvals are recorded `"unverified": true`.
- **New option:** a new hook goes into `hooks/` and `hooks.json`, and into the dev-mode registration step of [Install or link](../INSTALL.md#install-or-link).
- **Search:** `rg -n "hook_rules|dev_test_first|dev_safe_target|dev_reply_log|replies.jsonl" skills hooks INSTALL.md`.

## Review defaults

- **Setting:** `review.confidence_threshold`, `review.max_rounds`, and `review.clean_rounds_to_stop`.
- **Set by:** stated as defaults in [Ask the project decisions](../INSTALL.md#ask-the-project-decisions).
- **Read by:** [dev-plan review: Stop rule](../skills/dev-plan/stages/review.md#stop-rule), [dev-review: Tally and hand on](../skills/dev-review/routes/review.md#tally-and-hand-on), and `skills/dev-core/scripts/findings.py`.
- **Search:** `rg -n "confidence_threshold|max_rounds|clean_rounds" skills`.

## Add an option no setting covers

When a client's need fits none of the values above:

1. Find its section here and run its **Search**, so every file that must change is listed.
2. Hand the change to `skill-builder` as a change to the `howtoai-dev` plugin, with the section's **New option** steps as the starting plan. It plans, asks for approval, builds, and tests it.
3. After it lands, rerun [INSTALL](../INSTALL.md#change-a-decision-later) to pick the new value.

Never edit a skill file only for one install: in plugin mode the next update overwrites it, and in dev mode it changes the skill for every workspace.

## Keep this index current

`py -3 -I -B "<plugin>/scripts/install_check.py" index`, where `<plugin>` is this plugin's folder, checks that every link and heading here still exists and that every setting key named here is in the schema; it lists every dotted name it skipped. Run it in the Test of every change to this plugin, and INSTALL runs it in its Verify step; a failure means this index needs the same change.
