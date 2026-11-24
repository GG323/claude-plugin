"""Tests for devcore.py. Run: py -3 -I -m unittest <this file> (or py -3 -I <this file>).

Each test works in its own temporary workspace and passes --user-file, so no real settings are read
or written.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
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

    # F1 fix batch 6: settings values come from a file, so production markers never sit in a command's text,
    # where dev-safe-target would deny the command once the settings name them.
    def values_file(self, text, name="values.json"):
        path = os.path.join(self.tmp.name, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def test_setup_reads_values_from_a_file(self):
        values = self.values_file('{"environments": {"deny": ["orders-prod.shop.invalid"]}}')
        code, out = run("setup", "--workspace", self.ws, "--values-file", values)
        self.assertEqual((code, out["written"]), (0, False))
        self.assertEqual(out["settings"]["environments"]["deny"], ["orders-prod.shop.invalid"])
        code, out = run("setup", "--workspace", self.ws, "--values-file", values, "--write")
        self.assertEqual((code, out["written"]), (0, True))
        with open(out["path"], encoding="utf-8") as f:
            self.assertIn("orders-prod.shop.invalid", f.read())

    def test_setup_needs_exactly_one_values_source(self):
        values = self.values_file('{"plan_folder": "plans"}')
        for args in ((), ("--values", '{"plan_folder": "plans"}', "--values-file", values)):
            code, out = run("setup", "--workspace", self.ws, *args)
            self.assertNotEqual(code, 0, args)
            self.assertIn("exactly one of --values or --values-file", out["error"])
        code, out = run("setup", "--workspace", self.ws, "--values-file", os.path.join(self.tmp.name, "none.json"))
        self.assertNotEqual(code, 0)
        self.assertIn("--values-file", out["error"])
        code, out = run("setup", "--workspace", self.ws, "--values-file", self.values_file("{not json", "bad.json"))
        self.assertNotEqual(code, 0)
        self.assertIn("not valid JSON", out["error"])
        bom = os.path.join(self.tmp.name, "bom.json")
        with open(bom, "wb") as f:
            f.write(b"\xef\xbb\xbf" + b'{"plan_folder": "plans"}')
        self.assertEqual(run("setup", "--workspace", self.ws, "--values-file", bom)[0], 0)
        latin = os.path.join(self.tmp.name, "latin.json")
        with open(latin, "wb") as f:
            f.write(b'{"plan_folder": "pl\xe4ns"}')
        code, out = run("setup", "--workspace", self.ws, "--values-file", latin)
        self.assertNotEqual(code, 0)
        self.assertIn("--values-file cannot be read", out["error"])

    def test_control_inline_values_still_work(self):
        code, out = run("setup", "--workspace", self.ws, "--values", '{"plan_folder": "plans"}')
        self.assertEqual((code, out["written"]), (0, False))

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
        patch = json.dumps({"stage": "accept", "size": "Medium", "append": {"approvals": {"what": "plan", "by": "user", "reply": "approve"}},
                            "increment": {"plan-review": 2}})
        code, st = run("state", out["change_dir"], "--patch", patch, "--now", "2026-11-18T11:00:00+02:00")
        s = st["state"]
        self.assertEqual((s["stage"], s["size"], s["loops"]["plan-review"], len(s["history"])), ("accept", "Medium", 2, 2))
        self.assertNotEqual(s["approvals"][0]["at"], "2026-11-18T11:00:00+02:00")  # user approvals take the real clock
        self.assertTrue(s["approvals"][0]["unverified"])  # no reply log in this workspace
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
        self.assertIn("**/.github/workflows/**", merged["settings"]["build"]["protected_globs"])

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


HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                    "hooks", "dev_reply_log.py")


class UserApprovalNeedsTheReply(unittest.TestCase):
    """F8-C1: an approval "by": "user" is recorded only with the user's reply, checked against the
    dev-reply-log hook's record when it exists."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="devcore-reply-")
        self.ws = os.path.join(self.tmp.name, "ws")
        os.makedirs(os.path.join(self.ws, ".howtoai", "dev"))
        with open(os.path.join(self.ws, "AGENTS.md"), "w", encoding="utf-8") as f:
            f.write("# ws\n")
        with open(os.path.join(self.ws, ".howtoai", "dev", "settings.json"), "w", encoding="utf-8") as f:
            f.write('{"tracker": {"kind": "markdown"}}')
        self.user = os.path.join(self.tmp.name, "user.json")
        _, out = run("new-change", "--workspace", self.ws, "--user-file", self.user, "--title", "x")
        self.change = out["change_dir"]
        self.log = os.path.join(self.ws, ".howtoai", "dev", "replies.jsonl")

    def tearDown(self):
        self.tmp.cleanup()

    def reply(self, text):
        p = subprocess.run([sys.executable, "-I", "-B", HOOK], input=json.dumps({"prompt": text, "cwd": self.ws}),
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual((p.returncode, p.stdout), (0, ""))

    def approve(self, **entry):
        return run("state", self.change, "--patch", json.dumps({"append": {"approvals": {"what": "human review, round 2",
                                                                                         "by": "user", **entry}}}))

    def test_the_three_reproduced_shapes_are_refused(self):
        self.reply("tell me the findings")
        shapes = [{"stage": "deploy", "append": {"approvals": {"what": "human review, round 2", "by": "user"}}},
                  {"append": {"approvals": {"what": "plan", "by": "user", "conditions": "none"}}},
                  {"append": {"approvals": {"what": "production deploy", "by": "user", "reply": "yes"}}}]
        for patch in shapes:
            code, out = run("state", self.change, "--patch", json.dumps(patch))
            self.assertEqual(code, 1, patch)
            self.assertIn("reply", out["error"])
        _, st = run("state", self.change)
        self.assertEqual((st["state"]["approvals"], st["state"]["stage"]), ([], "plan"))

    def test_a_matching_reply_is_recorded_and_the_log_holds_no_text(self):
        self.reply("  Yes,   ship it ")
        code, out = self.approve(reply="yes, ship it")
        self.assertEqual(code, 0, out)
        self.assertNotIn("unverified", out["state"]["approvals"][0])
        with open(self.log, encoding="utf-8") as f:
            logged = f.read()
        self.assertNotIn("ship", logged.lower())
        self.assertEqual(sorted(json.loads(logged.splitlines()[0])), ["at", "sha256"])

    def test_a_reply_used_by_an_earlier_approval_is_stale(self):
        self.reply("yes")
        self.assertEqual(self.approve(reply="yes")[0], 0)
        code, out = self.approve(reply="yes")
        self.assertEqual(code, 1)
        self.assertIn("since the last user approval", out["error"])
        time.sleep(1.1)  # a new reply comes after the approval's second
        self.reply("yes")
        self.assertEqual(self.approve(reply="yes")[0], 0)

    def test_a_used_reply_cannot_be_made_fresh_by_backdating(self):
        self.reply("yes")
        code, out = self.approve(reply="yes", at="1970-01-01T00:00:00+00:00")
        self.assertEqual(code, 0, out)
        self.assertNotEqual(out["state"]["approvals"][0]["at"][:4], "1970")
        code, _ = run("state", self.change, "--now", "1970-01-01T00:00:00+00:00", "--patch", json.dumps(
            {"append": {"approvals": {"what": "plan", "by": "user", "reply": "yes"}}}))
        self.assertEqual(code, 1)

    def test_one_reply_for_several_items_is_one_record(self):
        self.reply("yes to WI 2 and WI 3")
        code, out = self.approve(what="build may change tests, WI 2", reply="yes to WI 2 and WI 3")
        self.assertEqual(code, 0, out)
        code, out = self.approve(what="build may change tests, WI 3", reply="yes to WI 2 and WI 3")
        self.assertEqual(code, 1)
        self.assertIn("since the last user approval", out["error"])
        _, st = run("state", self.change)
        self.assertEqual([a["what"] for a in st["state"]["approvals"]], ["build may change tests, WI 2"])

    def test_without_the_log_it_is_recorded_unverified_but_never_without_a_reply(self):
        code, out = self.approve(reply="approve")
        self.assertEqual(code, 0, out)
        self.assertTrue(out["state"]["approvals"][0]["unverified"])
        self.assertEqual(self.approve(reply="  ")[0], 1)

    def test_an_unverified_approval_prints_a_warning(self):
        code, out = self.approve(reply="approve")
        self.assertEqual(code, 0, out)
        self.assertTrue(any("unverified" in w for w in out["warnings"]), out)

    def test_control_a_verified_approval_prints_no_warning(self):
        self.reply("approve")
        code, out = self.approve(reply="approve")
        self.assertEqual(code, 0, out)
        self.assertEqual(out.get("warnings", []), [])


    def test_a_plan_cover_needs_the_users_plan_approval(self):
        cover = {"append": {"approvals": {"what": "build may change ci.yml, named in WI 1", "by": "plan",
                                          "paths": [".github/workflows/ci.yml"]}}}
        code, out = run("state", self.change, "--patch", json.dumps(cover))
        self.assertEqual(code, 1)
        self.assertIn("plan approval", out["error"])
        self.reply("approved")
        self.assertEqual(self.approve(what="plan", reply="approved")[0], 0)
        code, out = run("state", self.change, "--patch", json.dumps(cover))
        self.assertEqual(code, 0, out)
        self.assertTrue(out["state"]["approvals"][-1]["covers"].startswith("plan approval at "))

    def test_other_approvers_are_unchanged(self):
        self.reply("something")
        code, _ = run("state", self.change, "--patch", json.dumps({"append": {"approvals": {"what": "test change",
                                                                                            "by": "fix-now choice"}}}))
        self.assertEqual(code, 0)


class TestsFirstMoveChecksGit(unittest.TestCase):
    """No-hook batch: the move from tests-first to build is refused when git shows non-test work since tests-first."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="devcore-tf-")
        self.ws = os.path.join(self.tmp.name, "ws")
        os.makedirs(os.path.join(self.ws, "src"))
        self.put("AGENTS.md", "# ws\n")
        self.put("src/old.py", "x = 1\n")
        self.user = os.path.join(self.tmp.name, "user.json")

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, rel, body):
        path = os.path.join(self.ws, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(body)
        return path

    def git(self):
        subprocess.run(["git", "init", "-q", self.ws], check=True)
        subprocess.run(["git", "-C", self.ws, "add", "-A"], check=True)
        subprocess.run(["git", "-C", self.ws, "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                        "commit", "-q", "-m", "x"], check=True)

    def to_tests_first(self):
        _, out = run("new-change", "--workspace", self.ws, "--user-file", self.user, "--title", "x")
        self.change = out["change_dir"]
        run("state", self.change, "--user-file", self.user, "--patch", '{"stage": "tests-first"}',
            "--now", "2000-01-01T00:00:00+00:00")
        sp = os.path.join(self.change, "state.json")
        with open(sp, encoding="utf-8") as f:
            state = json.load(f)
        state["history"][-1]["at"] = "2026-01-01T00:00:00+00:00"  # tests-first began before every file below
        with open(sp, "w", encoding="utf-8") as f:
            json.dump(state, f)

    def to_build(self):
        return run("state", self.change, "--user-file", self.user, "--patch", '{"stage": "build"}')

    def test_product_code_changed_at_tests_first_is_refused(self):
        self.git()
        self.to_tests_first()
        self.put("src/app.py", "y = 2\n")
        code, out = self.to_build()
        self.assertEqual(code, 1, out)
        self.assertIn("src/app.py", out["error"])
        _, st = run("state", self.change)
        self.assertEqual(st["state"]["stage"], "tests-first")

    def test_control_tests_plan_files_and_older_changes_pass(self):
        self.git()
        self.put("src/old.py", "x = 3\n")
        os.utime(os.path.join(self.ws, "src", "old.py"), (946684800, 946684800))  # changed before tests-first
        self.to_tests_first()
        self.put("tests/test_app.py", "def test(): pass\n")
        self.put(".howtoai/dev/note.txt", "x\n")
        code, out = self.to_build()
        self.assertEqual(code, 0, out)
        self.assertEqual(out["state"]["stage"], "build")
        self.assertNotIn("unchecked", out["state"]["history"][-1])

    def test_without_git_the_move_is_recorded_unchecked(self):
        self.to_tests_first()
        self.put("src/app.py", "y = 2\n")
        code, out = self.to_build()
        self.assertEqual(code, 0, out)
        self.assertIn("git", out["state"]["history"][-1]["unchecked"])
        self.assertTrue(out["warnings"])


if __name__ == "__main__":
    unittest.main()
