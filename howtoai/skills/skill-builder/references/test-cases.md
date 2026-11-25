# Test cases

## Contents

- [Why save test cases](#why-save-test-cases)
- [Folder layout](#folder-layout)
- [prompt.md](#promptmd)
- [case.yaml](#caseyaml)
- [Graders](#graders)
- [Input files](#input-files)
  - [Connector fixtures](#connector-fixtures)
- [Trigger requests](#trigger-requests)
- [Running saved test cases](#running-saved-test-cases)

## Why save test cases

[Test](../stages/test.md#run-and-deliver) saves approved tests in the target skill's `evals/` folder so that every later fix can rerun them as regression tests. The layout is the one `claude plugin eval` reads.

Save only tests that are safe to rerun without manual setup: read-only tests, tests with disposable inputs, and tests that use dry runs or mocks. List any other approved test in the delivery as not saved, with the reason.

**A test where the target skill asks a question** cannot run unattended past the question, because a saved case has no scripted answer. Save it up to the question: `prompt.md` holds the request as the user typed it, and the graders judge the question itself — that it is asked, before anything is written or sent, and what it asks. The branch after the answer is tested by the main agent in [Test](../stages/test.md#how-tests-run), and the delivery lists it as not saved.

## Folder layout

```text
<target-skill>/
└── evals/
    ├── <case-name>/
    │   ├── prompt.md
    │   ├── case.yaml
    │   ├── graders/
    │   │   └── 01-<few-words>.md
    │   ├── files/            # only when the test needs input files
    │   └── place-files.sh    # only when files/ exists
    └── trigger-queries.json  # only when trigger tests were approved
```

The case name is the folder name: lowercase letters, digits, and hyphens, starting with a letter, saying in a few words what the test checks (for example, `flags-missing-owner`). Do not use `results`, `mocks`, `node_modules`, `files`, `true`, `false`, or `null`; these names are reserved or do not read as text.

## prompt.md

A settings block, then the request exactly as a user would type it.

```markdown
---
tags: [skill-builder]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Here are my notes from today's planning call, can you write them up?
```

Use only these four settings keys; an unknown key makes the test case fail to load. Keep free text out of the settings block, because the block ends at the first `---`, even mid-sentence. Narrow `allowed_tools` to what the test needs.

## case.yaml

```yaml
schema_version: "1.1"
name: flags-missing-owner
expected_outcome: |
  The notes list every action item; items without an owner are marked "unassigned".
```

Quote `schema_version`, or it is read as a number and the case fails to load. `name` matches the folder name.

## Graders

One file per verifiable statement, numbered to keep the order (`01-lists-all-actions.md`, `02-marks-unassigned.md`). Each file has the same block on top; the body is the statement.

```markdown
---
type: llm
focus: trace
weight: 1
---

Every action item from the source appears in the action-item table.
```

Word each statement about the result itself, not about where the test run saved it. When where files end up is the result (for example, a skill that organizes folders), name the expected locations. `focus: trace` lets the judge see what the run did, not only its final message.

A test case needs at least one grader to load. For a subjective test whose judgment stays with the user, add one placeholder grader whose body is `The result matches this description: <expected outcome>`, and do not grade it yourself.

## Input files

Put input files in the case's `files/` folder and end the prompt with a line naming them, for example `Input files: notes.txt`. Add `place-files.sh` next to `prompt.md`:

```bash
#!/usr/bin/env bash
set -eu
cp -R "$(dirname "$0")/files/." .
```

and name it in `case.yaml`:

```yaml
context:
  scaffold_script: place-files.sh
```

Input files follow the privacy rule in [Every target skill](skill-types.md#every-target-skill): synthetic or anonymized data only.

- **File dates.** Copying files (and git) resets their modification dates. When the target skill uses file dates, set them explicitly in `place-files.sh` (for example, with `touch -d`), and give the skill's script a fixed "as of" date in the prompt.
- **Generated inputs.** Do not save large or binary inputs such as videos. Generate them in `place-files.sh` instead (for example, `ffmpeg` test sources), and say in `expected_outcome` which tool the generation needs.
- **Shared inputs.** Keep fixtures small and copy them into each case's `files/`; every case must load on its own.
- **Planted and clean cases.** For a skill that enforces rules or refuses unsafe input, pair each planted-violation case with a clean case, preferably in a different style, and run the planted case once without the skill as a baseline: the clean case shows the skill does not flag good input, and the baseline shows what the skill adds.
- **Later stages of a process.** A case for a later stage starts from what the earlier stages really leave: every artifact, written by their own scripts or in their exact format (for example a test map, a red-check report, `state.json`, and the index), and a git repository when the skill reads git, created and committed in `place-files.sh`. With a file missing or hand-shaped, test subagents improvise or report false bugs. When the later stage checks what changed, also run the earlier stage's real step inside the case (for example, the test run before a build's gate): files that step rewrites on every run, such as a generated `TESTING.md`, must be left out of the later stage's checks, and only a real run shows whether they are; otherwise agents revert them as unapproved changes.
- **Results that depend on the machine.** Word `expected_outcome` so it holds on any machine, or state the requirement in it (for example, "needs FFmpeg; without it the skill stops with install steps").

### Connector fixtures

A target skill that reads a connector (mail, calendar, documents) is tested without real accounts through fixtures: files that stand in for the connector's answers. Keep them in `files/connectors/`:

```text
files/connectors/
├── CONNECTORS.md
├── calendar-list-events.json
└── gmail-get-thread.json
```

`CONNECTORS.md` starts with the "as of" line and maps each tool call the target skill makes to the JSON file that answers it:

```markdown
As of: 2026-03-12 09:30, time zone Europe/Riga

| Tool call | Arguments | Answer file |
| --- | --- | --- |
| list events | next 7 days | calendar-list-events.json |
| get thread | the thread linked in the event | gmail-get-thread.json |
```

- Shape each JSON file like the real tool's output, including the fields a search or list result leaves out, so the target skill meets the same partial records it meets in real use.
- The "as of" date, time, and time zone are explicit, and the target skill uses them instead of the machine clock, so "next meeting" or "overdue" gives the same answer on every rerun.
- End `prompt.md` with a setup line after the request, in place of setup notes each test would otherwise invent: `Connectors are replaced by fixtures: read files/connectors/CONNECTORS.md and, instead of calling a listed tool, read its answer file. Use its "as of" date and time zone as now.`
- Fixtures cover read-only calls only. A target skill that writes through a connector is tested on drafts in the sandbox, never through a fixture that pretends a send succeeded.
- Fixture contents follow the privacy rule above: invented people, addresses, and messages.

## Trigger requests

Save approved trigger tests as `evals/trigger-queries.json`, a list of requests with whether each should load the target skill:

```json
[
  {"query": "can u turn my call notes from this morning into proper minutes", "should_trigger": true},
  {"query": "summarize this PDF report for me", "should_trigger": false}
]
```

## Running saved test cases

- **By the main agent:** sync the test copy, give each test case's prompt and input files to a test subagent, then grade the results against the graders, as [Test](../stages/test.md#how-tests-run) does for any test.
- **By the user:** with Claude Code v2.1.269 or later, from the test copy's folder in `~/.claude/skills/`, `claude plugin eval . --allow-tools Write,Edit,Bash` (add `--scaffold` when a test case has input files). These are real, billed model runs, so offer the command rather than running it unasked.
