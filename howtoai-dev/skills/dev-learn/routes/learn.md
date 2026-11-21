# Route: learn

## Contents

- [Collect](#collect)
- [Find the root cause](#find-the-root-cause)
- [Write the record](#write-the-record)
- [Check drift](#check-drift)
- [Propose the fixes](#propose-the-fixes)
- [Hand on and settle](#hand-on-and-settle)
- [Skills and agents](#skills-and-agents)

## Collect

Entered from [SKILL.md](../SKILL.md#routes), usually when `dev-review`'s human review hands on.

1. `LEARN collect "<change folder>" --round <n> --lessons "<lessons log>"`. It lists every finding that is Critical or Major, declined (with the reason), or a likely repeat, with the open lessons and earlier applied fixes that look like the same problem.
2. For each candidate match, read the lesson or the earlier learn row and decide: the same problem (same cause, not only the same file), or not. Keep only real matches; a finding collected only as a likely repeat, with no real match, drops out and gets no row.
3. When `nothing_to_learn` is true, run `LEARN start "<change folder>" --round <n>` (the record with no rows) and go to [Check drift](#check-drift). Skip the Find the root cause and Write the record sections. Propose the fixes then asks only about the drift items, and with no drift item, close with the report line alone.
4. Tell the user one line: "Learn round <n> of `<change id>`: <c> findings collected, <r> repeats."

## Find the root cause

For each collected finding, work through the stage table in `dev-core`'s [method](../../dev-core/references/self-edit.md#the-stage-that-let-it-through) and note every stage whose rules or facts would have caught it. Name the one whose fix also stops the problem in later changes: a technology fact missing from a workbook reaches the plan, the build, and the review of every change, while a missing test covers only this one. When two fixes reach equally far, name the earlier stage. The other stages go into the evidence.

1. **Read the evidence.** The workbook statements for the technologies of the cited files, from `WORKBOOK resolve --workspace "<workspace>" --stage review --paths <cited files> --markdown` (the receipts in `state.json` show what each stage read); the finding and its location; `plan.md` and the work item; the test map and the test-run report; the build record (its ladder decisions, trace, and workbook statements applied); and, for a review-stage cause, the goldfish that ran in earlier rounds.
2. **Quote.** The instruction, statement, or test that let it through, with its file and line; or the file and section where the missing one belongs.
3. **A declined finding.** The user's reason is the evidence. "Not a bug, our convention is …" is a missing or wrong workbook fact. "The reviewer should not flag this" or "never ask for …" is a reviewer that reads too broadly (or, for a missed kind of problem, too narrowly): stage `review`, fixed in that goldfish at level 2. A reason that states a standing rule (should, never, always, our convention) is never a one-off; only "not now" or a choice for this change alone is.
4. **A repeat.** Of an open lesson: the cause the lesson named was right but nothing was fixed, so propose the fix now. A repeat of a lesson recorded as a one-off shows it was not one: the row names the real stage, and the lesson line keeps its text and only its count rises. Of an applied fix: that fix did not hold, so quote it and propose the next level up only when the evidence shows the lower level cannot work.
5. **Choose the level.** Apply [Where a fix may land](../../dev-core/references/self-edit.md#where-a-fix-may-land): try level 1 first, then level 2. Level 3 needs its "why not lower" reason written down; when you cannot write one from the files, the fix is level 1 or 2.

## Write the record

1. `LEARN start "<change folder>" --round <n>` writes `<change folder>/learn-<round>.md` from `dev-core`'s [learn template](../../dev-core/assets/templates/learn.md) with the title, change ID, and round filled in; keep its shape and add no sections.
2. One row per collected finding: the review ID, its lesson ID (filled in the next step), what it repeats, the stage, the quoted evidence, the smallest fix, the level, the target file (a workbook statement such as `csharp/Pitfalls`, a file path relative to the plugin, or `hook_rules`), the route, why not lower (level 3 only, else `-`), and the status `proposed`. A one-off gets route `none`, level `-`, and status `recorded`; its lesson line stays in the log, so a later repeat shows it was not a one-off.
3. **Lessons**, before or after the rows, as long as every row names its lesson before the check. A repeat of an open lesson: `LEARN lesson repeat "<lessons log>" --id <DL-ID>`, and the row names that lesson. Anything else: `LEARN lesson add "<lessons log>" --stage <stage> --change <change id> --finding <review ID> --where "<target file or location>" --text "<what went wrong and why>" --fix "<the proposed fix and its level, or none: one-off>"`; the row names the ID it returns.

## Check drift

1. List the docs the change touches or describes: files in the diff that are documentation (README, `docs/`, comments that state behaviour), the `TESTING.md` of each test folder the change touched, the behaviour `plan.md` states, and the commands the workbooks list for this project.
2. Compare each with the built code, and write one bullet per disagreement under Drift, quoting both sides with file and line. For `TESTING.md`, run `TESTINGMD check --workspace "<workspace>" --dirs <each test folder the change touched>` instead of reading it by eye; a stale folder is a drift item.
3. Leave out a disagreement a collected finding already covers (the finding's row holds it). "none found" when they agree. Drift is reported, never fixed here: each item can become a fix-later work item at the user's choice.

## Propose the fixes

1. `LEARN check "<change folder>/learn-<round>.md" --review "<change folder>/review-<round>.md" --lessons "<lessons log>" --state "<change folder>/state.json"` must return `"ok": true`; fix every problem it lists.
2. Ask in one message, worded for the user's technical level, with the `grilling` skill's method:
   - The report line from [SKILL.md](../SKILL.md#output-contract).
   - Repeats first, then the rest: per fix, the finding, the stage and its quoted evidence, the change as a short diff or statement, its level and target, and your recommendation (approve, or decline with why).
   - For a level 3 fix, its "why not lower" reason in the same line.
   - Each drift item, with "later" or "leave it" recommended.
   - "Reply with your choice for each, for example `R1-C1 yes, R1-T2 no: one-off`."
3. Wait for the answer; never assume a choice. Set each row's status to `approved` or `declined: <reason>`.

## Hand on and settle

Each approved fix goes to its owner; record the result in its row's status as `applied: <where it landed>` (a workbook statement ID, a file, or `hook_rules: <rule id>`).

1. **Workbook fact.** `dev-workbook`'s Propose with the statement, the technology, the section, the source `<change folder>/review-<round>.md` with the finding ID, and the layer (`project` unless the user says the fact is theirs everywhere); its own yes-or-no question is the user's approval already given, so pass the user's words. Applied when the write returns `"ok": true`.
2. **Hook rule.** Read the current `hook_rules` from `DEVCORE settings`, add the new rule (`id`, `match`, `action`, `reason`), show `DEVCORE setup --workspace "<workspace>" --values '{"hook_rules": [<all rules>]}'` as the preview, and write it with `--write` after the user's yes to the preview. Applied after the write.
3. **Goldfish, reference, or skill file.** Hand `skill-builder` the [change plan](../../dev-core/references/self-edit.md#the-change-plan) with `dev-learn` as the calling skill; its supplied change plan route checks it against the files and asks for its own approval. Applied when `skill-builder` delivers it; if it stops, the row stays `approved` with its reason in the status.
4. **Settle the lessons.** For each row now `applied` or `declined: <reason>`: `LEARN lesson remove "<lessons log>" --id <DL-ID>`, adding the IDs of any copies of the same lesson. Rows `recorded` or still `approved` keep their lessons.
5. Each drift item the user marked later becomes a work item, written the way `dev-review`'s Human review route writes a later finding: `wi/<next n>.md` from `dev-core`'s work-item template (`<next n>` follows the highest `n` in the state's `wi` list), recorded with `DEVCORE state "<change folder>" --patch '{"append": {"wi": {"n": <n>, "title": "<title>", "tracker_key": "wi/<n>.md", "depends_on": []}}}'`.
6. Run `LEARN check` again; it must return `"ok": true`. Close with one line per fix with where it landed, the lessons removed, and the next stage the change is at (unchanged by this skill).

## Skills and agents

- [SKILL.md](../SKILL.md) - the rules; [scripts/learn.py](../scripts/learn.py) - collect, lesson, and check.
- `dev-core` - the method, the templates, state, settings, and Setup for hook rules.
- `dev-workbook` - Propose; `dev-test` - the `TESTING.md` check; `skill-builder` - the supplied change plan route; `dev-review` - fix-later work items.
- `grilling` - the question method.
- No agents are used.
