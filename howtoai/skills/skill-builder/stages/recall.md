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

If neither the request nor the conversation names a task (for example, only "create a skill"), ask the user the single goal question from [references/grilling.md](../references/grilling.md) and wait for the answer before searching, because a search without a goal cannot judge any match. Ask nothing else at this point: every other question waits for Plan.

## Find the knowledge store

The knowledge store is two files that [Learn](learn.md) maintains:

- [state/registry.md](../state/registry.md) — the **registry** of target skills `skill-builder` has built, changed, or retired.
- [state/lessons.md](../state/lessons.md) — the **lessons**: what earlier runs showed about requirements, skill types, tests, failures, and the process.

Proven lessons have already been moved into [references/skill-types.md](../references/skill-types.md), which Plan reads anyway; the lessons file holds the rest.

If either file is missing, stop and ask the user to restore it or give its new location; do not recreate it silently, because that would lose past work. If this skill's folder is not writable (for example, a plugin install), ask the user for a writable project path for both files.

## Search past work

The levels **covers**, **partly covers**, and **related**, and the marks (**anthropic**, **curated**, **reviewed**, **local**, **unaudited**), are defined in `skill-finder`, which every search below uses; judge against the request at this stage, and against the drafted design in [Plan](plan.md#decide-the-design).

1. **Registry.** Search the registry for target skills (skills, tools, and procedures) with the same name, a similar purpose, or the same location. For each matching `active` row, check that its path exists on disk; a path is relative to the HowToAI workspace root, starts with `~`, or is absolute, as the registry's Format section states. When its Notes carry a template stamp ([item 11](../references/skill-types.md#every-target-skill)) older than the current design (the date `skill-design`'s house design or the client profile last changed), put a template rebuild offer in the recall note.
   - **Path missing, copy found:** look for a folder of the same name in the personal skills folder `~/.claude/skills/` and in the workspace's skills folders (for example, `.claude/skills/` or `SKILLS/`). If exactly one is found, put it in the recall note as the possible new path; it replaces the row's path only if step 3 decides it is the user's own, and Learn then rewrites the row. If more than one is found, ask the user which one is the skill, grouped with the recall note's one line.
   - **Path missing, no copy found:** tell the user in one line that the registered skill is no longer on disk, treat the request as a new target skill, and put the row in the recall note, so Learn sets it to `retired` with the reason "missing from disk".
2. **Skill search.** For a new target skill, run the `skill-finder` skill (for example, `/skill-finder`) with the request as the need, every time, even when step 1 found a match, because an existing skill elsewhere may fit better; first tell the user in one line that the search takes a few minutes. For a change, a reported problem, or a supplied change plan, skip it: the target skill already exists. The registry search in step 1 and the lessons search in step 5 still run, read-only, for a supplied change plan too. `skill-finder` searches the user's own skills (installed, workspace, and the build destination's folder) and every approved marketplace and list (skills, plugins, agents, commands, hooks, mods, and MCP servers), and returns its candidate table. Never replace it with a keyword search of catalogs: that missed most fitting candidates in earlier runs (L-114). Recall never downloads, copies, or installs a match.
   - A connector or MCP server that the target skill could use instead of being replaced by it goes in the recall note as a tool, not a candidate; if the plan installs it, it is vetted like any candidate.
   - If `skill-finder` cannot run, say why in the recall note and that the reuse search is missing; Plan's [Reuse decision](plan.md#decide-the-design) then tells the user so before approval.
3. **Ownership.** Decide whose work each existing skill, tool, or procedure the run may change is: the target of a change or reported problem, a copy step 1 found, and each local match from step 2. Only the user's own work is changed in place; everything else is a third-party candidate that `skill-finder` vets before any file changes. Take the first row that matches:
   - **Own:** it sits at the path of a registry row whose Route is not `main (reuse)` (`skill-builder` built or changed it there), or in the user's own plugin source (a registered path inside `PLUGIN/claude-plugin/`); or the user confirms they wrote it. A copy step 1 found at a new path is not covered by its row, so the rows below judge it.
   - **Third-party:** it sits in an installed plugin (`~/.claude/plugins/`), a marketplace clone, a vendored folder such as `External/`, or `~/.claude/skills/synced/`; it ships inside a plugin (a `.claude-plugin/plugin.json` in a folder above it, which `skill-finder` shows as `part of plugin:`); `skill-finder`'s `vetting:` line marks it third-party; or its registry row's Route is `main (reuse)`.
   - **Unknown:** anything else, for example an unregistered skill in `~/.claude/skills/` or a workspace's `.claude/skills/`, which may have been copied from a pack. Ask the user whether they wrote it, grouped with the recall note's one line, and treat it as third-party until they confirm.

   A match from step 2 that is the user's own can be a duplicate; every other match is a reuse candidate for Plan, never a duplicate. Put each decision and its reason in the recall note.
4. **Retired skills.** For a registry entry with status `retired` and a similar purpose, read why it was retired, so the plan does not repeat it.
5. **Lessons.** Search the lessons file by the likely skill types, the tools and connectors involved, and, for a reported problem, the symptom. Use a text search on keywords rather than reading the whole file. Take `confirmed` lessons before `candidate` ones, and always include `avoid` lessons that match.

## Write the recall note

Keep a short **recall note** in the conversation for the later stages:

- The `skill-finder` candidate table as returned, split into the user's own skills and reuse candidates; or "not searched" and why when step 2 was skipped or could not run.
- The ownership decisions from step 3, with their reasons, and any ownership question still waiting for the user.
- Registry rows whose path moved (with the new path) or is missing from disk, for Learn; any template rebuild offer.
- Lessons to apply, by ID.
- Lessons to avoid, by ID, with their reasons.
- For a reported problem: known causes and fixes for the same symptom.
- Tests that worked for this skill type.

If nothing matches, the note says "No relevant past work". Tell the user the note's main point in one line.

## Choose the next stage

Check the rows in order and take the first that matches. "Covers" and "partly covers" are the levels `skill-finder` returns. "The user's own" means own as [Search past work](#search-past-work) step 3 decided it; while ownership is unknown, wait for the user's answer, and an unconfirmed skill takes the third-party row.

| Request | Next stage |
| --- | --- |
| A new target skill that one of the user's own skills covers or partly covers | Tell the user which skill, what it already does, and what it lacks, and recommend extending it instead of building a duplicate. Combine this with the recall note's one line. If they agree, add the skill to the registry if it is missing, noting its origin as "the user's own, confirmed <date>", and go to [Plan](plan.md) with the request as a change to that skill; otherwise go to [Plan](plan.md) with it as a new target skill |
| A supplied change plan from another skill for one of the user's own skills or tools | Go to [Plan](plan.md#supplied-change-plan). If the target is not the user's own (for example, an installed plugin copy), stop and return the plan to the calling skill unchanged, saying why, so it can keep it as a change request |
| A change to, or a problem with, one of the user's own skills, including `skill-builder` | Add the skill to the registry if it is missing, noting its origin as "the user's own, confirmed <date>", then go to [Plan](plan.md) with it as a change |
| Only checking that a third-party skill, tool, or procedure works, with no change named | Go to [Plan](plan.md) with it as verification only; Build has `skill-finder` vet it, report-only, and nothing is copied or adapted |
| A change to, or a problem with, a third-party skill, tool, or procedure, installed or not (a plugin's skill, a vendored or synced skill, a downloaded agent or hook) | Go to [Plan](plan.md) with the request as adapting that candidate, so [Build](build.md#before-writing) vets it before any file changes. Its installed files are never edited in place |
| A new target skill, or remaking one | [Plan](plan.md), with the candidate table in the recall note; Plan's [Reuse decision](plan.md#decide-the-design) puts the candidates to the user against the drafted design |

## Skills and agents

- [skill-builder](../SKILL.md) — rules and vocabulary this stage applies.
- [Learn](learn.md) — maintains the files this stage searches.
- [Plan](plan.md) — the next stage, which uses the recall note.
- `skill-finder` — the skill search in [Search past work](#search-past-work).
- No dedicated recall agent is required.
