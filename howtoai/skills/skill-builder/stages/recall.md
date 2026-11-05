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

Judge every skill found against the request at one of three levels, by reading what it does, not only its description's wording:

- **Covers:** its main deliverable matches what the request asks for, from the same kind of input and within the request's scope. It may do more, or lack minor details such as options or formatting.
- **Partly covers:** its main deliverable matches, but it lacks an input, step, or scope the request names as central. For example, a skill that fills PDF forms partly covers "fill PDF forms from a spreadsheet", because reading the spreadsheet is central.
- **Related:** it shares the tool, service, or subject but makes a different deliverable.

An input, step, or scope the request states in its own words is central: "from my meeting notes, one issue per action item" makes extracting action items central, so a skill that turns any text into issues only partly covers it. When unsure between covers and partly covers, choose partly covers; it costs only the online search in step 2.

1. **Existing skills.** Search the registry for target skills with the same name, a similar purpose, or the same location. Then read the descriptions (not only the folder names) of skills in these places, because skills built without `skill-builder` are not in the registry:
   - **The user's own skills:** the workspace's skill folders (for example, `.claude/skills/` or `SKILLS/`), the personal folder `~/.claude/skills/`, and the build destination if the request names one. A match here can be a duplicate.
   - **Skills the user did not write:** skills installed in the harness (built-in or from plugins) and vendored third-party folders (for example, `External/`). A match here is a reuse candidate for Plan, never a duplicate. Mark a vendored one the same way as an online match in step 2 (**Anthropic** or **unaudited**), because a downloaded copy has not been audited either.
2. **Online catalogs.** Only for a new target skill that none of the skills found in step 1 covers; a skill that only partly covers it does not skip this step. Skip it for a change or a reported problem. Search these sources by the request's keywords and judge each match by its description, not its name:
   - **Anthropic's plugin marketplaces:** the catalog files `https://raw.githubusercontent.com/anthropics/claude-plugins-official/main/.claude-plugin/marketplace.json`, `https://raw.githubusercontent.com/anthropics/claude-plugins-community/main/.claude-plugin/marketplace.json`, and `https://raw.githubusercontent.com/anthropics/skills/main/.claude-plugin/marketplace.json`. They are public, so fetch them directly. The community catalog holds thousands of entries, so filter each file by keyword with a short script (with UTF-8 output, because entries hold non-Latin text) instead of reading it whole. Each lists plugins with a name, description, and source; the install command is `claude plugin install <plugin>@<marketplace name>`, where the marketplace name is the file's `name` field. A marketplace not yet added needs `--marketplace <owner>/<repo>` on the same command.
   - **AgenticSkills:** `https://agenticskills.io` has no API, so run a web search limited to `agenticskills.io` and open each likely hit, because listings and search snippets can be out of date.
   - **skills.sh** is not searched: its search API needs a Vercel OIDC token. Say so in the recall note.

   If a source does not load, mark it unavailable in the recall note and continue with the others; the online search only adds options and never blocks the process.

   Mark each match by its author, not by the catalog it is in: **Anthropic** when Anthropic wrote it (the catalog entry's author or the source repository is `anthropics`), **unaudited** otherwise, including partner plugins in the official marketplace. Keep only matches whose description fits the request, and leave out a match that is the same skill as one found in step 1. An online match is a reuse candidate; Recall never downloads or installs it, but may open its public pages and files on the web to judge what it does and lacks. A connector or MCP server is not a candidate: name it in the recall note as a tool the target skill could use.
3. **Retired skills.** For a registry entry with status `retired` and a similar purpose, read why it was retired, so the plan does not repeat it.
4. **Lessons.** Search the lessons file by the likely skill types, the tools and connectors involved, and, for a reported problem, the symptom. Use a text search on keywords rather than reading the whole file. Take `confirmed` lessons before `candidate` ones, and always include `avoid` lessons that match.

## Write the recall note

Keep a short **recall note** in the conversation for the later stages:

- Skills that cover the request, with their paths, split into the user's own skills and reuse candidates.
- Skills that partly cover the request or are related to it, with their paths, their level, and what each lacks.
- Online candidates: for each, its name, source link, install command (or "none given" when its page shows none), and mark (**Anthropic** or **unaudited**); sources that were unavailable or not searched, with the reason; or "not searched" and why when step 2 was skipped.
- Lessons to apply, by ID.
- Lessons to avoid, by ID, with their reasons.
- For a reported problem: known causes and fixes for the same symptom.
- Tests that worked for this skill type.

If nothing matches, the note says "No relevant past work". Tell the user the note's main point in one line.

## Choose the next stage

Check the rows in order and take the first that matches. "Covers" and "partly covers" are the levels defined in [Search past work](#search-past-work).

| Request | Next stage |
| --- | --- |
| A new target skill that one of the user's own skills covers or partly covers | Tell the user which skill, what it already does, and what it lacks, and recommend extending it instead of building a duplicate. Combine this with the recall note's one line. If they agree, add the skill to the registry if it is missing, noting its origin as unknown, and go to [Plan](plan.md) with the request as a change to that skill; otherwise go to [Plan](plan.md) with it as a new target skill |
| A new target skill that a reuse candidate covers, found locally or online | Tell the user the candidate, its path or source link, what it does and lacks, its mark, and, for an **unaudited** one, the safety review and audit it needs before install. Ask whether to reuse it or build a new skill, combined with the recall note's one line, and go to [Plan](plan.md) with the answer: reusing it as the target skill, or a new target skill |
| A change to, or a problem with, one of the user's own skills, including `skill-builder` | Add the skill to the registry if it is missing, noting its origin as unknown, then go to [Plan](plan.md) with it as a change |
| A new target skill, or remaking one | [Plan](plan.md); name any reuse candidate that partly covers it, with its mark, in the recall note's one line, as a base Plan may adapt |

## Skills and agents

- [skill-builder](../SKILL.md) — rules and vocabulary this stage applies.
- [Learn](learn.md) — maintains the files this stage searches.
- [Plan](plan.md) — the next stage, which uses the recall note.
- No dedicated recall agent is required.
