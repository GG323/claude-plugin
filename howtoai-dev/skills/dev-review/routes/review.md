# Route: review

Done: `review-<n>.md` tallied from every reviewer's findings and your own test inspection, the stage at `human-review`, and the Human review question asked in the same turn. Entered from [SKILL.md](../SKILL.md#routes) at stage `review`.

## Start the round

1. **Subagents.** Start no probe. When the harness has no way to start subagents, halt here; when the first reviewer in [Pass 1](#pass-1-spec) cannot start or does not answer, halt there. Either way, tell the user the review needs fresh subagents, which the harness did not start, and change nothing: no state, no round, no receipt, no findings, no review.
2. **The round.** `<n>` is one more than `loops.review` in state (none counts as 0). Record nothing yet: Pass 1 records the round and its receipt once the first reviewer answered, so a halt leaves state as it was and a retry is the same round.
3. **Scope.** Round 1 reviews the whole change. A later round reviews only the latest fix: the highest `n` in `builds` whose `route` is `fix`, built after the previous review.
4. **Declined findings.** Write `raw/review-<n>/declined.md` (under the change folder), one line per entry of `declined` in state (its finding and reason), or "none"; every brief names it. In a round after a fix, also write `raw/review-<n>/fix-now.md` with only the previous round's fix-now rows (ID, finding, fix), for the spec brief.
5. Tell the user: "Review round <n> of `<change id>`".

## Collect the diff

1. Round 1: `REVIEW diff "<change folder>" --round <n>`. A later round: `REVIEW diff "<change folder>" --round <n> --since-build <fix build n>`.
2. When `empty` is true, say so, set the stage back to `test`, and stop.
3. `REVIEW receipts "<change folder>" --round <n>` writes `process.md`, the process findings table, into the round's raw folder.

## Consult the workbook

1. `WORKBOOK resolve --workspace "<workspace>" --stage review --paths <the changed files, with their project files> --markdown`: its last line is the receipt Pass 1 records.
2. Run it again with `--versions` in place of `--markdown`, saved as `raw/review-<n>/workbook-resolve.json`, for the compliance reviewer.
3. A technology in `missing` does not stop the review: say in Test inspection which technology had no workbook.

## Pass 1: spec

1. Start `goldfish-spec` with its brief from [viewpoints](../references/viewpoints.md#what-each-brief-holds) and the prefix `R<n>-S`. Save its reply exactly as it came to `raw/review-<n>/spec.md`, then record the round and the receipt: `DEVCORE state "<change folder>" --patch '{"increment": {"review": 1}, "append": {"receipts": <receipt>}}'`.
2. When it has a Critical finding (a criterion not built, or must-not-change behaviour broken), skip pass 2, say so in the chat line, and go to [Collect the findings](#collect-the-findings).

## Pass 2: quality

1. Pick the viewpoints with the [Which run](../references/viewpoints.md#which-run) table and say which and why in one line.
2. Start them in one message, each with its brief and prefix (`R<n>-C`, `R<n>-T`, `R<n>-X`, `R<n>-P`, `R<n>-W`). Save each reply exactly as it came to `raw/review-<n>/<viewpoint>.md`.

## Collect the findings

1. `FINDINGS collect "<change folder>/raw/review-<n>" --kind code` merges every reply, `process.md` included, and folds the same problem from two reviewers (same location and quote) into one.
   - A reviewer is blocked, or a reply has neither a table nor "No findings": run that reviewer once more; a second time, stop and tell the user what it could not read.
   - A reply refused for another reason (an impact off the scale, a duplicate ID): send that reviewer the error, ask for its table again, and collect again.
2. Keep every finding in the round, repeats and outside findings too: the scorer scores repeats low, the tally gives outside findings their own section, and you point out a remaining repeat in [Human review](human-review.md#ask-for-the-choices). Never drop a finding because it is outside the change.
3. A finding the change causes that the tally would file as "unchanged line": ask that reviewer to cite the changed line it depends on, then collect (and tally) again.

## Inspect the tests

Check the evidence the reviewers can only read about.

1. Read the latest test-run report, its result files, and the test data the changed code is tested with: what ran, what passed, which changed lines the tests reach.
2. Where a test could confirm or refute a finding, or fill a gap a reviewer named, write a temporary test next to the existing ones, named `Review<n>_<what>` (or the framework's equivalent), end-to-end when the finding is about a user path. Run it through `dev-test`'s Run route as a progress run; its target checks and safety rules apply.
3. A temporary test that fails as predicted makes the bug **confirmed**, also when no reviewer raised it: add a row to `raw/review-<n>/confirmed.md` in the code reviewers' table shape, with the ID `R<n>-I<m>`, an impact on that scale, the changed line it depends on (or `outside` in Change), and the test as its Mark. Run `FINDINGS collect` again; these rows get confidence 100 and need no score or verdict.
4. Remove every temporary test and run the tests once more to show the suite is as it was. Keeping one is the user's decision at the human review (a fix-now finding if they agree). A temporary test found still in the suite later is removed, the tests rerun, and noted in Test inspection.
5. Write `raw/review-<n>/inspection.md` as three bullets: **Runs** (what ran, the results), **Temporary tests** (each one, what it showed, that it was removed), **Coverage gaps** (changed lines no test reaches, or "none").

## Score and verify

1. With no collected findings, skip to [Tally and hand on](#tally-and-hand-on).
2. Start both in one message: `goldfish-scorer` with `findings.md`, the diff, and the files the findings cite; and, when `high-impact.md` exists, `goldfish-verifier` with that file, the diff, `plan.md`, the test-run report, and the cited files. Save their tables as `raw/review-<n>/scores.md` and `verdicts.md`.

## Tally and hand on

1. `FINDINGS tally "<change folder>/raw/review-<n>" --kind code --round <n> --threshold <review.confidence_threshold> --title "<title>" --change-id <id> --size <size> --diff "<base>..working tree" --changed "<change folder>/raw/review-<n>/changed.json" --inspection "<change folder>/raw/review-<n>/inspection.md" --out "<change folder>/review-<n>.md"`. Findings under the threshold, refuted findings, and findings on lines this round did not change go to the appendix with the reason.
2. `DEVCORE state "<change folder>" --patch '{"stage": "human-review"}'`.
3. Tell the user: "Review round <n>: <kept> findings kept (<c> Critical, <m> Major, <mi> Minor, <ni> Nit), <h> held back." Then run [Human review](human-review.md) in the same turn.
