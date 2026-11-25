"""build - snapshot, hunk list, gate records, and trace check for dev-build.

Usage (Python 3, standard library only; every command prints one JSON object):
  py -3 -I -B build.py start  CHANGE_DIR --n N --wi WI [--route build|fix] [--review FILE] [--user-file F] [--now ISO]
  py -3 -I -B build.py hunks  CHANGE_DIR --n N [--user-file F]
  py -3 -I -B build.py gate   CHANGE_DIR --n N --label baseline|after --name NAME --command "CMD" [--user-file F] [--now ISO]
  py -3 -I -B build.py check  CHANGE_DIR --n N [--user-file F]

start  Snapshots the working tree as a git tree object (a temporary index, `git add -A`, `git
       write-tree`): untracked files that are not ignored are included, and the real index, HEAD,
       branches, and files are not touched. Writes <change>/raw/build-<n>/snapshot.json with the
       tree, the work item (a number or "whole"), the route, and for the Fix route the review file.
hunks  Diffs the snapshot against the working tree now and lists every changed hunk with its ID:
       "path:start-end" (lines in the new file) or "path:<line>d" (lines deleted after that line),
       "path:binary" for a binary file. Each hunk has a class: code, test (testing.test_globs),
       protected (build.protected_globs), or manifest (a package manifest). The plan folder,
       AGENTS/ (tooling and the settings folder), and TESTING.md files (dev-test owns them) are left out.
gate   Runs one gate command and records it in <change>/raw/build-<n>/gate.json under the label.
       The command must equal the command of the gate item NAME in build.gate (no ad-hoc commands).
       Records the exit code, duration, the working tree's tree ID, and the last output lines.
check  Checks <change>/build-<n>.md against the hunks, the test map or review, the state, and
       the gate records. Prints passed, errors, warnings, the checks it ran, and the checks it
       skipped with the reason (the work-item test run on the Fix route).

Exit code 0 when the command ran (check prints "passed": false on findings); 1 with
{"ok": false, "error": "..."} on any error. Writes only <change>/raw/build-<n>/ and git objects.
"""

import argparse
import datetime
import fnmatch
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
CORE = os.path.abspath(os.path.join(HERE, "..", "..", "dev-core", "scripts", "devcore.py"))
LABELS = ("baseline", "after")
ROUTES = ("build", "fix")
MANIFESTS = re.compile(r"(^|/)(package\.json|pyproject\.toml|requirements[^/]*\.txt|Pipfile|setup\.py|setup\.cfg|"
                       r"[^/]+\.csproj|[^/]+\.fsproj|[^/]+\.vbproj|Directory\.Packages\.props|Directory\.Build\.props|"
                       r"packages\.config|go\.mod|Cargo\.toml|Gemfile|composer\.json|pom\.xml|build\.gradle(\.kts)?)$")
SECRET = re.compile(r"((password|pwd|secret|token|apikey|api_key|accountkey|sharedaccesskey)\s*[=:]\s*)[^;\s\"']+"
                    r"|://[^/\s:@]+:[^@\s/]+@|\b(sk|ghp|xox[abprs])[-_][A-Za-z0-9_-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY", re.I)
HUNK_HDR = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
REF = re.compile(r"^(T\d+|C\d+|AC\d+|R\d+-[A-Z]?\d+)$")
PLACEHOLDER = re.compile(r"\{[A-Za-z\"][^{}\n]*\}")
TAIL_LINES = 40


class Fail(Exception):
    pass


def out(obj, code=0):
    sys.stdout.write(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")
    sys.exit(code)


def load_core():
    sys.dont_write_bytecode = True  # no __pycache__ in the plugin's dev-core folder, even without -B
    spec = importlib.util.spec_from_file_location("devcore", CORE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def now_iso(override=None):
    if override:
        try:
            datetime.datetime.fromisoformat(override)
        except ValueError:
            raise Fail(f"--now must be an ISO date and time, got {override!r}")
        return override
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def context(change_dir, user_file):
    core = load_core()
    cdir = os.path.abspath(change_dir)
    if not os.path.isfile(os.path.join(cdir, "state.json")):
        raise Fail(f"no state.json in {cdir}")
    ws = core.workspace_of(cdir)
    try:
        settings, _ = core.load_settings(ws, user_file)
    except core.Fail as e:
        raise Fail(str(e))
    with open(os.path.join(cdir, "state.json"), encoding="utf-8") as f:
        state = json.load(f)
    return core, cdir, ws, settings, state


def raw_dir(cdir, n):
    return os.path.join(cdir, "raw", f"build-{n}")


def read_json(path, default=None):
    if not os.path.isfile(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def git(ws, *args, env=None):
    p = subprocess.run(["git", "-c", "core.quotepath=off", "-c", f"safe.directory={ws.replace(os.sep, '/')}", *args],
                       cwd=ws, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
                       stdin=subprocess.DEVNULL)
    if p.returncode != 0:
        raise Fail(f"git {' '.join(args[:2])} failed: {p.stderr.strip()[:300]}")
    return p.stdout


SKIP_DIRS = {".git", "node_modules", ".venv", "venv"}  # never a name a repository could have


def git_top(folder):
    p = subprocess.run(["git", "-c", f"safe.directory={folder.replace(os.sep, '/')}", "rev-parse", "--show-toplevel"],
                       cwd=folder, capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)
    return os.path.abspath(p.stdout.strip()) if p.returncode == 0 else None


def gitlinks(root):
    """Submodules: the outer repository records their commit, so its tree must keep them."""
    entries = git(root, "ls-files", "-s", "-z").split("\0")
    return {e.split("\t", 1)[1] for e in entries if e.startswith("160000 ")}


def repositories(ws, settings):
    """(key, root) of every repository the workspace reaches: the one around it, and each one inside it.

    The key is the root's path relative to the workspace ("." for the workspace itself)."""
    ws = os.path.abspath(ws)
    roots = []
    top = subprocess.run(["git", "-c", f"safe.directory={ws.replace(os.sep, '/')}", "rev-parse", "--show-toplevel"],
                         cwd=ws, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if top.returncode == 0:
        roots.append(os.path.abspath(top.stdout.strip()))
    elif os.path.isfile(os.path.join(ws, ".git")) or (os.path.isdir(os.path.join(ws, ".git")) and os.listdir(os.path.join(ws, ".git"))):
        raise Fail("the workspace has a .git that git does not accept; repair or remove it")
    elif "not a git repository" not in top.stderr:
        raise Fail(f"git rev-parse failed: {top.stderr.strip()[:300]}")
    plans = settings.get("plan_folder", "dev-plans")
    for folder, dirs, files in os.walk(ws):
        if folder != ws and (".git" in files or (".git" in dirs and os.listdir(os.path.join(folder, ".git")))):
            if not any(os.path.realpath(folder) == os.path.realpath(r) for r in roots):
                if os.path.realpath(git_top(folder) or "") != os.path.realpath(folder):
                    raise Fail(f"{os.path.relpath(folder, ws)} has a .git that git does not accept; repair or remove it")
                roots.append(folder)
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not (folder == ws and (d == plans or d.lower() == "agents"))
                         and not getattr(os.path, "isjunction", lambda p: False)(os.path.join(folder, d)))
    if not roots:
        raise Fail(f"no git repository at, above, or inside {ws}")
    return [(os.path.relpath(r, ws).replace(os.sep, "/"), r) for r in roots]


def pathspecs(ws, settings, root, repos):
    """What one repository's snapshot leaves out: the records, and the repositories inside it."""
    plans = settings.get("plan_folder", "dev-plans")
    inside = os.path.relpath(ws, root).replace(os.sep, "/")
    specs = []
    if inside != ".." and not inside.startswith("../"):  # the workspace lies in this repository
        base = "" if inside == "." else inside + "/"
        specs += [f":(exclude){base}{plans}", f":(exclude){base}AGENTS", f":(exclude,glob){base}**/TESTING.md"]
    else:
        specs.append(":(exclude,glob)**/TESTING.md")
    links = gitlinks(root) if len(repos) > 1 else set()
    below = [os.path.relpath(other, root).replace(os.sep, "/") for _, other in repos]
    below = [rel for rel in below if rel not in (".", "..") and not rel.startswith("../")]
    for rel in below:
        if any(rel.startswith(parent + "/") for parent in below):
            continue  # a repository nearer to it leaves it out; git refuses a pathspec inside a submodule
        if rel not in links:
            specs.append(f":(exclude){rel}")
    return specs


def repo_tree(ws, settings, root, repos):
    fd, idx = tempfile.mkstemp(prefix="devbuild-index-")
    os.close(fd)
    os.remove(idx)
    env = dict(os.environ, GIT_INDEX_FILE=idx)
    try:
        if has_commit(root):
            git(root, "read-tree", "HEAD", env=env)
        wanted = pathspecs(ws, settings, root, repos)
        unnameable = [s for s in wanted if ignored(root, s)]
        git(root, "add", "-A", "--", ".", *[s for s in wanted if s not in unnameable], env=env)
        if unnameable and has_commit(root):
            # ignored but tracked: add updated them, so put them back as committed
            git(root, "reset", "-q", "HEAD", "--", *[s[len(":(exclude)"):] for s in unnameable], env=env)
        return git(root, "write-tree", env=env).strip()
    finally:
        if os.path.exists(idx):
            os.remove(idx)


def ignored(root, spec):
    """git add refuses an exclude naming an ignored path, which is left out of the tree anyway."""
    if not spec.startswith(":(exclude)"):
        return False
    return subprocess.run(["git", "-c", f"safe.directory={root.replace(os.sep, '/')}", "check-ignore", "-q", "--no-index", "--",
                           spec[len(":(exclude)"):]], cwd=root, capture_output=True).returncode == 0


def has_commit(root):
    return subprocess.run(["git", "-c", f"safe.directory={root.replace(os.sep, '/')}", "rev-parse", "--verify", "-q", "HEAD"],
                          cwd=root, capture_output=True).returncode == 0


def join_trees(pairs):
    """One ID for the workspace: the tree itself for one repository, else tree:key pairs."""
    if len(pairs) == 1 and (pairs[0][0] == "." or pairs[0][0].startswith("..")):
        return pairs[0][1]
    return ";".join(f"{tree}:{urllib.parse.quote(key, safe='/. -_@+')}" for key, tree in pairs)


def split_trees(tree_id, repos):
    if ":" not in tree_id:
        key = repos[0][0]
        if key != "." and not key.startswith(".."):
            raise Fail("the repository around the workspace is in the snapshot and is gone now")
        return {key: tree_id}
    return {urllib.parse.unquote(key): tree for tree, key in (pair.split(":", 1) for pair in tree_id.split(";"))}


def empty_tree(root):
    return git(root, "hash-object", "-w", "-t", "tree", "--stdin").strip()


def tree_now(ws, settings):
    """Tree ID of the working tree as `git add -A` would stage it, through a throwaway index, in every
    repository of the workspace.

    The plan folder, AGENTS/ (tooling and the settings folder), and TESTING.md files (dev-test rewrites their Latest run section after
    every run) are left out, so records written during the build do not change it."""
    repos = repositories(ws, settings)
    return join_trees([(key, repo_tree(ws, settings, root, repos)) for key, root in repos])


def head_trees(ws, settings):
    """The same kind of ID for what is committed."""
    repos = repositories(ws, settings)
    return join_trees([(key, git(root, "rev-parse", "HEAD^{tree}").strip() if has_commit(root) else empty_tree(root))
                       for key, root in repos])


def committed(root):
    return git(root, "rev-parse", "HEAD^{tree}").strip() if has_commit(root) else empty_tree(root)


def repo_moves(ws, settings, base, head):
    """Repositories that appeared or went since base: one hunk each, because their files are not this build's lines."""
    repos = repositories(ws, settings)
    before, after = set(split_trees(base, repos)), set(split_trees(head, repos))
    return sorted([(key, "repository-added") for key in after - before] + [(key, "repository-removed") for key in before - after])


def repo_changes(ws, settings, base, head):
    """(key, root, base tree, head tree, pathspecs) for each repository that differs."""
    repos = repositories(ws, settings)
    before, after = split_trees(base, repos), split_trees(head, repos)
    changes = []
    for key, root in repos:
        old, new = before.get(key) or committed(root), after.get(key) or committed(root)
        if old != new:
            changes.append((key, root, old, new, pathspecs(ws, settings, root, repos)))
    return changes


def patch_text(ws, settings, base, head):
    parts = [f"# {key}: {what.replace('-', ' ')}; its files are not in this patch\n"
             for key, what in repo_moves(ws, settings, base, head)]
    for key, root, old, new, specs in repo_changes(ws, settings, base, head):
        if key == "." or key.startswith(".."):  # the workspace's own repository, or the one around it
            scope = os.path.relpath(ws, root).replace(os.sep, "/")
            names = [] if scope == "." else [f"--relative={scope}/"]
        else:
            scope = "."
            names = [f"--src-prefix=a/{key}/", f"--dst-prefix=b/{key}/"]
        parts.append(git(root, "diff-tree", "-r", "-p", "-U3", "--no-renames", "--no-color", "--no-ext-diff", *names,
                         old, new, "--", scope, *specs))
    return "".join(parts)


def when(value):
    try:
        return datetime.datetime.fromisoformat(str(value)).astimezone()
    except ValueError:
        raise Fail(f"not an ISO date and time: {value!r}")


def match(path, globs):
    return any(fnmatch.fnmatch(path, g) or fnmatch.fnmatch("/" + path, g) for g in globs)


def classify(rel, settings):
    if match(rel, settings["testing"]["test_globs"]):
        return "test"
    if match(rel, settings["build"]["protected_globs"]):
        return "protected"
    if MANIFESTS.search(rel):
        return "manifest"
    return "code"


def diff_hunks(ws, settings, base, head):
    hunks = [{"id": f"{key}:{what}", "path": key, "class": classify(key, settings)}
             for key, what in repo_moves(ws, settings, base, head)]
    for key, root, old, new, _ in repo_changes(ws, settings, base, head):
        hunks += repo_hunks(ws, settings, root, old, new)
    return hunks


def repo_hunks(ws, settings, root, base, head):
    text = git(root, "diff-tree", "-r", "-p", "-U0", "--no-renames", "--no-color", "--no-ext-diff", base, head)
    plan_folder = settings.get("plan_folder", "dev-plans")
    skip = (plan_folder + "/", "AGENTS/")
    hunks, path, old = [], None, None
    for line in text.splitlines():
        if line.startswith("diff --git "):
            path = old = None
        elif line.startswith("--- "):
            p = line[4:].strip()
            old = None if p == "/dev/null" else p[2:] if p.startswith("a/") else p
        elif line.startswith("+++ "):
            p = line[4:].strip()
            path = old if p == "/dev/null" else p[2:] if p.startswith("b/") else p
        elif line.startswith("Binary files "):
            m = re.match(r"Binary files (?:a/(.+?)|/dev/null) and (?:b/(.+?)|/dev/null) differ", line)
            if m:
                path = m.group(2) or m.group(1)
                hunks.append((path, f"{path}:binary"))
        elif line.startswith("@@") and path:
            m = HUNK_HDR.match(line)
            if not m:
                continue
            new_start, new_count = int(m.group(3)), int(m.group(4) if m.group(4) is not None else 1)
            hid = f"{path}:{new_start}d" if new_count == 0 else f"{path}:{new_start}-{new_start + new_count - 1}"
            hunks.append((path, hid))
    result = []
    for path, hid in hunks:
        abs_path = os.path.join(root, path)
        rel = os.path.relpath(abs_path, ws).replace(os.sep, "/")
        if rel.startswith("../"):
            continue
        if rel.startswith(skip) or rel.lower().startswith("agents/") or rel == "TESTING.md" or rel.endswith("/TESTING.md"):
            continue
        hid = rel + hid[len(path):]
        result.append({"id": hid, "path": rel, "class": classify(rel, settings)})
    return result


def snapshot(cdir, n):
    snap = read_json(os.path.join(raw_dir(cdir, n), "snapshot.json"))
    if not snap:
        raise Fail(f"no snapshot for build {n}; run start first")
    return snap


def cmd_start(a):
    core, cdir, ws, settings, state = context(a.change_dir, a.user_file)
    if a.route not in ROUTES:
        raise Fail(f"--route must be one of {ROUTES}")
    if a.wi != "whole" and not a.wi.isdigit():
        raise Fail('--wi must be a work item number or "whole"')
    review = None
    if a.route == "fix":
        if not a.review:
            raise Fail("the Fix route needs --review <review-<round>.md>")
        review = os.path.basename(a.review)
        if not re.fullmatch(r"review-\d+\.md", review) or not os.path.isfile(os.path.join(cdir, review)):
            raise Fail(f"--review must name a review-<round>.md file in the change folder, got {a.review!r}")
    path = os.path.join(raw_dir(cdir, a.n), "snapshot.json")
    if os.path.exists(path):
        raise Fail(f"build {a.n} already has a snapshot; use the next build number")
    if a.route == "build":
        checks = [r for r in state.get("test_runs") or [] if r.get("route") == "red-check"
                  and (a.wi == "whole" or str(r.get("wi")) in ("None", "whole", a.wi))]
        latest = {}
        for run in checks:
            if a.wi != "whole" or str(run.get("wi")) in ("None", "whole"):
                latest.clear()  # one item: its newest matching check decides; whole plan: a whole-plan check replaces the items'
            latest[str(run.get("wi"))] = run.get("result")
        last = next((r for r in latest.values() if r != "red"), "red" if latest else "missing")
        if last != "red":
            raise Fail(f"the latest red check for this work is {last}, not red; dev-test's Write route runs it first")
    tree = tree_now(ws, settings)
    snap = {"n": a.n, "wi": a.wi, "route": a.route, "review": review, "tree": tree, "at": now_iso(a.now),
            "stage": state.get("stage")}
    write_json(path, snap)
    return {"ok": True, **snap, "snapshot": path}


def cmd_hunks(a):
    core, cdir, ws, settings, state = context(a.change_dir, a.user_file)
    snap = snapshot(cdir, a.n)
    now = tree_now(ws, settings)
    hunks = diff_hunks(ws, settings, snap["tree"], now)
    counts = {}
    for h in hunks:
        counts[h["class"]] = counts.get(h["class"], 0) + 1
    return {"ok": True, "base": snap["tree"], "tree": now, "hunks": hunks, "counts": counts}


def tail(text):
    lines = [SECRET.sub(lambda m: (m.group(1) or "") + "[redacted]", ln) for ln in text.splitlines()]
    return lines[-TAIL_LINES:]


def cmd_gate(a):
    core, cdir, ws, settings, state = context(a.change_dir, a.user_file)
    if a.label not in LABELS:
        raise Fail(f"--label must be one of {LABELS}")
    snapshot(cdir, a.n)
    items = {g.get("name"): g for g in settings["build"]["gate"]}
    if not items:
        raise Fail("build.gate is empty; propose the gate and save it with devcore setup first")
    if a.name not in items:
        raise Fail(f"--name must be a gate item in build.gate: {sorted(items)}")
    item = items[a.name]
    if a.command.strip() != item.get("command", "").strip():
        raise Fail(f"--command must equal the configured command for {a.name!r}: {item.get('command')!r}")
    cwd = os.path.join(ws, item.get("cwd") or ".")
    tree = tree_now(ws, settings)
    t0 = time.monotonic()
    try:
        p = subprocess.run(item["command"], shell=True, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=settings["build"]["gate_timeout_seconds"])
        code, output = p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired as e:
        code, output = None, f"timed out after {settings['build']['gate_timeout_seconds']} s\n" + str(e.output or "")
    rec = {"name": a.name, "command": item["command"], "label": a.label, "exit_code": code,
           "passed": code == 0, "seconds": round(time.monotonic() - t0, 1), "tree": tree, "at": now_iso(a.now),
           "tail": tail(output)}
    path = os.path.join(raw_dir(cdir, a.n), "gate.json")
    data = read_json(path, {"baseline": {}, "after": {}})
    data[a.label][a.name] = {k: v for k, v in rec.items() if k not in ("name", "label")}
    write_json(path, data)
    return {"ok": True, **rec, "record": path}


def section(text, title):
    m = re.search(rf"^## {re.escape(title)}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1) if m else None


def table_rows(block):
    rows = []
    for line in (block or "").splitlines():
        line = line.strip()
        if not line.startswith("|") or re.fullmatch(r"\|[\s\-:|]+\|", line):
            continue
        rows.append([c.strip() for c in line.strip("|").split("|")])
    return rows[1:] if rows else []


def strip_code(cell):
    return cell.replace("`", "").strip()


def known_refs(cdir, snap):
    """The IDs a hunk may trace to for this build."""
    refs = set()
    if snap["route"] == "fix":
        with open(os.path.join(cdir, snap["review"]), encoding="utf-8") as f:
            for line in f:
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if cells and re.fullmatch(r"R\d+-[A-Z]?\d+", cells[0]) and cells[-1].lower().startswith("fix now"):
                    refs.add(cells[0])
        return refs
    wi = snap["wi"]
    names = [f"test-map-{wi}.md", "test-map.md"] if wi != "whole" else ["test-map.md"]
    for name in names:
        path = os.path.join(cdir, name)
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                text = f.read()
            for title, prefix in (("Criteria", "T"), ("Characterization tests", "C")):
                for row in table_rows(section(text, title)):
                    m = re.fullmatch(r"[TC]?(\d+)", row[0]) if row else None
                    if m:
                        refs.add(f"{prefix}{m.group(1)}")
            break
    if wi != "whole":
        path = os.path.join(cdir, "wi", f"{wi}.md")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                block = section(f.read(), "Acceptance criteria") or ""
            n = sum(1 for ln in block.splitlines() if re.match(r"\s*[-*] \S", ln))
            refs.update(f"AC{i}" for i in range(1, n + 1))
    return refs


def approved_paths(state):
    paths = set()
    for ap in state.get("approvals") or []:
        for p in ap.get("paths") or []:
            paths.add(str(p).replace("\\", "/"))
    return paths


def approved_gates(state, n):
    names = set()
    for ap in state.get("approvals") or []:
        if ap.get("build") == n and ap.get("gate"):
            names.add(ap["gate"])
    return names


def cmd_check(a):
    core, cdir, ws, settings, state = context(a.change_dir, a.user_file)
    snap = snapshot(cdir, a.n)
    errors, warnings = [], []
    report = os.path.join(cdir, f"build-{a.n}.md")
    if not os.path.isfile(report):
        raise Fail(f"no build-{a.n}.md in the change folder")
    with open(report, encoding="utf-8") as f:
        text = f.read()
    for ph in sorted(set(PLACEHOLDER.findall(re.sub(r"`[^`\n]*`", "", text)))):
        errors.append(f"placeholder left in build-{a.n}.md: {ph}")

    now = tree_now(ws, settings)
    hunks = diff_hunks(ws, settings, snap["tree"], now)
    by_id = {h["id"]: h for h in hunks}

    ladder = {}
    for row in table_rows(section(text, "Ladder decisions")):
        if len(row) < 5:
            errors.append(f"Ladder decisions row has {len(row)} cells, needs 5: {row}")
            continue
        lid, rung = row[0], row[2]
        if not re.fullmatch(r"L\d+", lid):
            errors.append(f"Ladder decisions ID must look like L1, got {lid!r}")
            continue
        m = re.match(r"([1-6])\b", rung)
        if not m:
            errors.append(f"{lid}: rung must start with 1-6 (1 not needed ... 6 new code), got {rung!r}")
        ladder[lid] = int(m.group(1)) if m else None
        if not row[4] or row[4].lower() in ("-", "none"):
            errors.append(f"{lid}: Source is empty; name the workbook statement, project code, plan, or 'general'")
    if not ladder:
        errors.append("Ladder decisions has no rows")

    refs = known_refs(cdir, snap)
    if not refs:
        errors.append("no test-map rows, acceptance criteria, or fix-now findings found to trace to")
    traced = {}
    for row in table_rows(section(text, "Trace")):
        if len(row) < 4:
            errors.append(f"Trace row has {len(row)} cells, needs 4: {row}")
            continue
        hid = strip_code(row[0])
        if hid in traced:
            errors.append(f"hunk {hid} has more than one Trace row")
            continue
        traced[hid] = row
        if hid not in by_id:
            errors.append(f"Trace row names a hunk that does not exist now: {hid}")
        cited = [r.strip() for r in row[1].split(",") if r.strip()]
        if not cited:
            errors.append(f"{hid}: Traces to is empty")
        for r in cited:
            if not REF.fullmatch(r):
                errors.append(f"{hid}: {r!r} is not a trace ID (T<n>, C<n>, AC<n>, or a finding ID like R1-C3)")
            elif r not in refs:
                errors.append(f"{hid}: {r} is not in this build's test map, acceptance criteria, or fix-now findings")
        for lid in [x.strip() for x in row[2].split(",") if x.strip()]:
            if lid not in ladder:
                errors.append(f"{hid}: ladder {lid!r} is not a row of Ladder decisions")
        if not row[3]:
            errors.append(f"{hid}: Why this line is empty")
    for h in hunks:
        if h["id"] not in traced:
            errors.append(f"hunk not traced: {h['id']} (revert it, or add a Trace row if the work item needs it)")
    ok_paths = approved_paths(state)
    for h in hunks:
        if h["class"] in ("test", "protected") and h["path"] not in ok_paths:
            errors.append(f"{h['class']} file changed without approval: {h['id']}")
        elif h["class"] == "manifest":
            warnings.append(f"package manifest changed: {h['id']}; confirm the user approved any new dependency")

    gate_items = settings["build"]["gate"]
    records = read_json(os.path.join(raw_dir(cdir, a.n), "gate.json"), {"baseline": {}, "after": {}})
    allowed_fail = approved_gates(state, a.n)
    gate = {}
    if not gate_items:
        errors.append("build.gate is empty")
    for item in gate_items:
        name = item.get("name")
        base, after = records["baseline"].get(name), records["after"].get(name)
        if not after:
            errors.append(f"gate {name}: no 'after' run recorded")
            gate[name] = "not run"
            continue
        if after["tree"] != now:
            errors.append(f"gate {name}: the last 'after' run was on other code; run it again")
        if after["passed"]:
            gate[name] = "pass"
        elif base and not base["passed"] and name in allowed_fail:
            gate[name] = "pre-existing failure, continued with approval"
            warnings.append(f"gate {name} fails before and after the build; the user approved going on")
        else:
            gate[name] = "fail"
            errors.append(f"gate {name}: fails after the build")
    gate_block = section(text, "Gate") or ""
    for item in gate_items:
        if item.get("name") and item["name"] not in gate_block:
            errors.append(f"Gate table has no row for {item['name']}")

    tests = None
    checks_run = ["placeholders", "ladder", "trace", "protected-files", "gate"]
    skipped = []
    if snap["route"] == "fix":
        skipped.append({"check": "wi-tests", "reason": "Fix route: dev-test's Run route runs the tests at stage test, after the fix"})
    else:
        checks_run.append("wi-tests")
    if snap["route"] == "build":
        wi = snap["wi"]
        start = when(snap["at"])
        runs = [r for r in state.get("test_runs") or [] if r.get("route") == "run" and r.get("at")
                and str(r.get("wi")) in ((str(wi),) if wi != "whole" else ("None", "whole")) and when(r["at"]) >= start]
        last_after = max((when(r["at"]) for r in records["after"].values()), default=None)
        if not runs:
            errors.append("no dev-test Run route run recorded for this work item since the snapshot")
        else:
            tests = runs[-1]
            if tests.get("result") != "green":
                errors.append(f"the latest WI test run is {tests.get('result')}, not green")
            if last_after and when(tests["at"]) < last_after:
                errors.append("the WI tests ran before the last gate run; run them again on the final code")
    footer = section(text, "Skipped or unchecked")
    checks_run.append("footer")
    if not footer or not re.search(r"^\s*[-*] \S", footer, re.M):
        errors.append("Skipped or unchecked has no line")
    return {"ok": True, "passed": not errors, "errors": errors, "warnings": warnings, "hunks": len(hunks),
            "traced": len(traced), "gate": gate, "checks_run": checks_run, "skipped": skipped, "tests": tests and {k: tests.get(k) for k in ("n", "result", "passed", "failed", "report")}}


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="dev-build snapshot, hunks, gate, and check")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("change_dir")
        p.add_argument("--n", type=int, required=True)
        p.add_argument("--user-file")
        return p

    p = common(sub.add_parser("start"))
    p.add_argument("--wi", required=True)
    p.add_argument("--route", default="build")
    p.add_argument("--review")
    p.add_argument("--now")
    common(sub.add_parser("hunks"))
    p = common(sub.add_parser("gate"))
    p.add_argument("--label", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--command", required=True)
    p.add_argument("--now")
    common(sub.add_parser("check"))
    a = ap.parse_args(argv)
    try:
        if a.n < 1:
            raise Fail("--n must be 1 or more")
        result = {"start": cmd_start, "hunks": cmd_hunks, "gate": cmd_gate, "check": cmd_check}[a.cmd](a)
    except Fail as e:
        out({"ok": False, "error": str(e)}, 1)
    out(result)


if __name__ == "__main__":
    main()
