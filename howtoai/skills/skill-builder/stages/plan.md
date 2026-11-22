# Plan the skill

## Contents

- [Start from the request](#start-from-the-request)
- [Inspect the target context](#inspect-the-target-context)
- [Grill the request](#grill-the-request)
- [Choose the route](#choose-the-route)
- [Decide the design](#decide-the-design)
- [Draft the plan](#draft-the-plan)
- [Get approval before building](#get-approval-before-building)
- [Supplied change plan](#supplied-change-plan)
- [Skills and agents](#skills-and-agents)

## Start from the request

Plan interprets the problem: what the target skill is for, and how to get there. It is entered from [Recall](recall.md) for every request — a new target skill, a change, or a reported problem — and from [Test](test.md#run-and-deliver) when a problem found there changes the approved plan, or survives two fixes and the user chooses to revise the plan. Every change is planned here, whatever its size; a small change simply gets a short plan. Use the recall note throughout: apply its lessons, and do not repeat what it lists to avoid.

Use the request as the starting point, with the answer to the goal question when [Recall](recall.md#when-to-use-this-stage) had to ask it. If the request already explains the task or outcome, reflect it back briefly instead of asking again.

The request can be a new target skill, a change, a problem, or a verification:

- **A change** (new or different behavior): capture what should change and why. Do not frame it as a fault to diagnose.
- **A problem** (something went wrong): capture what was expected, what happened, and what was already tried; check the recall note for known causes and fixes of the same symptom, and for fixes that already failed; and identify the cause: the instructions or workflow, the supporting material, or both. If a required link or path is unavailable, ask the user for a working source.
- **A verification** ("make sure it works", no change named): capture what must work; it takes the verification-only route in [Choose the route](#choose-the-route).
- **A supplied change plan** (another skill hands over the target files, the cause with evidence, and the smallest change): go to [Supplied change plan](#supplied-change-plan).

For a change or a problem, you may reproduce the bug or probe the current behavior before approval, because a cheap probe often finds the cause and extra bugs. Probe only the user's own work; a third-party target is probed only after `skill-finder` has vetted it. Work on scratch copies in the [sandbox](../SKILL.md#vocabulary) only; a probe never changes the target skill or the user's files and never sends anything.

If the request would break a platform's terms (for example, automated messaging or scraping that a site forbids) or the [side-effect safety](../references/skill-types.md#every-target-skill) rules (for example, sending, posting, or deleting without the user's approval), say so before any plan: the risk, what will not be built, and a safer alternative, such as drafts the user sends. Continue only with a version the user accepts; if they accept none, go to [Learn](learn.md) to record why.

## Inspect the target context

Read relevant project instructions, existing skills, configuration, source material, and examples before asking about details.

- Technical workflows: identify the stack, tools, supported versions, commands, and safe verification options.
- Nontechnical workflows: identify the audience, source material, output formats, voice, policies, and examples of finished work.
- Identify the target harness only as far as needed for format, location, tools, and invocation, and the platforms the target skill must run on.
- List the skills and connectors the harness already offers that the target skill could depend on. Loading a tool's description to see what it does is fine; do not call a connector that reads private data until the plan is approved.
- Check that the tools and libraries the target skill will need are available here, and apply the [missing-tools rule](../SKILL.md#core-rules) to any that are not; put installs and proposed alternatives in the plan.
- Reuse candidate: when the plan reuses or adapts a candidate (a skill, a tool such as a plugin, agent, command, hook, mod, or MCP server, or a procedure) from the recall note or from a change request about a third-party tool, whatever its mark and whether or not it is already on this computer, do not download, copy, or install it during Plan. The plan states that [Build](build.md) runs the `skill-finder` skill's vetting (its "Vet and install a candidate" section: isolated copy, safety review, `environment-audit` candidate run, install approval, and check of the installed copy), and that installing is a second approval after the vetting report. `skill-finder` owns those checks; this skill never runs, shortens, duplicates, or skips them, and never treats a candidate as checked on other evidence.
  - If the candidate fails vetting or the user declines it, nothing is installed: have [Learn](learn.md) record it as an `avoid` lesson with the reason from the vetting report, so Recall does not offer it again, and ask the user whether to build a new target skill instead, which returns to [Start from the request](#start-from-the-request).
  - Reusing a candidate as published creates no skill files: Build runs only the vetting and the install, [Test](test.md) checks that it loads and runs one safe test, and the plan drops the items in [Draft the plan](#draft-the-plan) that do not apply. Adapting it is a change to the copy `skill-finder` vetted, which it places in the build destination, and follows the usual Build; the plan names that destination, because the vetted copy becomes the user's own skill there and the third-party original stays untouched.
- Existing skill: read it and its linked files in full. Trace incoming and outgoing references to related skills and documentation, and note coordinated changes.

Treat details inferred from project evidence as working assumptions and list them in the plan rather than asking about each one.

## Grill the request

Read [references/grilling.md](../references/grilling.md) and run the `grilling` skill's method with its items, for a skill, a tool, or an automated process alike. It asks the crucial items that the request, the conversation, and the context just inspected do not answer, in short rounds of numbered questions with recommended answers, and states the rest as defaults. Wait for each round's answers; stop when no crucial item is open. For a change, grill only what the change touches.

Carry the result into [Draft the plan](#draft-the-plan): answers become plan items, defaults go under the working assumptions marked **Assumed — tell me if wrong**, and any crucial item still open becomes a question in [Get approval before building](#get-approval-before-building), with its safest recommendation. Do not ask the same question again at approval. The Reuse decision is asked with the plan, not here.

## Choose the route

Find the target's kind in [Deliverable kinds](../references/skill-types.md#deliverable-kinds); the kind and the request decide the route.

**Coding skills, creative tuning, and repeated failures** take the main route, with these additions:

- **Coding skill** — a target skill whose main deliverable is code (writing, changing, or testing it) or findings about code (reviewing it). The plan applies [Coding](../references/skill-types.md#coding): tests check its code statically and never run the user's code; code the target skill writes runs only on a copy. A skill that bundles helper scripts to do other work, such as sorting files, is not a coding skill.
- **Creative tuning** — further rounds of tuning the quality, tone, or style of a creative output. The plan names the qualities to tune, what stays fixed, and the sample prompts the user compares (at most 3); each round is a change through Build and Test, at most 2 rounds unless the user asks for more.
- **Repeated failure** — a problem that survived two fixes, which Test stops on and reports to the user; it comes here only when the user chooses to revise. If the goal, scope, or output contract no longer match what the user wants, revise them; otherwise plan a different fix from the test evidence, never a third try of the same one.

**Handoffs.** A hook or settings automation ("whenever X") goes to `update-config`, and a mod to `plugin-authoring`, because they own those formats. The plan, its approval, and Test are the same as on the main route; only the writing is handed off, in Build's [Hand off or skip writing](build.md#hand-off-or-skip-writing).

**Verification only.** A request to confirm that an existing target works ("make sure it works"), with no change named, has nothing to build. Its plan is a short list, as for a small change: what is verified and the test depth tier; for a third-party target, that `skill-finder` vets it first, report-only. Build writes nothing, and any problem the tests find becomes a change that returns here.

The main route also takes everything else, including creating a creative skill in the first place, document, communication, media, research, and data skills, and subagents, plugin bundles, and procedures.

| Case | Route |
| --- | --- |
| Verification only | [Draft the plan](#draft-the-plan); after approval, Build's [Hand off or skip writing](build.md#hand-off-or-skip-writing) sends it to Test |
| Hook or settings automation, to `update-config`; mod, to `plugin-authoring` | [Decide the design](#decide-the-design); after approval, Build hands it off |
| A new MCP server or connector, when `skill-finder` finds none | Not built: say so, and offer what can be built instead, such as a skill that uses an existing connector |
| Everything else | [Decide the design](#decide-the-design) |

If `update-config` or `plugin-authoring` is unavailable, Build writes the change itself from the docs that [Deliverable kinds](../references/skill-types.md#deliverable-kinds) links.

## Decide the design

Apply the rules in [SKILL.md](../SKILL.md) to decide the items below. For a change, re-decide only what the change touches; the rest stays as the target has it.

- **Reuse decision** — required for every new target skill or remake, decided first, because a fitting existing skill, tool, or procedure makes the rest of the design unnecessary. Draft the design's outcome, inputs, central steps, and deliverable, then judge each candidate from the recall note's `skill-finder` table against that draft, not only against the request: a candidate that looked related can cover the drafted design, and one that looked like it covered can lack a central step. When the draft names a central step the original search did not, run `skill-finder` again with the draft as the need. The plan then shows the user, for every candidate that covers or partly covers the draft, what it does, what it lacks against the plan, its mark, its source link, and what reusing it takes (install as is, or adapt; always after `skill-finder`'s vetting, as [Inspect the target context](#inspect-the-target-context) says). The user must answer explicitly: reuse one, adapt one, or build new. With no such candidate, the plan says "No existing skill, tool, or procedure covers or partly covers this plan", names the searched sources and the index date, and any source that failed. Never skip this decision or answer it for the user, including when the user seems keen to build.
- **Skill type and requirements** — read [references/skill-types.md](../references/skill-types.md). Identify the target skill's type or types, then decide each applicable requirement from its [Every target skill](../references/skill-types.md#every-target-skill) section and from each matching type section.
- **Thinking effort** — for each step, a script, a cheap subagent, the main agent, or high effort, per item 10 of [Every target skill](../references/skill-types.md#every-target-skill).
- **Look** — for a deliverable people look at, an `assets/` template built once with `skill-design` (house or client design) and filled each run, per item 11; or, for a surface `skill-design` does not cover, the format skill and a note that no design review runs.
- **Placement** — the location for the target's kind in [Deliverable kinds](../references/skill-types.md#deliverable-kinds). Default: the project folder when it uses this workspace's files, personal (`~/.claude/`) otherwise, and a plugin only for the HowToAI pack; state the default and its reason in the plan. In dev mode, a personal target's place is the source folder, and the plan names both that path and the link Build creates.
- **Automation** — whether existing code or an official integration should handle any repeatable, deterministic part. Account for access, cost, data handling, and side effects. Prefer the project's stack; if none is set and a script is justified, default to Python when available.
- **Output contract** — deliverable, audience, format, delivery, and success check, per [Output contract](../SKILL.md#output-contract). For a document-like deliverable, also decide its standard structure, which data goes in tables or charts, and its format, starting from the [standardized-output defaults](../SKILL.md#output-contract) and giving the reason for any departure.
- **Memory and sources** — whether `references/`, `assets/`, `examples/`, or persistent `state/` are needed, and which links or paths the target skill relies on, per [Working memory and sources](../SKILL.md#working-memory-and-sources). For existing reference files, decide whether they stay in place or move into the target skill's `references/` folder.
- **Idea generation** — whether the output is creative or open-ended enough to benefit from the [idea-generation option](../SKILL.md#idea-generation-option). Default to no for procedural or deterministic outputs.
- **Stages** — whether to split the workflow into stages. Split only when it has distinct stages, each with its own inputs, decisions, and outputs, such as gather → draft → review. Keep it in `SKILL.md` when it is short or linear enough to read in one pass; splitting is for clarity, not a default. Build has the rules for writing a split workflow.

## Draft the plan

Write the plan as `plan.json` in the [sandbox](../SKILL.md#vocabulary), using the keys documented at the top of [scripts/render_plan.py](../scripts/render_plan.py); [examples/plan-sample.json](../examples/plan-sample.json) is a filled example. Include only the applicable items. The plan covers whatever is being built or changed (a skill, a tool, or a procedure), so it names it by its kind, never "skill" alone when a tool or procedure fits. Write it in plain words at the user's technical level, as [references/grilling.md](../references/grilling.md) sets out: the first six sections are for the user; the technical details are for whoever builds or checks it.

- **Summary** (`summary`): the goal and who uses the result, when it starts, from where to where, and from what to what. For a change or a problem: what changes from today.
- **Reuse decision** (`reuse`), for a new target skill or remake only: each candidate that covers or partly covers the drafted design (name, kind, level against the plan, what it does, what it lacks, mark, source, what reusing it takes), in plain words at the user's level ("a pack of 27 tools", not "a plugin"), and the recommendation; or the "No existing skill, tool, or procedure covers or partly covers this plan" line with the sources searched, the index date, and any source that failed. Leave it out for a change to an existing one.
- **How it will work** (`steps`): the main workflow, each step with its goal, including any questions the target skill asks at runtime.
- **What it will and won't do** (`will`, `wont`, `actions`, `access`): every action that reads, changes, sends, or deletes something outside the conversation, each marked as reads only, draft only, asks first, or runs without asking; and the folders, accounts, and connectors it needs.
- **Assumed defaults** (`assumed`): the working assumptions inferred from context and the defaults from [Grill the request](#grill-the-request), each with its reason.
- **Questions for you** (`questions`): the questions still open, numbered. Numbers are stable: a revised plan keeps every number already given, adds new questions after the highest, and keeps answered ones with their answer.
- **Technical details** (`details`):
  - The route; the target skill's type or types, and each requirement applied from [references/skill-types.md](../references/skill-types.md), in a few words each.
  - Placement (project or personal, and why), harness constraints, thinking effort, and look and design.
  - Supporting folders and files, with their purpose, including stage files under `stages/` when the workflow is split; for `state/`, its seeding and update/prune rules.
  - Lessons applied from the recall note, by ID, and the past failures this plan avoids; installs, with their license.
  - Under `notes`: the name, description, and trigger phrases; the [output contract](../SKILL.md#output-contract), including the standard shape and default format of a document-like deliverable; source links or paths, how access is checked, and what happens if they fail, with source and destination paths for any relocated files; automation or integrations; the idea-generation model, if used (count, reference/original split, model choice, and **Choose one** criteria), or a one-line note that it is not used and why; for an existing one, what to keep, change, or remove, and any dependent updates; for a problem, the diagnosis.

A small change, whose plan fits in a few lines and has no Reuse decision and no new action, access, or install, needs no `plan.json` or page: write the same items as a short list in the approval message.

## Get approval before building

Before [Build](build.md) creates, moves, or changes any file, show the full plan, then ask for approval in chat.

**Show the full plan** by the first route this environment offers. A small change skips this: its plan is in the message.

| Environment | Route |
| --- | --- |
| The Artifact tool is available (Claude Code) | Render the page without its document skeleton: `py -3 "${CLAUDE_SKILL_DIR}/scripts/render_plan.py" "_sandbox/<name>/plan.json" --artifact`, which writes `_sandbox/<name>/plan.html`. Where the harness asks for its page-design skill before a publish (`artifact-design`), load it; the page already follows its contract, so do not restyle it. Publish the file as a new private artifact with the icon `checklist` and a one-sentence description naming what the plan is for. A publish shows the new artifact to the user by itself; the Artifact tool's `open` action shows an existing artifact again without changing it, for when the user asks to see the plan again. Put the link first in the message. If the publish fails, take the next row. |
| A shell, but no Artifact tool | Render the standalone page (the same command without `--artifact`) and open it in the default browser: `start "" "<file>"` on Windows (`Start-Process "<file>"` in PowerShell), `open "<file>"` on macOS, `xdg-open "<file>"` on Linux. Give the file's full path in the message, also when opening it fails. |
| Claude desktop or claude.ai chat, without a shell (**Not verified**) | Make the plan page a native HTML artifact in the reply, with the sections and look of [assets/plan.html](../assets/plan.html). |
| Cowork (**Not verified**) | Render the standalone page with `--out "<outputs folder>/plan.html"` and name the file in the message. |
| No file or artifact support | Write the same sections as Markdown in chat, after the message's summary. |

**Ask for approval** in one message that works on its own, so that the user can answer and approve even when the page did not open or render:

1. A short summary, three to six lines in plain words: what will be built or changed, from where to where, from what to what, and any action that changes or sends something. Then the artifact link or file path, or, for a small change, the plan as a short list.
2. For a new target skill or remake, the Reuse decision as its own question, first: reuse or adapt each candidate that covers or partly covers the plan, or build new, with a recommendation. Say that a plain "yes" does not answer it; approval of the plan without an answer to it is not approval. Once answered, set `reuse.choice` and re-render as below; the renderer's `reuse_open` turns false.
3. The questions still open, numbered as on the page, about unresolved choices that would materially change scope, behavior, output, permissions, side effects, file placement, or harness compatibility. For each, give a recommendation and a short reason; offer alternatives only when they are genuinely plausible. Do not ask again what [Grill the request](#grill-the-request) already answered.
4. A request for explicit approval of the plan with the recommended answers.

This gate applies even when nothing is unresolved.

- Only a clear affirmative counts. Silence, ambiguity, or a request for changes is not approval.
- If the user changes an answer or the plan, update `plan.json` (raise `revision`, keep every question number, mark answered questions with their answer), render it to the same path, and republish to the same artifact (the same file path in this session, or the artifact's link in a later one) or overwrite the same file; then ask again in the same way. Each plan has one page, never a new one per revision.
- If the user has not confirmed, stop after Plan and wait. Do not treat the original request as approval.
- If the user drops the request, go to [Learn](learn.md) to record why.

After approval of a plan with a page, set `status` to `approved` with `approved_on` in `plan.json`, and render and republish it once more the same way, so the page shows the plan that was approved; a small change has no page and skips this. Then go to [Build](build.md).

## Supplied change plan

Entered from [Start from the request](#start-from-the-request) when another skill hands over a ready change plan for one of the user's own skills or tools. The calling skill already found the cause and wrote the smallest change, so this route does not grill or search again; the user still approves every file change.

1. **Check the brief.** It must name the target files by path, the cause with its evidence (the quoted instruction or the missing statement, and the finding, error, or user response that exposed it), the smallest change (as exact wording or a diff), and the calling skill. Ask the calling skill, or the user when it cannot answer, for anything missing; never fill a gap with a guess.
2. **Check it against the files.** Read the target files and confirm that the quoted text exists and that the change applies cleanly.
   - **Quote missing or different:** the plan was written against other text, or misquotes it. Change nothing; return the plan to the calling skill with the text the file actually has at that place, and ask it to confirm or correct the plan. Then go to [Learn](learn.md), which records the returned plan; skip the rest of this section.
   - **Applies, but reaches further:** the change contradicts another instruction, reaches beyond the stated cause, or adds an action, access, or install. Say so to the user, and plan it as an ordinary change from [Inspect the target context](#inspect-the-target-context) instead; skip the rest of this section.
   - **Applies, with a gap:** the change is within the cause but leaves a case open (for example, a list that reads as closed). Keep the supplied wording, and name the gap as a note in the approval message, so the user can approve it as is or ask for a change.
3. **Write the plan.** A change that fits in a few lines is a small change: its plan is a short list in the approval message with the target file and place, the cause and its evidence, the exact change, the calling skill, any gap from step 2, and "no new actions, access, or installs". Otherwise write `plan.json` as [Draft the plan](#draft-the-plan) says, with no Reuse decision. Either way, name the calling skill and the evidence in the summary, and record the calling skill in the plan's notes so [Learn](learn.md) puts it in the registry row.
4. Go to [Get approval before building](#get-approval-before-building). A plain "yes" approves the supplied change; a requested edit updates the plan as that section says.

## Skills and agents

- [skill-builder](../SKILL.md) — rules and vocabulary this stage applies.
- [Recall](recall.md) and [Test](test.md) — the stages that lead here.
- [Build](build.md) — the next stage after [Get approval before building](#get-approval-before-building).
- [references/grilling.md](../references/grilling.md) — the crucial and default items asked in [Grill the request](#grill-the-request); `grilling` — the shared question method that asks them; [references/skill-types.md](../references/skill-types.md) — the deliverable kinds and requirements behind the route and the design.
- [scripts/render_plan.py](../scripts/render_plan.py) — renders `plan.json` into the plan page from the template [assets/plan.html](../assets/plan.html); [examples/plan-sample.json](../examples/plan-sample.json) — a filled plan; used in [Draft the plan](#draft-the-plan) and [Get approval before building](#get-approval-before-building).
- `artifact-design` — loaded before the plan page is published as an artifact, where the harness asks for it.
- `skill-design` — builds, once, the template that [Decide the design](#decide-the-design) plans for the **Look**; it also built the plan page's template.
- `update-config` and `plugin-authoring` — write hooks, settings, and mods for the routes chosen in [Choose the route](#choose-the-route); Build hands the work to them.
- `skill-finder` — searched again in the [Reuse decision](#decide-the-design) when the drafted design adds a central step; vets and installs a reuse candidate, as planned in [Inspect the target context](#inspect-the-target-context).
- No dedicated planning agent is required.
