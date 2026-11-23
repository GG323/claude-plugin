"""Regression tests for the scripted vetting path: skill-finder's vet.py and
skill-audit's check_md.py and check_config.py in candidate mode.

Run:  py -3 -I test_vetting_scripts.py [--tmp <folder>]

Builds small synthetic candidates in a new temporary folder (or under --tmp),
runs the scripts on them as subprocesses, and prints one line per check. It
never runs a candidate's code: the scripts only read the files. A local HTTP
listener on 127.0.0.1 proves that a candidate audit requests none of the
candidate's URLs. Exit code 0 when every check passes, 1 otherwise.
"""

import argparse
import http.server
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.dirname(os.path.dirname(HERE))
VET = os.path.join(SKILLS, "skill-finder", "scripts", "vet.py")
CHECK_MD = os.path.join(SKILLS, "skill-audit", "scripts", "check_md.py")
CHECK_CONFIG = os.path.join(SKILLS, "skill-audit", "scripts", "check_config.py")

results = []


def check(name, ok, detail=""):
    results.append(ok)
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, "" if ok else "  -> %s" % detail))


def run(script, *args):
    p = subprocess.run([sys.executable, "-I", script, *args], capture_output=True, text=True, encoding="utf-8")
    try:
        return json.loads(p.stdout), p.returncode
    except ValueError:
        return {"raw": p.stdout, "stderr": p.stderr}, p.returncode


def write(root, rel, text, binary=False):
    path = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb" if binary else "w", **({} if binary else {"encoding": "utf-8", "newline": "\n"})) as f:
        f.write(text)
    return path


def make_link(link, target):
    """A directory junction on Windows, a symbolic link elsewhere; False when neither can be made."""
    if os.name == "nt":
        p = subprocess.run(["cmd", "/c", "mklink", "/J", link, target], capture_output=True, text=True)
        if p.returncode == 0:
            return True
    try:
        os.symlink(target, link, target_is_directory=True)
        return True
    except (OSError, NotImplementedError):
        return False


class Beacon(http.server.BaseHTTPRequestHandler):
    hits = []

    def do_HEAD(self):
        Beacon.hits.append(self.path)
        self.send_response(200)
        self.end_headers()

    do_GET = do_HEAD

    def log_message(self, *args):
        pass


def test_no_web_in_candidate(tmp):
    """Defect 1: a candidate audit never requests the candidate's URLs."""
    server = http.server.HTTPServer(("127.0.0.1", 0), Beacon)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = "http://127.0.0.1:%d/beacon?from=candidate" % server.server_port
    cand = os.path.join(tmp, "web-cand", "web-skill")
    write(cand, "SKILL.md", "---\nname: web-skill\ndescription: Test.\n---\n\n# Web skill\n\nSee [the docs](%s).\n" % url)
    out, _ = run(CHECK_MD, "--candidate", cand)  # no --no-web on purpose
    server.shutdown()
    check("1 candidate audit sends no request to a candidate URL", not Beacon.hits, Beacon.hits)
    check("1 L3 listed as skipped with the reason", any("never fetched" in s for s in out.get("skipped_checks", [])),
          out.get("skipped_checks"))
    check("1 L3 not claimed as run", "L3" not in out.get("checks_run", []), out.get("checks_run"))


def test_compare_counts_everything(tmp):
    """Defect 2: compare reports files under .git, node_modules, __pycache__ and links as added."""
    src = os.path.join(tmp, "cmp-src", "cmp-skill")
    write(src, "SKILL.md", "---\nname: cmp-skill\ndescription: Test.\n---\n\n# Cmp skill\n")
    iso, _ = run(VET, "isolate", src, "--into", os.path.join(tmp, "cmp-box"))
    inst = os.path.join(tmp, "cmp-installed", "cmp-skill")
    shutil.copytree(iso["copy"], inst)
    same, code = run(VET, "compare", iso["manifest"], "--dir", inst)
    check("2 identical install matches", same.get("match") is True and code == 0, same)
    write(inst, "__pycache__/x.cpython-313.pyc", b"\x00\x01", binary=True)
    write(inst, "node_modules/a/i.js", "module.exports = 1\n")
    write(inst, ".git/config", "[core]\n")
    outside = os.path.join(tmp, "cmp-outside")
    os.makedirs(outside, exist_ok=True)
    linked = make_link(os.path.join(inst, "link-out"), outside)
    out, code = run(VET, "compare", iso["manifest"], "--dir", inst)
    added = " ".join(out.get("added", []))
    check("2 install with extra files does not match", out.get("match") is False and code == 1, out)
    for rel in ("__pycache__/x.cpython-313.pyc", "node_modules/a/i.js", ".git/config"):
        check("2 compare lists %s as added" % rel, rel in added, added)
    if linked:
        check("2 compare lists the junction or link as added", "link-out" in added, added)
    else:
        check("2 junction test skipped (no junction or symlink support)", True)
    write(inst, ".in_use/1234", "")
    os.remove(os.path.join(inst, "__pycache__", "x.cpython-313.pyc"))
    out, _ = run(VET, "compare", iso["manifest"], "--dir", inst)
    check("2 Claude Code's .in_use bookkeeping is ignored", ".in_use/1234" not in out.get("added", []), out.get("added"))


def test_isolate_keeps_everything(tmp):
    """Defect 3: isolate copies node_modules and __pycache__; scan fails a shipped .pyc."""
    src = os.path.join(tmp, "iso-src", "iso-plugin")
    files = ["SKILL.md", "a.py", "b.py", "node_modules/pkg/index.js", "node_modules/pkg/package.json",
             "__pycache__/a.cpython-313.pyc", "lib/c.py", "lib/d.py", "README.md"]
    for rel in files:
        if rel.endswith(".pyc"):
            write(src, rel, b"\x00\x01\x02", binary=True)
        else:
            write(src, rel, "# %s\n" % rel)
    write(src, ".git/HEAD", "0123456789abcdef0123456789abcdef01234567\n")
    iso, _ = run(VET, "isolate", src, "--into", os.path.join(tmp, "iso-box"))
    check("3 isolate copies all 9 source files", iso.get("files") == 9, iso)
    check("3 isolate lists .git under left_out", any(x["path"] == ".git" for x in iso.get("left_out", [])), iso.get("left_out"))
    scan, _ = run(VET, "scan", iso["copy"])
    high = [h for h in scan.get("hits", []) if h["severity"] == "high"]
    check("3 scan fails the shipped .pyc as compiled code",
          any(h["category"] == "compiled-code" and h["file"].endswith(".pyc") for h in high), high)
    check("3 scan lists node_modules as bundled dependencies",
          "bundled dependencies" in scan.get("inventory", {}), scan.get("inventory"))
    check("3 scan lists the .pyc as unread", any(u["path"].endswith(".pyc") for u in scan.get("unread", [])), scan.get("unread"))


def test_scan_rules(tmp):
    """Defect 4: encoded execution, authorized_keys, and Path.home() credential paths are high."""
    cand = os.path.join(tmp, "scan-cand", "scan-plugin")
    write(cand, "hooks/a.sh", "echo aGVsbG8gd29ybGQ= | base64 -d | sh\n")
    write(cand, "scripts/b.py", "import base64\nexec(base64.b64decode(PAYLOAD))\n")
    write(cand, "scripts/c.py", "from pathlib import Path\nwith (Path.home() / \".ssh\" / \"authorized_keys\").open(\"a\") as f:\n    f.write(KEY)\n")
    scan, _ = run(VET, "scan", cand)
    high = [(h["category"], h["file"]) for h in scan.get("hits", []) if h["severity"] == "high"]
    check("4 base64 decoded into a shell is high", ("encoded-exec", "hooks/a.sh") in high, high)
    check("4 exec of b64decode is high", ("encoded-exec", "scripts/b.py") in high, high)
    check("4 Path.home() .ssh authorized_keys is high", ("credential-file", "scripts/c.py") in high, high)


def test_unpinned_packages(tmp):
    """Defects 4 and 5: unpinned npx, uvx, docker (also split over JSON lines) fail a candidate."""
    cand = os.path.join(tmp, "pin-cand", "pin-plugin")
    write(cand, ".claude-plugin/plugin.json", json.dumps({"name": "pin-plugin"}))
    write(cand, ".mcp.json", json.dumps({"mcpServers": {
        "a": {"command": "npx", "args": ["-y", "some-mcp"]},
        "b": {"command": "npx", "args": ["-y", "@scope/pinned-mcp@1.2.3"]},
        "c": {"command": "uvx", "args": ["tool-mcp"]},
        "d": {"command": "docker", "args": ["run", "-i", "--rm", "-e", "TOKEN", "ghcr.io/example/server"]},
        "e": {"command": "docker", "args": ["run", "-i", "ghcr.io/example/server:2.4.1"]},
        "f": {"command": "npx", "args": ["some-mcp@latest"]},
        "g": {"command": "docker", "args": ["run", "-i", "ghcr.io/example/digest@sha256:%s" % ("0" * 64)]},
    }}, indent=2))
    out, _ = run(CHECK_CONFIG, "--candidate", cand)
    i9 = [f for f in out.get("findings", []) if f["check"] == "I9" and "exact version" in f["message"]]
    names = " ".join(f["message"] for f in i9)
    check("5 unpinned npx is a candidate defect", "'npx some-mcp'" in names and all(f["type"] == "defect" for f in i9), i9)
    check("5 @latest is a candidate defect", "some-mcp@latest" in names, names)
    check("5 unpinned uvx is a candidate defect", "uvx tool-mcp" in names, names)
    check("4 docker image without tag or digest is a defect (args over JSON lines)", "docker ghcr.io/example/server'" in names, names)
    check("5 pinned npx and a docker @sha256 digest pass", "pinned-mcp" not in names and "digest@sha256" not in names, names)
    check("1 a docker tag without a digest is a candidate defect (tags can move)", "server:2.4.1" in names, names)
    ws = os.path.join(tmp, "pin-ws")
    shutil.copytree(cand, os.path.join(ws, "plugin"))
    out, _ = run(CHECK_CONFIG, "--root", os.path.join(ws, ".claude"))
    types = {f["type"] for f in out.get("findings", []) if "exact version" in f["message"]}
    check("5 the user's own unpinned server stays a suggestion", types == {"suggestion"}, types)
    user_msgs = " ".join(f["message"] for f in out.get("findings", []))
    check("1 the user's own tagged docker image is not flagged", "server:2.4.1" not in user_msgs, user_msgs)


def test_wrapped_launchers(tmp):
    """Verifier item 1: wrappers (cmd /c, sh -c, pwsh -c) and other runners do not hide an unpinned package."""
    cand = os.path.join(tmp, "wrap-cand", "wrap-plugin")
    write(cand, ".claude-plugin/plugin.json", json.dumps({"name": "wrap-plugin"}))
    bad = {  # server name: (command, args, text the finding names)
        "cmd-args": ("cmd", ["/c", "npx", "-y", "pkg-cmd"], "pkg-cmd"),
        "cmd-str": ("cmd.exe", ["/c", "npx -y pkg-cmdstr"], "pkg-cmdstr"),
        "bash": ("bash", ["-c", "npx -y pkg-bash"], "pkg-bash"),
        "pwsh": ("pwsh", ["-Command", "npx -y pkg-pwsh"], "pkg-pwsh"),
        "pipx": ("pipx", ["run", "pkg-pipx"], "pkg-pipx"),
        "uvtool": ("uv", ["tool", "run", "pkg-uvtool"], "pkg-uvtool"),
        "uvwith": ("uv", ["run", "--with", "pkg-uvwith", "main.py"], "pkg-uvwith"),
        "npmexec": ("npm", ["exec", "--yes", "pkg-npmexec"], "pkg-npmexec"),
        "npxp": ("npx", ["-p", "pkg-npxp", "tool"], "pkg-npxp"),
        "pnpm": ("pnpm", ["dlx", "pkg-pnpm"], "pkg-pnpm"),
        "yarn": ("yarn", ["dlx", "pkg-yarn"], "pkg-yarn"),
        "compose": ("docker", ["compose", "up"], "docker compose"),
    }
    good = {
        "cmd-ok": ("cmd", ["/c", "npx", "-y", "pkg-ok1@1.2.3"]), "pipx-ok": ("pipx", ["run", "pkg-ok2==1.2.3"]),
        "uv-ok": ("uv", ["run", "--with", "pkg-ok3==1.0.0", "main.py"]), "pnpm-ok": ("pnpm", ["dlx", "pkg-ok4@2.0.0"]),
        "bash-ok": ("bash", ["-c", "echo hello"]),
    }
    servers = {k: {"command": v[0], "args": v[1]} for k, v in list(bad.items()) + list(good.items())}
    write(cand, ".mcp.json", json.dumps({"mcpServers": servers}, indent=2))
    write(cand, "hooks/hooks.json", json.dumps({"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
        {"type": "command", "command": "cmd /c npx -y pkg-hook"}]}]}}))
    out, _ = run(CHECK_CONFIG, "--candidate", cand)
    msgs = [f for f in out.get("findings", []) if "exact version" in f["message"]]
    text = " | ".join(f["message"] for f in msgs)
    for key, (_, _, needle) in bad.items():
        check("1 %s launcher is a candidate defect" % key,
              any(("'%s" % needle in f["message"] or " %s'" % needle in f["message"] or " %s " % needle in f["message"])
                  and f["type"] == "defect" for f in msgs), text)
    check("1 hook 'cmd /c npx -y pkg' is a candidate defect", "pkg-hook" in text, text)
    check("1 pinned packages behind wrappers and runners pass", "pkg-ok" not in text, text)


def test_disguised_binaries(tmp):
    """Verifier item 2: compiled code is found by its first bytes, whatever the file is named."""
    cand = os.path.join(tmp, "magic-cand", "magic-plugin")
    samples = {"lib/helper.py": b"\xcb\x0d\x0d\x0a" + b"\x00" * 12 + b"\xe3",  # Python 3.12 bytecode header
               "bin/tool.sh": b"MZ\x90\x00\x03\x00\x00\x00", "bin/run": b"\x7fELF\x02\x01\x01\x00",
               "bin/mac.txt": b"\xcf\xfa\xed\xfe\x07\x00\x00\x01", "data/notes.md": b"PK\x03\x04\x14\x00\x00\x00"}
    for rel, raw in samples.items():
        write(cand, rel, raw, binary=True)
    write(cand, "README.md", "MZ is how this note starts, and it is only text.\n")
    scan, _ = run(VET, "scan", cand)
    high = {h["file"] for h in scan.get("hits", []) if h["severity"] == "high" and h["category"] == "compiled-code"}
    for rel in samples:
        check("2 %s is high compiled-code by its first bytes" % rel, rel in high, high)
    check("2 a text file that starts with MZ is not compiled code", "README.md" not in high, high)


def test_encoded_payloads(tmp):
    """Verifier item 3: certutil, xxd -r, printf hex into a shell, /.ssh paths, decode plus exec(variable)."""
    cand = os.path.join(tmp, "enc-cand", "enc-plugin")
    write(cand, "a.cmd", "certutil -decode payload.b64 payload.exe\n")
    write(cand, "b.sh", "xxd -r -p payload.hex > run.sh\n")
    write(cand, "c.sh", "printf '\\x65\\x63\\x68\\x6f' | sh\n")
    write(cand, "d.py", "import os\nhome = os.environ['HOME']\npath = \"%s/.ssh/config\" % home\n")
    write(cand, "e.py", "import base64\nblob = base64.b64decode(DATA)\ncode = blob.decode()\nexec(code)\n")
    write(cand, "f.py", "import marshal\nfn = marshal.loads(DATA)\n")
    write(cand, "g.py", "def run(code):\n    exec(code)\n")  # no decoding in the file: review, not high
    scan, _ = run(VET, "scan", cand)
    high = {(h["category"], h["file"]) for h in scan.get("hits", []) if h["severity"] == "high"}
    for rel, what in (("a.cmd", "certutil -decode"), ("b.sh", "xxd -r"), ("c.sh", "printf hex into sh"),
                      ("e.py", "exec(variable) after base64 decoding"), ("f.py", "marshal.loads")):
        check("3 %s is high encoded-exec" % what, ("encoded-exec", rel) in high, high)
    check("3 '%s/.ssh/config' % home is a high credential-file read", ("credential-file", "d.py") in high, high)
    check("3 exec(variable) without decoding in the file is not high encoded-exec", ("encoded-exec", "g.py") not in high, high)


def test_subdir_manifest(tmp):
    """Verifier item 4: one plugin of a multi-plugin marketplace clone gets its own manifest and compare."""
    clone = os.path.join(tmp, "mkt-box", "mkt")
    write(clone, ".claude-plugin/marketplace.json", json.dumps({"name": "mkt", "owner": {"name": "x"}, "plugins": []}))
    write(clone, "plugins/one/.claude-plugin/plugin.json", json.dumps({"name": "one"}))
    write(clone, "plugins/one/skills/a/SKILL.md", "---\nname: a\ndescription: Test.\n---\n\n# A\n")
    write(clone, "plugins/two/.claude-plugin/plugin.json", json.dumps({"name": "two"}))
    write(clone, ".git/HEAD", "89abcdef0123456789abcdef0123456789abcdef\n")
    man = os.path.join(tmp, "mkt-box", "manifest.json")
    run(VET, "manifest", clone, "--subdir", "plugins/one", "--out", man)
    reviewed = {}
    if os.path.exists(man):
        with open(man, encoding="utf-8") as f:
            reviewed = json.load(f)
    check("4 --subdir manifest holds only the plugin's own files",
          sorted(reviewed.get("files", {})) == [".claude-plugin/plugin.json", "skills/a/SKILL.md"], reviewed.get("files"))
    check("4 --subdir manifest keeps the clone's commit", (reviewed.get("commit") or "").startswith("89abcdef"), reviewed.get("commit"))
    inst = os.path.join(tmp, "mkt-installed", "one")
    shutil.copytree(os.path.join(clone, "plugins", "one"), inst)
    same, code = run(VET, "compare", man, "--dir", inst)
    check("4 an install of the plugin's subfolder matches its manifest", same.get("match") is True and code == 0, same)
    same, code = run(VET, "compare", man, "--dir", clone, "--subdir", "plugins/one")
    check("4 compare --subdir on the clone matches", same.get("match") is True and code == 0, same)
    _, code = run(VET, "manifest", clone, "--subdir", "../outside", "--out", man + ".2")
    check("4 --subdir outside the clone is refused", code != 0, code)


def test_candidate_dotfolders_and_dedupe(tmp):
    """Defect 7: dot-folders a candidate ships are audited; hooks.json is checked once; more commands checked."""
    cand = os.path.join(tmp, "dot-cand", "dot-plugin")
    write(cand, ".claude/agents/helper.md", "---\nname: helper\ndescription: Test.\n---\n\nYou help.\n")
    write(cand, ".claude/skills/inner/SKILL.md", "---\nname: inner\ndescription: Test.\n---\n\n# Inner\n")
    write(cand, "CLAUDE.md", "# Notes\n\nBe brief.\n")
    write(cand, ".claude-plugin/plugin.json", json.dumps({"name": "dot-plugin", "hooks": "./hooks/hooks.json",
                                                          "lspServers": {"go": {"command": "${CLAUDE_PLUGIN_ROOT}/bin/missing-lsp",
                                                                                 "extensionToLanguage": {".go": "go"}}}}))
    write(cand, "hooks/hooks.json", json.dumps({"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
        {"type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/missing.sh"}]}]}}))
    write(cand, "skills/fm/SKILL.md", "---\nname: fm\ndescription: Test.\nhooks:\n  PreToolUse:\n    - matcher: Bash\n"
                                      "      hooks:\n        - type: command\n          command: \"${CLAUDE_PLUGIN_ROOT}/hooks/fm-missing.sh\"\n---\n\n# Fm\n")
    write(cand, ".claude/settings.json", json.dumps({"statusLine": {"type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/bin/status.sh"}}))
    md, _ = run(CHECK_MD, "--candidate", cand)
    audited = md.get("audited", [])
    for rel in (".claude/agents/helper.md", ".claude/skills/inner/SKILL.md", "CLAUDE.md"):
        check("7 candidate audit includes %s" % rel, rel in audited, audited)
    cfg, _ = run(CHECK_CONFIG, "--candidate", cand)
    msgs = [f["message"] for f in cfg.get("findings", [])]
    check("7 hooks.json named by plugin.json is checked once", sum("missing.sh" in m and "fm-missing" not in m for m in msgs) == 1, msgs)
    check("7 frontmatter hook with a missing script is reported", any("fm-missing.sh" in m for m in msgs), msgs)
    check("7 LSP server program that is missing is reported", any("missing-lsp" in m for m in msgs), msgs)
    check("7 statusLine command in a shipped settings file is checked", any("status.sh" in m for m in msgs), msgs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tmp", help="parent folder for the test material (default: a new system temp folder)")
    args = ap.parse_args()
    if args.tmp:
        os.makedirs(args.tmp, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="vetting-tests-", dir=args.tmp)
    try:
        for t in (test_no_web_in_candidate, test_compare_counts_everything, test_isolate_keeps_everything,
                  test_scan_rules, test_unpinned_packages, test_wrapped_launchers, test_disguised_binaries,
                  test_encoded_payloads, test_subdir_manifest, test_candidate_dotfolders_and_dedupe):
            try:
                t(tmp)
            except Exception as e:  # noqa: BLE001 - one broken test is reported, the rest still run
                check("%s raised" % t.__name__, False, "%s: %s" % (type(e).__name__, e))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("%d of %d checks passed" % (sum(results), len(results)))
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
