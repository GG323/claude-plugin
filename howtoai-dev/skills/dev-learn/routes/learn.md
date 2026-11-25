# Route: learn

Done: `learn-<round>.md` passes `LEARN check`, the user has chosen for each proposed fix and drift item, each approved fix has landed with its owner, and settled lessons are gone from the log.

## Collect

1. `LEARN collect "<change folder>" --round <n> --lessons "<lessons log>"` lists every finding that is Critical, Major, declined (with the reason), or a likely repeat, with the open lessons and earlier applied fixes that look like the same problem.
2. Keep only real matches: the same cause, not only the same file. A finding collected only as a likely repeat, with no real match, drops out and gets no row.
3. When `nothing_to_learn` is true, run `LEARN start "<change folder>" --round <n>` and go to [Check drift](#check-drift); Propose the fixes then asks only about drift items, and with none, close with the report line alone.
4. Tell the user: "Learn round <n> of `<change id>`: <c> findings collected, <r> repeats."

## Find the root cause

For each finding, walk the [stage table](../../dev-core/references/self-edit.md#the-stage-that-let-it-through) and note every stage whose rules or facts would have caught it. Name the one whose fix also stops the problem in later changes (a missing workbook fact reaches every change; a missing test covers only this one); on a tie, the earlier stage. The others go into the evidence.

1. **Evidence:** the workbook statements from `WORKBOOK resolve --workspace "<workspace>" --stage review --paths <cited files> --markdown` (the receipts in `state.json` show what each stage read), the finding, `plan.md` and the work item, the test map and test-run report, the build record, and, for a review-stage cause, the goldfish that ran earlier. Quote what let it through with file and line, or the file and section where the missing one belongs.
2. **A declined finding:** the user's reason is the evidence. "Not a bug, our convention is …" is a missing or wrong workbook fact. "The reviewer should not flag this" or "never ask for …" is a goldfish reading too broadly (or too narrowly, for a missed kind): stage `review`, level 2 in that goldfish. A reason that states a standing rule (should, never, always, our convention) is never a one-off; only "not now" or a choice for this change alone is.
3. **A repeat** of an open lesson: the cause was right but nothing was fixed, so propose the fix now. Of a lesson recorded as a one-off: it was not one, so the row names the real stage and the lesson keeps its text with only its count raised. Of an applied fix: it did not hold, so quote it, and go a level up only when the evidence shows the lower level cannot work.
4. **The level:** apply [Where a fix may land](../../dev-core/references/self-edit.md#where-a-fix-may-land), level 1 first, then 2. Level 3 needs its "why not lower" reason written down; if you cannot write one from the files, the fix is level 1 or 2.

## Write the record

1. `LEARN start "<change folder>" --round <n>` writes `learn-<round>.md` from the template; keep its shape and add no sections.
2. One row per collected finding: review ID, lesson ID, what it repeats, stage, quoted evidence, smallest fix, level, target (a workbook statement such as `csharp/Pitfalls`, a path relative to the plugin, or `hook_rules`), route, why not lower (level 3 only, else `-`), and status `proposed`. A one-off gets route `none`, level `-`, and status `recorded`; its lesson stays in the log, so a later repeat shows it was not a one-off.
3. Every row names its lesson before the check. A repeat of an open lesson: `LEARN lesson repeat "<lessons log>" --id <DL-ID>`. Anything else: `LEARN lesson add "<lessons log>" --stage <stage> --change <change id> --finding <review ID> --where "<target file or location>" --text "<what went wrong and why>" --fix "<the proposed fix and its level, or none: one-off>"`, and the row names the ID it returns.

## Check drift

Compare the built code with the docs the change touches or describes: documentation files in the diff (README, `docs/`, comments that state behaviour), the behaviour `plan.md` states, the commands the workbooks list for this project, and the `TESTING.md` of each touched test folder, through `TESTINGMD check --workspace "<workspace>" --dirs <each test folder the change touched>` rather than by eye (a stale folder is a drift item). Write one Drift bullet per disagreement, quoting both sides with file and line, leaving out any a collected finding already covers; "none found" when they agree. Drift is reported, never fixed here; each item can become a fix-later work item at the user's choice.

## Propose the fixes

1. `LEARN check "<change folder>/learn-<round>.md" --review "<change folder>/review-<round>.md" --lessons "<lessons log>" --state "<change folder>/state.json"` must return `"ok": true`; fix every problem it lists.
2. Ask in one message, worded for the user's technical level, with the `grilling` method:
   - "Learn round <n>: <c> findings collected (<r> repeats), <p> fixes proposed, <d> drift items".
   - Repeats first, then the rest: per fix, the finding, the stage and its quoted evidence, the change as a short diff or statement, its level and target, and your recommendation (approve, or decline with why); a level 3 fix carries its "why not lower" in the same line.
   - Each drift item, with "later" or "leave it" recommended.
   - "Reply with your choice for each, for example `R1-C1 yes, R1-T2 no: one-off`."
3. Wait for the answer; never assume a choice. Set each row's status to `approved` or `declined: <reason>`.

## Hand on and settle

Each approved fix goes to its owner; its row's status becomes `applied: <where it landed>` (a workbook statement ID, a file, or `hook_rules: <rule id>`).

1. **Workbook fact.** `dev-workbook`'s Propose with the statement, the technology, the section, the source `<change folder>/review-<round>.md` with the finding ID, and the layer (`project` unless the user says the fact is theirs everywhere). Its own yes-or-no question is already answered by the user's approval, so pass the user's words. Applied when the write returns `"ok": true`.
2. **Hook rule.** Read the current `hook_rules` from `DEVCORE settings`, add the new rule (`id`, `match`, `action`, `reason`), write `{"hook_rules": [<all rules>]}` to a temporary file outside the workspace with the Write tool (a rule's `match` can name a production marker, and markers in a command's text make `dev-safe-target` deny it), show `DEVCORE setup --workspace "<workspace>" --values-file "<file>"` as the preview, and write it with `--write` after the user's yes to the preview. Applied after the write.
3. **Goldfish, reference, or skill file.** Hand `skill-builder` the [change plan](../../dev-core/references/self-edit.md#the-change-plan) with `dev-learn` as the calling skill; its supplied change plan route checks it and asks for its own approval. Applied when `skill-builder` delivers it; if it stops, the row stays `approved` with the reason in its status.
4. **Settle the lessons.** For each row now `applied` or `declined: <reason>`: `LEARN lesson remove "<lessons log>" --id <DL-ID>`, adding the IDs of any copies. Rows `recorded` or still `approved` keep their lessons.
5. **Drift marked later** becomes a work item, as `dev-review`'s Human review route writes a later finding: `wi/<next n>.md` from `dev-core`'s work-item template (`<next n>` follows the highest `n` in the state's `wi` list), written with the file tools (see `dev-core`'s [Plan folder contract](../../dev-core/SKILL.md#plan-folder-contract)) and recorded with `DEVCORE state "<change folder>" --patch '{"append": {"wi": {"n": <n>, "title": "<title>", "tracker_key": "wi/<n>.md", "depends_on": []}}}'`.
6. `LEARN check` again must return `"ok": true`. Close with one line per fix and where it landed, the lessons removed, and the change's next stage (unchanged by this skill).
