# Route: fix

## Contents

- [Start the fix](#start-the-fix)
- [Fix and trace](#fix-and-trace)
- [Gate and record](#gate-and-record)
- [Skills and agents](#skills-and-agents)

## Start the fix

Entered from [SKILL.md](../SKILL.md#routes) at stage `human-review`, after the user marked findings in the latest `review-<round>.md`.

1. Take the review file with the highest round. The findings to fix are the rows whose Your choice is `fix now`; `later` findings become work items through `dev-plan`, and `decline` findings are already recorded by `dev-review`. Their finding IDs (`R<round>-<letter><n>`, for example `R1-C2`) are the only IDs a hunk can trace to.
2. The build number `<n>` is one more than the highest `n` in `builds`. Tell the user in one line: "Applying <count> fix-now findings from review round <round> (build <n>)".
3. Set the stage to `build` with `DEVCORE state "<change folder>" --patch '{"stage": "build"}'`.

## Fix and trace

1. Consult the workbook for the files the findings name, as the Build route's [Consult the workbook](build.md#consult-the-workbook) section says. When `build.gate` is empty, set it next, as its [Set the gate](build.md#set-the-gate) section says.
2. `BUILD start "<change folder>" --n <n> --wi <the work item the findings belong to, or whole> --route fix --review review-<round>.md`, then run the gate's baseline as in [Snapshot and baseline](build.md#snapshot-and-baseline).
3. Apply each finding's proposed fix, or a smaller one that fully fixes it, with [the ladder](../SKILL.md#the-ladder) and the callers search, as in the Build route's [Find the callers](build.md#find-the-callers) and [Climb the ladder and edit](build.md#climb-the-ladder-and-edit) sections. A fix that would change a test, CI, or a lockfile needs the user's approval with its paths, as there. A fix-now mark covers a change to a test only when the finding's proposed fix names that test file: record that approval with its `"paths"` and `"by": "fix-now choice"`, never `"by": "user"`. Any other change to a test, to CI, or to a lockfile stops and asks, as in the Build route.
4. Trace every hunk to its finding ID, as in [Trace every hunk](build.md#trace-every-hunk).

## Gate and record

1. Run the gate with `--label after` and fix within `build.max_fix_rounds`, as in [Run the gate](build.md#run-the-gate), except for the tests: `dev-test`'s Run route runs them at stage `test`, after this route.
2. Write `build-<n>.md` with Route `fix`, run `BUILD check`, and record the build with `"route": "fix"`, as in [Record and hand on](build.md#record-and-hand-on). The stage moves to `test`, so `dev-test` and then `dev-review` run again on the changed files.
3. Close with the short report: the findings fixed, any finding you could not fix and why, the gate, and the Skipped or unchecked lines.

## Skills and agents

- [Build route](build.md) - the steps this route reuses; [SKILL.md](../SKILL.md) - the rules and checks.
- `dev-review` - writes the review file and runs again after `dev-test`.
- No agents are used.
