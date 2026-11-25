# Self-edit and root-cause method

`dev-review` and `dev-deploy` use this method to correct their own instructions, and `dev-learn` for every finding it collects after a review round. Done is the smallest approved fix at the lowest level that resolves the problem, handed on and recorded.

## When it applies

- A negative user response ("That finding is wrong", "never deploy on Fridays").
- An execution error (a failed pipeline step, a wrong command, a missing permission).
- A repeated correction (the same step fixed by hand in two runs).
- A serious, declined, or repeated review finding (a Critical bug the tests missed, a decline with a reason, a finding that matches an earlier lesson).

## The stage that let it through

For a review finding, note every stage whose rules or facts would have caught it, and name the one whose fix also stops the problem in later changes (on a tie, the earlier stage), with evidence:

| Stage | It let the problem through when |
| --- | --- |
| `plan` | The plan or a work item never stated the behaviour, the edge case, or the constraint. |
| `tests` | The plan stated it, but no test checks it, or a test checks the wrong thing. |
| `workbook` | A technology fact or project convention that would have prevented it is missing or wrong in a workbook. |
| `build` | The plan, tests, and workbooks were right, and the build did not follow them (the ladder, a workbook statement, scope). |
| `review` | An earlier review round saw the code and no viewpoint covers this kind of problem. |
| `deploy` | Only for `dev-deploy`: a deploy step, check, or rule. |
| `one-off` | Nothing general would have caught it: a slip, or a preference of this change only. |

Evidence is a quote with its file and line: the instruction that allowed it, or the place a missing statement belongs. When the agent improvised because no instruction covered the case, say so.

## Where a fix may land

The lowest level that resolves it. The dev skills' own files change only when the evidence shows that neither lower level can.

1. **A workbook or another reference file.** A technology fact goes to a workbook through `dev-workbook`; a rule a hook can enforce, to the project's `hook_rules`; checklists, rubrics, examples, and briefs, to reference and template files (`references/`, `assets/`).
2. **A goldfish.** A change to an `agents/goldfish-<name>.md` reviewer, or a new goldfish, when a review viewpoint is missing or reads too narrowly.
3. **A skill file.** A dev skill's `SKILL.md`, `routes/`, or `stages/` file, only for a process step itself: what a stage does, when it asks, or what it hands on. Record why levels 1 and 2 cannot resolve it: for example, a reference file the skill never reads at that step, or a goldfish that never runs there.

## The four steps

1. **Quote** the exact instruction, rule, or statement that produced the problem, with its file and line. When the agent improvised, say so: the fix is then a missing instruction, quoted as the place it belongs.
2. **Classify.**
   - A technology fact (how a language, framework, or tool behaves, or this project's convention for it) belongs to `dev-workbook`, never to a skill.
   - A rule a hook can enforce (a command or path to block or warn about) belongs to the project's `hook_rules`.
   - A process instruction (what a stage does, when it asks, which reviewer runs) gets a [change plan](#the-change-plan) at the lowest level that resolves it.
   - A one-off preference of this change only is recorded where the stage records choices (for example a decline reason), and nothing is edited.
3. **Show the smallest change** as a diff of the quoted text, with its level, and ask the user for approval in one message: the quote, the cause, the diff, and where it goes. Never apply it on your own.
4. **Hand on and record**, after a yes:
   - A technology fact: `dev-workbook`'s Propose, with the user's words or the finding as the evidence.
   - A hook rule: `dev-core`'s Setup preview with the new `hook_rules` entry added to the existing ones, then the write after the user approves the preview.
   - A process instruction: `skill-builder` with the change plan as its brief, through its supplied change plan route; it changes the file, checks it, and tests it.
   - Record what happened in the stage's own record: the review doc's Your choice cell, the learn record, or the deploy log.

## The change plan

Give `skill-builder` exactly these items, so its supplied change plan route can check them against the files without asking again:

- **Target files:** each path, relative to the plugin, and its level.
- **Cause:** the quoted instruction and the evidence that exposed it (the finding, error, or user response, quoted).
- **Smallest change:** the exact new wording, or the diff.
- **Why not lower:** for a level 3 change, why a workbook, reference file, or goldfish cannot resolve it.
- **Calling skill:** `dev-review`, `dev-learn`, or `dev-deploy`, and the change ID.
