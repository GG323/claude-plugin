"""Wording tests for the route rules that guard approvals, receipts, end-to-end tests, and the target check.

Run: py -3 -I -B <this file>. Reads the plugin's route files only; writes nothing.
"""

import os
import tempfile
import sys
import subprocess
import re
import unittest

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(PLUGIN, "skills")


def text(*parts):
    with open(os.path.join(SKILLS, *parts), encoding="utf-8") as f:
        return f.read()


class RouteRules(unittest.TestCase):
    def test_a_fix_now_mark_is_never_recorded_as_the_user_saying_yes(self):
        fix = text("dev-build", "routes", "fix.md")
        self.assertIn("only when the finding's proposed fix names that test file", fix)
        self.assertIn('"by": "fix-now choice"', fix)
        self.assertIn('never `"by": "user"`', fix)

    def test_control_a_real_user_answer_still_records_by_user(self):
        self.assertIn('"by": "user"', text("dev-plan", "stages", "accept.md"))
        self.assertIn('"by": "user"', text("dev-review", "routes", "human-review.md"))
        self.assertIn('"by": "user"', text("dev-build", "routes", "build.md"))

    def test_the_plan_receipt_is_recorded_as_resolved(self):
        scope = text("dev-plan", "stages", "scope.md")
        self.assertIn("exactly as `resolve` returned it, never a subset", scope)

    def test_control_other_stages_already_record_it_as_returned(self):
        self.assertIn("record the receipt as returned", text("dev-test", "routes", "run.md"))

    def test_an_end_to_end_row_is_a_script_that_reruns_after_the_build(self):
        write = text("dev-test", "routes", "write.md")
        self.assertIn("written as a script file next to the tests", write)
        self.assertIn("the Expected red reason says why", write)
        run = text("dev-test", "routes", "run.md")
        self.assertIn("run every end-to-end script the test maps name", run)

    def test_the_builds_tests_wait_for_a_clear_target_verdict(self):
        build = text("dev-build", "routes", "build.md")
        self.assertIn("never before that route's target check has a clear verdict", build)

    def test_the_test_stage_cannot_move_to_review_without_its_receipt(self):
        run = text("dev-test", "routes", "run.md")
        self.assertIn("before `green` moves the stage to `review`, check that `state.json` holds a `test` receipt", run)

    def test_the_deny_list_holds_production_markers_only(self):
        fact = "`environments.deny` holds production markers only. A shared target that is not production"
        self.assertIn(fact, text("dev-test", "references", "safety-rules.md"))
        with open(os.path.join(PLUGIN, "agents", "goldfish-compliance.md"), encoding="utf-8") as f:
            self.assertIn(fact, f.read())

    def test_a_request_to_set_up_the_plugin_goes_to_install_md(self):
        setup = text("dev-core", "SKILL.md").split("### Setup", 1)[1].split("### Start a change", 1)[0]
        self.assertIn("When the user asks to set up or install `howtoai-dev`, follow the plugin's `INSTALL.md` from its start instead", setup)
        self.assertIn("When `INSTALL.md` sent you here, skip this paragraph", setup)

    def test_control_the_first_run_still_only_offers_install_md(self):
        self.assertIn("when the plugin was never installed through it, say so in one line and offer it.", text("dev-core", "SKILL.md"))
        self.assertIn("When `configured` is false, run `dev-core`'s Setup route now", text("dev-plan", "stages", "setup.md"))

    def test_the_setup_route_keeps_shared_targets_off_both_lists_and_reads_production_names(self):
        setup = text("dev-core", "SKILL.md")
        self.assertIn("a shared target that is not production, such as a team's dev database, goes on neither list", setup)
        self.assertIn("with a command that prints only host, database, and account names, never a secret value", setup)

    def test_install_reports_a_blocked_step_and_shows_every_missing_item(self):
        with open(os.path.join(PLUGIN, "INSTALL.md"), encoding="utf-8") as f:
            install = f.read()
        self.assertIn("Never report that step as done, and never do it another way", install)
        self.assertIn("show every entry of `missing`, the dev hooks too", install)
        self.assertIn("Before sending a message to a nontechnical user, reread it", install)

    def test_the_summary_gives_a_nontechnical_user_no_record_path(self):
        with open(os.path.join(PLUGIN, "INSTALL.md"), encoding="utf-8") as f:
            install = f.read()
        summary = install.split("## Summary", 1)[1].split("\n## ", 1)[0]
        self.assertIn("for a nontechnical user, what it is (\"your setup notes, saved in this folder\"), with no path", summary)
        self.assertIn("for a developer, its path", summary)
        self.assertIn("where the record is (its path for a developer only)", install)
        self.assertIn("only a write preview keeps the exact path", install)


    def flat(self, *parts):
        return re.sub(r"\s+", " ", text(*parts))

    def test_control_an_unrecorded_project_the_change_does_not_move_is_recorded(self):
        self.assertRegex(self.flat("dev-plan", "stages", "scope.md"),
                         r"For each path in `unrecorded_paths`, run `dev-workbook`'s \[Record a version\]")

    def test_an_upgrade_records_nothing_for_the_version_it_leaves(self):
        for scope in (self.flat("dev-plan", "stages", "scope.md"), self.flat("dev-workbook", "routes", "resolve.md")):
            self.assertRegex(scope, r"(?i)moves to another version.{0,120}record nothing for the version it leaves")
        self.assertRegex(self.flat("dev-plan", "stages", "scope.md"), r"(?i)offer no workbook for it")

    def test_an_upgrade_flags_the_old_version_outside_the_workbook_versions(self):
        self.assertRegex(self.flat("dev-plan", "stages", "scope.md"), r"(?i)outside the `<technology>` workbook's Versions")

    def test_the_new_version_is_recorded_in_the_same_change(self):
        self.assertRegex(self.flat("dev-plan", "stages", "scope.md"),
                         r"(?i)recording the new version.{0,120}step of this change.{0,60}never as a follow-up")
        self.assertRegex(self.flat("dev-build", "routes", "build.md"),
                         r"(?i)## Record and hand on 1\. When the build changed a version.{0,200}Record a version route"
                         r".{0,120}before you write the build record\. A recording the user declines goes under Skipped or unchecked")

    def test_new_test_files_are_resolved_for_their_workbook(self):
        write_route = self.flat("dev-test", "routes", "write.md")
        self.assertRegex(write_route, r"(?i)Resolve again with the new test files' paths added, record its receipt")
        self.assertRegex(write_route, r"(?i)technology in `missing` pauses as code does")
        self.assertRegex(write_route, r"(?i)end-to-end script only in a language or tool that has a workbook")

    def test_a_fix_that_adds_or_replaces_a_test_writes_it_red_first(self):
        fix = self.flat("dev-build", "routes", "fix.md")
        self.assertRegex(fix, r"(?i)(adds|replaces) a test.{0,400}dev-test.{0,200}Write")
        self.assertRegex(fix, r"(?i)without that route's start check and without moving the stage")
        self.assertRegex(fix, r"(?i)must fail for its Expected red reason.{0,80}on the code as it is now for a finding's fix.{0,40}base commit")

    def test_every_hand_off_to_the_user_has_a_nontechnical_form(self):
        sweep = os.path.join(PLUGIN, "evals", "nontechnical_sweep.py")
        p = subprocess.run([sys.executable, "-I", "-X", "utf8", "-B", sweep, PLUGIN], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_the_sweep_catches_setting_keys_dotfiles_and_shown_commands(self):
        rule = "For a nontechnical user, the nontechnical form wins over any step's wording."
        cases = {
            "dotted setting key": "- Ask the user which hosts go in `environments.deny`.",
            "dotfile": "- Ask the user whether to change that `.gitignore`.",
            "shown command": "- For each check, show the command and run it after a yes.",
            "shown as found": "- **Confirmed** (shown as found): the test commands.",
        }
        sweep = os.path.join(PLUGIN, "evals", "nontechnical_sweep.py")
        for name, line in cases.items():
            with tempfile.TemporaryDirectory(prefix="sweep-case-") as root:
                os.makedirs(os.path.join(root, "skills", "dev-core"))
                with open(os.path.join(root, "INSTALL.md"), "w", encoding="utf-8") as f:
                    f.write(f"# Install\n\n{rule}\n\n{line}\n")
                with open(os.path.join(root, "skills", "dev-core", "SKILL.md"), "w", encoding="utf-8") as f:
                    f.write(f"# Dev core\n\n### Setup\n\n{rule}\n\n## End\n")
                p = subprocess.run([sys.executable, "-I", "-X", "utf8", "-B", sweep, root], capture_output=True,
                                   text=True, encoding="utf-8", errors="replace")
            with self.subTest(name):
                self.assertNotEqual(p.returncode, 0)
                self.assertIn("no nontechnical form", p.stdout)

    # F1 fix batch 5 (F1 run 6 R6-2, F7 run 2 M4): documents are written with the file tools, because
    # dev-safe-target denies a shell command whose text names a production marker.
    RULE = "with the file tools (Write, Edit), never through a shell redirect, heredoc, or here-string"

    def line(self, body, start):
        hits = [l for l in body.splitlines() if l.lstrip().startswith(start)]
        self.assertEqual(len(hits), 1, start)
        return hits[0]

    def test_documents_are_written_with_the_file_tools(self):
        core = text("dev-core", "SKILL.md")
        contract = core.split("## Plan folder contract", 1)[1].split("\n## ", 1)[0]
        self.assertIn(self.RULE, contract)
        self.assertIn("`dev-safe-target`", contract)

    def test_install_writes_its_files_with_the_file_tools(self):
        with open(os.path.join(PLUGIN, "INSTALL.md"), encoding="utf-8") as f:
            install = f.read()
        rules = install.split("**Rules for the whole run:**", 1)[1].split("\n## ", 1)[0]
        self.assertIn(self.RULE, rules)
        self.assertIn("`dev-safe-target`", rules)
        self.assertIn("(with the file tools, see Rules for the whole run)", self.line(install, "2. **Install record:** copy"))

    def test_steps_whose_documents_name_targets_point_to_the_file_tool_rule(self):
        run = text("dev-test", "routes", "run.md")
        deploy = text("dev-deploy", "routes", "setup-target.md")
        for body, start in ((run, "1. Copy `dev-core`'s [test-run template]"), (run, "3. **TESTING.md.**"),
                            (deploy, "2. When a deploy file is missing")):
            step = self.line(body, start)
            self.assertIn("with the file tools", step, start)
            self.assertIn("plan-folder-contract", step, start)

    def test_settings_values_go_through_a_file(self):
        with open(os.path.join(PLUGIN, "INSTALL.md"), encoding="utf-8") as f:
            install = f.read()
        core = text("dev-core", "SKILL.md")
        steps = ((install, "1. **Project settings:**"), (install, "Show the values as a preview with"),
                 (core, "3. After the answers, show the settings as a preview"))
        for body, start in steps:
            step = self.line(body, start)
            self.assertIn("--values-file", step, start)
            self.assertIn("Write tool", step, start)
            self.assertNotIn("--values '", step, start)
        entry = [l for l in text("dev-deploy", "routes", "setup-target.md").splitlines()
                 if l.startswith("3. ") and "DEPLOY target write" in l]
        self.assertEqual(len(entry), 1)
        entry = entry[0]
        self.assertIn("with the file tools", entry)
        self.assertIn("plan-folder-contract", entry)

    def test_the_hook_rule_step_passes_its_rules_in_a_file(self):
        step = self.line(text("dev-learn", "routes", "learn.md"), "2. **Hook rule.**")
        self.assertIn("--values-file", step)
        self.assertIn("Write tool", step)
        self.assertIn("`dev-safe-target`", step)
        self.assertNotIn("--values '", step)

    def test_the_build_gate_and_the_plan_templates_follow_dev_core(self):
        gate = self.line(text("dev-build", "routes", "build.md"), "3. After a yes, preview `DEVCORE setup")
        self.assertIn("--values-file", gate)
        self.assertIn("Write tool", gate)
        self.assertNotIn("--values '", gate)
        step = self.line(text("dev-plan", "stages", "setup.md"), "3. Copy `dev-core`'s `plan.md` and `questions.md`")
        self.assertIn("with the file tools", step)
        self.assertIn("plan-folder-contract", step)


class WithoutHooks(unittest.TestCase):
    """No-hook batch: every hook check has its own instruction first, so the rules hold where hooks don't run."""

    SAFETY = ("dev-test", "references", "safety-rules.md")

    def test_production_markers_are_checked_before_every_command(self):
        for parts in (("dev-build", "SKILL.md"), ("dev-test", "SKILL.md"), ("dev-review", "SKILL.md"), self.SAFETY):
            t = text(*parts)
            self.assertIn("Before any command or MCP call, check it against the settings' `environments.deny` markers; "
                          "on a match, stop and ask", t, parts)

    def test_destructive_commands_only_on_a_container_this_run_created(self):
        for skill in ("dev-build", "dev-test"):
            rules = text(skill, "SKILL.md").split("## Core rules", 1)[1].split("\n## ", 1)[0]
            self.assertIn("only on a throwaway container this run created; otherwise ask", rules, skill)

    def test_agents_never_touch_the_reply_log(self):
        self.assertIn("Never create, read, or write `AGENTS/howtoai/dev/replies.jsonl`", text("dev-core", "SKILL.md"))

    def test_unverified_approvals_are_shown_to_the_user(self):
        self.assertIn("show every unverified approval to the user in your next message", text("dev-core", "SKILL.md"))

    def test_a_destructive_migration_needs_a_recorded_yes(self):
        rules = text("dev-build", "SKILL.md").split("## Core rules", 1)[1].split("\n## ", 1)[0]
        self.assertIn("A migration that drops, truncates, or renames needs the user's yes, recorded with its `paths`", rules)

    def test_hook_rules_are_applied_by_the_agent(self):
        settings = text("dev-core", "SKILL.md").split("### Read settings", 1)[1].split("\n### ", 1)[0]
        self.assertIn("apply each `hook_rules` entry yourself before each command or edit", settings)

    def test_the_hooks_items_check_first_and_point_to_the_list(self):
        for skill in ("dev-build", "dev-test"):
            item = [l for l in text(skill, "SKILL.md").splitlines() if l.startswith("4. **Hooks.**")]
            self.assertEqual(len(item), 1, skill)
            self.assertIn("../dev-test/references/safety-rules.md#without-hooks" if skill == "dev-build"
                          else "references/safety-rules.md#without-hooks", item[0])
            self.assertIn("second layer", item[0])

    def test_the_safety_rules_name_the_hook_as_the_second_layer(self):
        t = text(*self.SAFETY)
        self.assertIn("\n## Without hooks\n", t)
        self.assertNotIn("when it is built", t)
        table = t.split("## The rules and their layers", 1)[1].split("\n## ", 1)[0]
        rows = [l for l in table.splitlines() if l.startswith("| ") and not l.startswith(("| Rule ", "| ---"))]
        hooked = [r for r in rows if r.split(" | ")[3] != "-"]
        self.assertTrue(hooked)
        for row in hooked:
            self.assertIn("second layer", row.lower())

    def test_the_troubleshooting_rows_check_first(self):
        row = [l for l in text("dev-test", "SKILL.md").splitlines() if l.startswith("| ") and "`testing.test_globs`" in l]
        self.assertEqual(len(row), 1)
        self.assertIn("second layer", row[0])
        row = [l for l in text("dev-deploy", "SKILL.md").splitlines() if l.startswith("| ") and "approved step" in l]
        self.assertEqual(len(row), 1)
        self.assertIn("`DEPLOY use`", row[0])
        self.assertIn("second layer", row[0])


if __name__ == "__main__":
    unittest.main()
