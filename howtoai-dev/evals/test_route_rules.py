"""Wording tests for the route rules that guard approvals, receipts, end-to-end tests, and the target check.

Run: py -3 -I -B <this file>. Reads the plugin's route files only; writes nothing.
"""

import os
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


if __name__ == "__main__":
    unittest.main()
