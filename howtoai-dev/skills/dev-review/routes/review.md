# Route: review

## Contents

- [Start the round](#start-the-round)
- [Collect the diff](#collect-the-diff)
- [Consult the workbook](#consult-the-workbook)
- [Pass 1: spec](#pass-1-spec)
- [Pass 2: quality](#pass-2-quality)
- [Collect the findings](#collect-the-findings)
- [Inspect the tests](#inspect-the-tests)
- [Score and verify](#score-and-verify)
- [Tally and hand on](#tally-and-hand-on)
- [Skills and agents](#skills-and-agents)

## Start the round

Entered from [SKILL.md](../SKILL.md#routes) at stage `review`.

1. **Check subagents.** Start one general-purpose subagent with only: "Reply with the word ready." If it cannot start or does not answer, halt: tell the user the review needs fresh subagents, which the harness did not start, and change nothing. A review by you alone would not be a goldfish review.
2. **The round.** `DEVCORE state "<change folder>" --patch '{"increment": {"review": 1}}'`; the round `<n>` is `loops.review` in the result.
3. **Re-review or first review.** Round 1 reviews the whole change. A later round reviews only the latest fix: the highest `n` in `builds` whose `route` is `fix`, built after the previous review.
4. **Declined findings.** Write `<change folder>/raw/review-<n>/declined.md` with one line per entry of `declined` in state (its finding and reason), or "none". Every brief names it.
5. Tell the user in one line: "Review round <n> of `<change id>`".

## Collect the diff

1. Round 1: `REVIEW diff "<change folder>" --round <n>`. A later round: `REVIEW diff "<change folder>" --round <n> --since-build <fix build n>`.
2. When `empty` is true, there is nothing to review: say so, set the stage back to the one before (`test`), and stop.
3. `REVIEW receipts "<change folder>" --round <n>`. It writes `process.md`, the process viewpoint's findings table, into the round's raw folder.

## Consult the workbook

1. `WORKBOOK resolve --workspace "<workspace>" --stage review --paths <the changed files, with their project files> --topics Pitfalls "Idioms and patterns" Security Performance Testing --markdown`, saved as `<change folder>/raw/review-<n>/workbook-statements.md`.
2. Run it again without `--markdown` for the receipt, and record it: `DEVCORE state "<change folder>" --patch '{"append": {"receipts": <receipt>}}'`.
3. A technology in `missing` does not stop the review: brief the reviewers without its statements, and say in Test inspection which technology had no workbook.

## Pass 1: spec

1. Start `goldfish-spec` with the brief [references/viewpoints.md](../references/viewpoints.md#what-each-brief-holds) gives it and the prefix `R<n>-S`. Save its reply exactly as it came to `raw/review-<n>/spec.md`.
2. Read its table. When it has a Critical finding (a criterion not built, or must-not-change behaviour broken), skip pass 2: the change is not complete, so quality findings would be about code that is about to change. Say so in the chat line and go to [Collect the findings](#collect-the-findings).

## Pass 2: quality

1. Pick the viewpoints from the diff with the [Which run](../references/viewpoints.md#which-run) table, and say which and why in one line.
2. Start them in one message, each with its brief and prefix (`R<n>-C`, `R<n>-T`, `R<n>-X`, `R<n>-P`, `R<n>-W`). Save each reply exactly as it came to `raw/review-<n>/<viewpoint>.md`.

## Collect the findings

1. `FINDINGS collect "<change folder>/raw/review-<n>" --kind code`. It merges every reply in the round's raw folder, `process.md` included, and turns the same problem raised by two reviewers (same location and quote) into one finding that names the other. When it refuses a reply (an impact off the scale, a duplicate ID), send that reviewer the error and ask for its table again, then collect again.
2. The goldfish searched wide, so the same problem can come back from two viewpoints in different words, and some findings lie outside the change. Keep them all in the round: the scorer scores repeats low, the tally sends outside findings to their own section, and you point out any remaining repeat to the user in [Human review](human-review.md#ask-for-the-choices). Never drop a finding because it is outside the change.

## Inspect the tests

You check the evidence the reviewers can only read about.

1. Read the latest test-run report and its result files, and the test data the changed code is tested with. Note what ran, what passed, and which changed lines the tests reach.
2. For a finding that a test could confirm or refute, or a gap the reviewers named, write a temporary test next to the existing tests, named `Review<n>_<what>` (or the framework's equivalent), end-to-end when the finding is about a user path. Run the tests through `dev-test`'s Run route as a progress run; its target checks and safety rules apply. A temporary test that fails as the finding predicts makes the finding **confirmed**: ask its reviewer to mark it so, or note it for the scorer.
3. Remove every temporary test, run the tests once more to show the suite is as it was, and list each temporary test with its result. Keeping one in the suite is the user's decision: ask at the human review, and note it as a fix-now finding if they agree.
4. Write the inspection notes as three bullets in `raw/review-<n>/inspection.md`: **Runs** (what ran and the results), **Temporary tests** (each one, what it showed, and that it was removed), **Coverage gaps** (changed lines no test reaches; "none").

## Score and verify

1. When the collected findings are none, skip to [Tally and hand on](#tally-and-hand-on).
2. Start both in one message: `goldfish-scorer` with `findings.md`, the diff, and the files the findings cite; and, when `high-impact.md` exists, `goldfish-verifier` with that file, the diff, `plan.md`, the test-run report, and the cited files. Save their tables as `raw/review-<n>/scores.md` and `verdicts.md`.

## Tally and hand on

1. `FINDINGS tally "<change folder>/raw/review-<n>" --kind code --round <n> --threshold <review.confidence_threshold> --title "<title>" --change-id <id> --size <size> --diff "<base>..working tree" --changed "<change folder>/raw/review-<n>/changed.json" --inspection "<change folder>/raw/review-<n>/inspection.md" --out "<change folder>/review-<n>.md"`. Findings under the threshold, refuted findings, and findings on lines this round did not change go to the appendix with the reason.
2. Set the stage: `DEVCORE state "<change folder>" --patch '{"stage": "human-review"}'`.
3. Tell the user one line: "Review round <n>: <kept> findings kept (<c> Critical, <m> Major, <mi> Minor, <ni> Nit), <h> held back." Then go to the [Human review](human-review.md) route in the same turn.

## Skills and agents

- [SKILL.md](../SKILL.md) - rules and checks; [references/viewpoints.md](../references/viewpoints.md) - which reviewers run and what they get.
- `dev-core` - the round counter and `findings.py`; `dev-workbook` - the statements; `dev-test` - the test runs.
- Agents: `goldfish-spec`, `goldfish-correctness`, `goldfish-tests`, `goldfish-security`, `goldfish-performance`, `goldfish-scorer`, `goldfish-verifier`.
