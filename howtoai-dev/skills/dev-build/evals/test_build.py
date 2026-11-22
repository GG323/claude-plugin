"""Tests for build.py. Run: py -3 -I -B <this file>.

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
SCRIPT = os.path.join(os.path.dirname(HERE), "scripts", "build.py")
DEVCORE = os.path.join(os.path.dirname(os.path.dirname(HERE)), "dev-core", "scripts", "devcore.py")
PY = sys.executable.replace("\\", "/")
PASS_CMD = f'"{PY}" -c "print(1)"'
FAIL_CMD = f'"{PY}" -c "import sys; sys.exit(3)"'

TEST_MAP = """# Discount: test map

## Criteria

| # | Criterion | Source | Level | Test file | Test name | Expected red reason | Red result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 10 or more items get 5% off | wi/1.md | unit | tests/t.py | test_bulk | assertion fails | failed as expected |
| 2 | Fewer than 10 items pay full price | wi/1.md | unit | tests/t.py | test_small | passes now and after | passed |

## Characterization tests

| # | Code | Why it is a neighbour | Test file | Test name | Result |
| --- | --- | --- | --- | --- | --- |
| C1 | src/totals.py:total | calls discount | tests/t.py | test_total | passed |
"""

WI = """# WI 1: Bulk discount

## Goal

Bulk orders get a discount.

## Acceptance criteria

- 10 or more items get 5% off
- Fewer than 10 items pay full price

## Out of scope

- none
"""


def run(*args):
    p = subprocess.run([sys.executable, "-I", "-B", SCRIPT, *args], capture_output=True, text=True, encoding="utf-8")
    return p.returncode, json.loads(p.stdout)


def core(*args):
    p = subprocess.run([sys.executable, "-I", "-B", DEVCORE, *args], capture_output=True, text=True, encoding="utf-8")
    return json.loads(p.stdout)


def git(ws, *args):
    return subprocess.run(["git", "-c", f"safe.directory={ws.replace(os.sep, '/')}", *args], cwd=ws,
                          capture_output=True, text=True, check=True).stdout


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="devbuild-test-")
        self.ws = os.path.join(self.tmp.name, "ws")
        self.user = os.path.join(self.tmp.name, "user.json")
        ws = self.ws
        write(os.path.join(ws, "AGENTS.md"), "# ws\n")
        write(os.path.join(ws, ".gitignore"), "obj/\n")
        write(os.path.join(ws, "src", "discount.py"), "def discount(n, price):\n    return price\n")
        write(os.path.join(ws, "src", "totals.py"), "def total(items):\n    x = 1\n    y = 2\n    return sum(items)\n")
        write(os.path.join(ws, "tests", "t.py"), "def test_bulk():\n    assert False\n")
        write(os.path.join(ws, ".github", "workflows", "ci.yml"), "name: ci\n")
        self.gate = [{"name": "lint", "command": PASS_CMD, "source": "test"}]
        core("setup", "--workspace", ws, "--user-file", self.user, "--values", json.dumps({"build": {"gate": self.gate}}), "--write")
        c = core("new-change", "--workspace", ws, "--user-file", self.user, "--title", "Discount", "--date", "2026-11-19")
        self.cdir = c["change_dir"]
        write(os.path.join(self.cdir, "test-map.md"), TEST_MAP)
        write(os.path.join(self.cdir, "wi", "1.md"), WI)
        git(ws, "init", "-q")
        git(ws, "add", "-A")
        git(ws, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "init")
        core("state", self.cdir, "--patch", json.dumps({"stage": "build", "append": {"test_runs": {
            "n": 1, "route": "red-check", "wi": None, "result": "red", "passed": 0, "failed": 1, "flaky": 0}}}))

    def tearDown(self):
        self.tmp.cleanup()

    def b(self, cmd, *args):
        return run(cmd, self.cdir, "--n", "1", "--user-file", self.user, *args)

    def edit_code(self):
        write(os.path.join(self.ws, "src", "discount.py"),
              "def discount(n, price):\n    return price * 0.95 if n >= 10 else price\n")

    def report(self, trace_rows, skipped="- Rounding to cents not checked here", gate_rows="| lint: `x` | test | passed | passed | pass |"):
        text = f"""# Discount: build 1

Change `c` · Work item: 1 · Route: build · Snapshot: `t` · now · Result: passed

## Ladder decisions

| # | Need | Rung | What was used | Source |
| --- | --- | --- | --- | --- |
| L1 | bulk rule | 5 one line | conditional expression | general |

## Callers checked

none: no existing function, type, or contract changed

## Trace

| Hunk | Traces to | Ladder | Why this line |
| --- | --- | --- | --- |
{trace_rows}

## Workbook statements applied

- none

## Gate

| Step | Source | Baseline | After | Result |
| --- | --- | --- | --- | --- |
{gate_rows}

## Skipped or unchecked

{skipped}

## Open points

- none
"""
        write(os.path.join(self.cdir, "build-1.md"), text)

    def green_tests(self):
        core("state", self.cdir, "--patch", json.dumps({"append": {"test_runs": {
            "n": 2, "route": "run", "wi": 1, "result": "green", "passed": 3, "failed": 0, "flaky": 0, "report": "test-run-2.md"}}}))

    def test_snapshot_and_hunks_leave_index_alone(self):
        code, s = self.b("start", "--wi", "1")
        self.assertEqual(code, 0, s)
        self.edit_code()
        write(os.path.join(self.ws, "src", "new_helper.py"), "X = 1\n")
        write(os.path.join(self.ws, "src", "totals.py"), "def total(items):\n    return sum(items)\n")
        write(os.path.join(self.ws, "tests", "t.py"), "def test_bulk():\n    assert True\n")
        write(os.path.join(self.ws, ".github", "workflows", "ci.yml"), "name: ci2\n")
        write(os.path.join(self.ws, "obj", "ignored.txt"), "x\n")
        write(os.path.join(self.cdir, "build-1.md"), "# draft\n")
        write(os.path.join(self.ws, "tests", "TESTING.md"), "# Testing\n\nLatest run: green\n")
        before = git(self.ws, "status", "--porcelain")
        code, h = self.b("hunks")
        self.assertEqual(code, 0, h)
        ids = {x["id"]: x["class"] for x in h["hunks"]}
        self.assertEqual(ids, {"src/discount.py:2-2": "code", "src/new_helper.py:1-1": "code", "src/totals.py:1d": "code",
                               "tests/t.py:2-2": "test", ".github/workflows/ci.yml:1-1": "protected"})
        self.assertEqual(git(self.ws, "status", "--porcelain"), before)
        self.assertEqual(git(self.ws, "diff", "--cached", "--name-only"), "")
        code, again = self.b("start", "--wi", "1")
        self.assertEqual(code, 1)
        self.assertIn("already has a snapshot", again["error"])

    def test_deleted_file_hunk(self):
        self.b("start", "--wi", "1")
        os.remove(os.path.join(self.ws, "src", "totals.py"))
        _, h = self.b("hunks")
        self.assertEqual([x["id"] for x in h["hunks"]], ["src/totals.py:0d"])

    def test_gate_refuses_ad_hoc_commands(self):
        self.b("start", "--wi", "1")
        code, out = self.b("gate", "--label", "after", "--name", "deploy", "--command", PASS_CMD)
        self.assertEqual(code, 1)
        self.assertIn("gate item", out["error"])
        code, out = self.b("gate", "--label", "after", "--name", "lint", "--command", "rm -rf /")
        self.assertEqual(code, 1)
        self.assertIn("must equal", out["error"])
        code, out = self.b("gate", "--label", "later", "--name", "lint", "--command", PASS_CMD)
        self.assertEqual(code, 1)

    def test_clean_build_passes(self):
        self.b("start", "--wi", "1")
        self.edit_code()
        self.report("| src/discount.py:2-2 | T1, T2, AC1 | L1 | applies 5% at 10 items |")
        code, g = self.b("gate", "--label", "after", "--name", "lint", "--command", PASS_CMD)
        self.assertEqual((code, g["passed"], g["exit_code"]), (0, True, 0))
        self.green_tests()
        code, c = self.b("check")
        self.assertEqual(code, 0, c)
        self.assertTrue(c["passed"], c["errors"])
        self.assertEqual((c["hunks"], c["gate"], c["tests"]["result"]), (1, {"lint": "pass"}, "green"))

    def test_check_finds_every_problem(self):
        self.b("start", "--wi", "1")
        self.edit_code()
        write(os.path.join(self.ws, "src", "totals.py"), "def total(items):\n    x = 10\n    y = 2\n    return sum(items)\n")
        write(os.path.join(self.ws, "tests", "t.py"), "def test_bulk():\n    assert True\n")
        self.report("| src/discount.py:2-2 | T9, AC1 | L2 | rule |\n| tests/t.py:2-2 | T1 | L1 | loosen |\n| src/gone.py:1-1 | T1 | L1 | x |",
                    skipped="{what this build left out}")
        self.b("gate", "--label", "after", "--name", "lint", "--command", PASS_CMD)
        _, c = self.b("check")
        self.assertFalse(c["passed"])
        joined = "\n".join(c["errors"])
        for needle in ("T9 is not in this build", "ladder 'L2'", "test file changed without approval: tests/t.py:2-2",
                       "does not exist now: src/gone.py:1-1", "hunk not traced: src/totals.py:2-2",
                       "no dev-test Run route run", "placeholder left", "Skipped or unchecked has no line"):
            self.assertIn(needle, joined)

    def test_gate_failures_and_stale_runs(self):
        self.b("start", "--wi", "1")
        self.edit_code()
        self.report("| src/discount.py:2-2 | T1 | L1 | rule |")
        self.b("gate", "--label", "after", "--name", "lint", "--command", PASS_CMD)
        write(os.path.join(self.ws, "src", "discount.py"),
              "def discount(n, price):\n    return price * 0.95 if n > 9 else price\n")
        self.green_tests()
        _, c = self.b("check")
        self.assertIn("gate lint: the last 'after' run was on other code; run it again", c["errors"])

    def test_pre_existing_failure_needs_approval(self):
        gate = [{"name": "lint", "command": FAIL_CMD, "source": "test"}]
        core("setup", "--workspace", self.ws, "--user-file", self.user, "--values", json.dumps({"build": {"gate": gate}}), "--write")
        self.b("start", "--wi", "1")
        _, base = self.b("gate", "--label", "baseline", "--name", "lint", "--command", FAIL_CMD)
        self.assertEqual((base["exit_code"], base["passed"]), (3, False))
        self.edit_code()
        self.report("| src/discount.py:2-2 | T1 | L1 | rule |")
        self.b("gate", "--label", "after", "--name", "lint", "--command", FAIL_CMD)
        self.green_tests()
        _, c = self.b("check")
        self.assertIn("gate lint: fails after the build", c["errors"])
        core("state", self.cdir, "--patch", json.dumps({"append": {"approvals": {
            "what": "continue with pre-existing gate failure", "by": "user", "build": 1, "gate": "lint"}}}))
        _, c = self.b("check")
        self.assertTrue(c["passed"], c["errors"])
        self.assertEqual(c["gate"]["lint"], "pre-existing failure, continued with approval")

    def test_approved_test_change_and_fix_route(self):
        write(os.path.join(self.cdir, "review-1.md"),
              "| ID | Impact | Confidence | Mark | Location | Finding | Proposed fix | Handling | Your choice |\n"
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
              "| R1-C1 | Major | 90 | confirmed | src/discount.py:2 | edge | use >= | AUTO-FIX | fix now |\n"
              "| R1-02 | Nit | 90 | confirmed | src/totals.py:2 | name | rename | ASK | decline: fine |\n")
        code, s = self.b("start", "--wi", "1", "--route", "fix", "--review", "review-1.md")
        self.assertEqual(code, 0, s)
        self.edit_code()
        write(os.path.join(self.ws, "tests", "t.py"), "def test_bulk():\n    assert 1\n")
        core("state", self.cdir, "--patch", json.dumps({"append": {"approvals": {
            "what": "fix may change the test", "by": "user", "paths": ["tests/t.py"]}}}))
        self.report("| src/discount.py:2-2 | R1-C1 | L1 | fix |\n| tests/t.py:2-2 | R1-02 | L1 | x |")
        self.b("gate", "--label", "after", "--name", "lint", "--command", PASS_CMD)
        _, c = self.b("check")
        self.assertEqual(c["errors"], ["tests/t.py:2-2: R1-02 is not in this build's test map, acceptance criteria, or fix-now findings"])
        self.assertEqual([x["check"] for x in c["skipped"]], ["wi-tests"])
        self.assertNotIn("wi-tests", c["checks_run"])


if __name__ == "__main__":
    unittest.main()
