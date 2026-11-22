"""Install checks for the howtoai-dev plugin. Standard library only; reads only.

Usage:
  py -3 -I -B install_check.py [--home DIR] [--plugin-root DIR] deps [--no-probe] [--path PATHLIST]
  py -3 -I -B install_check.py [--plugin-root DIR] index

deps    Checks what the install needs and prints one JSON object: deps_ok (no required item
        missing), items (name, kind, need, status, detail, fix, and for_choice where only one
        install choice needs it), and dev_links (each of this plugin's skills and agents in
        ~/.claude/skills and ~/.claude/agents: ok, missing, elsewhere, or real).
        need is "required", "optional", or "required for <choice>". status is "ok", "missing",
        or "unknown" (a script cannot see it: the agent checks its own tool list).
        Probes are read-only (`gh auth status`, `az extension show`, `az account show`,
        `docker version`); --no-probe skips them, reports presence on PATH only, and lists the
        skipped probes in checks_skipped. The dev hooks item also has in_settings and
        plugin_installed.
index   Checks docs/install-index.md: every relative link resolves to a file, every #anchor to a
        heading in that file, and every setting key written as `a.b` (with a top-level schema
        key) exists in dev-core's settings schema. Prints ok, the problems found, and in
        names_skipped every dotted name it did not check as a setting key, with the reason.

--home replaces the user's home folder and --path the PATH search list; both exist for tests.
Exit codes: 0 done (deps_ok or index ok), 1 a required item is missing or the index has problems,
2 bad arguments.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOWTOAI_SKILLS = {"grilling": "required", "skill-builder": "required", "skill-finder": "optional",
                  "skill-design": "optional", "environment-audit": "optional"}
HOOK_FILES = ("dev_test_first.py", "dev_safe_target.py")


def item(name, kind, need, status, detail="", fix="", for_choice=None):
    d = {"name": name, "kind": kind, "need": need, "status": status, "detail": detail, "fix": fix}
    if for_choice:
        d["for_choice"] = for_choice
    return d


def probe(cmd, timeout=25):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, str(e)


def find_skill(home, name):
    """Return the folder of an installed skill by name, from the personal folder or a plugin cache."""
    personal = os.path.join(home, ".claude", "skills", name)
    if os.path.isfile(os.path.join(personal, "SKILL.md")):
        return personal
    cache = os.path.join(home, ".claude", "plugins", "cache")
    if os.path.isdir(cache):
        for root, dirs, files in os.walk(cache):
            if os.path.basename(root) == name and "SKILL.md" in files and \
                    os.path.basename(os.path.dirname(root)) == "skills":
                return root
            if root.count(os.sep) - cache.count(os.sep) > 6:
                dirs[:] = []
    return None


def howtoai_root(home):
    pointer = os.path.join(home, ".claude", "howtoai", "install.json")
    try:
        with open(pointer, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None, None
    root = data.get("howtoai_root")
    if root and os.path.isfile(os.path.join(root, "scripts", "devmode.py")):
        return root, data.get("workspace")
    return None, data.get("workspace")


def tool(name, which, need, fix, for_choice=None):
    path = which(name)
    return item(name, "tool", need, "ok" if path else "missing", path or "not on PATH", "" if path else fix,
                for_choice), path


def check_deps(home, no_probe, search_path):
    which = (lambda n: shutil.which(n, path=search_path)) if search_path is not None else shutil.which
    items = []
    v = sys.version_info
    ok = v >= (3, 10)
    items.append(item("python", "tool", "required", "ok" if ok else "missing", f"{v.major}.{v.minor}.{v.micro}",
                      "" if ok else "Install Python 3.10 or later from python.org or with winget install Python.Python.3.12"))
    it, _ = tool("git", which, "required", "Install Git from git-scm.com or with winget install Git.Git")
    items.append(it)

    for name, need in HOWTOAI_SKILLS.items():
        found = find_skill(home, name)
        items.append(item(name, "skill", need, "ok" if found else "missing", found or "not installed",
                          "" if found else "Install the howtoai plugin: claude plugin install howtoai@howtoai-mods, "
                                           "or follow its INSTALL.md"))
    root, ws = howtoai_root(home)
    items.append(item("devmode.py", "script", "required for dev mode", "ok" if root else "missing",
                      os.path.join(root, "scripts", "devmode.py") if root else "no ~/.claude/howtoai/install.json pointer",
                      "" if root else "Run the howtoai plugin's INSTALL.md first; it writes the pointer",
                      "dev mode on"))

    it, gh = tool("gh", which, "required for tracker github", "Install GitHub CLI (winget install GitHub.cli), then gh auth login",
                  "tracker: github")
    if gh and not no_probe:
        code, out = probe([gh, "auth", "status"])
        if code != 0:
            it.update(status="missing", detail="gh is not signed in", fix="Run gh auth login (you sign in yourself)")
    items.append(it)

    it, az = tool("az", which, "required for tracker azure-devops (without its MCP server)",
                  "Install the Azure CLI (winget install Microsoft.AzureCLI), then az extension add --name azure-devops and az login",
                  "tracker: azure-devops")
    if az and not no_probe:
        code, _ = probe([az, "extension", "show", "--name", "azure-devops", "--output", "none"])
        if code != 0:
            it.update(status="missing", detail="az has no azure-devops extension", fix="Run az extension add --name azure-devops")
        else:
            code, _ = probe([az, "account", "show", "--output", "none"])
            if code != 0:
                it.update(status="missing", detail="az is not signed in", fix="Run az login (you sign in yourself)")
    items.append(it)

    it, docker = tool("docker", which, "required for throwaway test targets and Docker deploys",
                      "Install Docker Desktop, or set testing.ephemeral to none", "testing.ephemeral: docker")
    if docker and not no_probe:
        code, _ = probe([docker, "version", "--format", "{{.Server.Version}}"])
        if code != 0:
            it.update(status="missing", detail="docker CLI found, but the engine is not running", fix="Start Docker Desktop")
    items.append(it)
    it, _ = tool("kubectl", which, "required for Kubernetes deploys", "Install kubectl (winget install Kubernetes.kubectl)",
                 "deploy target: kubernetes")
    items.append(it)

    for name, choice in (("Atlassian MCP server", "tracker: jira"), ("Azure DevOps MCP server", "tracker: azure-devops")):
        items.append(item(name, "connector", f"required for {choice} (Azure DevOps can use az instead)" if "Azure" in name
                          else f"required for {choice}", "unknown", "a script cannot see connectors",
                          "The agent searches its own tool list; the user connects it in the harness", choice))
    for name, why in (("subagents", "the goldfish reviewers; without them they run one after another"),
                      ("Artifact tool", "plan.publish auto and artifact"),
                      ("hooks", "the dev-test-first and dev-safe-target hooks")):
        items.append(item(name, "harness", "optional", "unknown", why, "The agent checks what its harness offers"))

    links = dev_links(home)
    items.append(hooks_item(home))
    deps_ok = all(i["status"] == "ok" for i in items if i["need"] == "required")
    if no_probe:
        for i in items:
            if i["name"] in ("gh", "az", "docker") and i["status"] == "ok":
                i["detail"] += " (on PATH; sign-in, extension, and engine not probed: --no-probe)"
    skipped = [{"check": c, "reason": "--no-probe"} for c in
               ("gh auth status", "az extension show azure-devops", "az account show", "docker version")] if no_probe else []
    return {"ok": True, "deps_ok": deps_ok, "plugin_root": PLUGIN_ROOT, "howtoai_root": root,
            "pointer_workspace": ws, "items": items, "dev_links": links, "checks_skipped": skipped}


def real(p):
    return os.path.normcase(os.path.realpath(p))


def dev_links(home):
    out = []
    skills = os.path.join(PLUGIN_ROOT, "skills")
    agents = os.path.join(PLUGIN_ROOT, "agents")
    pairs = []
    if os.path.isdir(skills):
        pairs += [("skill", os.path.join(skills, n), os.path.join(home, ".claude", "skills", n))
                  for n in sorted(os.listdir(skills)) if os.path.isfile(os.path.join(skills, n, "SKILL.md"))]
    if os.path.isdir(agents):
        pairs += [("agent", os.path.join(agents, n), os.path.join(home, ".claude", "agents", n))
                  for n in sorted(os.listdir(agents)) if n.endswith(".md")]
    for kind, src, dest in pairs:
        if not os.path.lexists(dest):
            state = "missing"
        elif real(dest) == real(src):
            state = "ok"
        elif os.path.islink(dest) or real(dest) != os.path.normcase(os.path.abspath(dest)):
            state = "elsewhere"
        else:
            state = "real"
        out.append({"name": os.path.basename(src), "kind": kind, "source": src, "dest": dest, "state": state})
    return out


def hooks_item(home):
    settings = os.path.join(home, ".claude", "settings.json")
    in_settings = plugin_installed = False
    try:
        with open(settings, encoding="utf-8") as f:
            text = f.read()
        in_settings = all(h in text for h in HOOK_FILES)
    except OSError:
        pass
    try:
        with open(os.path.join(home, ".claude", "plugins", "installed_plugins.json"), encoding="utf-8") as f:
            plugin_installed = "howtoai-dev@" in f.read()
    except OSError:
        pass
    where = ([f"registered in {settings}"] if in_settings else []) + (["plugin howtoai-dev installed"] if plugin_installed else [])
    if in_settings and plugin_installed:
        fix = "Both are active, so each hook runs twice: keep one (INSTALL, Install or link)"
    elif where:
        fix = ""
    else:
        fix = ("Dev mode: register them in ~/.claude/settings.json (INSTALL, Install or link); "
               "plugin mode: they load with the installed plugin")
    d = item("dev hooks", "hooks", "optional", "ok" if where else "missing", "; ".join(where) or "not registered", fix)
    d.update(in_settings=in_settings, plugin_installed=plugin_installed)
    return d


SLUG_DROP = re.compile(r"[^\w\- ]", re.UNICODE)
FILE_EXTENSIONS = {"md", "json", "html", "py", "yml", "yaml", "txt", "js", "csproj", "tf"}


def slugs(path):
    seen, out = {}, set()
    in_code = False
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.lstrip().startswith("```"):
                in_code = not in_code
            if in_code:
                continue
            m = re.match(r"#{1,6}\s+(.*?)\s*#*\s*$", line)
            if not m:
                continue
            s = SLUG_DROP.sub("", m.group(1).replace("`", "").strip().lower()).replace(" ", "-")
            n = seen.get(s, 0)
            seen[s] = n + 1
            out.add(s if n == 0 else f"{s}-{n}")
    return out


def schema_has(schema, dotted):
    node = schema
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return False
        node = node[part]
    return True


def check_index():
    index = os.path.join(PLUGIN_ROOT, "docs", "install-index.md")
    if not os.path.isfile(index):
        return {"ok": False, "error": f"missing {index}"}
    with open(os.path.join(PLUGIN_ROOT, "skills", "dev-core", "assets", "settings.schema.json"), encoding="utf-8") as f:
        schema = json.load(f)
    with open(index, encoding="utf-8") as f:
        text = f.read()
    problems, links, keys, skipped = [], 0, 0, set()
    base = os.path.dirname(index)
    cache = {}
    for target in re.findall(r"\]\((<[^>]+>|[^)\s]+)\)", text):
        target = target.strip("<>")
        if re.match(r"[a-z]+:", target):
            continue
        links += 1
        file_part, _, anchor = target.partition("#")
        path = os.path.normpath(os.path.join(base, file_part)) if file_part else index
        if not os.path.exists(path):
            problems.append(f"link to a missing file: {target}")
            continue
        if anchor:
            if os.path.isdir(path) or not path.endswith(".md"):
                problems.append(f"anchor on a file that is not Markdown: {target}")
                continue
            if path not in cache:
                cache[path] = slugs(path)
            if anchor not in cache[path]:
                problems.append(f"missing heading #{anchor} in {os.path.relpath(path, PLUGIN_ROOT)}")
    for key in set(re.findall(r"`([a-z_]+(?:\.[a-z_]+)+)`", text)):
        if key.rsplit(".", 1)[1] in FILE_EXTENSIONS:
            skipped.add(f"{key}: a file name")
            continue
        if key.split(".")[0] in schema and not key.startswith("$"):
            keys += 1
            if not schema_has(schema, key):
                problems.append(f"setting key not in the schema: {key}")
        else:
            skipped.add(f"{key}: its first part is not a top-level setting")
    return {"ok": not problems, "index": index, "links_checked": links, "keys_checked": keys,
            "names_skipped": sorted(skipped), "problems": sorted(problems)}


def main(argv=None):
    ap = argparse.ArgumentParser(description="howtoai-dev install checks")
    ap.add_argument("--home")
    ap.add_argument("--plugin-root")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("deps")
    d.add_argument("--no-probe", action="store_true")
    d.add_argument("--path")
    sub.add_parser("index")
    a = ap.parse_args(argv)
    global PLUGIN_ROOT
    if a.plugin_root:
        PLUGIN_ROOT = os.path.abspath(a.plugin_root)
    if a.cmd == "deps":
        res = check_deps(os.path.abspath(a.home or os.path.expanduser("~")), a.no_probe, a.path)
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0 if res["deps_ok"] else 1
    res = check_index()
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
