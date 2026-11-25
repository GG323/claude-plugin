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
        write(os.path.join(self.ws, "AGENTS", "howtoai", "dev", "settings.json"), json.dumps(SETTINGS))
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
        write(os.path.join(self.ws, "AGENTS", "howtoai", "dev", "settings.json"), '{"environments": {"allow": "x"}}')
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


class HostValueTests(Base):
    PROD = "shop-prod.postgres.database.azure.com"
    API = "src/Api/appsettings.json"

    def classify_file(self, rel, text, environ="{}"):
        path = os.path.join(self.ws, *rel.split("/"))
        write(path, text)
        try:
            return self.classify_with(environ)
        finally:
            os.remove(path)

    def classify_with(self, environ="{}"):
        return run("targets.py", "classify", "--workspace", self.ws, "--user-file", self.user, "--environ", environ)[1]

    def test_deny_marker_is_production_whatever_the_key(self):
        p = self.PROD
        cases = [(self.API, json.dumps(doc)) for doc in (
            {"Smtp": {"Host": p}}, {"Smtp": {"Host": p.upper()}}, {"Smtp": {"Server": p}}, {"Queue": {"HostName": p}},
            {"Redis": {"Endpoint": p + ":6380"}}, {"Orders": {"DbHost": p}}, {"Kafka": {"Servers": ["localhost", p]}},
            {"Banner": p}, {"Jdbc": "jdbc:postgresql://" + p + "/shop"}, {"Logging": {"Seq": "https://" + p}})]
        cases += [
            ("tests/Api.Tests/appsettings.Test.json", json.dumps({"Smtp": {"Host": p}})),
            (".env.test", "SMTP_HOST=" + p + "\n"),
            (".env.testing", "export DB_HOST=\"" + p + "\"\n"),
            ("compose.yaml", "services:\n  web:\n    environment:\n      SMTP_HOST: " + p + "\n"),
            ("docker-compose.test.yml", "services:\n  web:\n    environment:\n      - DB_HOST=" + p + "\n"),
            ("compose.yml", "services:\n  web:\n    environment: {DB_HOST: " + p + "}\n"),
            ("compose.yml", "services:\n  web:\n    command:\n      - " + p + "\n"),
            ("tests/a.runsettings", "<RunSettings><DbHost>" + p + "</DbHost></RunSettings>\n"),
            ("tests/b.runsettings", "<RunSettings>\n<Parameter name=\"DbHost\" value=\"" + p + "\" />\n</RunSettings>\n"),
            ("appsettings.json", json.dumps({"Smtp": {"Host": p}})),
            ("rēķini/jūra/src/appsettings.json", json.dumps({"Smtp": {"Host": p}})),
            ("my repos/shop/.env.test", "DB_HOST=" + p + "\n"),
            (self.API, "{ // a comment makes this invalid JSON\n \"Host\": \"" + p + "\"}\n"),
            ("src/Api/Properties/launchSettings.json",
             json.dumps({"profiles": {"Api": {"environmentVariables": {"SMTP_HOST": p}}}})),
        ]
        os.makedirs(os.path.join(self.ws, "my repos", "shop", ".git"))  # a nested repository
        for rel, text in cases:
            with self.subTest(file=rel, text=text):
                res = self.classify_file(rel, text)
                self.assertEqual(res["verdict"], "refused", res)

    def test_deny_marker_in_the_environment_is_production(self):
        res = self.classify_with(json.dumps({"Smtp__Host": self.PROD}))
        self.assertEqual(res["verdict"], "refused", res)

    def test_unlisted_host_in_a_host_key_asks(self):
        for rel, text in (
            (self.API, json.dumps({"Smtp": {"Host": "mail.example.test", "Port": 25}})),
            (self.API, json.dumps({"Kafka": {"BootstrapServers": "localhost:9092,broker.example.test:9092"}})),
            (self.API, json.dumps({"Kafka": {"Servers": ["localhost", "broker.example.test"]}})),
            (self.API, json.dumps({"Redis": {"Endpoint": "grpc://cache.example.test:50051"}})),
            (".env.test", "SMTP_HOST=mail.example.test # the team's relay\n"),
            ("compose.yaml", "services:\n  web:\n    environment:\n      DB_HOST: db\n"),
            ("tests/a.runsettings", "<RunSettings><DbHost>db.example.test</DbHost></RunSettings>\n"),
        ):
            with self.subTest(file=rel, text=text):
                res = self.classify_file(rel, text)
                self.assertEqual(res["verdict"], "ask", res)

    def test_allowed_and_non_target_values_stay_ok(self):
        for rel, text in (
            (self.API, json.dumps({"Smtp": {"Host": "localhost", "Port": 1025}})),
            (self.API, json.dumps({"AllowedHosts": "*"})),
            (self.API, json.dumps({"AllowedHosts": "example.com"})),
            (self.API, json.dumps({"Features": {"UseSqlServer": "true"}, "Health": {"Endpoint": "/health"}})),
            (self.API, json.dumps({"Mail": {"FromAddress": "shop@example.test"}, "Kestrel": {"Host": "0.0.0.0"}})),
            (".env.test", "# DB_HOST=" + self.PROD + "\nDB_HOST=\n"),
            ("compose.yaml", "services:\n  db:\n    hostname: db\n    environment:\n"
                             "      POSTGRES_HOST_AUTH_METHOD: trust\n"),
            ("src/Api/appsettings.Production.json", json.dumps({"Smtp": {"Host": self.PROD}})),
            (".env.example", "SMTP_HOST=" + self.PROD + "\n"),
        ):
            with self.subTest(file=rel, text=text):
                res = self.classify_file(rel, text)
                self.assertEqual(res["verdict"], "ok", res)

    def test_the_machines_own_host_name_is_no_target(self):
        self.assertEqual(self.classify_with(json.dumps({"HOSTNAME": "devbox", "HOST": "devbox"}))["verdict"], "ok")

    def test_test_file_override_still_wins(self):
        write(os.path.join(self.ws, "src", "appsettings.json"), json.dumps({"Smtp": {"Host": self.PROD}}))
        write(os.path.join(self.ws, "src", "appsettings.Test.json"), json.dumps({"Smtp": {"Host": "localhost"}}))
        self.assertEqual(self.classify_with()["verdict"], "ok")

    def test_secret_part_of_a_denied_value_is_never_printed(self):
        res = self.classify_file(".env.test", "SMTP_RELAY=" + self.PROD + ";token=hunter2\n")
        self.assertEqual(res["verdict"], "refused", res)
        self.assertNotIn("hunter2", json.dumps(res))


class AddOnlyTests(Base):
    PROD = "shop-prod.postgres.database.azure.com"

    def classify_files(self, files, environ="{}"):
        paths = []
        for rel, text in files.items():
            paths.append(os.path.join(self.ws, *rel.split("/")))
            write(paths[-1], text)
        try:
            return run("targets.py", "classify", "--workspace", self.ws, "--user-file", self.user,
                       "--environ", environ)[1]
        finally:
            for path in paths:
                os.remove(path)

    def expect(self, verdict, cases):
        for files in cases:
            with self.subTest(files=files):
                res = self.classify_files(files)
                self.assertEqual(res["verdict"], verdict, res)

    def test_a_new_target_never_switches_off_one_found_before(self):
        p = self.PROD
        self.expect("refused", (
            {"appsettings.json": json.dumps({"ApiUrl": "https://" + p}),
             "t.runsettings": '<RunSettings><Parameter name="ApiUrl" value="http://localhost:5000" /></RunSettings>'},
            {"compose.yml": "DATABASE_URL: postgres://" + p + "/s\n",
             ".env.test": "export DATABASE_URL=postgres://localhost/s\n"},
            {"compose.yml": "HOST: https://" + p + "\n", "compose.test.yml": "HOST: localhost\n"},
            {"appsettings.json": json.dumps({"Host": "https://" + p}),
             "appsettings.Test.json": json.dumps({"Host": "localhost"})},
            {"compose.yml": "x:\n  LOG: info\n  ASPNETCORE_ENVIRONMENT:\n    Production\n"},
            {".env.test": "APP_ENV\u00a0=production\n"},
        ))

    def test_an_allowed_value_never_hides_a_denied_one(self):
        p = self.PROD
        self.expect("refused", (
            {".env.test": "PAYMENTS=" + p + "?fallback=localhost\nREDIS_HOST=localhost\n"},
            {"t.runsettings": "<RunSettings><Host>localhost</Host><Other>" + p + "</Other></RunSettings>"},
        ))

    def test_denied_json_number_is_production(self):
        write(os.path.join(self.ws, "AGENTS", "howtoai", "dev", "settings.json"),
              json.dumps({"environments": {"allow": [], "deny": ["123456789012"]}}))
        self.expect("refused", ({"appsettings.json": json.dumps({"AccountId": 123456789012})},))

    def test_odd_host_shapes_ask(self):
        cases = [{"appsettings.json": json.dumps({key: value})} for key, value in (
            ("Server", "tcp:x.database.windows.net,1433"), ("Server", "sql01\\SQLEXPRESS"),
            ("Endpoint", "cache.acme:6379/0"), ("Host", "user@box.acme"), ("Host", "2001:db8::7"),
            ("Host", "localhost,tcp:remote.acme"), ("RedisAddr", "cache.acme"), ("DbAddress", "10.0.0.7"),
            ("MailServerAddress", "mail.acme"), ("DBHost", "db.acme"))]
        cases += [{"compose.yml": "environment:\n  - \"DB_HOST=x.acme\"\n"},
                  {"compose.yml": "environment:\n  DB_HOST: ${H:-x.acme}\n"},
                  {"compose.yml": "servers:\n  - remote.acme\n"},
                  {"compose.yml": "DB_HOST:\n  remote.acme\n"}]
        self.expect("ask", cases)

    def test_no_secret_is_printed(self):
        for files in (
            {"appsettings.json": json.dumps({"Server": "smtp.acme;mailer;S3cretPass"})},
            {"appsettings.json": json.dumps({"Server": "redis+tls://u:aa,S3cretPass,bb@cache"})},
            {"appsettings.json": json.dumps({"Server": "User=sa;Password=aa,S3cretPass,bb"})},
            {"appsettings.json": json.dumps({"Server": "aa,S3cretPass,bb"})},
            {"appsettings.json": json.dumps({"Server": "mailer:S3cretPass@smtp.acme"})},
            {"compose.yml": "x:\n  - S3cretPass:" + self.PROD + "\n"},
            {"compose.yml": "x: |\n  S3cretPass== @" + self.PROD + "\n"},
        ):
            with self.subTest(files=files):
                self.assertNotIn("s3cretpass", json.dumps(self.classify_files(files)).lower())
        self.assertNotIn("48213", json.dumps(self.classify_files({".env.test": "SERVER=admin:48213\n"})))

    def test_no_false_alarms(self):
        p = self.PROD
        self.expect("ok", (
            {"appsettings.json": json.dumps({"Bucket": p}), "appsettings.Test.json": json.dumps({"Bucket": "test"})},
            {"appsettings.json": json.dumps({"Host": p}), "appsettings.Test.json": json.dumps({"Host": ""})},
            {".env.test": "OBSERVER=enabled\nGHOST=casper\nWEBSERVER=gunicorn\n"},
            {"appsettings.json": json.dumps({"Server": "Kestrel"})},
            {"compose.yml": "services:\n  api:\n    extra_hosts:\n      - host.docker.internal:host-gateway\n"},
            {"compose.yml": "services:\n  server:\n    image: shop\n"},
            {"t.runsettings": "<RunSettings>\n<!-- was\n" + p + " -->\n<!-- <Host>db.acme</Host> -->\n</RunSettings>"},
        ))
        env = json.dumps({"PATH": "C:/certs/" + p, "OLDPWD": "C:/src/" + p})
        self.assertEqual(self.classify_files({}, env)["verdict"], "ok")


class HostLayerTests(Base):
    def classify_file(self, rel, text, allow=("localhost",), extra=()):
        items = [{"name": "item", "kind": "local", "match": {"host": host}} for host in allow]
        write(os.path.join(self.ws, "AGENTS", "howtoai", "dev", "settings.json"),
              json.dumps({"environments": {"allow": items, "deny": []}}))
        path = os.path.join(self.ws, *rel.split("/"))
        write(path, text)
        try:
            return run("targets.py", "classify", "--workspace", self.ws, "--user-file", self.user,
                       "--environ", "{}", *extra)[1]
        finally:
            os.remove(path)

    def test_an_empty_key_does_not_take_unrelated_lines(self):
        for text in (
            "environment:\n  - DB_HOST=\n  - LOG=info\n  - TZ=UTC\n",
            "environment:\n  - DB_HOST:\n  - LOG\n",
            "services:\n  server:\n    <<: *b\n",
            "services:\n  server:\n    \"image\": shop\n",
            "servers:\n  - name: one\n",
        ):
            with self.subTest(text=text):
                self.assertEqual(self.classify_file("compose.yml", text)["verdict"], "ok")

    def test_lines_below_a_key_never_print_a_secret(self):
        for text in (
            "environment:\n  - SERVER=\n  - S3cretPass\n",
            "servers:\n  - password: |\n      S3cretPass\n",
            "servers:\n  - db.acme\n  - S3cretPass\n",
        ):
            with self.subTest(text=text):
                self.assertNotIn("s3cretpass", json.dumps(self.classify_file("compose.yml", text)).lower())

    def test_local_forms_are_local(self):
        for value in ("(localdb)\\MSSQLLocalDB", ".\\SQLEXPRESS", "(local)", ".", "localhost;", "localhost,"):
            with self.subTest(value=value):
                res = self.classify_file("appsettings.json", json.dumps({"Server": value}))
                self.assertEqual(res["verdict"], "ok", res)
        res = self.classify_file("compose.yml", "DB_HOST: ${DB_HOST:-localhost}\n")
        self.assertEqual(res["verdict"], "ok", res)
        self.assertEqual(self.classify_file("appsettings.json", '{"Host": "::1"}', allow=("::1",))["verdict"], "ok")

    def test_any_host_value_can_be_allowed_by_its_whole_value(self):
        for value in ("localhost:9092,kafka:29092", "kafka:9092,kafka2:9092", "user@box.acme",
                      "User=sa;Port=1433", "${DB_HOST}"):
            with self.subTest(value=value):
                asked = self.classify_file("compose.yml", "DB_HOST: " + value + "\n")
                self.assertEqual(asked["verdict"], "ask", asked)
                res = self.classify_file("compose.yml", "DB_HOST: " + value + "\n", allow=("localhost", value))
                self.assertEqual(res["verdict"], "ok", res)

    def test_a_run_container_clears_its_host_and_port(self):
        res = self.classify_file(".env.test", "DB_HOST=db:5432\n", extra=("--ephemeral", "db:5432"))
        self.assertEqual(res["verdict"], "ok", res)

    def test_contrived_secrets_are_not_printed(self):
        for value in ("smtp.acme;john.smith;S3cret.Pass", "proto://admin:48213#x@cache.acme",
                      "proto://admin:48213?x@cache.acme"):
            with self.subTest(value=value):
                out = json.dumps(self.classify_file("appsettings.json", json.dumps({"Server": value}))).lower()
                self.assertNotIn("s3cret", out)
                self.assertNotIn("48213", out)

    def test_names_that_are_no_hosts_stay_ok(self):
        for key, value in (("WebServer", "IIS"), ("BillingAddress", "12 Main St.")):
            with self.subTest(key=key):
                self.assertEqual(self.classify_file("appsettings.json", json.dumps({key: value}))["verdict"], "ok")

    def test_a_virtual_environment_path_is_no_target(self):
        prod = SETTINGS["environments"]["deny"][0]
        res = run("targets.py", "classify", "--workspace", self.ws, "--user-file", self.user,
                  "--environ", json.dumps({"VIRTUAL_ENV": "C:/src/" + prod + "/.venv"}))[1]
        self.assertEqual(res["verdict"], "ok", res)

    def test_many_empty_host_keys_stay_fast(self):
        began = __import__("time").monotonic()
        self.classify_file("compose.yml", "- host:\n" * 3000)
        self.classify_file("compose.yml", "host:\n" * 3000 + "  x\n")
        self.assertLess(__import__("time").monotonic() - began, 6)


class HostListTests(Base):
    classify_file = HostLayerTests.classify_file

    def test_a_comment_in_a_list_hides_no_host_after_it(self):
        for text in (
            "x-kafka:\n  servers:\n    - localhost:9092 # dev box\n    - broker.acme:9092\n",
            "servers:\n  - 'localhost:9092' # dev box\n  - broker.acme:9092\n",
            "servers:\n- localhost:9092 # dev box\n- broker.acme:9092\n",
        ):
            with self.subTest(text=text):
                self.assertEqual(self.classify_file("compose.yml", text)["verdict"], "ask")
        prod = SETTINGS["environments"]["deny"][0]
        write(os.path.join(self.ws, "AGENTS", "howtoai", "dev", "settings.json"), json.dumps(SETTINGS))
        path = os.path.join(self.ws, "compose.yml")
        write(path, "servers:\n  - localhost:9092 # dev\n  - " + prod + ":9092\n")
        res = run("targets.py", "classify", "--workspace", self.ws, "--user-file", self.user, "--environ", "{}")[1]
        self.assertEqual(res["verdict"], "refused", res)

    def test_a_quoted_list_clears_host_by_host(self):
        text = "servers:\n  - \"localhost:9092\"\n  - \"broker.acme:9092\"\n"
        res = self.classify_file("compose.yml", text, allow=("localhost", "broker.acme"))
        self.assertEqual(res["verdict"], "ok", res)

    def test_localdb_hides_no_remote_host(self):
        res = self.classify_file("appsettings.json", json.dumps({"Server": "(localdb)\\x,remote.acme"}))
        self.assertEqual(res["verdict"], "ask", res)

    def test_an_unnamed_allow_item_prints_no_value(self):
        value = "user@box.acme;Zq9Secretzz"
        write(os.path.join(self.ws, "AGENTS", "howtoai", "dev", "settings.json"),
              json.dumps({"environments": {"allow": [{"kind": "local", "match": {"host": value}}], "deny": []}}))
        write(os.path.join(self.ws, "appsettings.json"), json.dumps({"Host": value}))
        res = run("targets.py", "classify", "--workspace", self.ws, "--user-file", self.user, "--environ", "{}")[1]
        self.assertEqual(res["verdict"], "ok", res)
        self.assertNotIn("zq9secret", json.dumps(res).lower())


class CiFileTests(Base):
    def test_ci_of_a_repository_in_a_subfolder_is_read(self):
        write(os.path.join(self.ws, "shop", ".github", "workflows", "ci.yml"), "on: push\n")
        write(os.path.join(self.ws, ".github", "workflows", "root.yml"), "on: push\n")
        write(os.path.join(self.ws, "shop", "docs", "github", "workflows", "notes.yml"), "x: 1\n")
        code, res = self.classify()
        files = [f["file"] for f in res["files"]]
        self.assertIn("shop/.github/workflows/ci.yml", files)
        self.assertIn(".github/workflows/root.yml", files)
        self.assertNotIn("shop/docs/github/workflows/notes.yml", files)


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
