"""Find and classify every target a test run could reach. Standard library only.

Usage:
  py -3 -I targets.py classify --workspace <ws> [--user-file <path>] [--environ '<json>']
                               [--ephemeral <host:port or name> ...]

It reads config files only, never a real `.env`, `.env.production`, or other secret store:
  appsettings*.json, *.runsettings, launchSettings.json (environmentVariables only), .env.test,
  .env.testing, .env.example, docker-compose*.yml / compose*.yml, and CI workflow files.
and the process environment (or --environ) for APP_ENV, NODE_ENV, RAILS_ENV, ASPNETCORE_ENVIRONMENT,
DOTNET_ENVIRONMENT, DATABASE_URL, ConnectionStrings__*, AWS_PROFILE, AZURE_CONFIG_DIR, and
GOOGLE_CLOUD_PROJECT.

Each target gets a class, by evidence, in this order (first match wins):
  production  - a deny marker from the settings appears in it, or an environment variable names a
                production environment (production, prod, live, staging)
  allow kind  - an item of environments.allow matches its host, database, profile, or env
                (local, dev, test, remote-test)
  ephemeral   - its host:port or name was passed with --ephemeral (a container this run created)
  local       - an in-memory or file database (SQLite, LocalDB file); no network involved
  unknown     - anything else, including localhost not on the allow list (hint given). Unknown
                counts as production: the run must stop and ask.

Scope says whether a test run loads the file: test (test settings, .env.test, .runsettings, files
under a test folder), base (appsettings.json and other shared config, compose, launch settings),
other-env (files for production, prod, staging, or live), example (.env.example), ci (CI files).
A base key that a test-scope file of the same project overrides is marked used: false.

Verdict: "refused" when a used target in scope test or base is production, or a test-scope file
holds a production marker; "ask" when a used target in those scopes is unknown; else "ok".
Values are never printed: only the key, host, port, database, and profile names.

Files it may not read (real .env files) and files it cannot read or parse are listed under "skipped"
with the reason; an unreadable file in scope test or base makes the verdict at least "ask".

Prints one JSON object: {"ok", "verdict", "reasons", "targets", "markers", "files", "skipped", "checks"}.
"""

import argparse
import fnmatch
import importlib.util
import json
import os
import re
import sys
from urllib.parse import urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
DEVCORE = os.path.join(HERE, "..", "..", "dev-core", "scripts", "devcore.py")

SKIP_DIRS = {".git", "bin", "obj", "node_modules", ".venv", "venv", "__pycache__", "dist", "build",
             ".vs", ".idea", "dev-plans", ".howtoai"}
CONFIG_GLOBS = ["appsettings*.json", "*.runsettings", "launchSettings.json", ".env.test", ".env.testing",
                ".env.example", "docker-compose*.yml", "docker-compose*.yaml", "compose*.yml", "compose*.yaml"]
CI_GLOBS = [".github/workflows/*.yml", ".github/workflows/*.yaml", "azure-pipelines.yml", ".gitlab-ci.yml"]
NEVER_READ = re.compile(r"^\.env(\.(local|production|prod|staging|live|development))?$", re.I)
PROD_ENV = re.compile(r"^(production|prod|live|staging)$", re.I)
OTHER_ENV = re.compile(r"[._-](production|prod|staging|live)[._-]", re.I)
TEST_NAME = re.compile(r"(^|[._-])(test|tests|testing)([._-]|$)", re.I)
ENV_NAMES = ["APP_ENV", "NODE_ENV", "RAILS_ENV", "ASPNETCORE_ENVIRONMENT", "DOTNET_ENVIRONMENT"]
TARGET_ENV = re.compile(r"^(DATABASE_URL|REDIS_URL|AMQP_URL|ConnectionStrings__.+|AWS_PROFILE|AZURE_CONFIG_DIR|GOOGLE_CLOUD_PROJECT)$")
LOOPBACK = {"localhost", "127.0.0.1", "::1", "[::1]", "host.docker.internal"}
KV_HOST = re.compile(r"(?:^|;)\s*(?:host|server|data source|address|addr|hostname)\s*=\s*([^;]+)", re.I)
KV_DB = re.compile(r"(?:^|;)\s*(?:database|initial catalog|dbname)\s*=\s*([^;]+)", re.I)
SCHEME_KIND = {"postgres": "database", "postgresql": "database", "mysql": "database", "mariadb": "database",
               "sqlserver": "database", "mssql": "database", "mongodb": "database", "mongodb+srv": "database",
               "redis": "cache", "rediss": "cache", "amqp": "queue", "amqps": "queue", "sb": "queue",
               "kafka": "queue", "nats": "queue", "http": "api", "https": "api", "ws": "api", "wss": "api",
               "ssh": "server", "sftp": "server", "ftp": "server", "smtp": "api"}
SKIP_KEYS = re.compile(r"(^\$schema$|applicationUrl|launchUrl|^Logging|^Serilog|Url$.*docs|homepage)", re.I)


class Fail(Exception):
    pass


def out(obj, code=0):
    print(json.dumps(obj, ensure_ascii=False, indent=1))
    sys.exit(code)


def load_devcore():
    sys.dont_write_bytecode = True  # no __pycache__ in the plugin's dev-core folder, even without -B
    spec = importlib.util.spec_from_file_location("devcore", os.path.abspath(DEVCORE))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def walk_files(ws):
    for root, dirs, files in os.walk(ws):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), ws).replace("\\", "/")
            yield rel, f


def scope_of(rel, name, test_globs):
    low = name.lower()
    if rel.startswith(".github/") or name in ("azure-pipelines.yml", ".gitlab-ci.yml"):
        return "ci"
    if low == ".env.example":
        return "example"
    if OTHER_ENV.search("." + low.replace("appsettings", "") + "."):
        return "other-env"
    if low in (".env.test", ".env.testing") or low.endswith(".runsettings") or TEST_NAME.search(low.rsplit(".", 1)[0]):
        return "test"
    if any(fnmatch.fnmatch(rel, g) for g in test_globs if g != "**/TESTING.md"):
        return "test"
    return "base"


def flatten_json(node, prefix=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from flatten_json(v, f"{prefix}:{k}" if prefix else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from flatten_json(v, f"{prefix}:{i}")
    elif isinstance(node, str):
        yield prefix, node


def line_of(text, needle):
    i = text.find(needle)
    return text.count("\n", 0, i) + 1 if i >= 0 else 0


def parse_value(key, value):
    """Return a target dict (without class) or None when the value is not a target."""
    v = value.strip().strip('"').strip("'")
    if not v or SKIP_KEYS.search(key):
        return None
    m = re.match(r"^([a-z][a-z0-9+.-]*)://", v, re.I)
    if m:
        scheme = m.group(1).lower()
        if scheme not in SCHEME_KIND:
            return None
        try:
            u = urlsplit(v)
            host, port = (u.hostname or ""), u.port
        except ValueError:
            return None
        if not host:
            return None
        db = u.path.strip("/").split("/")[0] if SCHEME_KIND[scheme] == "database" else ""
        return {"kind": SCHEME_KIND[scheme], "host": host.lower(), "port": port, "database": db or None}
    if re.search(r"(^|;)\s*(data source|server|host)\s*=", v, re.I) and ";" in v + ";":
        hm, dm = KV_HOST.search(v), KV_DB.search(v)
        host = hm.group(1).strip() if hm else ""
        db = dm.group(1).strip() if dm else None
        low = host.lower()
        if low in (":memory:",) or "mode=memory" in v.lower() or re.search(r"\.(db|sqlite3?|mdf)$", low):
            return {"kind": "database", "host": None, "port": None, "database": db, "db_file": host}
        port = None
        if "," in host:
            host, p = host.split(",", 1)
            port = int(p) if p.strip().isdigit() else None
        elif re.match(r"^[^:\\]+:\d+$", host):
            host, p = host.rsplit(":", 1)
            port = int(p)
        host = re.sub(r"^tcp:", "", host.strip(), flags=re.I).lower()
        if host.startswith("(localdb)"):
            return {"kind": "database", "host": None, "port": None, "database": db, "db_file": host}
        return {"kind": "database", "host": host, "port": port, "database": db}
    if re.search(r"profile$", key, re.I) or key.upper() == "AWS_PROFILE":
        return {"kind": "cloud", "host": None, "port": None, "database": None, "profile": v}
    return None


def scan_text_pairs(text):
    """KEY=VALUE and KEY: VALUE lines (env files, compose, CI)."""
    for m in re.finditer(r"^\s*-?\s*([A-Za-z_][A-Za-z0-9_.:]*)\s*[=:]\s*(.+?)\s*$", text, re.M):
        yield m.group(1), m.group(2)


def find_targets(ws, test_globs):
    targets, files, markers, skipped = [], [], [], []
    for rel, name in walk_files(ws):
        if NEVER_READ.match(name):
            skipped.append({"file": rel, "reason": "secret store, never read"})
            continue
        is_cfg = any(fnmatch.fnmatch(name, g) for g in CONFIG_GLOBS)
        is_ci = any(fnmatch.fnmatch(rel, g) for g in CI_GLOBS)
        if not (is_cfg or is_ci):
            continue
        try:
            with open(os.path.join(ws, rel), encoding="utf-8-sig") as f:
                text = f.read()
        except (OSError, UnicodeDecodeError) as e:
            scope = scope_of(rel, name, test_globs)
            skipped.append({"file": rel, "scope": scope, "reason": f"unreadable: {type(e).__name__}"})
            continue
        scope = scope_of(rel, name, test_globs)
        files.append({"file": rel, "scope": scope})
        pairs = []
        if name.lower().endswith(".json"):
            try:
                data = json.loads(text)
            except ValueError:
                data = None
                skipped.append({"file": rel, "scope": scope, "reason": "not valid JSON; values not checked"})
            if name == "launchSettings.json" and isinstance(data, dict):
                for prof in (data.get("profiles") or {}).values():
                    for k, v in ((prof or {}).get("environmentVariables") or {}).items():
                        pairs.append((k, str(v)))
            elif data is not None:
                pairs = list(flatten_json(data))
        else:
            pairs = list(scan_text_pairs(text))
        for key, value in pairs:
            short = key.split(":")[-1]
            if short in ENV_NAMES and PROD_ENV.match(value.strip().strip('"\'')):
                markers.append({"file": rel, "line": line_of(text, short), "key": short, "scope": scope,
                                "reason": f"{short} names a production environment"})
                continue
            t = parse_value(key, value)
            if t:
                t.update({"file": rel, "line": line_of(text, value.strip()), "key": key, "scope": scope,
                          "_raw": value})
                targets.append(t)
    return targets, files, markers, skipped


def project_of(rel):
    return os.path.dirname(rel)


def mark_overrides(targets):
    test_keys = {(project_of(t["file"]), t["key"]) for t in targets if t["scope"] == "test"}
    for t in targets:
        t["used"] = not (t["scope"] == "base" and (project_of(t["file"]), t["key"]) in test_keys)
        if t["scope"] in ("other-env", "example", "ci"):
            t["used"] = False


def classify_one(t, allow, deny, ephemeral, environ):
    raw = (t.pop("_raw", "") or "").lower()
    probe = " ".join(str(x) for x in (raw, t.get("host"), t.get("database"), t.get("profile")) if x).lower()
    for m in deny:
        if m and m.lower() in probe:
            return "production", f"matches deny marker {m!r}"
    for item in allow:
        match = item.get("match") or {}
        for k, val in match.items():
            val = str(val).lower()
            if k == "host" and t.get("host") and t["host"] == val:
                return item.get("kind", "local"), f"allow list: {item.get('name', val)} (host)"
            if k == "database" and t.get("database") and t["database"].lower() == val:
                return item.get("kind", "local"), f"allow list: {item.get('name', val)} (database)"
            if k == "profile" and t.get("profile") and t["profile"].lower() == val:
                return item.get("kind", "local"), f"allow list: {item.get('name', val)} (profile)"
            if k == "env" and "=" in val:
                name, want = val.split("=", 1)
                got = {kk.lower(): vv for kk, vv in environ.items()}.get(name.strip())
                if got is not None and got.lower() == want.strip():
                    return item.get("kind", "local"), f"allow list: {item.get('name', val)} (env)"
    hp = f"{t.get('host')}:{t.get('port')}" if t.get("host") else None
    for e in ephemeral:
        e = e.lower()
        if hp and (e == hp or (t.get("port") and e.endswith(f":{t['port']}") and t["host"] in LOOPBACK)):
            return "ephemeral", "created by this run"
        if t.get("host") and e == t["host"] and e not in LOOPBACK:
            return "ephemeral", "created by this run"
    if t.get("db_file"):
        return "local", "in-memory or file database"
    if t.get("host") in LOOPBACK:
        return "unknown", "loopback host not on the allow list; add it if it is a local service"
    return "unknown", "not on the allow list"


def classify(ws, user_file, environ, ephemeral):
    dc = load_devcore()
    try:
        settings, _ = dc.load_settings(ws, user_file)
    except dc.Fail as e:
        raise Fail(str(e))
    env = settings.get("environments", {})
    allow, deny = env.get("allow", []), env.get("deny", [])
    test_globs = settings.get("testing", {}).get("test_globs", [])
    targets, files, markers, skipped = find_targets(ws, test_globs)
    for k, v in environ.items():
        if k in ENV_NAMES and PROD_ENV.match(v or ""):
            markers.append({"file": "environment", "line": 0, "key": k, "scope": "test",
                            "reason": f"{k} names a production environment"})
        elif TARGET_ENV.match(k):
            t = parse_value(k, v) or ({"kind": "cloud", "host": None, "port": None, "database": None,
                                       "profile": v} if k in ("AWS_PROFILE", "GOOGLE_CLOUD_PROJECT") else None)
            if t:
                t.update({"file": "environment", "line": 0, "key": k, "scope": "test", "_raw": v})
                targets.append(t)
    mark_overrides(targets)
    for t in targets:
        t["class"], t["why"] = classify_one(t, allow, deny, ephemeral, environ)
        for k in [k for k, v in t.items() if v is None]:
            del t[k]
    reasons, verdict = [], "ok"
    for m in markers:
        if m["scope"] in ("test", "base"):
            reasons.append(f"{m['file']}:{m['line']} {m['reason']}")
            verdict = "refused"
    for s in skipped:
        if s.get("scope") in ("test", "base"):
            reasons.append(f"{s['file']} could not be checked ({s['reason']})")
            if verdict == "ok":
                verdict = "ask"
    for t in targets:
        if not t["used"] or t["scope"] not in ("test", "base"):
            continue
        where = f"{t['file']}:{t['line']} {t['key']}"
        if t["class"] == "production":
            reasons.append(f"{where} is production ({t['why']})")
            verdict = "refused"
        elif t["class"] == "unknown":
            reasons.append(f"{where} is unknown ({t['why']})")
            if verdict == "ok":
                verdict = "ask"
    return {"ok": True, "verdict": verdict, "reasons": reasons, "targets": targets,
            "markers": markers, "files": files, "skipped": skipped,
            "checks": ["deny markers", "allow list (host, database, profile, env)", "run-created containers",
                       "file and in-memory databases", "production environment names in files and the environment",
                       "test-scope overrides of base keys"]}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Classify the targets a test run could reach.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("classify")
    c.add_argument("--workspace", required=True)
    c.add_argument("--user-file")
    c.add_argument("--environ", help="JSON object used instead of the process environment")
    c.add_argument("--ephemeral", nargs="*", default=[])
    a = ap.parse_args(argv)
    try:
        ws = os.path.abspath(a.workspace)
        if not os.path.isdir(ws):
            raise Fail(f"workspace not found: {ws}")
        environ = json.loads(a.environ) if a.environ else dict(os.environ)
        if not isinstance(environ, dict):
            raise Fail("--environ must be a JSON object")
        environ = {k: str(v) for k, v in environ.items()
                   if k in ENV_NAMES or TARGET_ENV.match(k)}
        out(classify(ws, a.user_file, environ, a.ephemeral))
    except (Fail, ValueError) as e:
        out({"ok": False, "error": str(e)}, 1)


if __name__ == "__main__":
    main()
