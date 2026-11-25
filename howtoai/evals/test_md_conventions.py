"""The Markdown structure checks after 2026-11-24. Run: py -3 -I -B <this file>.

No file needs a closing Skills and agents section any more, and an agent-read
file of a skill or agent under 100 lines needs no Contents list; longer files
and other documents still do.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

HOWTOAI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(HOWTOAI, "skills", "skill-audit", "scripts")
REFERENCES = os.path.join(HOWTOAI, "skills", "skill-audit", "references")

SHORT_SKILL = ("---\nname: demo\ndescription: Says hello.\n---\n\n# Demo\n\nSay hello.\n\n"
               "See [notes](references/notes.md).\n\n## Feedback\n\nSend changes to `skill-builder`.\n")


def put(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def run(script, *args):
    p = subprocess.run([sys.executable, "-I", "-B", os.path.join(SCRIPTS, script), *args, "--no-web"],
                       capture_output=True, text=True, encoding="utf-8", timeout=120)
    if p.returncode != 0:
        raise AssertionError(p.stderr[-500:])
    return json.loads(p.stdout)


class Base(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.t = os.path.realpath(tmp.name)
        self.home = os.path.join(self.t, "home")
        os.makedirs(self.home)


class ToolAudit(Base):
    def findings(self, check=None):
        got = run("check_md.py", "--root", self.home)
        return [f for f in got["findings"] if check is None or f["check"] == check], got

    def test_no_skills_and_agents_section_is_needed(self):
        put(os.path.join(self.home, "skills", "demo", "SKILL.md"), SHORT_SKILL)
        put(os.path.join(self.home, "skills", "demo", "references", "notes.md"), "# Notes\n\nHello.\n")
        found, got = self.findings()
        self.assertEqual([f for f in found if "Skills and agents" in f["message"]], [])
        self.assertNotIn("S4", got["checks_run"])

    def test_short_skill_files_need_no_contents(self):
        put(os.path.join(self.home, "skills", "demo", "SKILL.md"), SHORT_SKILL)
        put(os.path.join(self.home, "skills", "demo", "references", "notes.md"), "# Notes\n\nHello.\n")
        put(os.path.join(self.home, "agents", "helper.md"),
            "---\nname: helper\ndescription: Helps.\n---\n\n# Helper\n\nHelp.\n")
        self.assertEqual(self.findings("S1")[0], [])

    def test_long_skill_files_still_need_contents(self):
        put(os.path.join(self.home, "skills", "demo", "SKILL.md"), SHORT_SKILL)
        put(os.path.join(self.home, "skills", "demo", "references", "notes.md"),
            "# Notes\n\n" + "Line.\n" * 100)
        s1 = self.findings("S1")[0]
        self.assertEqual([f["file"].split("/")[-1] for f in s1], ["notes.md"])

    def test_other_documents_still_need_contents(self):
        put(os.path.join(self.home, "commands", "hello.md"), "# Hello\n\nSay hello.\n")
        self.assertEqual(len(self.findings("S1")[0]), 1)


class WorkspaceAudit(Base):
    def run_ws(self, text):
        ws = os.path.join(self.t, "ws")
        put(os.path.join(ws, "AGENTS.md"), text)
        return run("check_agents.py", "--workspace", ws, "--global-dir", self.home)["findings"]

    def test_agents_md_needs_no_skills_and_agents_section(self):
        found = self.run_ws("# W\n\n## Contents\n\n- [Project](#project)\n\n## Project\n\nText.\n")
        self.assertEqual([f for f in found if "Skills and agents" in f["message"]], [])

    def test_an_installed_skills_list_is_still_kept_in_sync(self):
        found = self.run_ws("# W\n\n## Contents\n\n- [Installed skills](#installed-skills)\n\n"
                            "## Installed skills\n\n- `ghost` - not installed.\n")
        self.assertIn("Listed but not installed: `ghost`; propose removal.", [f["message"] for f in found])


class PluginAuditLine(Base):
    """A `line` check finds a named list entry anywhere in AGENTS.md, under any heading."""

    def results(self, agents_md):
        ws = os.path.join(self.t, "ws")
        put(os.path.join(ws, "AGENTS.md"), agents_md)
        audit = os.path.join(self.t, "tool", "AUDIT.md")
        put(audit, "# x audit\n\n## Checks\n\n| ID | Scope | Applies | Kind | Target | Expect | Fix |\n"
                   "| --- | --- | --- | --- | --- | --- | --- |\n"
                   "| A | workspace | always | line | `{workspace}/AGENTS.md` | `#L` | Add it. |\n"
                   "\n## L\n\n```markdown\n- `tool` - does things.\n```\n")
        p = subprocess.run([sys.executable, "-I", "-B", os.path.join(SCRIPTS, "check_plugins.py"),
                            "--global-dir", self.home, "--audit", audit, "--workspace", ws],
                           capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr[-300:])
        return {r["id"]: r for r in json.loads(p.stdout)["results"]}

    def test_line_under_any_heading_passes(self):
        got = self.results("# W\n\n## Installed skills\n\n- `tool` - does things.\n")
        self.assertEqual(got["A"]["status"], "pass", got)

    def test_two_entries_of_one_name_still_fail(self):
        got = self.results("# W\n\n## A\n\n- `tool` - old.\n\n## B\n\n- `tool` - does things.\n")
        self.assertEqual(got["A"]["status"], "fail", got)


class References(unittest.TestCase):
    def test_conventions_no_longer_require_the_section(self):
        for name in ("markdown-conventions.md", "checks.md"):
            with open(os.path.join(REFERENCES, name), encoding="utf-8") as f:
                self.assertNotIn("Skills and agents", f.read(), name)


if __name__ == "__main__":
    unittest.main()
