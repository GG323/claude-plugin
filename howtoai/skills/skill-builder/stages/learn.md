# Learn from this run

## Contents

- [When to use this stage](#when-to-use-this-stage)
- [Gather what happened](#gather-what-happened)
- [Update the registry](#update-the-registry)
- [Record lessons](#record-lessons)
- [Promote proven lessons](#promote-proven-lessons)
- [Clean up](#clean-up)
- [Report](#report)
- [Skills and agents](#skills-and-agents)

## When to use this stage

Learn is the last stage of every run. It is entered from [Test](test.md#run-and-deliver) after delivery, and from [Plan](plan.md) when the user drops a request or retires a target skill. It records what this run showed in the knowledge store that [Recall](recall.md) searches, and keeps that store free of repeats and failed attempts.

Learn writes only to [state/registry.md](../state/registry.md) and [state/lessons.md](../state/lessons.md), plus [references/skill-types.md](../references/skill-types.md) or [references/test-cases.md](../references/test-cases.md) when the user approves a promotion, and it deletes the test outputs. Every date it records comes from the system clock. Never record credentials, tokens, or personal data; record skill names, paths, and general lessons only.

## Gather what happened

From this run, collect:

- The target skill, its path, its types, and the route (main or `skill-creator`).
- The requirements applied, and which recall-note lessons were applied and whether they helped.
- The tests run and their results, including the baseline and trigger tests.
- Problems found, their causes, and how they were fixed; handoff outcomes.
- The user's corrections, and anything the user rejected.

## Update the registry

Keep one row per target skill path:

- If the target skill already has a row, update it; otherwise add one.
- Fill in the columns: **Last change** is today's date; **Test cases** is the number of cases in its `evals/` folder, plus "triggers" when `trigger-queries.json` exists; **Notes** says in one line what the skill does now and where its test copy is installed.
- Set the status to `active`, or `retired` with a one-line reason.
- Keep retired rows: they stop later runs from rebuilding what failed.

## Record lessons

A lesson is worth recording only if it would change how a future target skill is planned, built, or tested. Skip one-off details and anything [references/skill-types.md](../references/skill-types.md) already says.

For each candidate lesson:

1. Search [state/lessons.md](../state/lessons.md) for the same point by keywords, area, and skill type.
2. If the point is already there, add this target skill to its evidence. If this run contradicts it, rewrite the entry to the better-supported version, or set it to `disputed` with both sides in one line; never keep two conflicting entries.
3. If the point is new, add it as a `candidate` with the next free ID, under the matching area.
4. Record a failed approach with the status `avoid` and its reason, so later runs do not repeat it. Never record it as a recommendation.
5. For each recall-note lesson that was applied, add this run as evidence for it if it helped, or against it if it did not. A lesson that failed twice is set to `avoid` or removed.

## Promote proven lessons

A lesson is proven when evidence from at least two different target skills supports it and nothing contradicts it. For each proven lesson, propose its exact wording and destination:

- Requirements, skill types, verification, typical failures, and reuse go into [references/skill-types.md](../references/skill-types.md). A lesson about a kind of skill no section covers becomes a new type section there.
- Lessons about how test cases are written (inputs, fixtures, graders) go into [references/test-cases.md](../references/test-cases.md).
- Lessons about `skill-builder`'s own stages are proposed as a change to `skill-builder`. An approved one becomes a new run with `skill-builder` as the target skill, starting at [Plan](plan.md) like any other change.

Ask the user about all proposals in one message. For each approved one, edit the destination, check that its links still resolve, and replace the lesson with a one-line pointer under **Promoted**, so later runs find it there instead of adding it again. For a declined one, keep the lesson, note `declined` with the date, and do not propose it again until new evidence arrives.

## Clean up

Test outputs are temporary; the delivery report and the saved test cases in `evals/` are what remains.

- Delete `_sandbox/<name>/`, the target skill's test-output folder, once delivery is done; the delivery report holds the test evidence. Delete `_sandbox/` itself when it is then empty. First confirm that no test subagent is still running.
- Delete everything else this run left behind outside the target skill: the baseline copy, and drafts or candidate versions that were not delivered.
- Confirm that the target skill's `evals/` holds no test cases for behavior that was removed.
- In the lessons file, merge near-duplicates and remove `candidate` lessons with one piece of evidence that are older than six months. Keep the file under about 200 lines; when it is longer, merge and remove before adding.
- In the registry, keep each row's notes to one line.

## Report

Tell the user in one or two lines what was recorded, which promotions were proposed or applied, and what was cleaned up. This ends the run.

## Skills and agents

- [skill-builder](../SKILL.md) — rules and vocabulary this stage applies.
- [Recall](recall.md) — searches what this stage records.
- [Plan](plan.md) — receives approved changes to `skill-builder` itself.
- No dedicated learning agent is required.
