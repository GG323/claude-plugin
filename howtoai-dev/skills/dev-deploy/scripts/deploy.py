"""deploy - discovery, targets, gate, approvals, checks, and the log for dev-deploy.

Usage (Python 3, standard library only; every command prints one JSON object):
  py -3 -I -B deploy.py discover --workspace WS
  py -3 -I -B deploy.py target   list|show|write --workspace WS [--name N] [--file ENTRY.json] [--write]
  py -3 -I -B deploy.py gate     --workspace WS --target N [--change CHANGE_DIR] [--new-file PATH ...]
  py -3 -I -B deploy.py approve  --workspace WS --target N --step ID --command CMD [--minutes M]
  py -3 -I -B deploy.py check    --url URL [--expect 200] [--contains TEXT] [--retries 5] [--wait 3]
  py -3 -I -B deploy.py log      --workspace WS --target N --steps S --outcome O --rollback R
                                 --approved A [--change CHANGE_DIR] [--checks C] [--now ISO]
  py -3 -I -B deploy.py self-edit --workspace WS --trigger T --quote Q --change-text C --route R
                                 --status S [--change CHANGE_DIR] [--now ISO]

discover   Lists what the workspace already has for deploying: container files (Dockerfile,
           compose), Kubernetes manifests (YAML with apiVersion and kind), Helm charts, Kustomize,
           Terraform, CI files, deploy scripts and Makefile or package.json deploy targets,
           hosting files; the deploy CLIs on PATH (with the WSL distros, where wsl is there); and the
           targets file. Reads only.
target     The workspace's targets file, <ws>/.howtoai/deploy/targets.json. write validates one
           entry (from --file) and, only with --write, adds or replaces it; without --write it
           prints the preview.
gate       Checks what code can: the target exists, the work is committed (git status clean
           apart from .howtoai/, the plan folder, and the deploy files a first setup just wrote,
           given as --new-file), and, with --change, the change is at
           stage deploy with an accepted human review and a green latest test run. Lists
           checks_run and checks_skipped.
approve    Records one approved step in <ws>/.howtoai/deploy/approvals.json with its exact
           command and an expiry (default: the target's approval_minutes, else 30). The
           dev-safe-target hook passes that command once before the expiry. Run it only after
           the user's yes for that step.
check      An HTTP check with retries: status code and optional text. Commands checks are run
           by the agent, not here.
log        Adds a run row to the deploy log: <change>/deploy-log.md with --change, else
           <ws>/.howtoai/deploy/log.md; the file is created from assets/deploy-log.md.
self-edit  Adds a row to the deploy log's Self-edits table.

Exit code 0 when the command ran (gate and check: "ok" says whether they passed); 1 with
{"ok": false, "error": "..."} on any error. Writes only the targets file (target write
--write), the approvals file, and the deploy log.
"""

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.abspath(os.path.join(HERE, "..", "assets"))
SKIP_DIRS = {".git", "node_modules", "bin", "obj", ".venv", "venv", "__pycache__", "dist", "build", ".howtoai",
             "TestResults", ".terraform"}
CLIS = ["docker", "podman", "nerdctl", "kubectl", "helm", "kustomize", "kind", "minikube", "rdctl", "k3d",
        "microk8s", "terraform", "az", "aws", "gcloud", "gh", "glab", "flyctl", "vercel", "netlify", "ssh", "scp",
        "rsync", "wsl"]
HOSTING = {"fly.toml": "Fly.io", "vercel.json": "Vercel", "netlify.toml": "Netlify", "app.yaml": "Google App Engine",
           "azure.yaml": "Azure Developer CLI", "Procfile": "Procfile host", "render.yaml": "Render",
           "serverless.yml": "Serverless Framework", "skaffold.yaml": "Skaffold", "Tiltfile": "Tilt"}
CI = {".gitlab-ci.yml": "GitLab CI", "azure-pipelines.yml": "Azure Pipelines", "Jenkinsfile": "Jenkins",
      "bitbucket-pipelines.yml": "Bitbucket Pipelines", ".drone.yml": "Drone"}
ENTRY_KEYS = {"name", "technologies", "production", "tools", "shell", "ready", "start", "steps", "checks",
              "approval_minutes", "notes"}
STEP_KEYS = {"id", "command", "rollback", "production", "watch", "note"}
CHECK_KEYS = {"name", "url", "expect_status", "contains", "command", "retries", "wait_seconds"}


class Fail(Exception):
    pass


def out(obj, code=0):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdout.write(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")
    sys.exit(code)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def now(a=None):
    if a is not None and getattr(a, "now", None):
        return datetime.datetime.fromisoformat(a.now)
    return datetime.datetime.now().astimezone()


def ws_path(ws, *parts):
    return os.path.join(os.path.abspath(ws), ".howtoai", "deploy", *parts)


# ---------------------------------------------------------------- discover

def walk(ws):
    for root, dirs, files in os.walk(ws):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            yield os.path.join(root, name)


def k8s_kinds(path):
    try:
        text = read(path)
    except (OSError, UnicodeDecodeError):
        return []
    if "apiVersion:" not in text:
        return []
    return sorted(set(re.findall(r"^kind:\s*(\w+)", text, re.M)))


def cli_info(name):
    path = shutil.which(name)
    return {"name": name, "path": path} if path else None


def cmd_discover(a):
    ws = os.path.abspath(a.workspace)
    if not os.path.isdir(ws):
        raise Fail(f"no such workspace: {ws}")
    found = {"containers": [], "kubernetes": [], "helm": [], "kustomize": [], "terraform": [], "ci": [],
             "scripts": [], "hosting": []}
    tf_dirs = set()
    for path in walk(ws):
        rel = os.path.relpath(path, ws).replace("\\", "/")
        name = os.path.basename(path)
        low = name.lower()
        if low.startswith("dockerfile") or low.endswith(".dockerfile") or low.startswith(("compose.", "docker-compose")):
            found["containers"].append(rel)
        elif low in ("chart.yaml",):
            found["helm"].append(os.path.dirname(rel) or ".")
        elif low in ("kustomization.yaml", "kustomization.yml"):
            found["kustomize"].append(os.path.dirname(rel) or ".")
        elif low.endswith((".yaml", ".yml")) and rel.startswith(".github/workflows/"):
            found["ci"].append({"file": rel, "system": "GitHub Actions"})
        elif name in CI:
            found["ci"].append({"file": rel, "system": CI[name]})
        elif low.endswith((".yaml", ".yml")):
            kinds = k8s_kinds(path)
            if kinds:
                found["kubernetes"].append({"file": rel, "kinds": kinds})
        elif low.endswith(".tf"):
            tf_dirs.add(os.path.dirname(rel) or ".")
        elif name in HOSTING:
            found["hosting"].append({"file": rel, "host": HOSTING[name]})
        if re.match(r"^(deploy|release|publish|rollout)[\w.-]*\.(sh|ps1|py|cmd|bat)$", low):
            found["scripts"].append(rel)
        if name == "Makefile":
            try:
                targets = re.findall(r"^([\w-]*(?:deploy|release|publish)[\w-]*):", read(path), re.M)
            except (OSError, UnicodeDecodeError):
                targets = []
            if targets:
                found["scripts"].append({"file": rel, "make_targets": targets})
        if name == "package.json":
            try:
                scripts = json.loads(read(path)).get("scripts", {})
            except (OSError, ValueError):
                scripts = {}
            hits = [k for k in scripts if re.search(r"deploy|release|publish", k)]
            if hits:
                found["scripts"].append({"file": rel, "npm_scripts": hits})
    found["terraform"] = sorted(tf_dirs)
    clis = [c for c in (cli_info(n) for n in CLIS) if c]
    wsl = next((c for c in clis if c["name"] == "wsl"), None)
    if wsl:
        try:
            r = subprocess.run([wsl["path"], "-l", "-q"], capture_output=True, timeout=20)
            raw = r.stdout.decode("utf-16-le", "replace") if b"\x00" in r.stdout else r.stdout.decode("utf-8", "replace")
            wsl["distros"] = [d.strip() for d in raw.replace("\x00", "").splitlines() if d.strip()]
        except (OSError, subprocess.SubprocessError):
            wsl["distros"] = "not read"
    targets = load_targets(ws)
    return {"ok": True, "workspace": ws, "found": found, "clis": clis,
            "targets": [t["name"] for t in targets["targets"]],
            "note": "Read-only. Contexts and versions come from the CLIs themselves (for example "
                    "kubectl config current-context), run by the agent."}


# ---------------------------------------------------------------- targets

def load_targets(ws):
    path = ws_path(ws, "targets.json")
    if not os.path.isfile(path):
        return {"targets": []}
    data = json.loads(read(path))
    if not isinstance(data.get("targets"), list):
        raise Fail(f"{path} has no targets list")
    return data


def validate_entry(e):
    problems = []
    if not isinstance(e, dict):
        return ["the entry must be a JSON object"]
    for k in sorted(set(e) - ENTRY_KEYS):
        problems.append(f"unknown key {k!r}")
    if not re.match(r"^[a-z0-9][a-z0-9-]{0,40}$", str(e.get("name", ""))):
        problems.append("name: lowercase letters, digits, and hyphens")
    if not isinstance(e.get("production"), bool):
        problems.append("production must be true or false (is this target production?)")
    if not isinstance(e.get("technologies"), list) or not e.get("technologies"):
        problems.append("technologies: the list of technologies whose workbooks this target uses")
    steps = e.get("steps")
    if not isinstance(steps, list) or not steps:
        problems.append("steps: at least one step")
        steps = []
    ids = set()
    for i, s in enumerate(steps, 1):
        if not isinstance(s, dict):
            problems.append(f"step {i}: must be an object")
            continue
        for k in sorted(set(s) - STEP_KEYS):
            problems.append(f"step {i}: unknown key {k!r}")
        sid = s.get("id")
        if not sid or sid in ids:
            problems.append(f"step {i}: needs a unique id")
        ids.add(sid)
        if not s.get("command"):
            problems.append(f"step {sid or i}: needs a command")
        if not s.get("rollback"):
            problems.append(f"step {sid or i}: needs a rollback (a command, or 'none: <why>')")
    for i, c in enumerate(e.get("checks") or [], 1):
        if not isinstance(c, dict):
            problems.append(f"check {i}: must be an object")
            continue
        for k in sorted(set(c) - CHECK_KEYS):
            problems.append(f"check {i}: unknown key {k!r}")
        if not (c.get("url") or c.get("command")):
            problems.append(f"check {i}: needs a url or a command")
    if not e.get("checks"):
        problems.append("checks: at least one check after the deploy (a health URL or a command)")
    if e.get("shell") not in (None, "bash", "powershell", "cmd"):
        problems.append("shell: bash, powershell, or cmd (the shell the commands are written for)")
    m = e.get("approval_minutes", 30)
    if not isinstance(m, int) or not 1 <= m <= 240:
        problems.append("approval_minutes: a whole number from 1 to 240")
    if re.search(r"(password|secret|token|apikey|api_key)\s*[=:]\s*\S", json.dumps(e), re.I):
        problems.append("the entry looks like it holds a secret; name the account or secret store instead")
    return problems


def cmd_target(a):
    ws = os.path.abspath(a.workspace)
    data = load_targets(ws)
    if a.action == "list":
        return {"ok": True, "targets": [{"name": t["name"], "production": t.get("production"),
                                         "technologies": t.get("technologies")} for t in data["targets"]]}
    if not a.name and a.action == "show":
        raise Fail("show needs --name")
    if a.action == "show":
        for t in data["targets"]:
            if t["name"] == a.name:
                return {"ok": True, "target": t}
        return {"ok": True, "target": None, "note": f"no target named {a.name}: set it up first"}
    if not a.file:
        raise Fail("write needs --file with the entry as JSON")
    entry = json.loads(read(a.file))
    problems = validate_entry(entry)
    if problems:
        return {"ok": False, "problems": problems}
    others = [t for t in data["targets"] if t["name"] != entry["name"]]
    replaced = len(others) != len(data["targets"])
    if not a.write:
        return {"ok": True, "preview": entry, "replaces": replaced, "written": False}
    data["targets"] = others + [entry]
    write_json(ws_path(ws, "targets.json"), data)
    return {"ok": True, "written": True, "replaces": replaced, "path": ws_path(ws, "targets.json")}


def get_target(ws, name):
    for t in load_targets(ws)["targets"]:
        if t["name"] == name:
            return t
    raise Fail(f"no target named {name}: set it up first")


# ---------------------------------------------------------------- gate

def git(ws, *args):
    return subprocess.run(["git", "-c", f"safe.directory={ws}", "-C", ws, *args], capture_output=True, text=True,
                          encoding="utf-8")


def cmd_gate(a):
    ws = os.path.abspath(a.workspace)
    run, skipped, problems = [], [], []
    run.append("target exists")
    try:
        get_target(ws, a.target)
    except Fail as e:
        problems.append(str(e))
    inside = git(ws, "rev-parse", "--is-inside-work-tree")
    if inside.returncode != 0:
        skipped.append({"check": "work committed", "reason": "not a git repository"})
    else:
        run.append("work committed")
        plan_folder = "dev-plans"
        if a.change:
            plan_folder = os.path.relpath(os.path.dirname(os.path.abspath(a.change)), ws).replace("\\", "/")
        dirty = []
        new_files = [n.replace("\\", "/").strip("/") for n in (a.new_file or [])]
        for line in git(ws, "status", "--porcelain", "--untracked-files=all").stdout.splitlines():
            path = line[3:].strip().strip('"')
            if path.startswith((".howtoai/", plan_folder + "/")) or path in (".howtoai", plan_folder):
                continue
            if any(path == n or path.startswith(n.rstrip("/") + "/") for n in new_files):
                continue
            dirty.append(line)
        if dirty:
            problems.append("uncommitted changes: " + "; ".join(dirty[:10]))
    if not a.change:
        skipped.append({"check": "dev process gate (stage, human review, test run)",
                        "reason": "no --change: a deploy outside the dev process"})
    else:
        sp = os.path.join(os.path.abspath(a.change), "state.json")
        if not os.path.isfile(sp):
            raise Fail(f"no state.json in {a.change}")
        st = json.loads(read(sp))
        run += ["stage deploy", "human review accepted", "latest test run green"]
        if st.get("stage") != "deploy":
            problems.append(f"the change is at stage {st.get('stage')}, not deploy")
        if not any(str(x.get("what", "")).startswith("human review") for x in st.get("approvals", [])):
            problems.append("no accepted human review in the change's approvals")
        runs = st.get("test_runs", [])
        if not runs:
            problems.append("no test run recorded")
        elif runs[-1].get("result") != "green":
            problems.append(f"the latest test run is {runs[-1].get('result')}, not green")
    return {"ok": not problems, "problems": problems, "checks_run": run, "checks_skipped": skipped,
            "note": "The target's ready commands (for example kubectl cluster-info) are run by the agent."}


# ---------------------------------------------------------------- approvals

def cmd_approve(a):
    ws = os.path.abspath(a.workspace)
    target = get_target(ws, a.target)
    step = next((s for s in target["steps"] if s.get("id") == a.step), None)
    if step is None and not a.step.startswith("rollback-"):
        raise Fail(f"target {a.target} has no step {a.step}")
    minutes = a.minutes or target.get("approval_minutes", 30)
    if not 1 <= minutes <= 240:
        raise Fail("--minutes must be from 1 to 240")
    t = now(a)
    path = ws_path(ws, "approvals.json")
    data = json.loads(read(path)) if os.path.isfile(path) else {"approvals": []}
    keep_after = t - datetime.timedelta(days=30)
    data["approvals"] = [x for x in data.get("approvals", [])
                         if datetime.datetime.fromisoformat(x["approved"]) > keep_after]
    n = 1 + max([int(x["id"][1:]) for x in data["approvals"] if re.match(r"^A\d+$", x.get("id", ""))] + [0])
    item = {"id": f"A{n}", "target": a.target, "step": a.step, "command": a.command.strip(),
            "approved": t.isoformat(timespec="seconds"),
            "expires": (t + datetime.timedelta(minutes=minutes)).isoformat(timespec="seconds"), "used": False}
    data["approvals"].append(item)
    write_json(path, data)
    return {"ok": True, "approval": item, "path": path}


# ---------------------------------------------------------------- checks

def cmd_check(a):
    tries = []
    for i in range(max(1, a.retries)):
        try:
            with urllib.request.urlopen(a.url, timeout=10) as r:
                status, body = r.status, r.read(65536).decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            status, body = e.code, ""
        except (urllib.error.URLError, OSError) as e:
            status, body = None, str(e)
        good = status == a.expect and (not a.contains or a.contains in body)
        tries.append({"try": i + 1, "status": status, "matched": good})
        if good:
            return {"ok": True, "url": a.url, "tries": tries}
        if i + 1 < a.retries:
            time.sleep(a.wait)
    return {"ok": False, "url": a.url, "tries": tries, "last_body": body[:300]}


# ---------------------------------------------------------------- log

def log_path(ws, change):
    return os.path.join(os.path.abspath(change), "deploy-log.md") if change else ws_path(ws, "log.md")


def ensure_log(path, ws, change):
    if os.path.isfile(path):
        return read(path)
    text = read(os.path.join(ASSETS, "deploy-log.md"))
    title, cid = os.path.basename(os.path.abspath(ws)), "none (outside the dev process)"
    if change and os.path.isfile(os.path.join(change, "state.json")):
        st = json.loads(read(os.path.join(change, "state.json")))
        title, cid = st.get("title", title), st.get("id", cid)
    lines = [l for l in text.splitlines() if not l.startswith("| {")]
    text = "\n".join(lines).replace("{title}", title).replace("{change_id}", cid) + "\n"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return text


def cell(v):
    v = str(v).replace("\n", " ").strip()
    if not v:
        raise Fail("every cell needs a value")
    return v.replace("|", "\\|")


def insert_row(text, header_start, row):
    lines = text.splitlines()
    for i, l in enumerate(lines):
        if l.startswith(header_start) and i + 1 < len(lines) and lines[i + 1].startswith("| ---"):
            lines.insert(i + 2, row)  # newest first
            return "\n".join(lines) + "\n"
    raise Fail(f"the deploy log has no table starting {header_start!r}")


def save(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def cmd_log(a):
    ws = os.path.abspath(a.workspace)
    path = log_path(ws, a.change)
    text = ensure_log(path, ws, a.change)
    when = now(a).strftime("%Y-%m-%d %H:%M")
    row = "| " + " | ".join(cell(v) for v in (when, a.target, a.steps, a.outcome, a.checks or "none", a.rollback,
                                               a.approved)) + " |"
    save(path, insert_row(text, "| Date | Target |", row))
    return {"ok": True, "path": path, "row": row}


def cmd_self_edit(a):
    ws = os.path.abspath(a.workspace)
    path = log_path(ws, a.change)
    text = ensure_log(path, ws, a.change)
    if not re.match(r"^(proposed|approved|applied(: .+)?|declined: .+)$", a.status):
        raise Fail("--status: proposed, approved, applied[: where], or declined: <reason>")
    row = "| " + " | ".join(cell(v) for v in (now(a).strftime("%Y-%m-%d"), a.trigger, a.quote, a.change_text,
                                               a.route, a.status)) + " |"
    save(path, insert_row(text, "| Date | Trigger |", row))
    return {"ok": True, "path": path, "row": row}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="deploy.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("discover"); p.add_argument("--workspace", required=True)
    p = sub.add_parser("target"); p.add_argument("action", choices=["list", "show", "write"])
    p.add_argument("--workspace", required=True); p.add_argument("--name"); p.add_argument("--file")
    p.add_argument("--write", action="store_true")
    p = sub.add_parser("gate"); p.add_argument("--workspace", required=True); p.add_argument("--target", required=True)
    p.add_argument("--change"); p.add_argument("--new-file", action="append")
    p = sub.add_parser("approve"); p.add_argument("--workspace", required=True)
    p.add_argument("--target", required=True); p.add_argument("--step", required=True)
    p.add_argument("--command", required=True); p.add_argument("--minutes", type=int); p.add_argument("--now")
    p = sub.add_parser("check"); p.add_argument("--url", required=True); p.add_argument("--expect", type=int, default=200)
    p.add_argument("--contains"); p.add_argument("--retries", type=int, default=5); p.add_argument("--wait", type=float, default=3)
    p = sub.add_parser("log"); p.add_argument("--workspace", required=True); p.add_argument("--target", required=True)
    for k in ("steps", "outcome", "rollback", "approved"):
        p.add_argument("--" + k, required=True)
    p.add_argument("--checks"); p.add_argument("--change"); p.add_argument("--now")
    p = sub.add_parser("self-edit"); p.add_argument("--workspace", required=True)
    for k in ("trigger", "quote", "change-text", "route", "status"):
        p.add_argument("--" + k, required=True)
    p.add_argument("--change"); p.add_argument("--now")
    a = ap.parse_args(argv)
    cmds = {"discover": cmd_discover, "target": cmd_target, "gate": cmd_gate, "approve": cmd_approve,
            "check": cmd_check, "log": cmd_log, "self-edit": cmd_self_edit}
    try:
        res = cmds[a.cmd](a)
    except (Fail, ValueError, OSError, json.JSONDecodeError, KeyError) as e:
        out({"ok": False, "error": str(e)}, 1)
    out(res, 0)


if __name__ == "__main__":
    main()
