"""Regression tests for dev-deploy's deploy.py. Run: py -3 -I -B test_deploy.py

Builds synthetic workspaces in a temporary folder and serves a tiny local HTTP endpoint for the
check command; runs no deploy tool and touches nothing outside the temporary folder.
"""

import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DEPLOY = os.path.join(HERE, "..", "scripts", "deploy.py")
EXAMPLE = os.path.join(HERE, "..", "assets", "target-example.json")


def run(*args):
    r = subprocess.run([sys.executable, "-I", "-B", DEPLOY, *args], capture_output=True, text=True, encoding="utf-8")
    return r.returncode, json.loads(r.stdout)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


class Health(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        code, body = (200, b"ok") if self.path == "/health" else (503, b"down")
        self.send_response(code)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


class DeployTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = os.path.join(self.tmp.name, "ws")
        write(os.path.join(self.ws, "AGENTS.md"), "# ws\n")
        with open(EXAMPLE, encoding="utf-8") as f:
            self.entry = json.load(f)

    def tearDown(self):
        self.tmp.cleanup()

    def entry_file(self, entry):
        p = os.path.join(self.tmp.name, "entry.json")
        write(p, json.dumps(entry))
        return p

    def add_target(self):
        return run("target", "write", "--workspace", self.ws, "--file", self.entry_file(self.entry), "--write")

    def test_discover_lists_deploy_files_and_skips_noise(self):
        write(os.path.join(self.ws, "Dockerfile"), "FROM scratch\n")
        write(os.path.join(self.ws, "deploy", "k8s", "app.yaml"), "apiVersion: apps/v1\nkind: Deployment\n---\napiVersion: v1\nkind: Service\n")
        write(os.path.join(self.ws, "config", "settings.yaml"), "logging: info\n")
        write(os.path.join(self.ws, "node_modules", "x", "Dockerfile"), "FROM scratch\n")
        write(os.path.join(self.ws, "infra", "main.tf"), "terraform {}\n")
        write(os.path.join(self.ws, ".github", "workflows", "ci.yml"), "on: push\n")
        write(os.path.join(self.ws, "scripts", "deploy.sh"), "echo\n")
        code, res = run("discover", "--workspace", self.ws)
        self.assertEqual(code, 0, res)
        f = res["found"]
        self.assertEqual(f["containers"], ["Dockerfile"])
        self.assertEqual(f["kubernetes"], [{"file": "deploy/k8s/app.yaml", "kinds": ["Deployment", "Service"]}])
        self.assertEqual(f["terraform"], ["infra"])
        self.assertEqual(f["ci"][0]["system"], "GitHub Actions")
        self.assertIn("scripts/deploy.sh", f["scripts"])

    def test_target_preview_then_write_and_show(self):
        code, res = run("target", "write", "--workspace", self.ws, "--file", self.entry_file(self.entry))
        self.assertEqual((code, res["written"]), (0, False))
        self.assertFalse(os.path.exists(os.path.join(self.ws, "AGENTS", "settings", "deploy", "targets.json")))
        self.assertTrue(self.add_target()[1]["written"])
        self.assertEqual(run("target", "show", "--workspace", self.ws, "--name", "local-k8s")[1]["target"]["name"], "local-k8s")
        self.assertIsNone(run("target", "show", "--workspace", self.ws, "--name", "prod")[1]["target"])

    # F1 fix batch 6: a target entry comes from a file, so its hosts never sit in the command's text.
    def test_target_write_keeps_hosts_out_of_the_command(self):
        entry = dict(self.entry, notes="reaches orders-prod.shop.invalid only through the cluster")
        args = ("target", "write", "--workspace", self.ws, "--file", self.entry_file(entry))
        self.assertFalse(any("orders-prod" in a for a in args))
        code, res = run(*args)
        self.assertEqual(code, 0, res)
        self.assertIn("orders-prod.shop.invalid", json.dumps(res["preview"]))

    def test_target_validation(self):
        bad = dict(self.entry)
        bad.pop("production")
        bad["steps"] = [{"id": "apply", "command": "kubectl apply -f x"}]
        bad["checks"] = []
        bad["notes"] = "password: hunter2"
        res = run("target", "write", "--workspace", self.ws, "--file", self.entry_file(bad))[1]
        joined = " ".join(res["problems"])
        for part in ("production must be", "needs a rollback", "at least one check", "holds a secret"):
            self.assertIn(part, joined)

    def test_gate_outside_and_inside_dev_process(self):
        self.add_target()
        subprocess.run(["git", "init", "-q", self.ws], check=True)
        subprocess.run(["git", "-C", self.ws, "add", "-A"], check=True)
        subprocess.run(["git", "-C", self.ws, "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                        "commit", "-q", "-m", "x"], check=True)
        res = run("gate", "--workspace", self.ws, "--target", "local-k8s")[1]
        self.assertTrue(res["ok"], res)
        self.assertEqual(res["checks_skipped"][0]["reason"], "no --change: a deploy outside the dev process")
        write(os.path.join(self.ws, "src.cs"), "x\n")
        self.assertIn("uncommitted", " ".join(run("gate", "--workspace", self.ws, "--target", "local-k8s")[1]["problems"]))
        os.remove(os.path.join(self.ws, "src.cs"))
        change = os.path.join(self.ws, "dev-plans", "c1")
        write(os.path.join(change, "state.json"), json.dumps({"id": "c1", "stage": "human-review", "approvals": [],
                                                               "test_runs": [{"result": "red"}]}))
        res = run("gate", "--workspace", self.ws, "--target", "local-k8s", "--change", change)[1]
        joined = " ".join(res["problems"])
        for part in ("not deploy", "no accepted human review", "not green"):
            self.assertIn(part, joined)

    def test_gate_without_change_ignores_an_untracked_change_folder(self):
        self.add_target()
        subprocess.run(["git", "init", "-q", self.ws], check=True)
        subprocess.run(["git", "-C", self.ws, "add", "-A"], check=True)
        subprocess.run(["git", "-C", self.ws, "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                        "commit", "-q", "-m", "x"], check=True)
        write(os.path.join(self.ws, "dev-plans", "c1", "state.json"), json.dumps({"id": "c1", "stage": "plan"}))
        write(os.path.join(self.ws, "AGENTS", "plans", "c2", "plan.md"), "# plan" + chr(10))
        res = run("gate", "--workspace", self.ws, "--target", "local-k8s")[1]
        self.assertTrue(res["ok"], res)
        write(os.path.join(self.ws, "tests", "Repro_Discount.cs"), "x" + chr(10))
        self.assertIn("uncommitted", " ".join(run("gate", "--workspace", self.ws, "--target", "local-k8s")[1]["problems"]))

    def gate_after(self, runs, later=()):
        """runs: (minute, result). Stage test is entered at minute 10 and review at 20; later: (minute, stage)."""
        self.add_target()
        change = os.path.join(self.ws, "dev-plans", "c1")
        at = "2026-11-22T14:{:02d}:00+01:00".format
        odd = {"bad": "yesterday", "naive": "2026-11-22T08:00:00"}
        moves = [(0, "plan"), (5, "build"), (10, "test"), (20, "review"), *later, (58, "deploy")]
        state = {"id": "c1", "stage": "deploy", "approvals": [{"what": "human review, round 1"}],
                 "history": [{"at": at(minute), "stage": stage} for minute, stage in moves],
                 "test_runs": [{"n": n, "route": route[0] if route else "run", "result": result,
                                "at": odd.get(minute) or at(minute)}
                               for n, (minute, result, *route) in enumerate(runs, 1)]}
        write(os.path.join(change, "state.json"), json.dumps(state))
        problems = run("gate", "--workspace", self.ws, "--target", "local-k8s", "--change", change)[1]["problems"]
        return [p for p in problems if "test" in p and "uncommitted" not in p]

    def test_gate_takes_the_run_that_started_at_stage_test(self):
        self.assertEqual(self.gate_after([(20, "green")]), [])

    def test_gate_a_resolved_red_after_the_full_run_passes(self):
        self.assertEqual(self.gate_after([(20, "green"), (25, "red"), (26, "green")]), [])

    def test_gate_a_narrow_green_does_not_cover_a_red_full_run(self):
        self.assertTrue(self.gate_after([(20, "red"), (26, "green")]))

    def test_gate_a_narrow_green_is_not_the_full_run(self):
        self.assertTrue(self.gate_after([(8, "green"), (26, "green")]))

    def test_gate_an_unresolved_red_after_the_full_run_stops_it(self):
        self.assertTrue(self.gate_after([(20, "green"), (25, "red")]))

    def test_gate_work_after_the_full_run_needs_a_new_one(self):
        self.assertTrue(self.gate_after([(20, "green"), (45, "green")], [(30, "build"), (46, "review")]))

    def test_gate_a_second_round_with_its_own_run_passes(self):
        self.assertEqual(self.gate_after([(20, "green"), (50, "green")], [(30, "build"), (40, "test"), (50, "review")]), [])

    def test_gate_a_red_check_is_not_the_full_run(self):
        self.assertTrue(self.gate_after([(15, "green", "red-check"), (26, "green")]))

    def test_gate_skips_an_older_run_it_cannot_place(self):
        self.assertEqual(self.gate_after([("bad", "red"), (20, "green")]), [])

    def test_gate_reads_a_time_without_a_zone_as_local(self):
        self.assertEqual(self.gate_after([("naive", "green"), (20, "green")]), [])

    def test_gate_lists_the_stage_test_check(self):
        self.gate_after([(20, "green")])
        change = os.path.join(self.ws, "dev-plans", "c1")
        done = run("gate", "--workspace", self.ws, "--target", "local-k8s", "--change", change)[1]["checks_run"]
        self.assertTrue(any("started at stage test" in check for check in done), done)

    def test_approve_records_exact_command_with_expiry(self):
        self.add_target()
        code, res = run("approve", "--workspace", self.ws, "--target", "local-k8s", "--step", "apply",
                        "--command", "  kubectl apply -f deploy/k8s/  ", "--minutes", "10", "--now", "2026-11-21T10:00:00+01:00")
        self.assertEqual(code, 0, res)
        a = res["approval"]
        self.assertEqual((a["id"], a["command"], a["used"]), ("A1", "kubectl apply -f deploy/k8s/", False))
        self.assertEqual(a["expires"], "2026-11-21T10:10:00+01:00")
        self.assertEqual(run("approve", "--workspace", self.ws, "--target", "local-k8s", "--step", "nope",
                             "--command", "x")[0], 1)
        self.assertEqual(run("approve", "--workspace", self.ws, "--target", "local-k8s", "--step", "rollback-apply",
                             "--command", "kubectl rollout undo deployment/shop-api")[1]["approval"]["id"], "A2")

    # No-hook batch: deploy.py itself makes each approval single-use, so it holds where the hook does not run.
    def test_use_claims_an_approval_once(self):
        self.add_target()
        t = "2026-11-21T10:00:00+01:00"
        run("approve", "--workspace", self.ws, "--target", "local-k8s", "--step", "apply",
            "--command", "kubectl apply -f deploy/k8s/", "--minutes", "10", "--now", t)
        use = lambda *a: run("use", "--workspace", self.ws, *a)
        self.assertEqual(use("--id", "A9", "--command", "kubectl apply -f deploy/k8s/", "--now", t)[0], 1)
        code, res = use("--id", "A1", "--command", "kubectl apply -f deploy/k8s/ --force", "--now", t)
        self.assertEqual(code, 1, res)
        self.assertEqual(use("--id", "A1", "--command", "kubectl apply -f deploy/k8s/",
                             "--now", "2026-11-21T10:11:00+01:00")[0], 1)
        code, res = use("--id", "A1", "--command", "  kubectl apply -f deploy/k8s/ ", "--now", "2026-11-21T10:05:00+01:00")
        self.assertEqual(code, 0, res)
        self.assertEqual(res["approval"]["claimed"], "2026-11-21T10:05:00+01:00")
        self.assertIs(res["approval"]["used"], False)  # the hook, where it runs, still passes the command once
        code, res = use("--id", "A1", "--command", "kubectl apply -f deploy/k8s/", "--now", "2026-11-21T10:06:00+01:00")
        self.assertEqual(code, 1, res)
        self.assertIn("already used", res["error"])

    def test_use_refuses_an_approval_the_hook_used(self):
        self.add_target()
        t = "2026-11-21T10:00:00+01:00"
        run("approve", "--workspace", self.ws, "--target", "local-k8s", "--step", "apply",
            "--command", "kubectl apply -f deploy/k8s/", "--now", t)
        path = os.path.join(self.ws, "AGENTS", "settings", "deploy", "approvals.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        data["approvals"][0]["used"] = "2026-11-21T10:01:00+01:00"
        write(path, json.dumps(data))
        self.assertEqual(run("use", "--workspace", self.ws, "--id", "A1", "--command", "kubectl apply -f deploy/k8s/",
                             "--now", t)[0], 1)

    def test_gate_lists_unverified_approvals_as_skipped(self):
        self.gate_after([(20, "green")])
        change = os.path.join(self.ws, "dev-plans", "c1")
        sp = os.path.join(change, "state.json")
        with open(sp, encoding="utf-8") as f:
            state = json.load(f)
        state["approvals"] = [{"what": "human review, round 1", "by": "user", "unverified": True},
                              {"what": "plan", "by": "user"}]
        write(sp, json.dumps(state))
        skipped = run("gate", "--workspace", self.ws, "--target", "local-k8s", "--change", change)[1]["checks_skipped"]
        hits = [s for s in skipped if "unverified" in s["reason"]]
        self.assertEqual(len(hits), 1, skipped)
        self.assertIn("human review, round 1", hits[0]["check"])

    def test_check_passes_and_fails(self):
        srv = http.server.HTTPServer(("127.0.0.1", 0), Health)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        port = srv.server_address[1]
        try:
            ok = run("check", "--url", f"http://127.0.0.1:{port}/health", "--contains", "ok", "--retries", "1")[1]
            self.assertTrue(ok["ok"], ok)
            bad = run("check", "--url", f"http://127.0.0.1:{port}/other", "--retries", "2", "--wait", "0.1")[1]
            self.assertFalse(bad["ok"])
            self.assertEqual([t["status"] for t in bad["tries"]], [503, 503])
        finally:
            srv.shutdown()

    def test_log_and_self_edit_rows(self):
        code, res = run("log", "--workspace", self.ws, "--target", "local-k8s", "--steps", "build, apply",
                        "--outcome", "failed at apply: ErrImagePull", "--checks", "not run", "--rollback", "used",
                        "--approved", "you, A1", "--now", "2026-11-21T10:00:00+01:00")
        self.assertEqual(code, 0, res)
        run("log", "--workspace", self.ws, "--target", "local-k8s", "--steps", "build, apply", "--outcome", "succeeded",
            "--checks", "passed", "--rollback", "not needed", "--approved", "you, A2", "--now", "2026-11-21T11:00:00+01:00")
        code, res = run("self-edit", "--workspace", self.ws, "--trigger", "execution error",
                        "--quote", "targets.json step apply", "--change-text", "image tag from the build, level 1",
                        "--route", "target entry", "--status", "proposed")
        self.assertEqual(code, 0, res)
        with open(os.path.join(self.ws, "AGENTS", "settings", "deploy", "log.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertLess(text.index("2026-11-21 11:00"), text.index("2026-11-21 10:00"))  # newest first
        self.assertNotIn("{", text)
        self.assertIn("image tag from the build", text)
        self.assertEqual(run("self-edit", "--workspace", self.ws, "--trigger", "x", "--quote", "x",
                             "--change-text", "x", "--route", "x", "--status", "maybe")[0], 1)


    def test_discover_finds_ci_of_a_repository_in_a_subfolder(self):
        write(os.path.join(self.ws, "shop", ".github", "workflows", "ci.yml"), "on: push\n")
        write(os.path.join(self.ws, ".github", "workflows", "root.yml"), "on: push\n")
        write(os.path.join(self.ws, "shop", "docs", "github", "workflows", "notes.yml"), "x: 1\n")
        code, res = run("discover", "--workspace", self.ws)
        self.assertEqual(code, 0, res)
        ci = [c["file"] for c in res["found"]["ci"]]
        self.assertIn("shop/.github/workflows/ci.yml", ci)
        self.assertIn(".github/workflows/root.yml", ci)
        self.assertNotIn("shop/docs/github/workflows/notes.yml", ci)


if __name__ == "__main__":
    unittest.main(verbosity=1)
