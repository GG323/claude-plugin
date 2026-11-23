# Test

## Contents

- [Check and design tests](#check-and-design-tests)
  - [Check](#check)
  - [Design candidate tests](#design-candidate-tests)
  - [How tests run](#how-tests-run)
  - [Rate risk](#rate-risk)
- [Ask for approval once](#ask-for-approval-once)
- [Run and deliver](#run-and-deliver)
  - [Run and fix](#run-and-fix)
  - [Design pass](#design-pass)
  - [Save and deliver](#save-and-deliver)
- [Skills and agents](#skills-and-agents)

## Check and design tests

Test covers every kind of target: a skill, a tool (slash command, subagent, plugin, mod, hook or settings change, MCP server or connector), or a procedure built from them. Where this stage says "skill", read the target's kind.

When the plan reused a candidate as published, or only verifies a third-party target, its files must stay identical to the copy `skill-finder` vetted and compared, so nothing in this stage edits them: of the checks in [references/check-brief.md](../references/check-brief.md#the-checks), run only check 1 (it is discoverable and loads), design one safe test of its main use, save no test case in its folder, and send any problem back to [Plan](plan.md#inspect-the-target-context) (adapt it, or choose another candidate) instead of the fix loop.

### Check

The checks are low-risk and read-only, and they live in one place: [references/check-brief.md](../references/check-brief.md#the-checks). This section says who runs them and what happens with the results.

1. **Start the checker.** Start a fresh built-in general-purpose subagent with the prompt in [check-brief.md](../references/check-brief.md#start-the-checker), filled in, so the files are judged by an agent that does not know what the author intended. Ask for all checks, or, for a small change, the checks the change affects (see [Test depth](#design-candidate-tests)). Starting it is part of this process, like the test subagents in [How tests run](#how-tests-run). The checker stays read-only and returns pass, pass (exception), fail, or not checked for each check, with evidence; a result without evidence counts as not checked.
2. **Fix what the plan covers.** Fix each failed check that the approved plan covers right away; fixes within the approved plan need no approval.
3. **List the rest.** A failure in text this run did not change, which the approved plan does not cover — a defect that was already there, or a requirement added to `skill-builder` after the target was built — is never fixed silently. List each one in [Ask for approval once](#ask-for-approval-once) with a recommendation (fix it in this run, or leave it and name it in the delivery), and fix only the ones the user approves.
4. **Recheck.** Send the numbers of the failed checks back to the checker: to the same subagent when the harness can message it, otherwise to a fresh checker that runs only those numbers. Repeat until they pass or only listed failures remain.
5. **Record** each check as passed, failed, or not checked, with its evidence and any fix. Each not-checked item carries the reason it was skipped, so the record never shows a skipped check as passed.

If the harness cannot run subagents, the main agent runs the same checks itself and labels the record **self-check** in the delivery: it is weaker evidence, because the author checks their own work.

### Design candidate tests

**Test depth.** Size the checks and tests to the work, and state the tier and its reason in the approval message. Everything at more depth runs when the user asks for it.

| Work | Checks | Tests |
| --- | --- | --- |
| Small change: a few lines that keep the description, output contract, and permissions | The checks the change affects | The saved test cases in `evals/`, plus one test of the changed behavior. Trigger tests only if the description changed. No baseline. |
| Larger change | All | The saved test cases, plus typical and edge tests of the changed parts. Trigger tests only if the description changed. No baseline. |
| New target or remake | All | Every candidate below that applies, including the baseline and trigger tests. |
| Verification only ("make sure it works") | All | The saved test cases, plus a typical and an edge test. No previous-version baseline: nothing was built, so it would test the same version twice. |
| Reused as published, or verifying a third-party target | Check 1 only | One safe test of its main use, as above. |
| Full depth, on the user's request | All | Every candidate below that applies, with the baseline against the previous version for a change. |

Derive the tests for the tier from the triggers, workflow, output contract, and success check:

- Every test case already saved in the target skill's `evals/` folder, as regression tests.
- Tests the recall note lists as having worked for this skill type, adapted to this target skill.
- A typical request that should trigger the target skill and exercise its main workflow.
- A meaningful edge case, such as a missing or very large input.
- **Baseline test** (for the tiers that include it): run the typical request twice, in two separate subagents — one with the target skill, one without it (for a remake or a full-depth change, with the copy of the previous version that [Build](build.md#before-writing) kept) — and compare the results. Give both the same request, including any constraints a user would normally type. Judge both outputs by the output contract's success check and the skill's own **Verify the output** method, including any bundled check script. The target skill adds value when it passes where the baseline fails, or reaches the same result more reliably, faster, or with less guidance. When a capable agent is likely to do the main job without the skill (audits, reviews, page design), aim the comparison at what a single run cannot improvise: scripted checks, a fixed report shape, stable numbering, routing to other skills, ask-first gates, and run logs. If it adds nothing, say so in the delivery. If the harness cannot run subagents but the skill bundles scripts, run the old and new scripts on the same inputs instead; otherwise leave the baseline out and say so.
- **Comparison test** (when the design took ideas from a third-party skill that `skill-finder` vetted): run the original skill on the same saved cases, from its vetted isolated copy (vet it again if that copy was deleted), never installed. Its brief names only the original: `Skill: do not use the skill named <name>. Read <vetted copy>/SKILL.md and follow it.` Compare the results the same way as the baseline. Since the original often finds the same thing, say what this version adds: scope kept, records and checks the original lacks, and ask-first gates. Report the comparison in the delivery; it never puts the original's text into the target skill.
- **Trigger tests** (when the description is new or changed): 6–10 realistic requests, about half that should load the target skill and half near-misses that share its keywords but need something else. The test copy is discoverable, so where the harness can run a fresh session (for example, `claude -p "<request>"`), run each and record whether the target skill loaded. Otherwise, judge each request against the description as a check, and report it as a check, not a test.
- Output tests with clear pass criteria, using the **Verify by** method for the target skill's type in [references/skill-types.md](../references/skill-types.md); for subjective writing or design, a short rubric with judgment left to the user.
- Feature tests only for features the target skill has: a run that updates and prunes `state/`; an unreachable source that leads to a user question; an idea-generation run that returns distinct candidates and one chosen result; a fixed-list request that returns items unchanged.

Offer checks only when no test adds useful evidence.

### How tests run

**Test copy.** Tests run against a copy of the target skill in the personal skills folder, `~/.claude/skills/<name>/` (on Windows `%USERPROFILE%\.claude\skills\<name>\`), so the skill is discoverable and `${CLAUDE_SKILL_DIR}` points to a real installed folder. Other kinds go where the harness discovers them: a subagent in `~/.claude/agents/`, a plugin through `claude --plugin-dir <plugin-directory>`, and a hook, settings change, or MCP configuration where the approved plan or the `update-config` handoff put it. Before the first test, sync the target skill's current files into that folder, replacing an earlier copy of the same skill. Sync again after every fix round, because fixes are made in the source files. Before each sync, delete any `__pycache__` folder in the source files, because it is not part of the skill. Skip the copy when the target skill already lives in, or is linked into, that folder. If the folder holds a different skill with the same name, stop and return to [Plan](plan.md).

**Test outputs.** All of this run's test outputs go in `<run>/` in the [sandbox](../SKILL.md#vocabulary), unless the plan names another place; `<run>` is the time Test started, as `<YYYYMMDD-HHMM>`, read from the system clock. Each test writes only inside its own subfolder, `<run>/<test-id>/`, and a rerun in a fix round writes in a new one (`<test-id>-r2`), so this run's outputs stay apart from earlier runs, earlier rounds, Build's `baseline/` copy, and Plan's probes. New test cases and their input files wait in `<run>/cases/<case-name>/`, in the layout of [references/test-cases.md](../references/test-cases.md), until [Save and deliver](#save-and-deliver) saves the approved ones in `evals/`. [Learn](learn.md#clean-up) deletes the sandbox after delivery, so the delivery report must carry the test evidence.

**Before the first test.** Install what the target skill needs to run, as the approved plan lists it under the [missing-tools rule](../SKILL.md#core-rules), because the test brief forbids installs. Check that each fresh install runs in this shell, using its full path when PATH is stale, and put those paths in the brief's Environment line.

Run each test in a separate subagent, except as **Nested subagents** below says, so the result is not shaped by what this conversation already knows. Starting these subagents is part of this process: the user's request to build or change a skill counts as asking for them. Give every test subagent the same brief, filled in for the test:

```text
You are testing a skill or tool. Act as its main agent; you are not its author.

Skill: use the skill named <name>. If it is not in your skill list, read
<test copy folder>/SKILL.md and follow it, reading ${CLAUDE_SKILL_DIR}
as <test copy folder>.
Request: <the test's prompt, exactly as a user would type it>
Inputs: <absolute paths of the test's input files, or "none">
Working directory: <absolute path the run treats as the user's folder>
Environment: <fresh installs and their full paths, tool notes, or "none">

Limits:
- Write only inside <sandbox folder for this test>. The skill's own scripts
  may also create and remove their own temporary files where they normally
  do. Name any temporary folder you create yourself <test-id>-<purpose>,
  because other tests run at the same time.
- Do not send, post, publish, or write through any connector or external
  service. Read connectors only if this brief says so. If it names a
  fixture folder, read its CONNECTORS.md and use the mapped files instead
  of the connector.
- Do not install anything; if a tool is missing, report it and stop.
- The user is unavailable. If the skill tells you to ask the user
  something, stop and return the exact question instead of guessing.
- The AGENTS.md and CLAUDE.md files on disk are current. Where they differ
  from the copy you were given at the start, the files on disk win.
- Where the skill's instructions differ from workspace instructions
  (AGENTS.md, CLAUDE.md), follow the skill.

Return:
1. The deliverable, or its path.
2. The report the skill tells you to give.
3. A log of every tool call and every file written, in order.
4. Every instruction that was unclear, contradictory, or missing.
```

For a target that is not a skill, the Skill line says how to use it instead, for example "use the agent named <name>" or "run the command /<name>".

**Baseline brief.** The installed test copy carries the new version under the target's name, so a baseline run that is told to use the skill by name would test the new version. The baseline brief changes only the Skill line, so that it names the baseline alone:

- For a remake or a change: `Skill: do not use the skill named <name>. Read <baseline folder>/SKILL.md and follow it, reading ${CLAUDE_SKILL_DIR} as <baseline folder>.`
- For a new target: `Skill: do not use the skill named <name> or any copy of it; do the task as you would without it.`

When a test subagent returns a question, answer it as the test plan says by sending the answer to the same subagent, so the branch after the question is tested too.

**Confirmation gate.** A confirmation that unlocks a consequential step, such as rendering or writing the deliverable, can be blocked when it is relayed: Claude Code's auto-mode permission check may refuse an action that a subagent takes on another agent's confirmation, while plain answers to questions relay normally. When that happens, the main agent runs the branch after the gate itself, on the same inputs and sandbox, and labels it **self-run**.

**Harness limits.** Start no more test subagents at once than the harness runs in parallel, and queue the rest. When a subagent stops on a rate limit, is interrupted, or ends without its Return, resume it once: send it "continue" when the harness can message it, or else start it again with the same brief in a fresh subfolder, after the wait a rate-limit message names. Mark that test **resumed** in the delivery. If the second try fails too, the test was not run; never report it as passed.

**Nested subagents.** A subagent cannot start subagents of its own. When the target skill starts subagents (explorers, reviewers, architects) or a step needs them (a `skill-audit` candidate run during vetting), the main agent runs that work: run one test from the main agent, so the target skill's subagents are real, and run the other tests as test subagents that play those roles themselves, each in a separate pass with only the inputs its brief would give. Label those results **roles played** in the delivery; they test the instructions and scripts, not the subagents' independence.

Subagents return only their final message, not a transcript, so the log in item 3 is self-reported; treat it as somewhat weaker evidence than a transcript.

If the harness cannot run subagents at all, the main agent runs the test itself by following the target skill's instructions on the test inputs, and labels the result **self-run** in the delivery: it is weaker evidence, because the author knows what the skill should do. Scripts the target skill bundles can also be run directly; that tests the script, not the instructions, so say which was tested.

### Rate risk

For each test, state the scenario, what it tests, how success is judged, and its impact:

- **Low:** read-only or disposable input.
- **Moderate:** writes to isolated local files, temporary databases, or disposable resources.
- **High:** affects shared or production systems, sends external messages, costs significantly, or is hard to reverse.

For tests with side effects, specify prerequisites, isolation or backup, setup, teardown that also runs after failures, and how cleanup is verified. Exclude tests that cannot be safely isolated.

## Ask for approval once

In one message: summarize the status; give the test depth tier and its reason; give the check results, labelled as the checker's or a **self-check**, and the check fixes already made (or state there were none); list each failure outside the approved plan with its recommendation; and present numbered tests with pass criteria, impact, and setup/teardown. Say that approved tests that are safe to rerun will be saved as test cases in the target skill's `evals/` folder unless the user declines. Recommend a proportionate selection and ask for approval.

## Run and deliver

### Run and fix

1. Run the approved setup, tests, and teardown, as described in [How tests run](#how-tests-run). Confirm cleanup, including after failures. Before moving on, confirm that every test subagent has finished, including the subagents the main agent started for a main-agent test and, in a harness that lets subagents start their own, any a test subagent started, because a test can report back before its own subagents end.
2. Review what each run did, not only its result: read its returned log and unclear-instruction list, or, for a self-run test, the steps you took. Look for wasted or repeated steps, instructions the main agent ignored or misread, and helper code that several runs wrote for themselves — the last is a sign the target skill should bundle that code as a script in `scripts/`. Treat each such finding as a problem for the fix loop.
3. **Fix loop.** Fixes within the approved plan (they keep its goal, scope, output contract, and permissions) need no approval, because the user already approved what the skill should do. Repeat these rounds:
   1. Fix every open problem from the tests and the review.
   2. Sync the test copy, then send the affected checks back to the checker, as [Check](#check) step 4 does, and rerun the affected tests in the same way they first ran.
   3. List each fix with its evidence for the delivery.

   Stop the loop when everything passes. Also stop, and report what is still failing as unverified, after three rounds that keep finding new problems.

   Leave the loop and return to [Plan](plan.md) when a fix would change the approved plan or the user wants further rounds of creative tuning. When the same problem survives two fixes, stop the loop and report it to the user: the problem, both fixes and their evidence, and a recommendation — revise the plan in [Plan](plan.md), or deliver it marked unverified. Go to Plan only when the user chooses to revise. When a revised plan has been built and Test runs again, rerun only the affected checks and tests, and ask for approval again only for new tests with side effects.

### Design pass

When the target's deliverable, or something it produces (a page, report, dashboard, or artifact), is a surface that `skill-design` reviews, as its description says, run one design review on it. Otherwise, say in the delivery that no design review ran and why.

1. Take one passing test output that shows the page as a real run makes it, preferably from the typical request.
2. Run `skill-design` (for example, `/skill-design`) in review mode on that output file. The main agent runs it, not a test subagent, because the review needs the browser pane. Where the plan built the target's template with `skill-design`, the page is judged against the design that template follows.
3. The verdict is `Block` while any `HIGH` finding remains, otherwise `Approve`. For `Block`, fix each `HIGH` finding where it comes from — the template in `assets/`, or the instructions or script that write the output — under the fix-loop rules above. Sync the test copy, rerun the output tests the fix affects, and review the new output once more. `MEDIUM` and `LOW` findings are fixed only when the fix stays within the approved plan; list the rest in the delivery.
4. Keep the verdict, the number of findings, and any finding left open for the delivery.

### Save and deliver

1. Save the approved tests that are safe to rerun as test cases in the target skill's `evals/` folder, moving them from `<run>/cases/` and following [references/test-cases.md](../references/test-cases.md), unless the user declined. Save the approved trigger requests in `evals/trigger-queries.json` whether they ran as tests or were judged as a check, and say which in the delivery. When the planned change or a fix changed the intended behavior, update the affected test cases instead of adding near-duplicates.
2. Delete the baseline copy that [Build](build.md#before-writing) kept, if any.
3. **Schedule.** For a scheduled procedure, create its unattended run only as the approved plan lists it (an `asks` action), after one more yes in chat, because it is a standing task that runs without the user. Use the tool for where it runs ([Scheduled and recurring](../references/skill-types.md#scheduled-and-recurring)): the local scheduled-tasks tools (for example, `mcp__scheduled-tasks__create_scheduled_task`) when it uses local or OneDrive paths, `schedule` for a cloud routine otherwise. Check that the task is listed with the planned schedule and time zone; where the tool can run it now, run it once and check that it only prepares drafts. Put the task's name and schedule in the delivery and in the registry row's Notes (Learn). If no scheduling tool is available, give the user the steps instead and say it is not scheduled.
4. Deliver in the same two-part shape every time, sized to the user's technical level as the `grilling` skill's wording table sets it:
   - **Summary**, first and in plain words: what the target does, how to start it (the exact phrase or command), and what was tested and how it went. For a nontechnical user, a few short lines with no paths or jargon.
   - **Details:** the target's name and location; where its synced copy is installed (it stays as the installed latest version; delete that folder to uninstall); how to invoke it; the test depth tier; the check results (checker or **self-check**); test results with evidence, marking **self-run** and **resumed** tests; fixes made during testing; the baseline comparison and any comparison test; the design verdict, or why no design review ran; failures outside the plan and what the user decided; deviations; cleanup status; the test cases saved and how to rerun them; anything unverified; and remaining limitations.

   Suggest refining it after real use.
5. Go to [Learn](learn.md).

## Skills and agents

- [skill-builder](../SKILL.md) — rules, vocabulary, and feature definitions checked here.
- [Plan](plan.md) — receives problems that change the approved plan, and repeated failures the user chooses to revise; [Learn](learn.md) — the next stage after delivery.
- [references/check-brief.md](../references/check-brief.md) — the check list and the checker's brief; [references/skill-types.md](../references/skill-types.md) and [references/test-cases.md](../references/test-cases.md) — the requirements checked here and the test-case format; `grilling` — the wording by technical level the delivery follows.
- The checker and the test subagents are the harness's built-in general-purpose subagents; no custom agent definition is required.
- `skill-design` — reviews one HTML test output in [Design pass](#design-pass).
- `update-config` — places a hook or settings change that Test then checks and tests where it put it.
- The local scheduled-tasks tools and `schedule` — create a scheduled procedure's unattended run in [Save and deliver](#save-and-deliver).
