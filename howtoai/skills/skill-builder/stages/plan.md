# Plan the skill

## Contents

- [Start from the request](#start-from-the-request)
- [Inspect the target context](#inspect-the-target-context)
- [Choose the route](#choose-the-route)
- [Decide the design](#decide-the-design)
- [Draft the plan](#draft-the-plan)
- [Get approval before building](#get-approval-before-building)
- [Hand off to skill-creator](#hand-off-to-skill-creator)
- [Skills and agents](#skills-and-agents)

## Start from the request

Plan interprets the problem: what the target skill is for, and how to get there. It is entered from [Recall](recall.md) for every request — a new target skill, a change, or a reported problem — and from [Test](test.md#run-and-deliver) when a problem found there changes the approved plan or survives two fixes. Every change is planned here, whatever its size; a small change simply gets a short plan. Use the recall note throughout: apply its lessons, and do not repeat what it lists to avoid.

Use the request as the starting point. If it already explains the task or outcome, reflect it back briefly instead of asking again. Ask for the goal only when it cannot be inferred. For a change or a problem, also:

- Capture what was expected, what happened, and what was already tried.
- Check the recall note for known causes and fixes of the same symptom, and for fixes that already failed.
- Identify the cause: the instructions or workflow, the supporting material, or both. If a required link or path is unavailable, ask the user for a working source.

## Inspect the target context

Read relevant project instructions, existing skills, configuration, source material, and examples before asking about details.

- Technical workflows: identify the stack, tools, supported versions, commands, and safe verification options.
- Nontechnical workflows: identify the audience, source material, output formats, voice, policies, and examples of finished work.
- Identify the target harness only as far as needed for format, location, tools, and invocation, and the platforms the target skill must run on.
- List the skills and connectors the harness already offers that the target skill could depend on. Loading a tool's description to see what it does is fine; do not call a connector that reads private data until the plan is approved.
- Check that the tools and libraries the target skill will need are available here, and apply the [missing-tools rule](../SKILL.md#core-rules) to any that are not; put installs and proposed alternatives in the plan.
- Existing skill: read it and its linked files in full. Trace incoming and outgoing references to related skills and documentation, and note coordinated changes.

Treat details inferred from project evidence as working assumptions and list them in the plan rather than asking about each one.

## Choose the route

Decide which of two routes the work takes.

**What `skill-creator` is for in Plan.** `skill-creator` (for example, `anthropic-skills:skill-creator` or `/skill-creator`) improves a skill through evidence: it runs test prompts with and without the skill, grades the results, shows them to the user, and repeats in rounds. It is used for three cases only:

- **Coding skill** — creating, remaking, or changing a target skill whose main deliverable is code (writing, changing, or testing it) or findings about code (reviewing it). Code can be checked objectively, so the test-and-improve loop pays off. A skill that bundles helper scripts to do other work, such as sorting files or checking links, is not a coding skill; Test checks its scripts like any other part.
- **Creative tuning** — the request asks for further rounds of tuning the quality, tone, or style of a creative output. The review loop lets the user compare sample outputs round by round.
- **Repeated failure** — Test passed back a problem that survived two fixes, and the target skill's goal, scope, and output contract still match what the user wants. More editing by guesswork is unlikely to help; the with/without-skill comparison shows whether the target skill adds value as defined and what the runs actually do. If the goal, scope, or output contract no longer match, the plan itself is wrong: take the main route and revise it.

Everything else takes the main route, including creating a creative skill in the first place and document, communication, media, research, and data skills.

| Case | Route |
| --- | --- |
| Coding skill, creative tuning, or repeated failure | [Hand off to skill-creator](#hand-off-to-skill-creator) |
| Everything else | [Decide the design](#decide-the-design) |

If `skill-creator` is unavailable (not installed, or the harness cannot run subagents), take the main route for these cases too, and note in the plan that the evidence will be weaker.

## Decide the design

Apply the rules in [SKILL.md](../SKILL.md) to decide:

- **Skill type and requirements** — read [references/skill-types.md](../references/skill-types.md). Identify the target skill's type or types, then decide each applicable requirement from its [Every target skill](../references/skill-types.md#every-target-skill) section and from each matching type section.
- **Automation** — whether existing code or an official integration should handle any repeatable, deterministic part. Account for access, cost, data handling, and side effects. Prefer the project's stack; if none is set and a script is justified, default to Python when available.
- **Output contract** — deliverable, audience, format, delivery, and success check, per [Output contract](../SKILL.md#output-contract). For a document-like deliverable, also decide its standard structure, which data goes in tables or charts, and its format, starting from the [standardized-output defaults](../SKILL.md#output-contract) and giving the reason for any departure.
- **Memory and sources** — whether `references/`, `assets/`, `examples/`, or persistent `state/` are needed, and which links or paths the target skill relies on, per [Working memory and sources](../SKILL.md#working-memory-and-sources). For existing reference files, decide whether they stay in place or move into the target skill's `references/` folder.
- **Idea generation** — whether the output is creative or open-ended enough to benefit from the [idea-generation option](../SKILL.md#idea-generation-option). Default to no for procedural or deterministic outputs.
- **Stages** — whether to split the workflow into stages. Split only when it has distinct stages, each with its own inputs, decisions, and outputs, such as gather → draft → review or plan → execute → verify. Keep it in `SKILL.md` when it is short or linear enough to read in one pass; splitting is for clarity, not a default. Build has the rules for writing a split workflow.

## Draft the plan

Prepare a concise plan with only the applicable items:

- Intended outcome, name, description, and trigger phrases.
- Required inputs and any questions the target skill should ask at runtime.
- Main workflow and the [output contract](../SKILL.md#output-contract), including the standard shape and default format of a document-like deliverable.
- Skill type or types, and each requirement applied from [references/skill-types.md](../references/skill-types.md), in a few words each.
- Supporting folders and files, with their purpose, including stage files under `stages/` when the workflow is split; for `state/`, its seeding and update/prune rules.
- Source links or paths, how access is checked, and what happens if they fail; source and destination paths for any relocated files.
- Idea-generation model, if used: count, reference/original split, model choice, and **Choose one** criteria — or a one-line note that it is not used and why.
- Automation or integrations, location and scope (project or personal), and harness constraints.
- Working assumptions inferred from context.
- Lessons applied from the recall note, by ID, and the past failures this plan avoids.
- For an existing skill: what to keep, change, or remove, and any dependent-skill updates. For a change or a problem: the diagnosis and the intended change.

## Get approval before building

Before [Build](build.md) creates, moves, or changes any file, send one message with:

1. The plan.
2. Questions about unresolved choices that would materially change scope, behavior, output, permissions, side effects, file placement, or harness compatibility, grouped together. For each, give a recommendation and a short reason; offer alternatives only when they are genuinely plausible.
3. A request for explicit approval of the plan with the recommended answers.

This gate applies even when nothing is unresolved.

- Only a clear affirmative counts. Silence, ambiguity, or a request for changes is not approval.
- If the user changes an answer or the plan, revise the plan and ask again in the same way.
- If the user has not confirmed, stop after Plan and wait. Do not treat the original request as approval.
- If the user drops the request, go to [Learn](learn.md) to record why.

After approval, continue to [Build](build.md). Skip the [Hand off to skill-creator](#hand-off-to-skill-creator) section.

## Hand off to skill-creator

1. **Present a short plan:** intended outcome, name, description, and trigger phrases; permissions and side effects, including what the target skill must not do; location and scope; the [output contract](../SKILL.md#output-contract); for an existing skill, what changes; for creative tuning, the qualities to tune and what stays fixed. State what `skill-creator` will do (draft and test a coding skill, or run review rounds on sample outputs) and that its tests are real, billed model runs.
2. **Get explicit approval.** Ask about any material choices in one grouped message, then ask for approval to the same standard as [Get approval before building](#get-approval-before-building). Do not start the handoff without it.
3. **Invoke `skill-creator`** with a brief containing:
   - The target skill's path (new or existing) and the approved plan.
   - For creative tuning: the user's feedback, any sample outputs, and the qualities to tune; the target skill's goal and scope stay as they are.
   - For a change or a repeated failure: the problem, the expected behavior, and what was already tried, including both fixes for a repeated failure.
   - The output contract and any test cases in the target skill's `evals/` folder.
   - What to preserve: the [Feedback note](../SKILL.md#feedback-note-for-target-skills), the target repository's documentation conventions, and the target skill's permissions.
   - Side-effect limits: tests must not send, publish, delete, or write outside the `skill-creator` workspace. Use dry runs, mocks, or disposable copies; if a test cannot be isolated, leave it out and say so.
   - Whether the user wants description-trigger optimization or packaging; skip both unless asked.
4. **When `skill-creator` finishes,** continue with [Check and design tests](test.md#check-and-design-tests) in Test to restore conventions `skill-creator` may not know. If its comparison showed that the target skill does not beat working without it, ask the user whether to redefine it (return to [Start from the request](#start-from-the-request)), keep it as is, or retire it. If they retire it, go to [Learn](learn.md).

## Skills and agents

- [skill-builder](../SKILL.md) — rules and vocabulary this stage applies.
- [Recall](recall.md) and [Test](test.md) — the stages that lead here.
- [Build](build.md) — the next stage after [Get approval before building](#get-approval-before-building).
- `skill-creator` — receives the handoff in [Hand off to skill-creator](#hand-off-to-skill-creator); [Test](test.md) follows.
- No dedicated planning agent is required.
