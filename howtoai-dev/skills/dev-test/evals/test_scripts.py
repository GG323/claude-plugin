"""Tests for dev-test's scripts. Run: py -3 -I <this file>.

Each test builds its own workspace in a temporary folder and passes --user-file, so no real
settings are read. ephemeral.py is tested in --dry-run only.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")


def run(script, *args):
    p = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, script), *args],
                       capture_output=True, text=True, encoding="utf-8")
    try:
        return p.returncode, json.loads(p.stdout)
    except ValueError:
        raise AssertionError(f"{script} printed no JSON: {p.stdout!r} {p.stderr!r}")


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


SETTINGS = {"environments": {"allow": [{"name": "local db", "kind": "local", "match": {"host": "localhost"}}],
                             "deny": ["shop-prod.postgres.database.azure.com"]}}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="devtest-")
        self.ws = os.path.join(self.tmp.name, "ws")
        write(os.path.join(self.ws, "AGENTS.md"), "# ws\n")
        write(os.path.join(self.ws, ".howtoai", "dev", "settings.json"), json.dumps(SETTINGS))
        self.user = os.path.join(self.tmp.name, "user.json")

    def tearDown(self):
        self.tmp.cleanup()

    def classify(self, environ="{}", *extra):
        return run("targets.py", "classify", "--workspace", self.ws, "--user-file", self.user, "--environ", environ, *extra)


class TargetsTests(Base):
    def test_clean_repo_is_ok(self):
        write(os.path.join(self.ws, "src/Api/appsettings.json"),
              json.dumps({"ConnectionStrings": {"Shop": "Host=localhost;Port=5432;Database=shop;Username=app;Password=pw"}}))
        write(os.path.join(self.ws, "src/Api/appsettings.Production.json"),
              json.dumps({"ConnectionStrings": {"Shop": "Host=shop-prod.postgres.database.azure.com;Database=shop"}}))
        write(os.path.join(self.ws, ".env"), "DATABASE_URL=postgres://u:p@shop-prod.postgres.database.azure.com/shop\n")
        code, res = self.classify()
        self.assertEqual((code, res["verdict"]), (0, "ok"), res)
        by_scope = {t["scope"]: t for t in res["targets"]}
        self.assertEqual(by_scope["base"]["class"], "local")
        self.assertEqual((by_scope["other-env"]["class"], by_scope["other-env"]["used"]), ("production", False))
        self.assertNotIn(".env", [f["file"] for f in res["files"]])
        self.assertEqual(res["skipped"], [{"file": ".env", "reason": "secret store, never read"}])
        self.assertNotIn("pw", json.dumps(res))

    def test_production_in_base_is_refused(self):
        write(os.path.join(self.ws, "src/Api/appsettings.json"),
              json.dumps({"ConnectionStrings": {"Shop": "Host=shop-prod.postgres.database.azure.com;Database=shop;Password=x1"}}))
        code, res = self.classify()
        self.assertEqual(res["verdict"], "refused")
        self.assertIn("deny marker", res["reasons"][0])

    def test_test_override_makes_base_unused(self):
        write(os.path.join(self.ws, "src/Api/appsettings.json"),
              json.dumps({"ConnectionStrings": {"Shop": "Host=shop-prod.postgres.database.azure.com;Database=shop"}}))
        write(os.path.join(self.ws, "src/Api/appsettings.Test.json"),
              json.dumps({"ConnectionStrings": {"Shop": "Data Source=:memory:"}}))
        _, res = self.classify()
        self.assertEqual(res["verdict"], "ok", res)
        self.assertEqual({t["scope"]: t["class"] for t in res["targets"]}, {"base": "production", "test": "local"})

    def test_unknown_asks_and_loopback_hint(self):
        write(os.path.join(self.ws, "src/Api/appsettings.json"),
              json.dumps({"Payments": {"BaseUrl": "https://api.payments.example.com/v1"},
                          "Cache": "redis://127.0.0.1:6379", "$schema": "https://json.schemastore.org/appsettings.json"}))
        _, res = self.classify()
        self.assertEqual(res["verdict"], "ask")
        self.assertEqual(len(res["targets"]), 2)
        loop = [t for t in res["targets"] if t.get("host") == "127.0.0.1"][0]
        self.assertIn("loopback", loop["why"])

    def test_production_marker_in_env_test_and_environ(self):
        write(os.path.join(self.ws, ".env.test"), "ASPNETCORE_ENVIRONMENT=Production\n")
        _, res = self.classify()
        self.assertEqual(res["verdict"], "refused")
        os.remove(os.path.join(self.ws, ".env.test"))
        _, res = self.classify('{"APP_ENV": "production"}')
        self.assertEqual(res["verdict"], "refused")
        _, res = self.classify('{"DATABASE_URL": "postgres://u:secretpw@db.internal.example/shop"}')
        self.assertEqual(res["verdict"], "ask")
        self.assertNotIn("secretpw", json.dumps(res))

    def test_ephemeral_and_allow_database(self):
        write(os.path.join(self.ws, ".env.test"), "DATABASE_URL=postgres://127.0.0.1:55001/shop_test\n")
        _, res = self.classify("{}", "--ephemeral", "127.0.0.1:55001")
        self.assertEqual(res["targets"][0]["class"], "ephemeral")
        self.assertEqual(res["verdict"], "ok")

    def test_broken_json_in_base_asks(self):
        write(os.path.join(self.ws, "src/Api/appsettings.json"), '{"ConnectionStrings": {')
        _, res = self.classify()
        self.assertEqual((res["verdict"], res["skipped"][0]["file"]), ("ask", "src/Api/appsettings.json"))

    def test_bad_settings_fail(self):
        write(os.path.join(self.ws, ".howtoai", "dev", "settings.json"), '{"environments": {"allow": "x"}}')
        code, res = self.classify()
        self.assertEqual(code, 1)


TRX = """<?xml version="1.0" encoding="utf-8"?>
<TestRun xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010"><Results>
<UnitTestResult testName="A.Passes" outcome="Passed" duration="00:00:00.5000000"/>
<UnitTestResult testName="A.Fails" outcome="Failed" duration="00:00:01.0000000"><Output><ErrorInfo><Message>Assert.AreEqual failed. Expected:&lt;3&gt;. password=hunter2
second line</Message></ErrorInfo></Output></UnitTestResult>
<UnitTestResult testName="A.Skipped" outcome="NotExecuted"/>
</Results></TestRun>"""
TRX_RERUN = """<?xml version="1.0"?><TestRun xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010"><Results>
<UnitTestResult testName="A.Fails" outcome="Passed" duration="00:00:01"/></Results></TestRun>"""
JUNIT = """<testsuites><testsuite name="s"><testcase classname="m" name="ok" time="0.1"/>
<testcase classname="m" name="bad" time="0.2"><failure message="boom">trace</failure></testcase></testsuite></testsuites>"""


class ResultsTests(Base):
    def test_parse_trx_and_junit(self):
        write(os.path.join(self.ws, "r/a.trx"), TRX)
        write(os.path.join(self.ws, "r/j.xml"), JUNIT)
        _, res = run("results.py", "parse", os.path.join(self.ws, "r", "a.trx"))
        self.assertEqual((res["passed"], res["failed"], res["skipped"], res["duration_s"]), (1, 1, 1, 1.5))
        self.assertEqual(res["failed_tests"][0]["message"], "Assert.AreEqual failed. Expected:<3>. [redacted]")
        _, res = run("results.py", "parse", os.path.join(self.ws, "r", "*.xml"))
        self.assertEqual((res["failed"], res["failed_tests"][0]["name"]), (1, "m.bad"))

    def test_merge_marks_flaky(self):
        write(os.path.join(self.ws, "r/a.trx"), TRX)
        write(os.path.join(self.ws, "r/b.trx"), TRX_RERUN)
        _, res = run("results.py", "merge", "--first", os.path.join(self.ws, "r", "a.trx"),
                     "--rerun", os.path.join(self.ws, "r", "b.trx"))
        self.assertEqual((res["failed"], res["flaky"], res["flaky_tests"][0]), (0, 1, {"name": "A.Fails", "reruns": 1}))

    def test_bad_file(self):
        write(os.path.join(self.ws, "r/x.xml"), "<html/>")
        code, res = run("results.py", "parse", os.path.join(self.ws, "r", "x.xml"))
        self.assertEqual(code, 1)


class TestingMdTests(Base):
    def data(self, **kw):
        d = {"run": "2026-11-19T10:00:00+01:00", "commit": "abc1234", "environment": ["local db: local"],
             "results": "4 passed, 0 failed", **kw}
        p = os.path.join(self.tmp.name, "data.json")
        write(p, json.dumps(d))
        return p

    def test_missing_needs_create_then_keeps_base(self):
        tdir = os.path.join(self.ws, "tests", "Api.Tests")
        write(os.path.join(tdir, "AuthTests.cs"), "class A {}")
        code, res = run("testing_md.py", "update", tdir, "--data", self.data())
        self.assertEqual(code, 1)
        code, res = run("testing_md.py", "update", tdir, "--data", self.data(), "--create")
        self.assertTrue(res["created"])
        self.assertTrue(res["base_placeholders"])
        path = os.path.join(tdir, "TESTING.md")
        with open(path, encoding="utf-8") as f:
            text = f.read().replace("{Each fixture and what it means.}", "Seeded users: alice, bob.")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        run("testing_md.py", "update", tdir, "--data",
            self.data(results="5 passed", data="conn Password=topsecret; postgres://u:pw@h/db"))
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("# Testing: Api.Tests", text)
        self.assertIn("Seeded users: alice, bob.", text)
        self.assertIn("**Results:** 5 passed", text)
        self.assertIn("**Flaky tests:** none", text)
        self.assertNotIn("topsecret", text)
        self.assertNotIn("u:pw@", text)
        self.assertEqual(text.count("<!-- generated:start -->"), 1)

    def test_check_missing_stale_fresh(self):
        tdir = os.path.join(self.ws, "tests", "Api.Tests")
        write(os.path.join(tdir, "AuthTests.cs"), "class A {}")
        write(os.path.join(self.ws, "tests", "Web.Tests", "UiTests.cs"), "class B {}")
        run("testing_md.py", "update", tdir, "--data", self.data(run="2000-01-01T00:00:00+00:00"), "--create")
        code, res = run("testing_md.py", "check", "--workspace", self.ws, "--user-file", self.user)
        self.assertEqual(res["missing"], ["tests/Web.Tests"])
        self.assertEqual(res["stale"][0]["dir"], "tests/Api.Tests")
        run("testing_md.py", "update", tdir, "--data", self.data(run="2999-01-01T00:00:00+00:00"))
        _, res = run("testing_md.py", "check", "--workspace", self.ws, "--user-file", self.user, "--dirs", "tests/Api.Tests")
        self.assertEqual((res["fresh"], res["passed"]), (["tests/Api.Tests"], True))

    def test_unknown_key_refused(self):
        tdir = os.path.join(self.ws, "tests")
        os.makedirs(tdir)
        p = os.path.join(self.tmp.name, "bad.json")
        write(p, '{"rsults": "x"}')
        code, _ = run("testing_md.py", "update", tdir, "--data", p, "--create")
        self.assertEqual(code, 1)
        write(p, '{"run": "2026-11-19-bulk-discount-2"}')
        code, res = run("testing_md.py", "update", tdir, "--data", p, "--create")
        self.assertEqual(code, 1)
        self.assertIn("ISO date and time", res["error"])


class EphemeralTests(unittest.TestCase):
    def test_dry_run_commands(self):
        code, res = run("ephemeral.py", "up", "--run-id", "2026-11-19-x-1", "--name", "pg", "--image", "postgres:17-alpine",
                        "--port", "5432", "--env", "POSTGRES_HOST_AUTH_METHOD=trust", "--dry-run")
        self.assertEqual(code, 0, res)
        self.assertIn("--label howtoai.dev.run=2026-11-19-x-1", res["commands"][0])
        self.assertIn("-p 127.0.0.1::5432", res["commands"][0])
        _, res = run("ephemeral.py", "down", "--run-id", "2026-11-19-x-1", "--dry-run")
        self.assertIn("label=howtoai.dev.run=2026-11-19-x-1", res["commands"][0])
        _, res = run("ephemeral.py", "sweep", "--dry-run")
        self.assertIn("label=howtoai.dev=1", res["commands"][0])

    @unittest.skipIf(__import__("shutil").which("docker"), "Docker is installed")
    def test_down_and_sweep_without_docker(self):
        code, res = run("ephemeral.py", "down", "--run-id", "r1")
        self.assertEqual((code, res["docker_missing"], res["removed"]), (0, True, []))
        code, res = run("ephemeral.py", "sweep")
        self.assertEqual((code, res["docker_missing"]), (0, True))
        code, _ = run("ephemeral.py", "up", "--run-id", "r1", "--name", "pg", "--image", "postgres:17", "--port", "5432")
        self.assertEqual(code, 1)

    def test_refuses_latest_and_secrets(self):
        for args in (["--image", "postgres"], ["--image", "postgres:latest"],
                     ["--image", "postgres:17", "--env", "POSTGRES_PASSWORD=hunter2"]):
            code, _ = run("ephemeral.py", "up", "--run-id", "r1", "--name", "pg", "--port", "5432", *args, "--dry-run")
            self.assertEqual(code, 1, args)


if __name__ == "__main__":
    unittest.main()
