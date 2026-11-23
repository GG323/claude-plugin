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

Version 0.11.0 holds the install procedure, the plan, test, build, review, learn, and deploy stages, two safety hooks, the foundations, and the workbooks:

- `dev-plan` - the entry point: the install's line in your `AGENTS.md` starts every code change with it, and you can also say "plan <your change>". It sizes the change Small, Medium, or Large from the code, asks the open decisions top-down with recommendations, drafts a plan with a Verification section, has the goldfish agents review it in a scored loop, splits large work into standalone work items (Markdown, Jira, GitHub Issues, or Azure DevOps, created only after you approve the list), and asks for your approval on a plan page.
- `dev-test` - tests before code, and safe test runs: after a plan's approval it turns each Verification criterion into a test and proves it fails first; after the build it classifies every database, queue, API, and server the tests could reach (unknown counts as production and stops the run), runs the project's own test commands, finds flaky tests, uses a throwaway Docker container only after you approve it, and rewrites the Latest run section of each `TESTING.md`.
- `dev-build` - the build stage: once a work item's tests fail, it writes the smallest change that makes them pass (a reuse-first ladder: skip what is not needed, reuse existing code, the standard library, or an installed dependency before writing new code), follows the workbook rules, traces every changed hunk to an acceptance criterion or test-map row, and passes a gate of your lint, format, and type-check commands, then the work item's tests. It leaves `build-<n>.md` with a Skipped or unchecked footer for review, never edits tests or CI, never adds a dependency without asking, and commits nothing. It also applies review findings you mark fix now.
- `dev-review` - the review stages: context-free goldfish reviewers check the built change, first against the plan and work items, then for correctness, tests and gate integrity, security, performance, and compliance with the workbooks and instruction files; a scorer and a verifier rate and challenge each finding; it reruns the tests and adds temporary tests itself; `review-<n>.md` ranks the findings, with low-confidence ones, refuted ones, and ones on unchanged lines in an appendix. You then mark each finding fix now, later (a new work item), or decline, and fixes go back through `dev-build` and `dev-test` and a re-review. When you say a finding is wrong, it proposes the smallest fix to its own rules, after your approval.
- `dev-deploy` - deploys, releases, or rolls back an app to a target you name (a local Docker or Kubernetes cluster, a server, a cloud), with that target's own tools. No target is built in: the first deploy to one sets it up after your yes (it finds the existing deploy files and CLIs, gets `dev-workbook` to find or make each technology's workbook, and records the steps, rollback, and health checks in `.howtoai/deploy/targets.json`). Every run checks a gate, shows its plan with the rollback first, runs each production step only after your yes (the approval, with its exact command and a short expiry, is what lets `dev-safe-target` pass it), watches the run, checks the result, keeps a deploy log, and proposes fixes to its own rules when a step fails or you correct it. It works on its own in any workspace, and as the last stage of this process.
- `dev-learn` - the learn stage, after each human review: for the Critical, Major, declined, and repeated findings it names the stage that let each through, with quoted evidence, writes `learn-<n>.md` with the smallest fix at the lowest level that resolves it (a workbook or reference file first, then a goldfish, then a skill file only with proof that neither works), keeps the project lessons log `dev-plan` reads (a lesson leaves the log once its fix is applied or declined), lists where docs and code disagree, and hands each fix you approve to `dev-workbook`, the project's hook rules, or `skill-builder`.
- Hooks: `dev-test-first` (only test files change while a change is at stage tests-first; no CI edits during test stages) and `dev-safe-target` (denies commands that reach a production marker; asks before destructive commands and migration edits). `dev-test-first` acts only while a change is at a test or build stage; `dev-safe-target` applies your deny markers wherever the dev settings name them, and its destructive checks only in workspaces with project dev settings.
- `dev-core` - an internal skill with the settings and their setup, the plan folder script (`state.json` per change, `dev-plans/INDEX.md`), the document templates, and `findings.py`, which tallies review findings.
- `dev-workbook` - the keeper of technology documentation: one workbook per language or tool, in a fixed format with stable statement IDs and three layers (base, user, project), each statement tagged, with `workbook.py` (open, resolve, validate, propose, skeleton, audit, check-skills). It is the one way agents read workbooks: every MUST rule on load, and the rest by tag search. `AUDIT.md` holds what an install must leave true, checked by the install and by `skill-audit`. It ships base workbooks for C#, .NET, Docker, and Terraform written from their official documentation, and a small Python one of rules found in use, each with its source.
- Plan-review agents with no conversation context ("goldfish"): `goldfish-comprehension`, `goldfish-zoom-out`, `goldfish-critic`, `goldfish-readiness`. Each starts from its own viewpoint but reports every problem it finds and marks what lies outside the change; `dev-plan` sorts them and brings findings outside the change to you.
- Code-review goldfish: `goldfish-spec`, `goldfish-correctness`, `goldfish-tests`, `goldfish-security`, `goldfish-performance`, searching wide the same way.
- `goldfish-compliance`, in both reviews: checks the change against the workbooks and the workspace's instruction files (AGENTS.md, CLAUDE.md, README, CONTRIBUTING), and whether those files are out of date, against the code and against official docs online or through documentation connectors (read-only).
- `goldfish-scorer` (confidence score per finding) and `goldfish-verifier` (tries to refute Critical and Major findings).

## Where it keeps data

- `<workspace>/dev-plans/` - one folder per change (plans, test maps, test run reports, build records, review docs) and `INDEX.md`. The plugin never deletes anything there; clean up old changes yourself.
- `<workspace>/.howtoai/dev/settings.json` - project settings; `~/.claude/howtoai/dev-settings.json` - your defaults across projects. No secrets are stored.
- `<workspace>/.howtoai/workbooks/` - the project's own workbook statements; `~/.claude/howtoai/workbooks/` - yours across projects. Both are written only after you approve a statement.
- `TESTING.md` in each test folder of your code: you own its base part; `dev-test` rewrites only its Latest run section.

## Install

Ask your agent to follow [INSTALL.md](INSTALL.md). It checks the dependencies (the `howtoai` plugin for `skill-builder` and `grilling`, Python 3.10 or later, git, and the tools your choices need), asks whether to keep the plugin in workspace files under version control (dev mode) or install it normally, and then asks every per-user and per-project decision:

- the tracker for work items: Markdown files, Jira, GitHub Issues, or Azure DevOps Boards;
- the plan format, where plans are shown for approval: an artifact, an HTML file, the Markdown plan itself, or a parent item in the tracker;
- allowed test targets and production markers, test and gate commands, and throwaway Docker targets;
- workbooks for each technology and code-project version, and an optional deploy target.

It writes only settings, workbooks, deploy targets, links, and an install record, each after your yes, and ends with a double check by `skill-builder`. [docs/install-index.md](docs/install-index.md) lists every install requirement, the files that read it, and what to change when a client needs an option that is not there yet.

The plain plugin install, without the setup, is:

```bash
claude plugin install howtoai@howtoai-mods
claude plugin install howtoai-dev@howtoai-mods
```

## Attribution

`dev-plan` takes ideas, not text, from [obra/superpowers](https://github.com/obra/superpowers) (MIT), [automazeio/ccpm](https://github.com/automazeio/ccpm) (MIT), and Anthropic's `feature-dev` plugin (Apache 2.0, the three architect stances). `dev-test` and the hooks take ideas, not code, from obra/superpowers (test-driven development), [nizos/tdd-guard](https://github.com/nizos/tdd-guard) (MIT, an edit guard judged against the test state), and [a-abdellatif98/db-migration-guard](https://github.com/a-abdellatif98/db-migration-guard) (MIT, risk tiers for migrations and a confirm marker), rewritten as standard-library Python with no model calls.

## Skills and agents

- `dev-plan` - plans a change and gets it approved.
- `dev-test` - writes tests first and runs them safely.
- `dev-build` - builds each work item and applies fix-now review findings.
- `dev-review` - reviews the built change and records your choices.
- `dev-learn` - finds why serious, declined, and repeated findings got through and routes the fixes you approve.
- `dev-deploy` - deploys to a target you name, set up on first use, with an approval per production step.
- `dev-core` - shared settings, plan folder state, templates, and the findings tally.
- `dev-workbook` - technology workbooks and their script.
- `goldfish-comprehension`, `goldfish-zoom-out`, `goldfish-critic`, `goldfish-readiness`, `goldfish-scorer`, `goldfish-verifier`, `goldfish-spec`, `goldfish-correctness`, `goldfish-tests`, `goldfish-security`, `goldfish-performance`, `goldfish-compliance` - review agents.
- Hooks `dev-test-first` and `dev-safe-target` in `hooks/`.
