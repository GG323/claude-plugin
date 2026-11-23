"""The AUDIT runner's hard limits. Run: py -3 -I -B <this file>.

No input may hang the audit, whatever the pattern that would be slow on it: each file has a time limit.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

HOWTOAI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(HOWTOAI, "skills", "skill-audit", "scripts", "check_plugins.py")
HEAD = "# x audit\n\n## Checks\n\n| ID | Scope | Applies | Kind | Target | Expect | Fix |\n| --- | --- | --- | --- | --- | --- | --- |\n"
SECTION = "| A | workspace | always | section | `{workspace}/AGENTS.md` | `#T` | none |\n"
BUDGET = 20  # seconds for a whole run with one hostile file


def put(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def block(body):
    return f"\n## T\n\n```markdown\n## R\n\n{body}\n```\n"


class Setup(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.t = os.path.realpath(tmp.name)
        self.home, self.ws = os.path.join(self.t, "home"), os.path.join(self.t, "ws")
        os.makedirs(self.home)
        put(os.path.join(self.ws, "AGENTS.md"), "# A\n")

    def run_script(self, *args, script=SCRIPT):
        started = time.monotonic()
        p = subprocess.run([sys.executable, "-I", "-B", script, "--global-dir", self.home, *args],
                           capture_output=True, text=True, encoding="utf-8", timeout=BUDGET)
        self.assertLess(time.monotonic() - started, BUDGET)
        self.assertEqual(p.returncode, 0, p.stderr[-300:])
        return json.loads(p.stdout)

    def audit(self, rows, after=""):
        path = os.path.join(self.t, "tool", "AUDIT.md")
        put(path, HEAD + rows + after)
        return self.run_script("--audit", path, "--workspace", self.ws)["results"]


class NoImports(Setup):
    def refused(self, body):
        got = self.audit(SECTION, block(body))
        self.assertEqual([r["status"] for r in got], ["invalid"], body)
        self.assertNotIn("text", got[0])

    def test_second_at(self):
        self.refused("@a@b/../../../x.md")

    def test_between_code_spans(self):
        self.refused("`` ` `` @../../../x.md `` ` ``")

    def test_no_slash_or_extension(self):
        self.refused("@README")

    def test_home(self):
        self.refused("@~")

    def test_after_punctuation(self):
        self.refused("see (@notes)")


class Limits(Setup):
    def test_many_fill_in_starts(self):
        got = self.audit(SECTION * 3, block("{json:" * 9000))
        self.assertTrue(all(r["status"] == "invalid" for r in got))

    def test_many_link_starts_in_a_plugin_file(self):
        put(os.path.join(self.t, "tool", "big.md"), "## R\n\n" + "](" * 200000 + "\n")
        got = self.audit("| A | workspace | always | section | `{workspace}/AGENTS.md` | `{plugin}/big.md#R` | none |\n")
        self.assertEqual(got[0]["status"], "invalid")

    def test_block_size(self):
        self.assertEqual(self.audit(SECTION, block("x" * 4097))[0]["status"], "invalid")

    def test_check_count(self):
        rows = "".join(f"| C{i} | workspace | always | exists | `{{workspace}}` | x | none |\n" for i in range(65))
        got = self.audit(rows)
        self.assertIn("invalid", [r["status"] for r in got])
        self.assertLessEqual(len([r for r in got if r["status"] == "pass"]), 64)

    def test_wildcard_count(self):
        got = self.audit("| A | workspace | always | exists | `{workspace}/*/*/*` | x | none |\n")
        self.assertEqual(got[0]["status"], "invalid")

    def test_a_stuck_file_is_killed_and_the_others_still_run(self):
        """Independent of what is slow: plant a check kind that never ends, in a copy of the script."""
        with open(SCRIPT, encoding="utf-8") as f:
            code = f.read()
        anchor = '        if kind == "exists":\n            found = self.many(target)\n'
        self.assertEqual(code.count(anchor), 1)
        stuck = os.path.join(self.t, "check_plugins.py")
        put(stuck, code.replace(anchor, '        if kind == "exists" and expect == "stick":\n'
                                        '            re.match(r"(a+)+$", "a" * 60 + "b")\n' + anchor))
        put(os.path.join(self.home, "skills", "stuck", "AUDIT.md"),
            HEAD + "| S | global | always | exists | `{plugin}` | stick | none |\n")
        put(os.path.join(self.home, "skills", "fine", "AUDIT.md"),
            HEAD + "| F | global | always | exists | `{plugin}` | x | none |\n")
        got = {r["tool"]: r["status"] for r in self.run_script(script=stuck)["results"]}
        self.assertEqual(got, {"stuck": "invalid", "fine": "pass"})


class CommandPaths(Setup):
    def test_parentheses_inside_quotes(self):
        self.ws = os.path.join(self.t, "Client (EU) & Co's")
        os.makedirs(self.ws)
        got = self.audit('| A | workspace | always | command | `tool --workspace "{workspace}"` | ok | none |\n')
        self.assertEqual(got[0]["status"], "needs-approval")

    def test_parentheses_outside_quotes(self):
        self.ws = os.path.join(self.t, "Client (EU)")
        os.makedirs(self.ws)
        got = self.audit("| A | workspace | always | command | `tool --workspace {workspace}` | ok | none |\n")
        self.assertEqual(got[0]["status"], "invalid")


class CommandFolders(Setup):
    def test_an_agent_below_a_folder_named_commands(self):
        root = os.path.join(self.t, "commands", "pack")
        put(os.path.join(root, ".claude-plugin", "plugin.json"), '{"name": "pack"}')
        put(os.path.join(root, "agents", "helper.md"), "---\nname: helper\n---\n")
        put(os.path.join(root, "agents", "helper.AUDIT.md"), HEAD + "| A | global | always | exists | `{plugin}` | x | none |\n")
        put(os.path.join(self.home, "plugins", "installed_plugins.json"), json.dumps({"plugins": {"pack@m": [{"installPath": root}]}}))
        self.assertEqual([a["tool"] for a in self.run_script()["audits"]], ["helper"])

    def test_a_folder_named_commands_inside_commands(self):
        put(os.path.join(self.home, "commands", "commands", "x.md"), "do x\n")
        put(os.path.join(self.home, "audits", "commands", "x.AUDIT.md"),
            HEAD + "| A | global | always | exists | `{plugin}` | x | none |\n")
        self.assertEqual([a["tool"] for a in self.run_script()["audits"]], ["x"])


class RunLimits(Setup):
    def test_one_tool_cannot_flood_the_run(self):
        root = os.path.join(self.t, "flood")
        put(os.path.join(root, ".claude-plugin", "plugin.json"), '{"name": "flood"}')
        for n in range(40):
            put(os.path.join(root, "skills", f"s{n}", "AUDIT.md"), HEAD + "| A | global | always | exists | `{plugin}` | x | none |\n")
        put(os.path.join(self.home, "skills", "fine", "AUDIT.md"), HEAD + "| F | global | always | exists | `{plugin}` | x | none |\n")
        put(os.path.join(self.home, "plugins", "installed_plugins.json"), json.dumps({"plugins": {"flood@m": [{"installPath": root}]}}))
        got = self.run_script()["results"]
        self.assertEqual([r["status"] for r in got if r["tool"] == "fine"], ["pass"])
        self.assertLessEqual(len([r for r in got if r["status"] == "pass"]), 17)
        self.assertEqual(len([r for r in got if "not run" in r["evidence"]]), 24)

    def test_slow_tools_cannot_use_up_the_whole_run(self):
        with open(SCRIPT, encoding="utf-8") as f:
            code = f.read()
        anchor = '        if kind == "exists":\n            found = self.many(target)\n'
        slow = os.path.join(self.t, "check_plugins.py")
        put(slow, code.replace(anchor, '        if kind == "exists" and expect == "stick":\n'
                                       '            re.match(r"(a+)+$", "a" * 60 + "b")\n' + anchor)
            .replace("RUN_SECONDS, OWNER_SECONDS, OWNER_FILES = 60, 10, 16", "RUN_SECONDS, OWNER_SECONDS, OWNER_FILES = 7, 10, 16"))
        for n in range(6):
            put(os.path.join(self.home, "skills", f"slow{n}", "AUDIT.md"),
                HEAD + "| S | global | always | exists | `{plugin}` | stick | none |\n")
        got = self.run_script(script=slow)["results"]
        self.assertEqual(len(got), 6)
        self.assertTrue(any("seconds were used up" in r["evidence"] for r in got))


class Network(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Windows network paths")
    def test_network_paths_are_seen_without_touching_them(self):
        sys.path.insert(0, os.path.dirname(SCRIPT))
        import check_plugins
        started = time.monotonic()
        self.assertTrue(check_plugins.remote("\\\\host.invalid\\share\\x.md"))
        self.assertTrue(check_plugins.remote("//host.invalid/share/x.md"))
        self.assertFalse(check_plugins.remote(SCRIPT))
        self.assertLess(time.monotonic() - started, 1)


if __name__ == "__main__":
    unittest.main()
