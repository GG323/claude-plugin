"""Tests for findings.py. Run: py -3 -I -m unittest <this file> (or py -3 -I <this file>).

Each test writes reviewer, scorer, and verifier tables into its own temporary raw folder.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(SKILL, "scripts", "findings.py")
TEMPLATE = os.path.join(SKILL, "assets", "templates", "plan-review.md")

CRITIC = """| ID | Severity | Location | Quote | Finding | Mark | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| P1-K1 | Blocker | Design details | "rename `a|b` column" | No rollback for the rename. | confirmed: `db/1.sql:4` | Expand then contract. |
| P1-K2 | Major | Risks | "none" | Lockout abuse not covered. | inferred: no rate limit per IP | Add per-IP limit. |
| P1-K3 | Nit | Goal | "stop guessing" | Vague verb. | inferred | Say "limit". |
"""
COMPREHENSION = """No findings
"""
SCORES = """| ID | Score | Reason |
| --- | --- | --- |
| P1-K1 | 92 | Quote found. |
| P1-K2 | 85 | Likely. |
| P1-K3 | 40 | Style only. |
"""
VERDICTS = """| ID | Verdict | Impact now | Evidence |
| --- | --- | --- | --- |
| P1-K1 | Stands | Blocker | searched `db/`; nothing defuses it |
| P1-K2 | Refuted | none | `src/auth/Ip.cs:10` already limits per IP (confirmed) |
"""


def run(*args):
    p = subprocess.run([sys.executable, "-I", SCRIPT, *args], capture_output=True, text=True, encoding="utf-8")
    return p.returncode, json.loads(p.stdout)


class FindingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="findings-test-")
        self.change = self.tmp.name
        self.raw = os.path.join(self.change, "raw", "plan-review-1")
        os.makedirs(self.raw)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, text, folder=None):
        with open(os.path.join(folder or self.raw, name), "w", encoding="utf-8") as f:
            f.write(text)

    def review(self, n=1):
        return os.path.join(self.change, "plan-review-%d.md" % n)

    def full_round(self):
        self.write("critic.md", CRITIC)
        self.write("comprehension.md", COMPREHENSION)
        code, out = run("collect", self.raw)
        self.assertEqual(code, 0, out)
        self.write("scores.md", SCORES)
        self.write("verdicts.md", VERDICTS)
        return run("tally", self.raw, "--round", "1", "--out", self.review(), "--title", "Login", "--change-id", "x", "--size", "Medium")

    def test_collect_counts_and_pipes_in_backticks(self):
        self.write("critic.md", CRITIC)
        code, out = run("collect", self.raw)
        self.assertEqual(code, 0)
        self.assertEqual(out["count"], 3)
        self.assertEqual(out["high_impact"], ["P1-K1", "P1-K2"])
        self.assertEqual(out["outside_change"], [])
        data = json.load(open(os.path.join(self.raw, "findings.json"), encoding="utf-8"))
        self.assertIn("a|b", data["findings"][0]["quote"])
        self.assertTrue(os.path.exists(os.path.join(self.raw, "high-impact.md")))

    def test_collect_rejects_bad_severity_and_duplicates(self):
        self.write("critic.md", CRITIC.replace("| Nit |", "| Minor |"))
        code, out = run("collect", self.raw)
        self.assertEqual(code, 1)
        self.assertIn("Minor", out["error"])
        self.write("critic.md", CRITIC)
        self.write("zoom-out.md", CRITIC)
        code, out = run("collect", self.raw)
        self.assertIn("duplicate", out["error"])

    def test_tally_threshold_refuted_and_clean(self):
        code, out = self.full_round()
        self.assertEqual(code, 0, out)
        self.assertEqual((out["kept"], out["held_back"], out["refuted"], out["clean"]), (1, 2, 1, False))
        text = open(self.review(), encoding="utf-8").read()
        self.assertIn("Result: not clean", text)
        self.assertIn("| P1-K1 | Blocker | 92 | stands |", text)
        self.assertIn("refuted: `src/auth/Ip.cs:10`", text)
        self.assertIn("below threshold: Style only.", text)
        self.assertIn("## Outside this change\n\nnone", text)

    def test_weakened_changes_impact(self):
        self.write("critic.md", CRITIC)
        run("collect", self.raw)
        self.write("scores.md", SCORES)
        self.write("verdicts.md", VERDICTS.replace("| P1-K1 | Stands | Blocker |", "| P1-K1 | Weakened | Nit |"))
        code, out = run("tally", self.raw, "--round", "1", "--out", self.review())
        self.assertEqual(code, 0, out)
        self.assertTrue(out["clean"])
        self.assertEqual(out["kept_by_severity"]["Nit"], 1)
        with open(self.review(), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("weakened from Blocker", text)
        self.assertIn("| Blocker | 1 | 1 | 0 | 0 | 0 | 1 |", text)

    def test_tally_needs_scores_and_verdicts(self):
        self.write("critic.md", CRITIC)
        run("collect", self.raw)
        code, out = run("tally", self.raw, "--round", "1", "--out", self.review())
        self.assertIn("scores.md missing", out["error"])
        self.write("scores.md", SCORES)
        code, out = run("tally", self.raw, "--round", "1", "--out", self.review())
        self.assertIn("verdicts.md missing", out["error"])

    def test_no_findings_is_clean(self):
        self.write("comprehension.md", COMPREHENSION)
        run("collect", self.raw)
        code, out = run("tally", self.raw, "--round", "1", "--out", self.review())
        self.assertEqual((code, out["clean"], out["kept"]), (0, True, 0))

    def test_check_and_refuse_overwrite(self):
        self.full_round()
        code, out = run("check", self.review())
        self.assertEqual(out["open"], ["P1-K1"])
        self.assertFalse(out["ok"])
        path = self.review()
        text = open(path, encoding="utf-8").read().replace("| open |", "| fixed: Design details |")
        open(path, "w", encoding="utf-8").write(text)
        code, out = run("check", path)
        self.assertTrue(out["ok"])
        code, out = run("tally", self.raw, "--round", "1", "--out", path)
        self.assertIn("already has resolutions", out["error"])

    def test_check_rejects_unknown_resolution(self):
        self.full_round()
        path = self.review()
        text = open(path, encoding="utf-8").read().replace("| open |", "| maybe later |")
        open(path, "w", encoding="utf-8").write(text)
        code, out = run("check", path)
        self.assertEqual(out["invalid"], ["P1-K1"])

    def test_stop_rule(self):
        def put(n, result):
            self.write("plan-review-%d.md" % n, "# t\n\nChange `x` · Result: %s\n" % result, self.change)
        put(1, "not clean")
        self.assertEqual(run("stop", self.change)[1]["stop"], "continue")
        put(2, "clean")
        self.assertEqual(run("stop", self.change)[1]["stop"], "continue")
        put(3, "clean")
        out = run("stop", self.change)[1]
        self.assertEqual((out["stop"], out["consecutive_clean"]), ("clean", 2))
        for n in (3, 4, 5):
            put(n, "not clean")
        out = run("stop", self.change, "--max-rounds", "5")[1]
        self.assertEqual((out["stop"], out["last_clean"]), ("cap", False))

    def test_plan_output_matches_template_headings(self):
        self.full_round()
        heads = lambda t: [l for l in t.splitlines() if l.startswith("## ")]
        self.assertEqual(heads(open(self.review(), encoding="utf-8").read()), heads(open(TEMPLATE, encoding="utf-8").read()))

    def test_code_kind_renders_review_shape(self):
        code_findings = CRITIC.replace("| Blocker |", "| Critical |").replace("| Nit |", "| Minor |").replace("P1-K", "R1-")
        self.write("correctness.md", code_findings)
        code, out = run("collect", self.raw, "--kind", "code")
        self.assertEqual(code, 0, out)
        self.write("scores.md", SCORES.replace("P1-K", "R1-"))
        self.write("verdicts.md", VERDICTS.replace("P1-K", "R1-").replace("| Blocker |", "| Critical |"))
        code, out = run("tally", self.raw, "--round", "1", "--out", self.review(), "--diff", "a..b")
        self.assertEqual(code, 0, out)
        text = open(self.review(), encoding="utf-8").read()
        self.assertIn("Verdict: blocked", text)
        self.assertIn("## Findings by area", text)

    def test_same_location_and_quote_merge(self):
        head = "| ID | Impact | Area | Location | Quote | Finding | Mark | Proposed fix | Handling |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
        self.write("spec.md", head + "| R1-S1 | Major | Spec | `src/C.cs:14` | \"Math.Round(x)\" | Plan says 2 decimals. | confirmed | Pass 2. | AUTO-FIX |\n")
        self.write("correctness.md", head + "| R1-C1 | Critical | Correctness | src/C.cs:14 | Math.Round(x) | Rounds to units. | confirmed | Pass 2. | AUTO-FIX |\n")
        self.write("tests.md", head + "| R1-T1 | Major | Tests | src/C.cs:14 | \"Math.Round\" | No test with cents. | confirmed | Add one. | AUTO-FIX |\n")
        code, out = run("collect", self.raw, "--kind", "code")
        self.assertEqual((code, out["count"], out["merged"]), (0, 2, [{"id": "R1-S1", "into": "R1-C1"}]), out)
        self.write("scores.md", "| ID | Score | Reason |\n| --- | --- | --- |\n| R1-C1 | 95 | r |\n| R1-T1 | 90 | r |\n")
        self.write("verdicts.md", "| ID | Verdict | Impact now | Evidence |\n| --- | --- | --- | --- |\n| R1-C1 | Stands | Critical | e |\n| R1-T1 | Stands | Major | e |\n")
        code, out = run("tally", self.raw, "--round", "1", "--out", self.review())
        self.assertEqual((code, out["kept"], out["held_back"]), (0, 2, 1), out)
        with open(self.review(), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("Also raised by R1-S1 (spec)", text)
        self.assertIn("duplicate of R1-C1", text.split("## Appendix")[1])

    def test_code_unchanged_lines_go_outside_the_change(self):
        rows = ("| ID | Impact | Area | Location | Quote | Finding | Mark | Proposed fix | Handling |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
                "| R1-C1 | Major | Correctness | `src/Calc.cs:14` | \"Math.Round(x)\" | Rounds to units. | confirmed | Pass 2. | AUTO-FIX |\n"
                "| R1-C2 | Major | Correctness | src/Order.cs:9 | \"Sum(q)\" | Negative quantities count. | inferred | Guard. | ASK |\n"
                "| R1-C3 | Minor | Correctness | `src/Calc.cs:40` | \"x\" | Far from the change. | inferred | - | ASK |\n")
        spec = ("| ID | Impact | Area | Location | Quote | Finding | Mark | Proposed fix | Handling |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
                "| R1-S1 | Major | Spec | wi/1.md:12 | \"AC2\" | AC2 not built. | confirmed | Build it. | ASK |\n")
        self.write("correctness.md", rows)
        self.write("spec.md", spec)
        self.assertEqual(run("collect", self.raw, "--kind", "code")[0], 0)
        self.write("scores.md", "| ID | Score | Reason |\n| --- | --- | --- |\n| R1-C1 | 95 | r |\n| R1-C2 | 90 | r |\n| R1-C3 | 85 | r |\n| R1-S1 | 90 | r |\n")
        self.write("verdicts.md", "| ID | Verdict | Impact now | Evidence |\n| --- | --- | --- | --- |\n| R1-C1 | Stands | Major | e |\n| R1-C2 | Stands | Major | e |\n| R1-S1 | Stands | Major | e |\n")
        changed = os.path.join(self.change, "changed.json")
        self.write("changed.json", json.dumps({"files": {"src/Calc.cs": [[13, 15]]}}), self.change)
        insp = os.path.join(self.change, "inspection.md")
        self.write("inspection.md", "- **Runs:** test-run-2, 7 passed\n- **Temporary tests:** one, removed\n- **Coverage gaps:** none\n", self.change)
        code, out = run("tally", self.raw, "--round", "1", "--out", self.review(), "--changed", changed, "--inspection", insp)
        self.assertEqual((code, out["kept"], out["held_back"], out["outside_change"]), (0, 2, 1, ["R1-C2"]), out)
        text = open(self.review(), encoding="utf-8").read()
        kept = text.split("## Findings by area")[1].split("## Test inspection")[0]
        self.assertIn("R1-C1", kept)
        self.assertIn("R1-S1", kept)
        self.assertNotIn("R1-C2", kept)
        outside = text.split("## Outside this change")[1].split("## Appendix")[0]
        self.assertIn("| R1-C2 | Major |", outside)
        self.assertIn("unchanged line", outside)
        self.assertIn("outside the change, Minor", text.split("## Appendix")[1])
        self.assertEqual(sorted(run("check", self.review())[1]["open"]), ["R1-C1", "R1-C2", "R1-S1"])
        self.assertIn("test-run-2, 7 passed", text)
        self.assertNotIn("{filled by dev-review}", text)


    def test_plan_change_column_outside(self):
        head = "| ID | Severity | Area | Change | Location | Quote | Finding | Mark | Recommendation |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
        self.write("critic.md", head
                   + "| P1-K1 | Major | Risk | in | Design details | \"retry\" | Double charge on retry. | confirmed | Idempotency key. |\n"
                   + "| P1-K2 | Blocker | Risk | **outside** | `src/Host.cs:10` | \"AddHostedService\" | A failed job stops the host today. | confirmed | Catch and log. |\n"
                   + "| P1-K3 | Nit | Clarity | outside | README.md:3 | \".NET 6\" | README says .NET 6. | confirmed | Update it. |\n")
        code, out = run("collect", self.raw)
        self.assertEqual((code, out["outside_change"]), (0, ["P1-K2", "P1-K3"]), out)
        self.write("scores.md", "| ID | Score | Reason |\n| --- | --- | --- |\n| P1-K1 | 90 | r |\n| P1-K2 | 60 | r |\n| P1-K3 | 90 | r |\n")
        self.write("verdicts.md", "| ID | Verdict | Impact now | Evidence |\n| --- | --- | --- | --- |\n| P1-K1 | Weakened | Nit | e |\n| P1-K2 | Stands | Blocker | e |\n")
        code, out = run("tally", self.raw, "--round", "1", "--out", self.review())
        self.assertEqual((code, out["clean"], out["kept"], out["outside_change"], out["held_back"]), (0, True, 1, ["P1-K2"], 1), out)
        text = open(self.review(), encoding="utf-8").read()
        self.assertIn("| Blocker | 1 | 0 | 1 | 0 | 0 | 0 |", text)
        self.assertIn("marked outside the change by the reviewer", text.split("## Outside this change")[1])
        self.assertIn("outside the change, Nit", text.split("## Appendix")[1])
        self.assertEqual(run("check", self.review())[1]["open"], ["P1-K1", "P1-K2"])
        text = text.replace("| open |", "| fixed: Risks |", 1).replace("| open |", "| outside: follow-up change for the host |", 1)
        open(self.review(), "w", encoding="utf-8").write(text)
        self.assertTrue(run("check", self.review())[1]["ok"])

if __name__ == "__main__":
    unittest.main()
