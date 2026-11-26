"""Regression tests for dev-learn's learn.py. Run: py -3 -I -B test_learn.py

Builds synthetic review docs, learn records, and lessons logs in a temporary folder;
runs no project code and touches nothing outside that folder.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
LEARN = os.path.join(HERE, "..", "scripts", "learn.py")

REVIEW = """# Demo: review round 1

Change `c1` · Diff: HEAD..working tree · Reviewers: correctness, tests · Verdict: blocked · Result: not clean

## Summary

| Impact | Findings | AUTO-FIX | ASK |
| --- | --- | --- | --- |
| Critical | 1 | 1 | 0 |

## Findings by area

### Correctness

| ID | Impact | Confidence | Mark | Location | Finding | Proposed fix | Handling | Your choice |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R1-C1 | Critical | 95 | confirmed | `src/Calc.cs:14` | `Math.Round` without digits rounds the discount to whole units | pass 2 digits | AUTO-FIX | fix now |
| R1-C2 | Minor | 85 | inferred | `src/Other.cs:3` | Variable name is unclear | rename it | ASK | {c2} |

## Test inspection

- **Runs:** none

## Outside this change

| ID | Severity | Confidence | Verdict | Viewpoint | Location | Finding | Recommendation | Why outside | Your choice |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R1-X1 | Major | 90 | stands | security | `src/Auth.cs:9` | Token logged in plain text | redact it | unchanged line | {x1} |

## Appendix: low confidence and filtered

| ID | Confidence | Reason held back | Finding |
| --- | --- | --- | --- |
| R1-T1 | 60 | below threshold | weak test |
"""

LEARN_OK = """# Demo: learn round 1

Change `c1` · From review round 1

| Finding | Lesson | Repeats | Root cause stage | Evidence | Smallest fix | Level | Target file | Route | Why not lower | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R1-C1 | DL-001 | first time | workbook | no C# statement on Math.Round digits (csharp Pitfalls) | add the statement | 1 | csharp/Pitfalls | dev-workbook | - | proposed |

## Drift

- none found
"""


def run(*args):
    r = subprocess.run([sys.executable, "-I", "-B", LEARN, *args], capture_output=True, text=True, encoding="utf-8")
    return r.returncode, json.loads(r.stdout)


class LearnTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.plans = os.path.join(self.root, "dev-plans")
        self.change = os.path.join(self.plans, "c1")
        os.makedirs(self.change)
        self.log = os.path.join(self.root, "AGENTS", "lessons.md")
        self.review(c2="later", x1="later")
        with open(os.path.join(self.change, "state.json"), "w", encoding="utf-8") as f:
            json.dump({"stage": "human-review", "declined": []}, f)

    def tearDown(self):
        self.tmp.cleanup()

    def review(self, **kw):
        with open(os.path.join(self.change, "review-1.md"), "w", encoding="utf-8") as f:
            f.write(REVIEW.format(**kw))

    def add(self, **kw):
        args = {"stage": "build", "change": "c0", "finding": "R1-C9", "where": "src/Calc.cs",
                "text": "Something broke", "fix": "none: one-off", "date": "2026-11-10"}
        args.update(kw)
        flat = []
        for k, v in args.items():
            flat += ["--" + k, v]
        return run("lesson", "add", self.log, *flat)

    def learn_file(self, text):
        p = os.path.join(self.change, "learn-1.md")
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        return p

    def check(self, text):
        return run("check", self.learn_file(text), "--review", os.path.join(self.change, "review-1.md"),
                   "--lessons", self.log, "--state", os.path.join(self.change, "state.json"))

    def test_add_numbers_and_never_reuses_ids(self):
        self.assertEqual(self.add()[1]["added"], "DL-001")
        self.assertEqual(self.add()[1]["added"], "DL-002")
        code, res = run("lesson", "remove", self.log, "--id", "DL-002")
        self.assertEqual(code, 0, res)
        self.assertEqual(self.add()[1]["added"], "DL-003")

    def test_add_refuses_bad_values(self):
        self.assertEqual(self.add(stage="guess")[0], 1)
        self.assertEqual(self.add(text="a · b")[0], 1)

    def test_repeat_raises_count(self):
        self.add()
        code, res = run("lesson", "repeat", self.log, "--id", "DL-001")
        self.assertEqual((code, res["repeats"]), (0, 2))
        self.assertEqual(run("lesson", "repeat", self.log, "--id", "DL-009")[0], 1)

    def test_remove_settled_lesson_and_copies(self):
        self.add(); self.add(); self.add()
        code, res = run("lesson", "remove", self.log, "--id", "DL-001", "--id", "DL-003")
        self.assertEqual(code, 0, res)
        with open(self.log, encoding="utf-8") as f:
            text = f.read()
        self.assertNotIn("DL-001", text.replace("highest DL", ""))
        self.assertIn("**DL-002**", text)
        self.assertNotIn("**DL-003**", text)

    def test_collect_picks_serious_declined_and_repeats(self):
        self.review(c2="later", x1="decline: tokens are test fixtures")
        self.add(text="Math.Round on a decimal without digits rounded the discount to whole units")
        code, res = run("collect", self.change, "--round", "1", "--lessons", self.log)
        self.assertEqual(code, 0, res)
        got = {c["id"]: c for c in res["collected"]}
        self.assertIn("critical", got["R1-C1"]["why"])
        self.assertIn("repeats a lesson", got["R1-C1"]["why"])
        self.assertEqual(got["R1-X1"]["why"], ["declined"])
        self.assertEqual(got["R1-X1"]["reason"], "tokens are test fixtures")
        self.assertIn("R1-C2", res["not_collected"])
        self.assertNotIn("R1-T1", got)

    def test_collect_finds_applied_fix_in_other_change(self):
        other = os.path.join(self.plans, "c0")
        os.makedirs(other)
        with open(os.path.join(other, "learn-1.md"), "w", encoding="utf-8") as f:
            f.write(LEARN_OK.replace("| proposed |", "| applied |").replace("R1-C1", "R1-C7")
                    .replace("add the statement", "add the statement for src/Calc.cs"))
        code, res = run("collect", self.change, "--round", "1", "--lessons", self.log)
        self.assertEqual(code, 0, res)
        c1 = next(c for c in res["collected"] if c["id"] == "R1-C1")
        self.assertIn("repeats an applied fix", c1["why"])
        self.assertEqual(c1["applied_fixes"][0]["change"], "c0")

    def test_check_accepts_valid_record(self):
        self.add()
        code, res = self.check(LEARN_OK)
        self.assertTrue(res["ok"], res)

    def test_check_level_rules(self):
        self.add()
        lvl3 = LEARN_OK.replace("| 1 | csharp/Pitfalls | dev-workbook | - |", "| 3 | skills/dev-test/SKILL.md | skill-builder | - |")
        self.assertIn("level 3 needs evidence", " ".join(self.check(lvl3)[1]["problems"]))
        lvl2 = LEARN_OK.replace("| 1 | csharp/Pitfalls | dev-workbook | - |", "| 2 | skills/dev-test/SKILL.md | skill-builder | - |")
        self.assertIn("level 2 changes a goldfish", " ".join(self.check(lvl2)[1]["problems"]))
        lvl1 = LEARN_OK.replace("| 1 | csharp/Pitfalls | dev-workbook | - |", "| 1 | agents/goldfish-tests.md | skill-builder | - |")
        self.assertIn("level 1 changes a workbook", " ".join(self.check(lvl1)[1]["problems"]))
        ok2 = LEARN_OK.replace("| 1 | csharp/Pitfalls | dev-workbook | - |", "| 2 | agents/goldfish-tests.md | skill-builder | - |")
        self.assertTrue(self.check(ok2)[1]["ok"])

    def test_check_settled_lesson_must_leave_log(self):
        self.add()
        res = self.check(LEARN_OK.replace("| proposed |", "| applied |"))[1]
        self.assertIn("still in the lessons log", " ".join(res["problems"]))
        run("lesson", "remove", self.log, "--id", "DL-001")
        self.assertTrue(self.check(LEARN_OK.replace("| proposed |", "| applied |"))[1]["ok"])

    def test_start_writes_empty_record_once(self):
        with open(os.path.join(self.change, "state.json"), "w", encoding="utf-8") as f:
            json.dump({"id": "c1", "title": "Demo", "stage": "deploy", "declined": []}, f)
        code, res = run("start", self.change, "--round", "1")
        self.assertEqual(code, 0, res)
        with open(res["written"], encoding="utf-8") as f:
            text = f.read()
        self.assertIn("# Demo: learn round 1", text)
        self.assertNotIn("{review ID}", text)
        self.assertEqual(run("start", self.change, "--round", "1")[0], 1)
        with open(res["written"], "a", encoding="utf-8") as f:
            f.write("- none found\n")
        code, res = run("check", res["written"], "--review", os.path.join(self.change, "review-1.md"),
                        "--lessons", self.log)
        self.assertIn("missing row for collected finding R1-C1", " ".join(res["problems"]))
        self.assertEqual(res["checks_skipped"][0]["reason"], "no --state given")

    def test_check_coverage_and_drift(self):
        self.add()
        self.review(c2="later", x1="decline: not ours")
        res = self.check(LEARN_OK.replace("## Drift\n\n- none found\n", ""))[1]
        joined = " ".join(res["problems"])
        self.assertIn("missing row for collected finding R1-X1", joined)
        self.assertIn("Drift", joined)


if __name__ == "__main__":
    unittest.main(verbosity=1)
