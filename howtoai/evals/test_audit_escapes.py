"""Hostile AUDIT.md files against check_plugins.py. Run: py -3 -I -B <this file>.

Everything lives in a temporary folder; the "secrets" are made-up marker strings.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

HOWTOAI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(HOWTOAI, "skills", "skill-audit", "scripts", "check_plugins.py")
HEAD = "# x audit\n\n## Checks\n\n| ID | Scope | Applies | Kind | Target | Expect | Fix |\n| --- | --- | --- | --- | --- | --- | --- |\n"
MARK = "outsidemarker42"


def put(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


class Setup(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.t = os.path.realpath(tmp.name)
        self.home, self.ws, self.tool = (os.path.join(self.t, n) for n in ("home", "ws", "tool"))
        for d in (self.home, self.ws, self.tool):
            os.makedirs(d)
        put(os.path.join(self.ws, "AGENTS.md"), "# A\n")
        put(os.path.join(self.t, "outside", "o.md"), f"# O\n\n## S\n\n{MARK}\n")

    def run_audit(self, rows, after=""):
        audit = os.path.join(self.tool, "AUDIT.md")
        put(audit, HEAD + rows + after)
        p = subprocess.run([sys.executable, "-I", "-B", SCRIPT, "--global-dir", self.home, "--audit", audit, "--workspace", self.ws],
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(p.returncode, 0, p.stderr[-400:])
        return p.stdout, {r["id"]: r["status"] for r in json.loads(p.stdout)["results"]}


class Hostile(Setup):
    def test_double_slash_does_not_leave_the_root(self):
        outside = os.path.splitdrive(os.path.join(self.t, "outside", "o.md"))[1].replace("\\", "/")
        out, got = self.run_audit(f"| A | workspace | always | section | `{{workspace}}/AGENTS.md` | `{{plugin}}/{outside}#S` | none |\n")
        self.assertNotIn(MARK, out)
        self.assertEqual(got["A"], "invalid")

    @unittest.skipUnless(os.name == "nt", "junctions are Windows only")
    def test_a_junction_does_not_leave_the_root(self):
        import _winapi
        link = os.path.join(self.tool, "link")
        _winapi.CreateJunction(os.path.join(self.t, "outside"), link)
        self.addCleanup(os.rmdir, link)
        out, got = self.run_audit("| A | workspace | always | section | `{workspace}/AGENTS.md` | `{plugin}/link/o.md#S` | none |\n")
        self.assertNotIn(MARK, out)
        self.assertEqual(got["A"], "invalid")

    def test_fill_in_reads_no_other_settings(self):
        put(os.path.join(self.ws, ".claude", "settings.local.json"), json.dumps({"env": {"SOME_VALUE": MARK}}))
        out, _ = self.run_audit("| A | workspace | always | section | `{workspace}/AGENTS.md` | `#T` | none |\n",
                                "\n## T\n\n```markdown\n## R\n\n{json:.claude/settings.local.json#env/SOME_VALUE}\n```\n")
        self.assertNotIn(MARK, out)

    def test_contains_is_no_oracle_for_settings(self):
        put(os.path.join(self.home, "settings.json"), json.dumps({"env": {"V": MARK}}))
        _, got = self.run_audit(f"| A | global | always | contains | `{{global}}/settings.json` | `{MARK[:4]}` | none |\n")
        self.assertEqual(got["A"], "invalid")

    @unittest.skipUnless(os.name == "nt", "Windows name rules")
    def test_trailing_dot_does_not_open_a_secret(self):
        put(os.path.join(self.ws, "server.pem"), MARK)
        _, got = self.run_audit(f"| A | workspace | always | contains | `{{workspace}}/server.pem.` | `{MARK}` | none |\n")
        self.assertEqual(got["A"], "invalid")

    def test_one_bad_check_does_not_end_the_run(self):
        _, got = self.run_audit("| A | workspace | always | exists | `{workspace}/a\0b` | x | none |\n"
                                "| B | workspace | always | exists | `{workspace}/AGENTS.md` | x | none |\n")
        self.assertEqual(got["B"], "pass")


class SecondRound(Setup):
    def test_import_is_only_agents_md(self):
        put(os.path.join(self.ws, "CLAUDE.md"), "# C\n")
        _, got = self.run_audit("| A | workspace | always | import | `{workspace}` | `@../../../x.md` | none |\n")
        self.assertEqual(got["A"], "invalid")

    def test_installed_text_imports_nothing(self):
        _, got = self.run_audit("| A | workspace | always | section | `{workspace}/AGENTS.md` | `#T` | none |\n",
                                "\n## T\n\n```markdown\n## R\n\n@~/notes.md\n```\n")
        self.assertEqual(got["A"], "invalid")

    def test_a_bad_name_does_not_lose_the_results(self):
        put(os.path.join(self.tool, ".claude-plugin", "plugin.json"), '{"name": "a\\ud800b"}')
        _, got = self.run_audit("| A | workspace | always | exists | `{workspace}/AGENTS.md` | x | none |\n")
        self.assertEqual(got["A"], "pass")

    def test_long_lines_do_not_hang(self):
        _, got = self.run_audit("| A | workspace | always | exists | `{workspace}/AGENTS.md` | x | none |\n",
                                "\n# a" + " " * 60000 + "b\n")
        self.assertEqual(got["A"], "pass")

    def test_other_markdown_is_no_oracle(self):
        put(os.path.join(self.ws, "notes.md"), MARK)
        _, got = self.run_audit(f"| A | workspace | always | contains | `{{workspace}}/notes.md` | `{MARK[:4]}` | none |\n")
        self.assertEqual(got["A"], "invalid")

    def test_hidden_characters_never_reach_approval(self):
        _, got = self.run_audit("| A | global | always | command | `echo ok\u202e hs.x` | ok | none |\n")
        self.assertEqual(got["A"], "invalid")

    def test_report_text_cannot_become_markup(self):
        sys.path.insert(0, os.path.dirname(SCRIPT))
        import render_report
        sample = '[x](https://e/"onmouseover="y)'
        self.assertNotIn('"onmouseover', render_report.text(sample))
        self.assertNotIn("<a", render_report.text(sample, False))


if __name__ == "__main__":
    unittest.main()
