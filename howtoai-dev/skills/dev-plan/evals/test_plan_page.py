"""Tests for plan_page.py. Run: py -3 -I -m unittest <this file> (or py -3 -I <this file>).

Renders a copy of examples/plan-page-sample/ in a temporary folder, so the sample stays unchanged.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "scripts", "plan_page.py")
SAMPLE = os.path.join(os.path.dirname(HERE), "examples", "plan-page-sample")


def run(*args):
    p = subprocess.run([sys.executable, "-I", SCRIPT, *args], capture_output=True, text=True, encoding="utf-8")
    return p.returncode, json.loads(p.stdout)


class PlanPageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="plan-page-test-")
        self.change = os.path.join(self.tmp.name, "change")
        for root, _, files in os.walk(SAMPLE):  # plain copies: OneDrive folder attributes would block cleanup
            dest = os.path.join(self.change, os.path.relpath(root, SAMPLE))
            os.makedirs(dest, exist_ok=True)
            for name in files:
                shutil.copyfile(os.path.join(root, name), os.path.join(dest, name))

    def tearDown(self):
        self.tmp.cleanup()

    def page(self):
        return open(os.path.join(self.change, "plan.html"), encoding="utf-8").read()

    def test_render_figures(self):
        code, out = run("render", self.change)
        self.assertEqual(code, 0, out)
        self.assertEqual((out["size"], out["decisions"], out["open_questions"], out["review_rounds"],
                          out["open_blockers_majors"], out["work_items"]), ("Medium", 2, 1, 1, 0, 1))
        page = self.page()
        self.assertTrue(page.startswith("<!doctype html>"))
        self.assertNotIn("{{", page)
        self.assertIn("Should support staff be able to unlock", page)
        self.assertIn("<code>dotnet.patterns.012</code>", page)

    def test_markdown_shapes(self):
        run("render", self.change)
        page = self.page()
        self.assertIn('<div class="scroll"><table>', page)
        self.assertIn("<ul><li><code>src/auth/AttemptTracker.cs</code>", page)
        self.assertIn("<ul><li>Reset on success.</li></ul>", page)
        self.assertIn("<strong>Size:</strong>", page)
        self.assertNotIn('id="s-goal"', page)

    def test_sections_dropped_when_empty(self):
        os.remove(os.path.join(self.change, "plan-review-1.md"))
        shutil.rmtree(os.path.join(self.change, "wi"))
        path = os.path.join(self.change, "plan.md")
        text = open(path, encoding="utf-8").read().replace("- **Open:** Should support staff be able to unlock an account by hand?", "- **Open:** none")
        open(path, "w", encoding="utf-8").write(text)
        code, out = run("render", self.change)
        self.assertEqual(code, 0, out)
        page = self.page()
        for sid in ('id="s-review"', 'id="s-wi"', "Open questions</strong>", "<!-- section:"):
            self.assertFalse(sid in page, sid)

    def test_open_blocker_counted(self):
        path = os.path.join(self.change, "plan-review-1.md")
        text = open(path, encoding="utf-8").read().replace("| fixed: Design details |", "| open |")
        open(path, "w", encoding="utf-8").write(text)
        code, out = run("render", self.change)
        self.assertEqual(out["open_blockers_majors"], 1)
        self.assertIn('figure danger', self.page())

    def test_artifact_mode_and_escaping(self):
        path = os.path.join(self.change, "plan.md")
        text = open(path, encoding="utf-8").read().replace("Captcha and multi-factor sign-in.", "<script>alert(1)</script>")
        open(path, "w", encoding="utf-8").write(text)
        code, out = run("render", self.change, "--artifact")
        self.assertEqual(code, 0, out)
        page = self.page()
        self.assertNotIn("<!doctype", page)
        self.assertNotIn("<body>", page)
        self.assertNotIn("<script>alert", page)
        self.assertIn("&lt;script&gt;", page)

    def test_missing_plan(self):
        os.remove(os.path.join(self.change, "plan.md"))
        code, out = run("render", self.change)
        self.assertEqual(code, 1)
        self.assertIn("no plan.md", out["error"])


if __name__ == "__main__":
    unittest.main()
