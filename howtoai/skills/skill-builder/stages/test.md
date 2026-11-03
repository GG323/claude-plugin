# Test

## Contents

- [Check and design tests](#check-and-design-tests)
- [Ask for approval once](#ask-for-approval-once)
- [Run and deliver](#run-and-deliver)
- [Skills and agents](#skills-and-agents)

## Check and design tests

### Check

Run low-risk, read-only checks on the target skill's files:

- The directory name matches frontmatter `name`, and the location is discoverable by the target harness. If the approved plan puts it outside a discovery path, record the check as passed with that exception; the test copy described in [How tests run](#how-tests-run) makes it discoverable.
- Frontmatter parses; the description states what the target skill does and when to use it.
- Relative links resolve and referenced files exist, and stay within the scope [Build](build.md#instructions) allows for the skill's location (its own files; for a project skill, also the workspace's files); documentation follows the target repository's conventions, except files with a fixed format (see [Core rules](../SKILL.md#core-rules)); list those exempt files in the check record.
- Every bundled script is called through the skill's own folder (`${CLAUDE_SKILL_DIR}` for Claude Code), never by a bare relative path.
- The output contract separates the deliverable from its report and states audience, format, and delivery. A document-like deliverable has a fixed structure, presentation, and format per the [standardized-output defaults](../SKILL.md#output-contract), or the approved plan's reason for departing from them.
- If the workflow is split into stages, `SKILL.md` holds only the overview and shared rules, each stage file owns its own instructions and handoffs, and no instructions are split across files.
- The instructions use one name per thing, following the stage, section, and step terms in [Vocabulary](../SKILL.md#vocabulary).
- The target skill has the **Feedback** section, last before `Skills and agents`, sending changes to `skill-builder` by name.
- Planned `state/` has defined seeding and update/prune rules; source links and paths are reachable, or the target skill asks the user when they fail.
- Every requirement the plan applied from [references/skill-types.md](../references/skill-types.md) is written where [Build](build.md#instructions) places it, including privacy: no credentials, tokens, or real personal data in skill files, examples, or test cases.
- Existing test cases in `evals/` follow [references/test-cases.md](../references/test-cases.md), including case and grader names.
- If the idea-generation option is used, the count, split, model choice, and **Choose one** step match the approved plan. If not used, nothing in the target skill implies it.
- For revisions: no stale instructions or references remain in authorized files, and related skills found during planning are still consistent.
- Existing syntax or static checks for bundled scripts pass, when practical.

Record each check as passed, failed, or not checked. Fix each failed check right away, rerun it, and record the fix; fixes within the approved plan need no approval.

### Design candidate tests

Derive a small set of tests from the triggers, workflow, output contract, and success check:

- Every test case already saved in the target skill's `evals/` folder, as regression tests.
- Tests the recall note lists as having worked for this skill type, adapted to this target skill.
- A typical request that should trigger the target skill and exercise its main workflow.
- A meaningful edge case, such as a missing or very large input.
- **Baseline test:** run the typical request twice, in two separate subagents — one with the target skill, one without it (for a revision, with the copy of the previous version that [Build](build.md#before-writing) kept) — and compare the results. Give both the same request, including any constraints a user would normally type. Judge both outputs by the output contract's success check and the skill's own **Verify the output** method, including any bundled check script. The target skill adds value when it passes where the baseline fails, or reaches the same result more reliably, faster, or with less guidance. If it adds nothing, say so in the delivery. If the harness cannot run subagents but the skill bundles scripts, run the old and new scripts on the same inputs instead; otherwise leave the baseline out and say so.
- **Trigger tests:** 6–10 realistic requests, about half that should load the target skill and half near-misses that share its keywords but need something else. The test copy is discoverable, so where the harness can run a fresh session (for example, `claude -p "<request>"`), run each and record whether the target skill loaded. Otherwise, judge each request against the description as a check, and report it as a check, not a test.
- Output tests with clear pass criteria, using the **Verify by** method for the target skill's type in [references/skill-types.md](../references/skill-types.md); for subjective writing or design, a short rubric with judgment left to the user.
- Feature tests only for features the target skill has: a run that updates and prunes `state/`; an unreachable source that leads to a user question; an idea-generation run that returns distinct candidates and one chosen result; a fixed-list request that returns items unchanged.

Offer checks only when no test adds useful evidence.

### How tests run

**Test copy.** Tests run against a copy of the target skill in the personal skills folder, `~/.claude/skills/<name>/` (on Windows `%USERPROFILE%\.claude\skills\<name>\`), so the skill is discoverable and `${CLAUDE_SKILL_DIR}` points to a real installed folder. Before the first test, sync the target skill's current files into that folder, replacing an earlier copy of the same skill. Sync again after every fix round, because fixes are made in the source files. Skip the copy when the target skill already lives in, or is linked into, that folder. If the folder holds a different skill with the same name, stop and return to [Plan](plan.md).

**Test outputs.** Each test writes only inside its own subfolder of `_sandbox/<name>/` in the user's working directory, unless the plan names another place. [Learn](learn.md#clean-up) deletes the folder after delivery, so the delivery report must carry the test evidence.

Run each test in a separate subagent, so the result is not shaped by what this conversation already knows. Starting these subagents is part of this process: the user's request to build or change a skill counts as asking for them. Give every test subagent the same brief, filled in for the test:

```text
You are testing a skill. Act as its main agent; you are not its author.

Skill: use the skill named <name>. If it is not in your skill list, read
<test copy folder>/SKILL.md and follow it, reading ${CLAUDE_SKILL_DIR}
as <test copy folder>.
Request: <the test's prompt, exactly as a user would type it>
Inputs: <absolute paths of the test's input files, or "none">

Limits:
- Write only inside <sandbox folder for this test>.
- Do not send, post, publish, or write through any connector or external
  service. Read connectors only if this brief says so.
- Do not install anything; if a tool is missing, report it and stop.
- The user is unavailable. If the skill tells you to ask the user
  something, stop and return the exact question instead of guessing.
- Where the skill's instructions differ from workspace instructions
  (AGENTS.md, CLAUDE.md), follow the skill.

Return:
1. The deliverable, or its path.
2. The report the skill tells you to give.
3. A log of every tool call and every file written, in order.
4. Every instruction that was unclear, contradictory, or missing.
```

When a test subagent returns a question, answer it as the test plan says by sending the answer to the same subagent, so the branch after the question is tested too.

Subagents return only their final message, not a transcript, so the log in item 3 is self-reported; treat it as somewhat weaker evidence than a transcript.

If the harness cannot run subagents at all, the main agent runs the test itself by following the target skill's instructions on the test inputs, and labels the result **self-run** in the delivery: it is weaker evidence, because the author knows what the skill should do. Scripts the target skill bundles can also be run directly; that tests the script, not the instructions, so say which was tested.

### Rate risk

For each test, state the scenario, what it tests, how success is judged, and its impact:

- **Low:** read-only or disposable input.
- **Moderate:** writes to isolated local files, temporary databases, or disposable resources.
- **High:** affects shared or production systems, sends external messages, costs significantly, or is hard to reverse.

For tests with side effects, specify prerequisites, isolation or backup, setup, teardown that also runs after failures, and how cleanup is verified. Exclude tests that cannot be safely isolated.

## Ask for approval once

In one message: summarize the status, list the check fixes already made (or state there were none), and present numbered tests with pass criteria, impact, and setup/teardown. Say that approved tests that are safe to rerun will be saved as test cases in the target skill's `evals/` folder unless the user declines. Recommend a proportionate selection and ask for approval.

## Run and deliver

1. Run the approved setup, tests, and teardown, as described in [How tests run](#how-tests-run). Confirm cleanup, including after failures.
2. Review what each run did, not only its result: read its returned log and unclear-instruction list, or, for a self-run test, the steps you took. Look for wasted or repeated steps, instructions the main agent ignored or misread, and helper code that several runs wrote for themselves — the last is a sign the target skill should bundle that code as a script in `scripts/`. Treat each such finding as a problem for the fix loop.
3. **Fix loop.** Fixes within the approved plan (they keep its goal, scope, output contract, and permissions) need no approval, because the user already approved what the skill should do. Repeat these rounds:
   1. Fix every open problem from the tests and the review.
   2. Sync the test copy, then rerun the affected checks, and the affected tests in the same way they first ran.
   3. List each fix with its evidence for the delivery.

   Stop the loop when everything passes. Also stop, and report what is still failing as unverified, after three rounds that keep finding new problems.

   Leave the loop and return to [Plan](plan.md) when a fix would change the approved plan, when the user wants further rounds of creative tuning, or when the same problem survives two fixes (report both fixes; Plan treats it as a repeated failure). When a revised plan has been built and Test runs again, rerun only the affected checks and tests, and ask for approval again only for new tests with side effects.
4. Save the approved tests that are safe to rerun as test cases in the target skill's `evals/` folder, following [references/test-cases.md](../references/test-cases.md), unless the user declined. Save the approved trigger requests in `evals/trigger-queries.json` whether they ran as tests or were judged as a check, and say which in the delivery. When a fix changed the intended behavior, update the affected test cases instead of adding near-duplicates.
5. Delete the baseline copy that [Build](build.md#before-writing) kept, if any.
6. Deliver: the target skill's name and location, where its synced copy is installed (it stays as the installed latest version; delete that folder to uninstall), how to invoke it, test results with evidence (marking self-run tests), fixes made during testing, the baseline comparison, deviations, cleanup status, the test cases saved and how to rerun them, anything unverified, and remaining limitations. Suggest refining it after real use.
7. Go to [Learn](learn.md).

## Skills and agents

- [skill-builder](../SKILL.md) — rules, vocabulary, and feature definitions checked here.
- [Plan](plan.md) — receives problems that change the approved plan or survive two fixes; [Learn](learn.md) — the next stage after delivery.
- [references/skill-types.md](../references/skill-types.md) and [references/test-cases.md](../references/test-cases.md) — the requirements checked here and the test-case format.
- No dedicated test agent is required.
