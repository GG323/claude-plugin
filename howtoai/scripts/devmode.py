"""devmode.py - the howtoai plugin's dev-mode tool. The contract is docs/dev-mode.md.

Run it as:  py -3 -I -B devmode.py [--claude-dir <dir>] <command> [options]
(python3 -I -B outside Windows). Standard library only. Every command prints one JSON object.
Exit codes: 0 done or previewed, 1 refused or failed (JSON has "error"), 2 bad arguments.

The setting lives in the workspace's shared AGENTS/settings.json, under the "howtoai" key:
  {"howtoai": {"dev_mode": true, "source_folder": "AGENTS", "plugins_folder": "AGENTS/plugins"}}
dev_mode (true or false) is required: a missing or invalid value is an error, never a default.
The folders are optional and default to AGENTS and <source>/plugins. Other tools' keys in the file
are kept as they are. Git is not a setting: status reports whether Git covers the files, and dev
mode on needs that check to pass before linking.
~/.claude/howtoai/install.json is only a pointer: which workspace holds the setting, and where
this plugin is (howtoai_root).

Commands
  status [--workspace <path>]
      The setting (read from <workspace>/AGENTS/settings.json; the workspace defaults to the
      pointer's), the pointer, the resolved folders, whether Git covers the files, and the health
      of every entry in <claude-dir>/skills and <claude-dir>/agents. Exit 1 with needs_setting
      when the setting is missing or invalid.
  set --dev-mode on|off --workspace <path> [--source-folder <f>] [--plugins-folder <f>] [--write]
      Previews the "howtoai" key in <workspace>/AGENTS/settings.json and the pointer; writes both
      only with --write, keeping every other key in the file. Folders are relative to the
      workspace: source default AGENTS, plugins default <source>/plugins; a default is not
      written into the key. The plugins folder may instead be the absolute path of an existing
      howtoai-mods clone (shared with the workspace that owns it; the pointer then stays on that
      workspace). An option left out keeps the current value. Never runs git init, add, or
      commit. A workspace root with no repository whose direct subfolders hold repositories is a
      multi-repo layout: its root files are notes, not Git problems.
  link --source <skill folder or agent .md file> [--into global|workspace] [--workspace <path>]
      [--harness claude|agents|copilot] [--replace-link] [--write]
      Previews the link for one skill (<root>/skills/<name>) or agent (<root>/agents/<name>.md);
      creates it only with --write. <root> is <claude-dir> (global, the default), ~/.agents or
      ~/.copilot, or <workspace>/.claude, .agents, .copilot with --into workspace (a skill that
      belongs to that workspace only). Never replaces a real folder or file; replaces an
      existing link only with --replace-link. On Windows a skill gets a directory junction and
      an agent a symbolic link. Refuses a source inside a harness folder: harness folders hold
      only links, and the files live in an AGENTS/ folder.
  unlink --dest <link in a harness folder's skills/ or agents/> [--write]
      Previews removing one link (global or in a workspace's .claude, .agents, .copilot);
      removes it only with --write. Removes only the link, never its target, and never a real
      folder or file.
  check-deps
      Whether the tools and skills the howtoai plugin needs are present.
  agents-md --workspace <path> [--replace-baseline] [--write]
      Previews adding the Markdown conventions block (read from skill-audit's reference)
      to the workspace's AGENTS.md. A block that differs is kept unless --replace-baseline.

--claude-dir replaces ~/.claude, for tests.
"""

import argparse
import datetime
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HOWTOAI_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
REFERENCE = os.path.join(HOWTOAI_ROOT, "skills", "skill-audit", "references", "markdown-conventions.md")
HOWTOAI_SKILLS = ["skill-builder", "skill-finder", "skill-audit", "skill-design", "brain-dump", "grilling", "handover"]
HARNESS_SKILLS = [
    ("update-config", "required", "skill-builder hands hook and settings changes to it"),
    ("plugin-authoring", "required", "skill-builder hands mods to it"),
    ("artifact-design", "optional", "loaded before plan pages and reports are published as artifacts"),
    ("docx", "optional", "skill-design's Word documents"),
    ("pptx", "optional", "skill-design's slide decks"),
    ("schedule", "optional", "cloud schedules for procedures skill-builder builds"),
]
IS_WINDOWS = os.name == "nt"
REPARSE_MOUNT_POINT = 0xA0000003
BASELINE_HEADING = "Markdown conventions"
SETTINGS_FILE = "settings.json"  # the workspace's shared AGENTS/settings.json, one top-level key per tool
SETTINGS_KEY = "howtoai"        # this plugin's key in it
HARNESS_FOLDERS = (".claude", ".agents", ".copilot")


class Refused(Exception):
    def __init__(self, message, **extra):
        super().__init__(message)
        self.extra = extra


class BadArgs(Exception):
    pass


def out(obj, code=0):
    sys.stdout.write(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
    sys.exit(code)


def same(a, b):
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


def inside(path, folder):
    try:
        p, f = os.path.normcase(os.path.realpath(path)), os.path.normcase(os.path.realpath(folder))
        return os.path.commonpath([p, f]) == f
    except ValueError:
        return False


# ---- links --------------------------------------------------------------------------------

def is_junction(path):
    if hasattr(os.path, "isjunction"):
        return os.path.isjunction(path)
    try:
        return getattr(os.lstat(path), "st_reparse_tag", 0) == REPARSE_MOUNT_POINT
    except OSError:
        return False


def link_target(path):
    """Return the target of a symbolic link or junction, or None for anything else."""
    if not (os.path.islink(path) or is_junction(path)):
        return None
    target = os.readlink(path)
    if target.startswith("\\\\?\\"):
        target = target[4:]
    if not os.path.isabs(target):
        target = os.path.join(os.path.dirname(path), target)
    return os.path.normpath(target)


def remove_link(path):
    if is_junction(path) or (IS_WINDOWS and os.path.isdir(path)):
        os.rmdir(path)  # removes the junction or directory link only, never the target
    else:
        os.unlink(path)


def make_link(source, dest, is_dir):
    if is_dir and IS_WINDOWS:
        try:
            import _winapi
            _winapi.CreateJunction(source, dest)
            return "junction"
        except (ImportError, AttributeError):
            r = subprocess.run(["cmd", "/c", "mklink", "/J", dest, source], capture_output=True, text=True)
            if r.returncode != 0:
                raise Refused("mklink /J failed: %s" % (r.stderr or r.stdout).strip())
            return "junction"
    try:
        os.symlink(source, dest, target_is_directory=is_dir)
    except OSError as e:
        if IS_WINDOWS and getattr(e, "winerror", None) == 1314:
            raise Refused(
                "Windows allows file links only with Developer Mode or as administrator. Turn on "
                "Developer Mode (Windows 11: Settings > System > For developers; Windows 10: Settings > "
                "Update & Security > For developers), then run this again, or run it from an "
                "administrator shell.")
        raise Refused("Could not create the link: %s" % e)
    return "symlink"


def entry_health(path, kind, workspace):
    name = os.path.basename(path)
    item = {"name": name[:-3] if kind == "agent" else name, "kind": kind, "path": path}
    target = link_target(path)
    if target is None:
        item["state"] = "real"
        if kind == "skill" and not os.path.isfile(os.path.join(path, "SKILL.md")):
            item["note"] = "no SKILL.md (not a skill folder)"
        return item
    item["link"] = "junction" if is_junction(path) else "symlink"
    item["target"] = target
    item["state"] = "link-ok" if os.path.exists(target) else "link-broken"
    if workspace:
        item["in_workspace"] = inside(target, workspace)
    return item


# ---- pointer and setting ------------------------------------------------------------------

def pointer_path(claude_dir):
    return os.path.join(claude_dir, "howtoai", "install.json")


def read_pointer(claude_dir):
    p = pointer_path(claude_dir)
    if not os.path.isfile(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise Refused("The pointer %s cannot be read: %s. Fix or delete it, then run set again." % (p, e))


def check_relative(name, value):
    v = value.replace("\\", "/").strip()
    if os.path.isabs(value) or v.startswith("/") or ".." in v.split("/"):
        raise BadArgs("%s must be a folder inside the workspace, given relative to it, without '..': %s" % (name, value))
    return v.strip("/")


def is_marketplace_clone(path):
    return os.path.isfile(os.path.join(path, ".claude-plugin", "marketplace.json")) and \
        os.path.isdir(os.path.join(path, "howtoai"))


def check_plugins_folder(value):
    """A folder inside the workspace (relative), or an existing howtoai-mods clone anywhere (absolute)."""
    if not os.path.isabs(os.path.expanduser(value)):
        return check_relative("--plugins-folder", value)
    path = os.path.normpath(os.path.abspath(os.path.expanduser(value)))
    if not is_marketplace_clone(path):
        raise BadArgs("--plugins-folder given as an absolute path must be an existing clone of the howtoai-mods "
                      "marketplace (with .claude-plugin/marketplace.json and howtoai/), so it can be shared with "
                      "another workspace: %s" % value)
    return path.replace("\\", "/")


def harness_root(a, workspace=None):
    """The folder a link goes into: <home>/.<harness> (global), or <workspace>/.<harness>."""
    name = "." + a.harness
    if workspace:
        return os.path.join(workspace, name)
    return a.claude_dir if a.harness == "claude" else os.path.join(os.path.dirname(a.claude_dir), name)


def in_harness_folder(source):
    """True for <...>/<harness folder>/skills/<name> or <...>/<harness folder>/agents/<name>.md."""
    parent = os.path.dirname(source)
    return os.path.basename(parent).lower() in ("skills", "agents") and \
        os.path.basename(os.path.dirname(parent)).lower() in HARNESS_FOLDERS


def nested_repos(ws):
    """Direct subfolders of the workspace that hold their own .git (folder or file)."""
    try:
        names = sorted(os.listdir(ws))
    except OSError:
        return []
    return [os.path.join(ws, n) for n in names
            if os.path.isdir(os.path.join(ws, n)) and os.path.exists(os.path.join(ws, n, ".git"))]


def read_agents(ws):
    path = os.path.join(ws, "AGENTS.md")
    if not os.path.isfile(path):
        return path, None
    with open(path, encoding="utf-8", newline="") as f:
        return path, f.read()


def agents_dir(ws):
    """The workspace's AGENTS/ folder in the case it exists in (Agents/ counts), else <ws>/AGENTS."""
    try:
        for name in os.listdir(ws):
            if name.lower() == "agents" and os.path.isdir(os.path.join(ws, name)):
                return os.path.join(ws, name)
    except OSError:
        pass
    return os.path.join(ws, "AGENTS")


def settings_path(ws):
    return os.path.join(agents_dir(ws), SETTINGS_FILE)


def read_settings_file(ws):
    """(path, the whole shared settings object or None when there is no file). A file that is not a
    JSON object is refused, because writing to it would lose other tools' settings."""
    path = settings_path(ws)
    if not os.path.isfile(path):
        return path, None
    try:
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise Refused("%s cannot be read: %s. Fix it first; it holds every tool's settings." % (path, e))
    if not isinstance(data, dict):
        raise Refused("%s must hold a JSON object with one key per tool." % path)
    return path, data


def folder_value(raw):
    raw = str(raw).strip().replace("\\", "/")
    # a leading "/" is dropped (relative folders), unless the value is an absolute shared clone
    return raw.rstrip("/") if is_marketplace_clone(raw.rstrip("/") or "/") else raw.strip("/")


def parse_setting(raw):
    """What the "howtoai" key says, valid or not; None when there is no key."""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        return {"dev_mode": None, "source_folder": "AGENTS", "plugins_folder": "AGENTS/plugins", "bad": {"howtoai": raw}}
    entry = {"bad": {}}
    entry["dev_mode"] = raw.get("dev_mode") if isinstance(raw.get("dev_mode"), bool) else None
    if "dev_mode" in raw and entry["dev_mode"] is None:
        entry["bad"]["dev_mode"] = raw.get("dev_mode")
    src = folder_value(raw.get("source_folder") or "AGENTS") or "AGENTS"
    entry["source_folder"] = src
    entry["plugins_folder"] = folder_value(raw.get("plugins_folder") or src + "/plugins") or src + "/plugins"
    return entry


def setting_needs(entry):
    """What stops the key from being a valid setting; an empty list when it is valid."""
    entry = entry or {}
    if isinstance(entry.get("dev_mode"), bool):
        return []
    if "howtoai" in entry.get("bad", {}):
        problem = 'The "howtoai" key in AGENTS/settings.json must be an object.'
    elif "dev_mode" in entry.get("bad", {}):
        problem = 'Dev mode is %r in AGENTS/settings.json; it must be true or false.' % (entry["bad"]["dev_mode"],)
    else:
        problem = "Dev mode is not set; it must be made on or off."
    return [{"setting": "Dev mode", "problem": problem}]


def needs_error(needs):
    return (" ".join(n["problem"] for n in needs) + " Ask the user, then record the answer: devmode.py set "
            "--workspace <path> --dev-mode on|off.")


def public(entry):
    return {k: v for k, v in entry.items() if k != "bad"} if entry else None


def resolved_paths(ws, setting):
    if not ws or not setting:
        return None
    src = os.path.normpath(os.path.join(ws, setting["source_folder"]))
    plugins = os.path.normpath(os.path.join(ws, setting["plugins_folder"]))
    return {"workspace": ws, "source": src, "skills": os.path.join(src, "skills"), "agents": os.path.join(src, "agents"),
            "docs": os.path.join(src, "docs"), "plugins": plugins,
            "plugins_shared": not inside(plugins, ws)}


def repo_root(path):
    """The nearest folder at or above path that holds .git; found without running git."""
    d = os.path.realpath(path)
    while True:
        if os.path.exists(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def git_health(ws, setting):
    """Whether Git covers the files (AGENTS/settings.json, and with dev mode on the source and plugins folders);
    None without a valid setting. Git is not a setting: dev mode on needs ok here before linking. Read-only."""
    if not ws or not setting:
        return None
    git = shutil.which("git")
    problems = [] if git else ["Git is not installed (Windows: winget install Git.Git)."]
    targets = [("settings", settings_path(ws), False)]
    if setting["dev_mode"]:
        paths = resolved_paths(ws, setting)
        targets += [(key, paths[key], True) for key in ("skills", "agents", "docs", "plugins")]
    repos, notes = {}, []
    subrepos = [] if repo_root(ws) else nested_repos(ws)
    for key, path, is_folder in targets:
        root = repo_root(path)
        repos[key] = root
        if not root and subrepos and inside(path, ws):
            notes.append("%s is at the workspace root, outside its repositories, so it stays local: %s" % (key, path))
        elif not root:
            problems.append("%s is not in a Git repository: %s" % (key, path))
        elif key == "plugins" and not os.path.isdir(path):
            notes.append("plugins is not cloned yet, so its own repository is checked after the clone: %s" % path)
        elif git and not same(path, root):
            probe = os.path.join(os.path.realpath(path), ".devmode-probe") if is_folder else os.path.realpath(path)
            r = subprocess.run([git, "-c", "core.fsmonitor=false", "-C", root, "check-ignore", "-q", "--",
                                os.path.relpath(probe, root)], capture_output=True, text=True, errors="replace")
            if r.returncode == 0:
                problems.append("%s is ignored by the repository %s: %s" % (key, root, path))
            elif r.returncode != 1:
                problems.append("%s could not be checked in %s: %s" % (key, root, r.stderr.strip()))
    return {"ok": not problems, "required": bool(setting["dev_mode"]), "problems": problems, "notes": notes, "repos": repos,
            "layout": "multi-repo" if subrepos else "single-repo", "nested_repos": subrepos}


def load_setting(a, workspace=None):
    """Return (workspace, settings_path, valid setting or None, pointer, needs)."""
    pointer = read_pointer(a.claude_dir)
    ws = workspace or (pointer or {}).get("workspace")
    path, entry = None, None
    if ws:
        ws = os.path.abspath(os.path.expanduser(ws))
        path, data = read_settings_file(ws)
        entry = parse_setting((data or {}).get(SETTINGS_KEY))
    needs = setting_needs(entry)
    return ws or None, path, None if needs else public(entry), pointer, needs


# ---- commands -----------------------------------------------------------------------------

def cmd_status(a):
    ws, path, setting, pointer, needs = load_setting(a, a.workspace)
    paths = resolved_paths(ws, setting)
    links = []
    for kind, folder in (("skill", "skills"), ("agent", "agents")):
        d = os.path.join(a.claude_dir, folder)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if name.startswith(".") or (kind == "agent" and not name.endswith(".md")):
                continue
            links.append(entry_health(os.path.join(d, name), kind, ws if setting else None))
    counts = {}
    for item in links:
        counts[item["state"]] = counts.get(item["state"], 0) + 1
    res = {"ok": not needs, "workspace": ws, "settings_file": path,
           "settings_file_exists": bool(path and os.path.isfile(path)),
           "setting": setting, "dev_mode": setting["dev_mode"] if setting else None,
           "pointer_path": pointer_path(a.claude_dir), "pointer": pointer,
           "howtoai_root": HOWTOAI_ROOT, "git": git_health(ws, setting), "paths": paths, "links": links, "counts": counts}
    if paths:
        res["exists"] = {k: os.path.isdir(v) for k, v in paths.items() if isinstance(v, str)}
    if needs:
        res.update(error=needs_error(needs), needs_setting=needs)
    out(res, 1 if needs else 0)


def holds_valid_setting(workspace):
    if not isinstance(workspace, str) or not os.path.isabs(workspace):
        return False
    try:
        data = read_settings_file(workspace)[1]
    except Refused:
        return False
    return not setting_needs(parse_setting((data or {}).get(SETTINGS_KEY)))


def json_text(data):
    return json.dumps(data, indent=1, ensure_ascii=False) + "\n"


def cmd_set(a):
    ws = os.path.abspath(os.path.expanduser(a.workspace))
    if not os.path.isdir(ws):
        raise BadArgs("The workspace folder does not exist: %s" % ws)
    on = a.dev_mode == "on"
    path, data = read_settings_file(ws)
    whole = dict(data or {})
    prev = parse_setting(whole.get(SETTINGS_KEY))
    if prev and "howtoai" in prev.get("bad", {}):
        prev = None
    src = check_relative("--source-folder", a.source_folder) if a.source_folder else (prev or {}).get("source_folder", "AGENTS")
    if a.plugins_folder:
        plugins = check_plugins_folder(a.plugins_folder)
    elif prev and not a.source_folder:
        plugins = prev["plugins_folder"]
    else:
        plugins = src + "/plugins"
    setting = {"dev_mode": on, "source_folder": src, "plugins_folder": plugins}
    key = {"dev_mode": on}
    if src != "AGENTS":
        key["source_folder"] = src
    if plugins != src + "/plugins":
        key["plugins_folder"] = plugins
    before = json_text(data) if data is not None else ""
    whole[SETTINGS_KEY] = key
    after = json_text(whole)
    old_pointer = read_pointer(a.claude_dir)
    pointed = ws
    shared = not inside(os.path.join(ws, plugins), ws)
    if (not on or shared) and isinstance(old_pointer, dict) and holds_valid_setting(old_pointer.get("workspace")) \
            and not same(old_pointer["workspace"], ws):
        # dev mode off, or dev mode on with another workspace's clone, never takes that workspace's pointer
        pointed = old_pointer["workspace"]
    pointer = {"workspace": pointed, "howtoai_root": HOWTOAI_ROOT, "updated": a.as_of or datetime.date.today().isoformat()}
    pointer_changed = old_pointer is None or {k: v for k, v in old_pointer.items() if k != "updated"} != \
        {k: v for k, v in pointer.items() if k != "updated"}
    changed = after != before
    res = {"ok": True, "write": bool(a.write), "workspace": ws, "settings_file": path, "key": SETTINGS_KEY,
           "setting": setting, "previous": {k: v for k, v in public(prev).items()} if prev else None, "changed": changed,
           "diff": "\n".join(difflib.unified_diff(before.splitlines(), after.splitlines(), "AGENTS/settings.json",
                                                    "AGENTS/settings.json (new)", lineterm="")) if changed else "",
           "pointer_path": pointer_path(a.claude_dir), "pointer": pointer, "pointer_changed": pointer_changed,
           "git": git_health(ws, setting), "paths": resolved_paths(ws, setting)}
    res["exists"] = {k: os.path.isdir(v) for k, v in res["paths"].items() if isinstance(v, str)}
    res["written"] = False
    if a.write:
        if changed:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8", newline="\n") as f:
                f.write(after)
            os.replace(tmp, path)
        if pointer_changed:
            p = pointer_path(a.claude_dir)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8", newline="\n") as f:
                json.dump(pointer, f, indent=2, ensure_ascii=False)
                f.write("\n")
        res["written"] = changed or pointer_changed
    out(res)


def cmd_link(a):
    source = os.path.realpath(os.path.abspath(os.path.expanduser(a.source)))
    into_ws = None
    if a.into == "workspace":
        if not a.workspace:
            raise BadArgs("--into workspace needs --workspace <path>")
        into_ws = os.path.abspath(os.path.expanduser(a.workspace))
    root = harness_root(a, into_ws)
    if os.path.isdir(source):
        if not os.path.isfile(os.path.join(source, "SKILL.md")):
            raise Refused("%s is not a skill folder: it has no SKILL.md" % source)
        kind, dest = "skill", os.path.join(root, "skills", os.path.basename(source))
    elif os.path.isfile(source) and source.lower().endswith(".md"):
        kind, dest = "agent", os.path.join(root, "agents", os.path.basename(source))
    else:
        raise Refused("The source must be a skill folder (with SKILL.md) or an agent .md file: %s" % source)
    if in_harness_folder(source):
        raise Refused("%s is in a harness folder (%s). Harness folders hold only links: keep the skill or agent in "
                      "an AGENTS/ folder (AGENTS/skills/<name>, AGENTS/agents/<name>.md) and link it from there."
                      % (source, ", ".join(HARNESS_FOLDERS)), in_harness_folder=True)
    ws, _, setting, _, needs = load_setting(a, into_ws)
    if needs and not into_ws:  # a workspace link needs no setting in that workspace
        raise Refused(needs_error(needs), needs_setting=needs)
    paths = resolved_paths(ws, setting) or (
        {"source": os.path.join(into_ws, "AGENTS"), "plugins": os.path.join(into_ws, "AGENTS", "plugins")} if into_ws else None)
    res = {"ok": True, "write": bool(a.write), "kind": kind, "source": source, "dest": dest,
           "into": a.into, "harness": a.harness,
           "link": "junction" if (kind == "skill" and IS_WINDOWS) else "symlink"}
    if paths:
        res["in_source"] = any(inside(source, p) for p in (paths["source"], paths["plugins"]) if os.path.exists(p))
        if not res["in_source"]:
            res["note"] = "The source is outside the recorded source and plugin folders."
    target = link_target(dest)
    if target is not None:
        if os.path.exists(target) and same(target, source):
            res.update(action="none", state="already linked", written=False)
            out(res)
        if not a.replace_link:
            raise Refused("%s is already a link to %s%s. Pass --replace-link to point it at the new source; "
                          "the old target is not touched." % (dest, target, "" if os.path.exists(target) else " (broken)"))
        res["action"], res["replaces"] = "replace", target
    elif os.path.lexists(dest):
        raise Refused("%s is a real %s, not a link, and is never replaced. Move it into the source folder "
                      "first, or link under another name." % (dest, "folder" if os.path.isdir(dest) else "file"))
    else:
        res["action"] = "create"
    res["written"] = False
    if a.write:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if res["action"] == "replace":
            remove_link(dest)
        res["link"] = make_link(source, dest, kind == "skill")
        if not same(dest, source):
            raise Refused("The link was created but does not resolve to the source: %s" % dest)
        res["written"], res["state"] = True, "link-ok"
    out(res)


def cmd_unlink(a):
    dest = os.path.abspath(os.path.expanduser(a.dest))
    roots = [os.path.join(a.claude_dir, "skills"), os.path.join(a.claude_dir, "agents")]
    if os.path.normcase(os.path.dirname(dest)) not in [os.path.normcase(r) for r in roots] and not in_harness_folder(dest):
        raise Refused("Only links directly in a harness folder's skills/ or agents/ (global %s or %s, or a "
                      "workspace's .claude, .agents, or .copilot) are removed: %s" % (roots[0], roots[1], dest))
    if not os.path.lexists(dest):
        out({"ok": True, "write": bool(a.write), "dest": dest, "action": "none", "state": "nothing there", "written": False})
    target = link_target(dest)
    if target is None:
        raise Refused("%s is a real %s, not a link; it is never removed." % (dest, "folder" if os.path.isdir(dest) else "file"))
    res = {"ok": True, "write": bool(a.write), "dest": dest, "target": target, "action": "remove", "written": False}
    if a.write:
        remove_link(dest)
        res["written"] = True
    out(res)


def can_symlink():
    d = tempfile.mkdtemp(prefix="devmode-")
    try:
        f = os.path.join(d, "a.txt")
        open(f, "w").close()
        os.symlink(f, os.path.join(d, "b.txt"))
        return True, ""
    except OSError as e:
        return False, str(e)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def cmd_check_deps(a):
    items = []
    py_ok = sys.version_info >= (3, 10)
    items.append({"name": "python", "kind": "tool", "need": "required", "status": "ok" if py_ok else "missing",
                  "detail": "Python %d.%d.%d" % sys.version_info[:3],
                  "fix": "" if py_ok else "Install Python 3.10 or later (Windows: winget install Python.Python.3.13)"})
    git = shutil.which("git")
    items.append({"name": "git", "kind": "tool", "need": "required for dev mode", "status": "ok" if git else "missing",
                  "detail": git or "keeps the workspace's files under version control",
                  "fix": "" if git else "Windows: winget install Git.Git"})
    uv = shutil.which("uv")
    chroma = subprocess.run([sys.executable, "-c", "import chromadb"], capture_output=True).returncode == 0
    items.append({"name": "uv or chromadb", "kind": "tool", "need": "optional", "status": "ok" if (uv or chroma) else "missing",
                  "detail": "skill-finder search: " + ("uv at %s" % uv if uv else "chromadb importable" if chroma else "neither found"),
                  "fix": "" if (uv or chroma) else "winget install astral-sh.uv, or py -3 -m pip install --user chromadb==1.5.9"})
    ok, err = can_symlink()
    items.append({"name": "file links", "kind": "system", "need": "required for dev mode", "status": "ok" if ok else "missing",
                  "detail": "agent files are linked with symbolic links" + ("" if ok else ": " + err),
                  "fix": "" if ok else "Turn on Windows Developer Mode (Settings > For developers) or run the install as administrator; skill folders use junctions and need neither"})
    for s in HOWTOAI_SKILLS:
        present = os.path.isfile(os.path.join(HOWTOAI_ROOT, "skills", s, "SKILL.md"))
        items.append({"name": s, "kind": "howtoai skill", "need": "required", "status": "ok" if present else "missing",
                      "detail": os.path.join(HOWTOAI_ROOT, "skills", s),
                      "fix": "" if present else "Restore the howtoai plugin's files (reinstall or pull the source)"})
    for name, need, why in HARNESS_SKILLS:
        items.append({"name": name, "kind": "harness skill", "need": need, "status": "unknown", "detail": why,
                      "fix": "Built into Claude Code or the anthropic-skills plugin; the installing agent checks its own skill list"})
    ok_all = all(i["status"] != "missing" for i in items if i["need"] == "required")
    out({"ok": True, "deps_ok": ok_all, "howtoai_root": HOWTOAI_ROOT, "items": items})


# ---- AGENTS.md ----------------------------------------------------------------------------

def sections(lines):
    """Return [(title, start, end)] for each '## ' section, ignoring code fences."""
    found, fence = [], False
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            fence = not fence
        if not fence and line.startswith("## "):
            found.append([line[3:].strip(), i, None])
    for k, s in enumerate(found):
        s[2] = found[k + 1][1] if k + 1 < len(found) else len(lines)
    return [tuple(s) for s in found]


def find(secs, title):
    for s in secs:
        if s[0].lower() == title.lower():
            return s
    return None


def trim(block):
    while block and not block[-1].strip():
        block = block[:-1]
    return block


def write_text(path, original, lines):
    nl = "\r\n" if "\r\n" in original else "\n"
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(nl.join(lines) + (nl if original.endswith(("\n", "\r\n")) or not original else ""))


def baseline_block():
    if not os.path.isfile(REFERENCE):
        raise Refused("The conventions reference is missing: %s. Restore the skill-audit skill." % REFERENCE)
    with open(REFERENCE, encoding="utf-8") as f:
        lines = f.read().splitlines()
    s = find(sections(lines), BASELINE_HEADING)
    if not s:
        raise Refused("The reference has no '## %s' section: %s" % (BASELINE_HEADING, REFERENCE))
    return trim(lines[s[1]:s[2]])


def contents_entries(block):
    entries = []
    for line in block:
        if line.startswith("## ") or line.startswith("### "):
            title = line.lstrip("#").strip()
            anchor = "".join(c for c in title.lower().replace(" ", "-") if c.isalnum() or c in "-_")
            entries.append(("  " if line.startswith("### ") else "") + "- [%s](#%s)" % (title, anchor))
    return entries


def add_contents(lines, block, before_title):
    c = find(sections(lines), "Contents")
    if not c:
        return lines
    entries = contents_entries(block)
    if any(lines[i].strip() == entries[0].strip() for i in range(c[1], c[2])):
        return lines
    at = None
    if before_title:
        for i in range(c[1], c[2]):
            if lines[i].startswith("- [%s](" % before_title):
                at = i
                break
    if at is None:
        last = [i for i in range(c[1], c[2]) if lines[i].lstrip().startswith("- [")]
        at = (last[-1] + 1) if last else c[2]
    return lines[:at] + entries + lines[at:]


def place(lines, block, title, after=(), before=()):
    """Insert or replace section `title`. Returns (lines, action)."""
    secs = sections(lines)
    cur = find(secs, title)
    if cur:
        old = trim(lines[cur[1]:cur[2]])
        if old == block:
            return lines, "none"
        tail = lines[cur[1]:cur[2]][len(old):]
        return lines[:cur[1]] + block + (tail or [""]) + lines[cur[2]:], "replace"
    at, next_title = None, None
    for t in after:
        s = find(secs, t)
        if s:
            at = s[2]
            nxt = [x for x in secs if x[1] == s[2]]
            next_title = nxt[0][0] if nxt else None
            break
    if at is None:
        for t in before:
            s = find(secs, t)
            if s:
                at, next_title = s[1], s[0]
                break
    if at is None:
        at = len(lines)
        if lines and lines[-1].strip():
            lines = lines + [""]
            at += 1
    new = lines[:at] + block + [""] + lines[at:]
    return add_contents(new, block, next_title), "insert"


def cmd_agents_md(a):
    ws = os.path.abspath(os.path.expanduser(a.workspace))
    path, text = read_agents(ws)
    if text is None:
        raise Refused("No AGENTS.md in %s. Create one first (skill-audit's workspace audit drafts it)." % ws)
    before = text.splitlines()
    lines = list(before)
    ref = baseline_block()
    cur = find(sections(lines), BASELINE_HEADING)
    block = {"block": "markdown-conventions"}
    if cur and trim(lines[cur[1]:cur[2]]) != ref and not a.replace_baseline:
        block.update(action="kept", state="differs",
                     diff="\n".join(difflib.unified_diff(trim(lines[cur[1]:cur[2]]), ref, "AGENTS.md", "reference", lineterm="")),
                     note="Ask the user which copy wins; rerun with --replace-baseline to take the reference, "
                          "or change the reference in skill-audit.")
    else:
        block["state"] = "missing" if not cur else ("matches" if trim(lines[cur[1]:cur[2]]) == ref else "differs")
        lines, block["action"] = place(lines, ref, BASELINE_HEADING, before=("Installed skills",))
    changed = lines != before
    res = {"ok": True, "write": bool(a.write), "agents_md": path, "blocks": [block], "changed": changed,
           "diff": "\n".join(difflib.unified_diff(before, lines, "AGENTS.md", "AGENTS.md (new)", lineterm="")) if changed else ""}
    res["written"] = False
    if a.write and changed:
        write_text(path, text, lines)
        res["written"] = True
    out(res)


# ---- main ---------------------------------------------------------------------------------

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="The howtoai plugin's dev-mode tool (see docs/dev-mode.md).")
    p.add_argument("--claude-dir", default=os.path.join(os.path.expanduser("~"), ".claude"))
    sub = p.add_subparsers(dest="command", required=True)
    st = sub.add_parser("status")
    st.add_argument("--workspace")
    s = sub.add_parser("set")
    s.add_argument("--dev-mode", choices=["on", "off"], required=True)
    s.add_argument("--workspace", required=True)
    s.add_argument("--source-folder")
    s.add_argument("--plugins-folder")
    s.add_argument("--as-of", help="date for the pointer's 'updated' field, YYYY-MM-DD (tests)")
    s.add_argument("--write", action="store_true")
    l = sub.add_parser("link")
    l.add_argument("--source", required=True)
    l.add_argument("--into", choices=["global", "workspace"], default="global")
    l.add_argument("--workspace")
    l.add_argument("--harness", choices=["claude", "agents", "copilot"], default="claude")
    l.add_argument("--replace-link", action="store_true")
    l.add_argument("--write", action="store_true")
    u = sub.add_parser("unlink")
    u.add_argument("--dest", required=True)
    u.add_argument("--write", action="store_true")
    sub.add_parser("check-deps")
    m = sub.add_parser("agents-md")
    m.add_argument("--workspace", required=True)
    m.add_argument("--replace-baseline", action="store_true")
    m.add_argument("--write", action="store_true")
    a = p.parse_args()
    a.claude_dir = os.path.abspath(os.path.expanduser(a.claude_dir))
    try:
        {"status": cmd_status, "set": cmd_set, "link": cmd_link, "unlink": cmd_unlink, "check-deps": cmd_check_deps,
         "agents-md": cmd_agents_md}[a.command](a)
    except BadArgs as e:
        out({"ok": False, "error": str(e)}, 2)
    except Refused as e:
        out(dict(e.extra, ok=False, error=str(e)), 1)


if __name__ == "__main__":
    main()
