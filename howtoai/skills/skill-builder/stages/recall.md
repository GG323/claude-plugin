# Recall past work

## Contents

- [When to use this stage](#when-to-use-this-stage)
- [Find the knowledge store](#find-the-knowledge-store)
- [Search past work](#search-past-work)
- [Write the recall note](#write-the-recall-note)
- [Choose the next stage](#choose-the-next-stage)
- [Skills and agents](#skills-and-agents)

## When to use this stage

Recall is the first stage for every request to `skill-builder`: a new target skill, a change, or a reported problem. It looks at what earlier runs learned so that this run reuses what worked and does not repeat what failed. [Test](test.md) returns problems it finds straight to [Plan](plan.md) without Recall, because the recall note from the start of the process still applies.

## Find the knowledge store

The knowledge store is two files that [Learn](learn.md) maintains:

- [state/registry.md](../state/registry.md) — the **registry** of target skills `skill-builder` has built, changed, or retired.
- [state/lessons.md](../state/lessons.md) — the **lessons**: what earlier runs showed about requirements, skill types, tests, failures, and the process.

Proven lessons have already been moved into [references/skill-types.md](../references/skill-types.md), which Plan reads anyway; the lessons file holds the rest.

If either file is missing, stop and ask the user to restore it or give its new location; do not recreate it silently, because that would lose past work. If this skill's folder is not writable (for example, a plugin install), ask the user for a writable project path for both files.

## Search past work

1. **Existing skills.** Search the registry for target skills with the same name, a similar purpose, or the same location. Then read the descriptions (not only the folder names) of skills in these places, because skills built without `skill-builder` are not in the registry:
   - **The user's own skills:** the workspace's skill folders (for example, `.claude/skills/` or `SKILLS/`), the personal folder `~/.claude/skills/`, and the build destination if the request names one. A match here can be a duplicate.
   - **Skills the user did not write:** skills installed in the harness (built-in or from plugins) and vendored third-party folders (for example, `External/`). A match here is a reuse candidate for Plan, never a duplicate.
2. **Retired skills.** For a registry entry with status `retired` and a similar purpose, read why it was retired, so the plan does not repeat it.
3. **Lessons.** Search the lessons file by the likely skill types, the tools and connectors involved, and, for a reported problem, the symptom. Use a text search on keywords rather than reading the whole file. Take `confirmed` lessons before `candidate` ones, and always include `avoid` lessons that match.

## Write the recall note

Keep a short **recall note** in the conversation for the later stages:

- Similar or existing skills, with their paths, split into the user's own skills and reuse candidates.
- Lessons to apply, by ID.
- Lessons to avoid, by ID, with their reasons.
- For a reported problem: known causes and fixes for the same symptom.
- Tests that worked for this skill type.

If nothing matches, the note says "No relevant past work". Tell the user the note's main point in one line.

## Choose the next stage

Check the rows in order and take the first that matches. A skill **covers** a request when its main deliverable matches what the request asks for, even if it lacks part of it or does more.

| Request | Next stage |
| --- | --- |
| A new target skill that one of the user's own skills already covers | Tell the user which skill, what it already does, and what it lacks, and recommend extending it instead of building a duplicate. Combine this with the recall note's one line. If they agree, add the skill to the registry if it is missing, noting its origin as unknown, and go to [Plan](plan.md) with the request as a change to that skill; otherwise go to [Plan](plan.md) with it as a new target skill |
| A change to, or a problem with, one of the user's own skills, including `skill-builder` | Add the skill to the registry if it is missing, noting its origin as unknown, then go to [Plan](plan.md) with it as a change |
| A new target skill, or remaking one | [Plan](plan.md) |

## Skills and agents

- [skill-builder](../SKILL.md) — rules and vocabulary this stage applies.
- [Learn](learn.md) — maintains the files this stage searches.
- [Plan](plan.md) — the next stage, which uses the recall note.
- No dedicated recall agent is required.
