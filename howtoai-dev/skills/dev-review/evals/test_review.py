"""Tests for review.py. Run: py -3 -I -B <this file>.

Each test builds its own temporary git workspace and passes --user-file, so no real settings
are read or written.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.dirname(os.path.dirname(HERE))
SCRIPT = os.path.join(os.path.dirname(HERE), "scripts", "review.py")
DEVCORE = os.path.join(SKILLS, "dev-core", "scripts", "devcore.py")
BUILD = os.path.join(SKILLS, "dev-build", "scripts", "build.py")
FINDINGS = os.path.join(SKILLS, "dev-core", "scripts", "findings.py")


def py(script, *args):
    p = subprocess.run([sys.executable, "-I", "-B", script, *args], capture_output=True, text=True, encoding="utf-8")
    return p.returncode, json.loads(p.stdout)


def git(ws, *args):
    return subprocess.run(["git", "-c", f"safe.directory={ws.replace(os.sep, '/')}", *args], cwd=ws,
                          capture_output=True, text=True, check=True).stdout


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="devreview-test-")
        self.ws = ws = os.path.join(self.tmp.name, "ws")
        self.user = os.path.join(self.tmp.name, "user.json")
        write(os.path.join(ws, "AGENTS.md"), "# ws\n")
        write(os.path.join(ws, "src", "calc.py"), "def f(n):\n    a = 1\n    b = 2\n    return n\n")
        write(os.path.join(ws, "tests", "test_calc.py"), "def test_f():\n    assert True\n")
        py(DEVCORE, "setup", "--workspace", ws, "--user-file", self.user, "--write", "--values", "{}")
        c = py(DEVCORE, "new-change", "--workspace", ws, "--user-file", self.user, "--title", "Calc", "--date", "2026-11-19")[1]
        self.cdir = c["change_dir"]
        git(ws, "init", "-q")
        git(ws, "add", "-A")
        git(ws, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "init")

    def tearDown(self):
        self.tmp.cleanup()

    def r(self, cmd, *args):
        return py(SCRIPT, cmd, self.cdir, "--user-file", self.user, *args)

    def test_round_one_diff_includes_uncommitted_tests_and_leaves_records_out(self):
        write(os.path.join(self.ws, "src", "calc.py"), "def f(n):\n    a = 1\n    b = 2\n    return n * 2\n")
        write(os.path.join(self.ws, "tests", "test_calc.py"), "def test_f():\n    assert f(2) == 4\n")
        write(os.path.join(self.ws, "tests", "TESTING.md"), "# Testing\n")
        write(os.path.join(self.cdir, "build-1.md"), "# b\n")
        before = git(self.ws, "status", "--porcelain")
        code, d = self.r("diff", "--round", "1")
        self.assertEqual(code, 0, d)
        self.assertEqual(d["files"], ["src/calc.py", "tests/test_calc.py"])
        changed = json.load(open(d["changed"], encoding="utf-8"))
        self.assertEqual(changed["files"]["src/calc.py"], [[4, 4]])
        patch = open(d["patch"], encoding="utf-8").read()
        self.assertIn("+    return n * 2", patch)
        self.assertNotIn("TESTING.md", patch)
        self.assertNotIn("build-1.md", patch)
        after = [ln for ln in git(self.ws, "status", "--porcelain").splitlines() if "/raw/" not in ln]
        self.assertEqual(after, before.splitlines())
        self.assertEqual(git(self.ws, "diff", "--cached", "--name-only"), "")

    def test_rereview_sees_only_the_fix(self):
        write(os.path.join(self.ws, "src", "calc.py"), "def f(n):\n    a = 1\n    b = 2\n    return n * 2\n")
        write(os.path.join(self.cdir, "review-1.md"), "| ID | Your choice |\n| --- | --- |\n| R1-C1 | fix now |\n")
        code, s = py(BUILD, "start", self.cdir, "--n", "1", "--wi", "whole", "--route", "fix", "--review", "review-1.md", "--user-file", self.user)
        self.assertEqual(code, 0, s)
        write(os.path.join(self.ws, "src", "calc.py"), "def f(n):\n    a = 10\n    b = 2\n    return n * 2\n")
        code, d = self.r("diff", "--round", "2", "--since-build", "1")
        self.assertEqual(code, 0, d)
        self.assertEqual(json.load(open(d["changed"], encoding="utf-8"))["files"], {"src/calc.py": [[2, 2]]})

    def test_rereview_needs_a_fix_build(self):
        py(BUILD, "start", self.cdir, "--n", "1", "--wi", "whole", "--user-file", self.user)
        code, d = self.r("diff", "--round", "2", "--since-build", "1")
        self.assertEqual(code, 1)
        self.assertIn("not a Fix-route build", d["error"])

    def test_receipts_become_major_process_findings(self):
        for st in ("tests-first", "build", "test", "review"):
            py(DEVCORE, "state", self.cdir, "--patch", json.dumps({"stage": st}))
        py(DEVCORE, "state", self.cdir, "--patch", json.dumps({"append": {"receipts": {"stage": "build", "statements": ["x.1"], "workbooks": {"x": "1"}}}}))
        code, out = self.r("receipts", "--round", "1")
        self.assertEqual((code, out["missing"]), (0, ["plan", "tests-first", "test"]), out)
        raw = os.path.dirname(out["file"])
        code, col = py(FINDINGS, "collect", raw, "--kind", "code")
        self.assertEqual((code, col["count"], col["high_impact"]), (0, 3, ["R1-G1", "R1-G2", "R1-G3"]), col)

    def test_receipts_clean(self):
        py(DEVCORE, "state", self.cdir, "--patch", json.dumps({"append": {"receipts": {"stage": "plan", "statements": [], "workbooks": {}}}}))
        code, out = self.r("receipts", "--round", "1")
        self.assertEqual((code, out["missing"]), (0, []))
        self.assertIn("No findings", open(out["file"], encoding="utf-8").read())


if __name__ == "__main__":
    unittest.main()
