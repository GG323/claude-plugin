---
name: skill-builder
description: Create, improve, or repair a focused agent skill (SKILL.md plus optional supporting files) for a repeatable technical or nontechnical task. Use when asked to make a skill, turn a workflow or prompt into a skill, write or update a SKILL.md, revise a skill's workflow or supporting material, or fix a skill's behavior after using it. Entry point for all skill work; hands coding skills, creative fine-tuning loops, and stubborn repeated failures to skill-creator.
---

# Skill builder

## Contents

- [Vocabulary](#vocabulary)
- [The process](#the-process)
- [Core rules](#core-rules)
- [Output contract](#output-contract)
- [Working memory and sources](#working-memory-and-sources)
- [Idea-generation option](#idea-generation-option)
- [Feedback note for target skills](#feedback-note-for-target-skills)
- [Supporting files](#supporting-files)
- [Skills and agents](#skills-and-agents)

## Vocabulary

Every file in this skill uses these terms, one name per thing.

| Term | Meaning |
| --- | --- |
| **process** | This skill's whole lifecycle: Recall → Plan → Build → Test → Learn, for new skills, changes, and problems alike. |
| **stage** | One of the five parts of the process; each is one file in `stages/`. |
| **section** | A heading inside a file. |
| **step** | A numbered action inside a section. |
| **route** | A branch chosen at a decision, such as the main route or the `skill-creator` route. "Path" means only a file or folder path. |
| **handoff** | Passing work to another skill, such as `skill-creator`. The **brief** is what that skill receives. |
| **delivery** | Giving the user a deliverable together with its report. For this skill, the deliverable is the target skill. |
| **target skill** | The skill being created or changed. |
| **workflow** | The target skill's own procedure. This skill's procedure is the process. |
| **instructions** | The text of a skill that tells the main agent what to do. |
| **rule** | A standing constraint that applies to every stage, listed in [Core rules](#core-rules). |
| **check** | A read-only verification of files; nothing is run. |
| **test** | Running the target skill on a prompt. A **test case** is a test saved in the target skill's `evals/` folder. |
| **deliverable** / **report** | The target skill's main output / the status message about it. |
| **loop** / **round** | `skill-creator`'s repeated test-and-improve cycle / one pass through it. |
| **main agent** / **subagent** | The agent running a skill / a helper agent it starts. |
| **registry** | The list of target skills this skill has built, changed, or retired, in [state/registry.md](state/registry.md). |
| **lesson** | One recorded finding from past runs, in [state/lessons.md](state/lessons.md). |
| **recall note** | The short summary of relevant past work that Recall writes for the later stages. |

## The process

1. **Recall** — For every request, first read [stages/recall.md](stages/recall.md). Search past target skills and lessons, write the recall note, and go to Plan.
2. **Plan** — Read [stages/plan.md](stages/plan.md). Interpret the problem, inspect context, choose the route (the main route or a handoff to `skill-creator`), draft the plan, and get the user's explicit approval.
3. **Build** — Only after approval, read [stages/build.md](stages/build.md) and create or revise the target skill. If the plan changes materially, return to Plan for approval first.
4. **Test** — Read [stages/test.md](stages/test.md). Run checks, propose risk-rated tests, run only approved tests, and deliver the target skill.
5. **Learn** — Every run ends with [stages/learn.md](stages/learn.md): update the registry and lessons, promote proven lessons with the user's approval, and clean up.

There is no separate fix stage. A change or a reported problem goes through the same process as a new skill, with a plan sized to the change; problems Test finds are fixed in Test's automatic fix loop when they stay within the approved plan, and go back to Plan otherwise.

The rules below apply to every stage. Stage files refer to them instead of repeating them.

## Core rules

- **Infer, then ask.** Infer ordinary details from the request, project instructions, existing files, and examples. Ask only about unknowns that materially affect scope, behavior, output, permissions, side effects, or placement. Group related questions in one message.
- **Code before AI for deterministic work.** Before assigning repeatable, deterministic work to instructions, consider existing code or an official API, SDK, CLI, or integration. Keep AI for judgment and synthesis.
- **Start small.** Make the first version focused and useful. Add inputs, runtime questions, templates, examples, scripts, and folders only when the workflow benefits. Never create empty or speculative folders.
- **Current behavior only.** When revising a skill, remove obsolete instructions, files, and references within the authorized skill; do not leave change notes or compatibility fallbacks. Preserve unrelated files and history.
- **Portable core, verified harness.** Follow the [Agent Skills specification](https://agentskills.io/specification) for the portable core. Verify each target harness's discovery paths and optional features; do not promise universal behavior.
- **Target-repository conventions win.** Follow the target repository's `AGENTS.md`, `CLAUDE.md`, or equivalent for naming, documentation structure, and packaging. The exception is files whose format is fixed by a tool or by the deliverable — test-case files in `evals/` (`prompt.md`, `case.yaml`, graders, input files), run state in `state/` (logs, registries, lessons in the skill's own format), templates in `assets/` that are copied into outputs, and deliverables such as email drafts or newsletter copy. They follow their own format, because added titles or contents lists would break them; Test records them as exempt.
- **Missing tools.** Whenever the work needs a tool, library, or connector — to build, check, or test the target skill — first check that it is available:
  - **Available:** use it.
  - **Missing, but obtainable** from its official source or the platform's package manager (for example, `winget` or `pip`): install it, continue, and name it in the report.
  - **Missing and not obtainable** (no trusted source, no permission, or a connector only the user can turn on): stop that part, and propose another way that needs only the main agent — for example, a standard-library script, doing the step without the tool, or a manual step for the user — then continue with the one the user picks.
- **Dates and times from the system.** Whenever a date, weekday, time, time zone, or interval matters — today's date for a registry row, the age of a lesson, a test's "as of" date, a deadline in a target skill — read it from the system clock (for example, `date`, PowerShell `Get-Date`, or Python `datetime`) and compute weekdays and date arithmetic with code. Never infer them, because a guessed date looks right and is often wrong.
- **Honest reporting.** Never claim an unrun check or test passed.

## Output contract

Every target skill must define its deliverable separately from its report, and state:

- Format, audience, required content, and structure.
- Delivery: returned inline, saved to a named location, or both.
- A practical success and safety check, and what the main agent reports after delivery.

**Standardized outputs.** A deliverable that reads like a document, such as a written report, summary, brief, overview, or fact or data sheet, gets a standard shape, whether it is saved as a file or returned in chat. Then every run looks the same, readers know where to look, and runs can be compared. These are defaults that point the design in the right direction, not a fixed template: Plan adapts them to the target skill and states any departure with its reason.

- **Structure:** the same sections in the same order, with the same labels and fields, and a stated placeholder for missing data (for example, "none found") instead of a dropped section. When the structure is longer than a few lines, keep it as a template in `assets/` or a sample in `examples/`, so the main agent copies it instead of reinventing it each run.
- **Presentation:** show data in the form that reads fastest. Use tables for records and comparisons; charts or simple graphics for trends, shares, timelines, and progress; key figures up front; and prose for reasoning, context, and caveats. Choose by the data, and leave out a table or chart that adds nothing to the text. Where the harness offers page-design or chart skills, depend on them by name instead of writing styling rules into the target skill.
- **Format:** artifact-compatible by default, so the output opens anywhere and can be shown or shared as an artifact where the harness offers one. A file deliverable defaults to one self-contained HTML file, with styles and graphics inline and no local dependencies. A deliverable returned in chat uses Markdown, with tables where they fit. Use another format when the user asks for it, when the destination needs it, or when a tool fixes the format.

Messages, drafts, code, and other deliverables with conventions of their own keep those conventions. The report after delivery also keeps one short, fixed shape across runs.

## Working memory and sources

- **Static material.** `references/` holds documentation the main agent reads on demand; `assets/` holds templates and files copied into outputs; `examples/` holds complete samples. Treat these as read-only during normal runs. In `skill-builder` itself, only [Learn](stages/learn.md) changes `references/`, and only with the user's approval.
- **Persistent state.** If the target skill must remember things across runs (for example, a decision log or a history of past outputs to avoid repeats), plan a `state/` folder in the skill, or a project path the user chooses when the skill folder may not be writable (plugin installs, shared or read-only locations). Define what it holds, how it is seeded, and how runs update, replace, and prune it. If no state is needed, say so. Records of individual runs (plans, journals, logs, histories of what a run produced) belong next to the run's outputs instead, with a prune rule, so test runs never share history with real runs.
- **Sources.** Prefer an authoritative web link or local directory path over copying changeable material. Check access when the source is needed. If it fails, ask the user to restore or update it; do not silently use a stale copy or guess a replacement. Keep local copies only when the file is the maintained artifact or a justified snapshot.

## Idea-generation option

Some target skills produce creative or open-ended outputs (names, copy, concepts, designs, strategies) where comparing several distinct candidates improves the result. For those, Plan may recommend a multi-generator model:

- Several separate subagents (five is a good starting point), each returning exactly one distinct idea that takes a different viable direction, adapted to the user's case — not a rewording.
- When the plan has reference materials, a mix of reference-grounded and deliberately original generators (for example, 3/2). Originality never permits breaking user constraints, safety requirements, or facts.
- The cheapest model that can do the job well; use a stronger model when quality depends on it.
- A main-agent **Choose one** step: compare, deduplicate, and choose or combine according to planned criteria. Return candidates to the user only when the plan calls for options.

Do not use it for procedural, deterministic, or single-correct-answer outputs, or when the output must return exact items from a fixed list. When recommended, disclose the count, split, model choice, and selection method in the plan and invite adjustment. If the harness cannot run subagents, say so in the plan and ask how to proceed instead of silently reducing the batch.

## Feedback note for target skills

Every target skill has a short **Feedback** section, placed last before `Skills and agents`, telling the main agent to send requested changes or reported problems to the `skill-builder` skill by name (for example, `/skill-builder` in Claude Code), not by file path. If `skill-builder` is unavailable, the main agent edits the skill directly: it agrees the change with the user first, keeps it as small as the problem needs, and checks the skill afterwards.

## Supporting files

- [stages/recall.md](stages/recall.md), [stages/plan.md](stages/plan.md), [stages/build.md](stages/build.md), [stages/test.md](stages/test.md), [stages/learn.md](stages/learn.md) — read only the file for the current stage.
- [state/registry.md](state/registry.md) and [state/lessons.md](state/lessons.md) — this skill's own knowledge store: written only by Learn, searched by Recall.
- [references/skill-types.md](references/skill-types.md) — requirements for every target skill and for each skill type; read in Plan, written in Build, checked in Test.
- [references/test-cases.md](references/test-cases.md) — the format for test cases saved in a target skill's `evals/` folder; used in Test.
- [examples/example-target-skill.md](examples/example-target-skill.md) — a short, complete sample of a target skill's `SKILL.md`; adapt its shape, not its content.
- The official Claude Code [skills](https://code.claude.com/docs/en/skills) and [subagents](https://code.claude.com/docs/en/sub-agents) docs — the authoritative source for harness-specific features.

Resolve links to files inside this skill relative to this directory. If a bundled file is missing, stop and ask the user to restore it or give its new location; do not skip it or guess its contents.

## Skills and agents

- [Recall](stages/recall.md), [Plan](stages/plan.md), [Build](stages/build.md), [Test](stages/test.md), [Learn](stages/learn.md) — this skill's stages.
- `skill-creator` — receives coding skills, creative tuning, and repeated failures from [Plan](stages/plan.md#choose-the-route).
- No custom agent definition is required. Target skills that use the idea-generation option rely on the harness's built-in subagents unless the plan says otherwise.
