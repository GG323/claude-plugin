"""Tests for the howtoai-dev hooks. Run: py -3 -I <this file>.

Each test builds a workspace in a temporary folder, feeds the hook Claude Code's PreToolUse input
JSON on stdin, and sets HOWTOAI_DEV_USER_FILE so no real settings are read.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOKS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hooks")


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


class HookBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="devhooks-")
        self.ws = os.path.join(self.tmp.name, "ws")
        write(os.path.join(self.ws, "AGENTS.md"), "# ws\n")
        self.settings({"environments": {"allow": [], "deny": ["shop-prod.postgres.database.azure.com"]}})
        self.env = dict(os.environ, HOWTOAI_DEV_USER_FILE=os.path.join(self.tmp.name, "user.json"))

    def tearDown(self):
        self.tmp.cleanup()

    def settings(self, s):
        write(os.path.join(self.ws, "AGENTS", "settings", "dev", "settings.json"), json.dumps(s))

    def change(self, stage, **extra):
        st = {"id": "2026-11-19-x", "title": "x", "stage": stage, "updated": "2026-11-19T10:00:00+01:00",
              "test_runs": [], "ephemeral": [], **extra}
        write(os.path.join(self.ws, "dev-plans", "2026-11-19-x", "state.json"), json.dumps(st))

    def hook(self, name, tool, **tool_input):
        data = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input, "cwd": self.ws}
        p = subprocess.run([sys.executable, "-I", "-B", os.path.join(HOOKS, name)], input=json.dumps(data),
                           capture_output=True, text=True, env=self.env, encoding="utf-8")
        self.assertEqual(p.returncode, 0, p.stderr)
        if not p.stdout.strip():
            return None, ""
        o = json.loads(p.stdout)["hookSpecificOutput"]
        return o.get("permissionDecision", "warn"), o.get("permissionDecisionReason") or o.get("additionalContext", "")

    def path(self, rel):
        return os.path.join(self.ws, *rel.split("/"))


class TestFirstTests(HookBase):
    H = "dev_test_first.py"

    def test_silent_without_active_change(self):
        self.assertEqual(self.hook(self.H, "Edit", file_path=self.path("src/Api/Auth.cs"))[0], None)
        self.change("review")
        self.assertEqual(self.hook(self.H, "Write", file_path=self.path("src/Api/Auth.cs"))[0], None)

    def test_tests_first_blocks_code_allows_tests(self):
        self.change("tests-first")
        d, reason = self.hook(self.H, "Edit", file_path=self.path("src/Api/Auth.cs"))
        self.assertEqual(d, "deny")
        self.assertIn("tests-first", reason)
        for ok in ("tests/Api.Tests/AuthTests.cs", "src/Api/AuthTests.cs", "web/login.test.ts",
                   "dev-plans/2026-11-19-x/test-map.md", "tests/Api.Tests/TESTING.md"):
            self.assertEqual(self.hook(self.H, "Write", file_path=self.path(ok))[0], None, ok)

    def test_ci_denied_in_test_stages_only(self):
        self.change("test")
        self.assertEqual(self.hook(self.H, "Edit", file_path=self.path(".github/workflows/ci.yml"))[0], "deny")
        self.change("build", test_runs=[{"route": "red-check", "result": "red"}])
        self.assertEqual(self.hook(self.H, "Edit", file_path=self.path(".github/workflows/ci.yml"))[0], None)

    def test_build_warns_without_red_run(self):
        self.change("build")
        self.assertEqual(self.hook(self.H, "Edit", file_path=self.path("src/Api/Auth.cs"))[0], "warn")
        self.change("build", test_runs=[{"route": "red-check", "result": "red"}])
        self.assertEqual(self.hook(self.H, "Edit", file_path=self.path("src/Api/Auth.cs"))[0], None)

    def test_warn_and_off_modes(self):
        self.change("tests-first")
        self.settings({"testing": {"test_first": "warn"}})
        self.assertEqual(self.hook(self.H, "Edit", file_path=self.path("src/Api/Auth.cs"))[0], "warn")
        self.settings({"testing": {"test_first": "off"}})
        self.assertEqual(self.hook(self.H, "Edit", file_path=self.path("src/Api/Auth.cs"))[0], None)

    def test_outside_workspace_and_bad_input_are_silent(self):
        self.change("tests-first")
        other = os.path.join(self.tmp.name, "elsewhere", "x.cs")
        self.assertEqual(self.hook(self.H, "Edit", file_path=other)[0], None)
        p = subprocess.run([sys.executable, "-I", "-B", os.path.join(HOOKS, self.H)], input="not json",
                           capture_output=True, text=True, env=self.env)
        self.assertEqual((p.returncode, p.stdout), (0, ""))


    def test_ci_of_a_repository_in_a_subfolder_is_denied_in_test_stages(self):
        for stage in ("tests-first", "test"):
            self.change(stage)
            for ci in ("shop/.github/workflows/ci.yml", "a/b/.github/workflows/deploy.yaml", "shop/azure-pipelines.yml",
                       "shop/.gitlab-ci.yml", "shop/Jenkinsfile"):
                d, reason = self.hook(self.H, "Edit", file_path=self.path(ci))
                self.assertEqual(d, "deny", (stage, ci))
                self.assertIn("CI configuration", reason)
        self.change("build", test_runs=[{"route": "red-check", "result": "red"}])
        self.assertEqual(self.hook(self.H, "Edit", file_path=self.path("shop/.github/workflows/ci.yml"))[0], None)

    def test_control_ci_look_alikes_are_not_ci(self):
        self.change("test")
        for other in ("shop/docs/.github-notes.md", "shop/src/github/workflows.cs", "shop/x.github/workflows/ci.yml"):
            self.assertEqual(self.hook(self.H, "Edit", file_path=self.path(other))[0], None, other)


class SafeTargetTests(HookBase):
    H = "dev_safe_target.py"

    def test_deny_marker_in_command_and_mcp(self):
        d, reason = self.hook(self.H, "Bash", command="psql -h shop-prod.postgres.database.azure.com -c 'select 1'")
        self.assertEqual(d, "deny")
        self.assertIn("environments.deny", reason)
        self.assertEqual(self.hook(self.H, "mcp__db__query", host="SHOP-PROD.postgres.database.azure.com", sql="select 1")[0], "deny")
        self.assertEqual(self.hook(self.H, "PowerShell", command="dotnet test")[0], None)

    # F1 fix batch 5: the marker match stays as it is, so a written script cannot carry a marker; documents
    # go through the Write tool, which this hook does not read for markers.
    def test_a_heredoc_naming_a_marker_is_still_denied(self):
        cmd = "cat > AGENTS/settings/dev/report.md <<'EOF'\n| Target | shop-prod.postgres.database.azure.com | refused |\nEOF"
        self.assertEqual(self.hook(self.H, "Bash", command=cmd)[0], "deny")
        here = "$r=@'\n| Target | shop-prod.postgres.database.azure.com |\n'@; [IO.File]::WriteAllText('test-run-1.md', $r)"
        self.assertEqual(self.hook(self.H, "PowerShell", command=here)[0], "deny")

    def test_a_write_tool_document_naming_a_marker_is_allowed(self):
        body = "| Target | shop-prod.postgres.database.azure.com | refused |\n"
        self.assertEqual(self.hook(self.H, "Write", file_path=self.path("AGENTS/settings/dev/report.md"), content=body)[0], None)

    # F1 fix batch 6: inline settings values that name a marker are still denied; a values file keeps the
    # command free of the marker.
    def test_inline_values_naming_a_marker_are_still_denied(self):
        inline = ("py -3 -I -B devcore.py setup --workspace ws --values "
                  "'{\"environments\": {\"deny\": [\"shop-prod.postgres.database.azure.com\"]}}' --write")
        self.assertEqual(self.hook(self.H, "Bash", command=inline)[0], "deny")
        by_file = 'py -3 -I -B devcore.py setup --workspace ws --values-file "C:/scratch/values.json" --write'
        self.assertEqual(self.hook(self.H, "Bash", command=by_file)[0], None)

    def test_destructive_commands_ask_unless_owned(self):
        for cmd in ("psql -h db.test -c 'DROP TABLE users'", "dotnet ef database drop --force", "terraform destroy",
                    "sqlcmd -Q \"DELETE FROM Orders\"", "rails db:reset", "docker volume prune -f"):
            self.assertEqual(self.hook(self.H, "Bash", command=cmd)[0], "ask", cmd)
        self.assertEqual(self.hook(self.H, "Bash", command="psql -c \"DELETE FROM Orders WHERE id = 3\"")[0], None)
        self.change("test", ephemeral=[{"run_id": "2026-11-19-x-1", "name": "2026-11-19-x-1-pg", "state": "created"}])
        self.assertEqual(self.hook(self.H, "Bash", command="docker exec 2026-11-19-x-1-pg psql -c 'DROP TABLE users'")[0], None)
        self.change("test", ephemeral=[{"run_id": "2026-11-19-x-1", "name": "2026-11-19-x-1-pg", "state": "created"},
                                       {"run_id": "2026-11-19-x-1", "name": "2026-11-19-x-1-pg", "state": "removed"}])
        self.assertEqual(self.hook(self.H, "Bash", command="docker exec 2026-11-19-x-1-pg psql -c 'DROP TABLE users'")[0], "ask")
        self.assertEqual(self.hook(self.H, "Bash", command="psql -h db.shared -c 'DROP TABLE users' # 2026-11-19-x-1")[0], "ask")

    def test_migration_edits(self):
        mig = self.path("src/Api/Migrations/20261119_Rename.cs")
        d, reason = self.hook(self.H, "Write", file_path=mig,
                              content="protected override void Up(MigrationBuilder m) { migrationBuilder.RenameColumn(\"Email\", \"Users\", \"Login\"); }")
        self.assertEqual(d, "ask")
        self.assertIn("destructive-confirmed", reason)
        create = ("protected override void Up(MigrationBuilder migrationBuilder) { migrationBuilder.CreateTable(\"Logins\"); }\n"
                  "protected override void Down(MigrationBuilder migrationBuilder) { migrationBuilder.DropTable(\"Logins\"); }")
        self.assertEqual(self.hook(self.H, "Write", file_path=mig, content=create)[0], None)
        self.assertEqual(self.hook(self.H, "Write", file_path=self.path("db/migrations/003.sql"),
                                   content="-- howtoai-dev: destructive-confirmed\nALTER TABLE users DROP COLUMN email;")[0], None)
        self.assertEqual(self.hook(self.H, "Edit", file_path=self.path("db/migrations/003.sql"),
                                   old_string="x", new_string="ALTER TABLE users ALTER COLUMN age TYPE bigint;")[0], "ask")
        write(mig, create)
        self.assertEqual(self.hook(self.H, "Edit", file_path=mig, old_string="migrationBuilder.DropTable(\"Logins\");",
                                   new_string="migrationBuilder.DropTable(\"Logins\"); migrationBuilder.DropIndex(\"ix\");")[0], None)
        self.assertEqual(self.hook(self.H, "Edit", file_path=self.path("src/Api/Users.cs"),
                                   old_string="a", new_string="// DROP TABLE users")[0], None)

    def test_deny_message_says_what_why_where_and_how_to_change(self):
        project = os.path.join(self.ws, "AGENTS", "settings", "dev", "settings.json")
        user = self.env["HOWTOAI_DEV_USER_FILE"]
        d, reason = self.hook(self.H, "Bash", command="psql -h SHOP-PROD.postgres.database.azure.com")
        self.assertEqual(d, "deny")
        for part in ("blocked this command", "'shop-prod.postgres.database.azure.com'", project, "ignoring case",
                     "anywhere", "file edits are not checked", "environments.allow", "Setup route", "INSTALL"):
            self.assertIn(part, reason)
        self.assertNotIn(user, reason, "a marker only the project lists does not name the user file")
        self.assertIn("mcp__db__query call", self.hook(self.H, "mcp__db__query", host="shop-prod.postgres.database.azure.com")[1])
        write(user, json.dumps({"environments": {"deny": ["Shop-Prod.postgres.database.azure.com"]}}))
        reason = self.hook(self.H, "Bash", command="psql -h shop-prod.postgres.database.azure.com")[1]
        self.assertIn(project + " and " + user, reason, "a marker both files list names both")

    def test_deny_message_names_only_the_user_file(self):
        os.remove(os.path.join(self.ws, "AGENTS", "settings", "dev", "settings.json"))
        user = self.env["HOWTOAI_DEV_USER_FILE"]
        write(user, json.dumps({"environments": {"deny": ["prod-db.example.com"]}}))
        reason = self.hook(self.H, "Bash", command="psql -h prod-db.example.com")[1]
        self.assertIn("in " + user + ".", reason)

    def test_unconfigured_workspace_only_deny_markers(self):
        os.remove(os.path.join(self.ws, "AGENTS", "settings", "dev", "settings.json"))
        write(self.env["HOWTOAI_DEV_USER_FILE"], json.dumps({"environments": {"deny": ["prod-db.example.com"]}}))
        self.assertEqual(self.hook(self.H, "Bash", command="terraform destroy")[0], None)
        self.assertEqual(self.hook(self.H, "Bash", command="psql -h prod-db.example.com")[0], "deny")

    def test_hook_rules(self):
        self.settings({"hook_rules": [{"id": "R1", "match": "git\\s+push\\s+--force", "action": "block", "reason": "no force push"},
                                      {"id": "R2", "match": "npm\\s+publish", "action": "warn", "reason": "publishing"}]})
        self.assertEqual(self.hook(self.H, "Bash", command="git push --force origin main"), ("deny", "dev-safe-target rule R1: no force push"))
        self.assertEqual(self.hook(self.H, "Bash", command="npm publish")[0], "warn")

    def approvals(self, items):
        write(os.path.join(self.ws, "AGENTS", "settings", "deploy", "approvals.json"), json.dumps({"approvals": items}))

    def test_approved_deploy_step_passes_once_and_never_allows(self):
        import datetime
        later = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30)).isoformat()
        cmd = "kubectl --context shop-prod.postgres.database.azure.com rollout restart deploy/shop"
        self.approvals([{"id": "A1", "command": cmd, "expires": later, "used": False}])
        self.assertEqual(self.hook(self.H, "Bash", command="  " + cmd + " ")[0], None)  # no allow, no deny
        with open(os.path.join(self.ws, "AGENTS", "settings", "deploy", "approvals.json"), encoding="utf-8") as f:
            self.assertTrue(json.load(f)["approvals"][0]["used"])
        self.assertEqual(self.hook(self.H, "Bash", command=cmd)[0], "deny")  # one use only

    def test_expired_or_different_approval_does_not_pass(self):
        import datetime
        past = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1)).isoformat()
        later = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30)).isoformat()
        cmd = "psql -h shop-prod.postgres.database.azure.com -c 'select 1'"
        self.approvals([{"id": "A1", "command": cmd, "expires": past, "used": False},
                        {"id": "A2", "command": cmd + " --other", "expires": later, "used": False}])
        self.assertEqual(self.hook(self.H, "Bash", command=cmd)[0], "deny")
        write(os.path.join(self.ws, "AGENTS", "settings", "deploy", "approvals.json"), "{broken")
        self.assertEqual(self.hook(self.H, "Bash", command=cmd)[0], "deny")


class ReplyLogTests(HookBase):
    """F8-C1: the dev-reply-log hook records a hash of each user prompt; nothing else may write it."""
    H = "dev_reply_log.py"
    LOG = "AGENTS/settings/dev/replies.jsonl"

    def prompt(self, text, cwd=None):
        data = {"hook_event_name": "UserPromptSubmit", "prompt": text, "cwd": cwd or self.ws}
        p = subprocess.run([sys.executable, "-I", "-B", os.path.join(HOOKS, self.H)], input=json.dumps(data),
                           capture_output=True, text=True, env=self.env, encoding="utf-8")
        self.assertEqual((p.returncode, p.stdout), (0, ""), p.stderr)

    def test_records_a_hash_and_time_never_the_text(self):
        for n in range(55):
            self.prompt(f"approve number {n}")
        with open(self.path(self.LOG), encoding="utf-8") as f:
            lines = f.read().splitlines()
        self.assertEqual(len(lines), 50)
        self.assertEqual(sorted(json.loads(lines[-1])), ["at", "sha256"])
        self.assertNotIn("approve", "".join(lines))

    def test_silent_and_writes_nothing_without_project_settings(self):
        other = os.path.join(self.tmp.name, "plain")
        write(os.path.join(other, "AGENTS.md"), "# plain\n")
        self.prompt("yes", cwd=other)
        self.assertFalse(os.path.exists(os.path.join(other, "AGENTS/settings")))

    def test_safe_target_denies_writing_the_log(self):
        self.prompt("yes")
        log = self.path(self.LOG)
        self.assertEqual(self.hook("dev_safe_target.py", "Write", file_path=log, content="{}")[0], "deny")
        self.assertEqual(self.hook("dev_safe_target.py", "Edit", file_path=log, old_string="a", new_string="b")[0], "deny")
        self.assertEqual(self.hook("dev_safe_target.py", "Bash", command=f"echo x >> {self.LOG}")[0], "deny")
        self.assertEqual(self.hook("dev_safe_target.py", "PowerShell", command="Add-Content AGENTS/settings/dev/replies.jsonl x")[0], "deny")

    def test_control_other_dev_files_are_not_denied_by_this_rule(self):
        self.assertIsNone(self.hook("dev_safe_target.py", "Write", file_path=self.path("AGENTS/settings/dev/install.md"), content="x")[0])


if __name__ == "__main__":
    unittest.main()
