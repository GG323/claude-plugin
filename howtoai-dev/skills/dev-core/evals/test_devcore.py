"""Tests for devcore.py. Run: py -3 -I -m unittest <this file> (or py -3 -I <this file>).

Each test works in its own temporary workspace and passes --user-file, so no real settings are read
or written.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "devcore.py")


def run(*args):
    p = subprocess.run([sys.executable, "-I", SCRIPT, *args], capture_output=True, text=True, encoding="utf-8")
    return p.returncode, json.loads(p.stdout)


class DevcoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="devcore-test-")
        self.ws = os.path.join(self.tmp.name, "ws")
        os.makedirs(os.path.join(self.ws, "src", "deep"))
        with open(os.path.join(self.ws, "AGENTS.md"), "w", encoding="utf-8") as f:
            f.write("# ws\n")
        self.user = os.path.join(self.tmp.name, "user.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_root_found_from_subfolder(self):
        code, out = run("root", "--cwd", os.path.join(self.ws, "src", "deep"))
        self.assertEqual(code, 0)
        self.assertEqual(os.path.normcase(out["workspace"]), os.path.normcase(self.ws))

    def test_root_missing(self):
        code, out = run("root", "--cwd", self.tmp.name)
        self.assertEqual(code, 1)
        self.assertIn("AGENTS.md", out["error"])

    def test_settings_defaults_then_layers(self):
        code, out = run("settings", "--workspace", self.ws, "--user-file", self.user)
        self.assertEqual((code, out["configured"], out["settings"]["tracker"]["kind"]), (0, False, "markdown"))
        with open(self.user, "w", encoding="utf-8") as f:
            json.dump({"tracker": {"kind": "github"}, "review": {"max_rounds": 3}}, f)
        run("setup", "--workspace", self.ws, "--values", '{"tracker": {"kind": "jira", "jira_project": "ABC"}}', "--write")
        code, out = run("settings", "--workspace", self.ws, "--user-file", self.user)
        s = out["settings"]
        self.assertEqual((s["tracker"]["kind"], s["tracker"]["jira_project"], s["review"]["max_rounds"]), ("jira", "ABC", 3))
        self.assertEqual((out["sources"]["tracker"], out["sources"]["review"], out["configured"]), ("project", "user", True))

    def test_setup_preview_writes_nothing(self):
        code, out = run("setup", "--workspace", self.ws, "--values", '{"plan_folder": "plans"}')
        self.assertEqual((code, out["written"]), (0, False))
        self.assertFalse(os.path.exists(out["path"]))

    def test_setup_rejects_unknown_bad_and_secret(self):
        for values in ('{"nope": 1}', '{"tracker": {"kind": "trello"}}', '{"review": {"max_rounds": "5"}}',
                       '{"deploy": {"entry_points": [{"command": "psql postgres://u:pw@db/x"}]}}',
                       '{"environments": {"deny": ["ghp_abcdefghijklmnopqrstuvwxyz0123"]}}'):
            code, out = run("setup", "--workspace", self.ws, "--values", values)
            self.assertEqual(code, 1, values)
            self.assertFalse(out["ok"])

    def test_new_change_state_and_index(self):
        code, out = run("new-change", "--workspace", self.ws, "--user-file", self.user, "--title", "Login rate limit!", "--date", "2026-11-18",
                        "--now", "2026-11-18T10:00:00+02:00")
        self.assertEqual((code, out["id"]), (0, "2026-11-18-login-rate-limit"))
        code, again = run("new-change", "--workspace", self.ws, "--user-file", self.user, "--title", "Login rate limit", "--date", "2026-11-18")
        self.assertEqual(again["id"], "2026-11-18-login-rate-limit-2")
        patch = json.dumps({"stage": "accept", "size": "Medium", "append": {"approvals": {"what": "plan", "by": "user"}},
                            "increment": {"plan-review": 2}})
        code, st = run("state", out["change_dir"], "--patch", patch, "--now", "2026-11-18T11:00:00+02:00")
        s = st["state"]
        self.assertEqual((s["stage"], s["size"], s["loops"]["plan-review"], len(s["history"])), ("accept", "Medium", 2, 2))
        self.assertEqual(s["approvals"][0]["at"], "2026-11-18T11:00:00+02:00")
        with open(os.path.join(self.ws, "dev-plans", "INDEX.md"), encoding="utf-8") as f:
            index = f.read()
        self.assertIn("| accept | Medium |", index)
        self.assertEqual(index.count("2026-11-18-login-rate-limit"), 4)

    def test_state_rejects_bad_patches(self):
        _, out = run("new-change", "--workspace", self.ws, "--user-file", self.user, "--title", "x", "--date", "2026-11-18")
        for patch in ('{"stage": "shipping"}', '{"size": "Huge"}', '{"owner": "me"}', '{"append": {"notes": {}}}',
                      '{"increment": {"Review": 1}}', '{"append": {"approvals": {"by": "token sk-abcdefghijklmnopqrstu"}}}'):
            code, res = run("state", out["change_dir"], "--patch", patch)
            self.assertEqual(code, 1, patch)
        _, st = run("state", out["change_dir"])
        self.assertEqual(st["state"]["stage"], "plan")

    def test_index_rebuild_after_manual_delete(self):
        _, a = run("new-change", "--workspace", self.ws, "--user-file", self.user, "--title", "a", "--date", "2026-11-18")
        run("new-change", "--workspace", self.ws, "--user-file", self.user, "--title", "b", "--date", "2026-11-18")
        os.remove(os.path.join(a["change_dir"], "state.json"))
        code, out = run("index", "--workspace", self.ws, "--user-file", self.user)
        self.assertEqual((code, out["changes"]), (0, 1))

    def test_test_runs_ephemeral_and_testing_settings(self):
        _, out = run("new-change", "--workspace", self.ws, "--user-file", self.user, "--title", "t", "--date", "2026-11-19")
        patch = json.dumps({"stage": "test", "append": {
            "test_runs": {"n": 1, "route": "run", "result": "green", "passed": 4, "failed": 0, "report": "test-run-1.md"},
            "ephemeral": {"run_id": "r1", "name": "pg", "label": "howtoai.dev.run=r1", "state": "removed"}}})
        code, st = run("state", out["change_dir"], "--patch", patch)
        self.assertEqual(code, 0)
        self.assertEqual((st["state"]["test_runs"][0]["result"], st["state"]["ephemeral"][0]["state"]), ("green", "removed"))
        good = json.dumps({"testing": {"entry_points": [{"name": "unit", "command": "dotnet test"}], "test_first": "warn"}})
        code, prev = run("setup", "--workspace", self.ws, "--user-file", self.user, "--values", good)
        self.assertEqual(code, 0, prev)
        code, _ = run("setup", "--workspace", self.ws, "--user-file", self.user, "--values", '{"testing": {"test_first": "maybe"}}')
        self.assertEqual(code, 1)
        _, merged = run("settings", "--workspace", self.ws, "--user-file", self.user)
        self.assertEqual((merged["settings"]["testing"]["max_reruns"], merged["settings"]["testing"]["reruns_per_test"]), (10, 3))

    def test_builds_and_build_settings(self):
        _, out = run("new-change", "--workspace", self.ws, "--user-file", self.user, "--title", "b", "--date", "2026-11-19")
        self.assertEqual(json.load(open(out["state"], encoding="utf-8"))["builds"], [])
        patch = json.dumps({"append": {"builds": {"n": 1, "wi": 1, "route": "build", "result": "passed", "report": "build-1.md"}}})
        code, st = run("state", out["change_dir"], "--patch", patch)
        self.assertEqual((code, st["state"]["builds"][0]["result"]), (0, "passed"))
        good = json.dumps({"build": {"gate": [{"name": "format", "command": "dotnet format --verify-no-changes", "source": "dotnet.commands.002"}]}})
        code, prev = run("setup", "--workspace", self.ws, "--user-file", self.user, "--values", good)
        self.assertEqual(code, 0, prev)
        code, _ = run("setup", "--workspace", self.ws, "--user-file", self.user, "--values", '{"build": {"max_fix_rounds": "3"}}')
        self.assertEqual(code, 1)
        _, merged = run("settings", "--workspace", self.ws, "--user-file", self.user)
        self.assertEqual(merged["settings"]["build"]["max_fix_rounds"], 3)
        self.assertIn(".github/workflows/**", merged["settings"]["build"]["protected_globs"])

    def test_azure_devops_tracker_and_plan_publish(self):
        _, merged = run("settings", "--workspace", self.ws, "--user-file", self.user)
        self.assertEqual((merged["settings"]["plan"]["publish"], merged["settings"]["tracker"]["plan_item_type"]), ("auto", "Epic"))
        code, out = run("setup", "--workspace", self.ws, "--user-file", self.user, "--values", '{"plan": {"publish": "tracker"}}')
        self.assertEqual(code, 1)
        self.assertIn("plan.publish tracker", out["error"])
        code, _ = run("setup", "--workspace", self.ws, "--user-file", self.user, "--values", '{"plan": {"publish": "slides"}}')
        self.assertEqual(code, 1)
        good = json.dumps({"tracker": {"kind": "azure-devops", "ado_org": "https://dev.azure.com/contoso", "ado_project": "Shop"},
                           "plan": {"publish": "tracker"}})
        code, out = run("setup", "--workspace", self.ws, "--user-file", self.user, "--values", good, "--write")
        self.assertEqual(code, 0, out)
        _, merged = run("settings", "--workspace", self.ws, "--user-file", self.user)
        self.assertEqual((merged["settings"]["tracker"]["kind"], merged["settings"]["tracker"]["ado_work_item_type"]), ("azure-devops", "Task"))
        code, _ = run("setup", "--workspace", self.ws, "--user-file", self.user, "--values", '{"tracker": {"kind": "markdown"}}')
        self.assertEqual(code, 1)
        with open(self.user, "w", encoding="utf-8") as f:
            json.dump({"tracker": {"kind": "jira", "jira_project": "SHOP"}}, f)
        ws2 = os.path.join(self.tmp.name, "ws2")
        os.makedirs(ws2)
        code, out = run("setup", "--workspace", ws2, "--user-file", self.user, "--values", '{"plan": {"publish": "tracker"}}')
        self.assertEqual(code, 0, out)
        _, ch = run("new-change", "--workspace", self.ws, "--user-file", self.user, "--title", "p", "--date", "2026-11-21")
        code, st = run("state", ch["change_dir"], "--patch", '{"plan_item": {"tracker_key": "4711", "kind": "azure-devops"}}')
        self.assertEqual((code, st["state"]["plan_item"]["tracker_key"]), (0, "4711"))
        code, _ = run("state", ch["change_dir"], "--patch", '{"plan_item": {"url": "x"}}')
        self.assertEqual(code, 1)

    def test_setup_user_scope_writes_user_file(self):
        code, out = run("setup", "--workspace", self.ws, "--user-file", self.user, "--scope", "user",
                        "--values", '{"plan": {"publish": "markdown"}}', "--write")
        self.assertEqual((code, out["scope"], out["path"]), (0, "user", self.user))
        self.assertFalse(os.path.exists(os.path.join(self.ws, ".howtoai", "dev", "settings.json")))
        _, merged = run("settings", "--workspace", self.ws, "--user-file", self.user)
        self.assertEqual((merged["settings"]["plan"]["publish"], merged["sources"]["plan"], merged["configured"]),
                         ("markdown", "user", False))

    def test_plan_folder_must_be_plain_name(self):
        run("setup", "--workspace", self.ws, "--values", '{"plan_folder": "../outside"}', "--write")
        code, out = run("new-change", "--workspace", self.ws, "--user-file", self.user, "--title", "x")
        self.assertEqual(code, 1)
        self.assertIn("plain folder name", out["error"])


if __name__ == "__main__":
    unittest.main()
