"""devcore - shared settings and plan folder state for the howtoai-dev skills.

Usage (Python 3, standard library only; every command prints one JSON object):
  py -3 -I devcore.py root      [--cwd DIR]
  (every command except root also takes [--user-file F], read instead of the default user defaults file)
  py -3 -I devcore.py settings  [--workspace W] [--user-file F]
  py -3 -I devcore.py setup     --workspace W (--values JSON | --values-file F) [--scope project|user] [--write]
  py -3 -I devcore.py new-change --workspace W --title TEXT [--slug SLUG] [--date YYYY-MM-DD]
  py -3 -I devcore.py state     CHANGE_DIR [--patch JSON] [--now ISO]
  py -3 -I devcore.py index     --workspace W

root        Finds the workspace root: the nearest folder at or above --cwd (default: the current
            folder) that holds AGENTS.md or CLAUDE.md.
settings    Merges the schema defaults, the user file (default ~/.claude/howtoai/dev-settings.json),
            and this plugin's "howtoai-dev" key in the project file (<workspace>/AGENTS/settings.json,
            shared by the workspace's tools, one top-level key each). Prints the merged values,
            the source of each top-level key, and whether the project is configured.
setup       Validates --values (a JSON object of project settings), or the same JSON read from the
            --values-file F (UTF-8), against the schema. Give exactly one of the two. Without
            --write it prints the file it would write (a preview); with --write it writes
            the "howtoai-dev" key of <workspace>/AGENTS/settings.json (other keys are kept), or with
            --scope user the user defaults file.
            Values that look like secrets are refused.
new-change  Creates <workspace>/<plan_folder>/<date>-<slug>/state.json and rebuilds INDEX.md.
            An existing folder gets a -2, -3, ... suffix. The date comes from the system clock
            unless --date is given.
state       Prints a change's state.json. With --patch it applies the patch first:
              {"stage": "build", "size": "Medium", "title": "...", "plan_item": {"tracker_key": "..."},
               "append": {"approvals": {...}, "receipts": {...}, "wi": {...}, "declined": {...},
                          "test_runs": {...}, "ephemeral": {...}, "builds": {...}},
               "increment": {"review": 1}}
            Stage changes are recorded in history. The index is rebuilt after every write.
            An approval with "by": "user" needs "reply", the user's reply word for word. When
            dev-core's state/replies.jsonl exists (written by the dev-reply-log hook on each
            user prompt, as a sha256 of the normalized text, never the text), the reply must match an
            entry newer than the change's last user approval, or the patch is refused. Without that
            log the approval is recorded with "unverified": true and a warning is printed.
            A move from tests-first to build is refused when git shows files changed since the
            tests-first stage outside testing.test_globs, the plan folder, and AGENTS/ (tooling, settings, and run state); without
            git the move is recorded with "unchecked" and a warning.
index       Rebuilds <workspace>/<plan_folder>/INDEX.md in full from every state.json.

Exit code 0 on success; 1 with {"ok": false, "error": "..."} on any error. Nothing is written
outside <workspace>/<plan_folder>/ and <workspace>/AGENTS/settings.json.
"""

import argparse
import datetime
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_PATH = os.path.join(SKILL_DIR, "assets", "settings.schema.json")
STAGES = ["plan", "accept", "tests-first", "build", "test", "review", "human-review", "deploy", "done", "dropped"]
SIZES = ["Small", "Medium", "Large"]
LISTS = ["approvals", "receipts", "wi", "declined", "test_runs", "ephemeral", "builds"]
SECRET_PATTERNS = [r"-----BEGIN [A-Z ]*PRIVATE KEY", r"\bghp_[A-Za-z0-9]{20,}", r"\bgithub_pat_", r"\bxox[abprs]-",
                   r"\bAKIA[0-9A-Z]{16}\b", r"\bsk-[A-Za-z0-9_-]{20,}", r"://[^/\s:@]+:[^/\s@]+@"]


class Fail(Exception):
    pass


def out(obj, code=0):
    sys.stdout.write(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")
    sys.exit(code)


def now_iso(override=None):
    if override:
        return override
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        raise Fail(f"{path} is not valid JSON: {e}")


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


# workspace and settings -------------------------------------------------------------------

def find_root(cwd):
    d = os.path.abspath(cwd)
    while True:
        if os.path.isfile(os.path.join(d, "AGENTS.md")) or os.path.isfile(os.path.join(d, "CLAUDE.md")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            raise Fail(f"no AGENTS.md or CLAUDE.md at or above {cwd}; pass --workspace")
        d = parent


def schema():
    s = read_json(SCHEMA_PATH)
    if s is None:
        raise Fail(f"missing {SCHEMA_PATH}")
    return s


def is_leaf(node):
    return isinstance(node, dict) and "type" in node and "default" in node


def defaults(node):
    if is_leaf(node):
        return json.loads(json.dumps(node["default"]))
    return {k: defaults(v) for k, v in node.items() if not k.startswith("$")}


TYPES = {"string": str, "integer": int, "boolean": bool, "array": list, "object": dict}


def validate(values, node, path=""):
    errors = []
    if not isinstance(values, dict):
        return [f"{path or 'settings'} must be an object"]
    for k, v in values.items():
        p = f"{path}.{k}" if path else k
        if k not in node or k.startswith("$"):
            errors.append(f"unknown key {p}")
            continue
        sub = node[k]
        if is_leaf(sub):
            t = sub["type"]
            if t == "enum":
                if v not in sub.get("options", []):
                    errors.append(f"{p} must be one of {sub.get('options')}")
            elif t == "integer" and (isinstance(v, bool) or not isinstance(v, int)):
                errors.append(f"{p} must be an integer")
            elif t != "integer" and not isinstance(v, TYPES[t]):
                errors.append(f"{p} must be {t}")
        else:
            errors.extend(validate(v, sub, p))
    return errors


def secrets_in(value):
    text = json.dumps(value, ensure_ascii=False)
    return [p for p in SECRET_PATTERNS if re.search(p, text)]


def merge(base, over):
    if not isinstance(base, dict) or not isinstance(over, dict):
        return json.loads(json.dumps(over))
    result = dict(base)
    for k, v in over.items():
        result[k] = merge(base.get(k), v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return result


SETTINGS_FILE = "settings.json"  # the workspace's shared AGENTS/settings.json, one top-level key per tool
SETTINGS_KEY = "howtoai-dev"     # this plugin's key in it
STATE_FOLDER = "state"           # AGENTS/state/: run records the tools write for themselves, left out of Git
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def agents_dir(ws):
    """The workspace's AGENTS/ folder in the case it exists in (Agents/ counts), else <ws>/AGENTS."""
    try:
        for name in os.listdir(ws):
            if name.lower() == "agents" and os.path.isdir(os.path.join(ws, name)):
                return os.path.join(ws, name)
    except OSError:
        pass
    return os.path.join(ws, "AGENTS")


def agents_file(ws, *parts):
    """A file the user reviews, at the AGENTS/ root: settings.json, install.md, lessons.md, workbooks/,
    deploy-targets.json."""
    return os.path.join(agents_dir(ws), *parts)


def state_dir(ws, *parts):
    """<workspace>/AGENTS/state/<parts>: run records (deploy approvals, deploy log, cache), left out of Git."""
    return os.path.join(agents_dir(ws), STATE_FOLDER, *parts)


def project_file(ws):
    return agents_file(ws, SETTINGS_FILE)


def read_project(ws):
    """This plugin's part of the shared AGENTS/settings.json, or None when the file or the key is missing."""
    data = read_json(project_file(ws))
    if data is None:
        return None
    if not isinstance(data, dict):
        raise Fail(f"{project_file(ws)} must hold a JSON object with one key per tool")
    return data.get(SETTINGS_KEY)


def is_configured(ws):
    return bool(ws) and read_project(ws) is not None


def user_file(arg):
    return arg or os.path.join(os.path.expanduser("~"), ".claude", "howtoai", "dev-settings.json")


def load_settings(ws, user_arg=None):
    sch = schema()
    merged = defaults(sch)
    sources = {k: "default" for k in merged}
    for label, path in (("user", user_file(user_arg)), ("project", project_file(ws) if ws else None)):
        if not path:
            continue
        data = read_json(path) if label == "user" else read_project(ws)
        if data is None:
            continue
        errs = validate(data, sch)
        if errs:
            raise Fail(f"{label} settings {path}: " + "; ".join(errs))
        merged = merge(merged, data)
        for k in data:
            sources[k] = label
    return merged, sources


# plan folder ------------------------------------------------------------------------------

def plans_dir(ws, user_arg=None):
    settings, _ = load_settings(ws, user_arg)
    name = settings["plan_folder"]
    if not re.fullmatch(r"[A-Za-z0-9._-]+", name) or name in (".", ".."):
        raise Fail(f"plan_folder must be a plain folder name, got {name!r}")
    return os.path.join(ws, name)


def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:48].rstrip("-") or "change"


def change_dirs(pdir):
    if not os.path.isdir(pdir):
        return []
    return sorted(os.path.join(pdir, d) for d in os.listdir(pdir)
                  if os.path.isfile(os.path.join(pdir, d, "state.json")))


def rebuild_index(ws, user_arg=None):
    pdir = plans_dir(ws, user_arg)
    rows = []
    for d in change_dirs(pdir):
        st = read_json(os.path.join(d, "state.json")) or {}
        rows.append(st)
    rows.sort(key=lambda r: r.get("updated", ""), reverse=True)
    lines = ["# Dev plans", "",
             "Generated by `dev-core` from each change's `state.json`; rebuilt on every state change. Do not edit.", "",
             "| Change | Title | Stage | Size | WI | Updated |", "| --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        cid = r.get("id", "?")
        title = str(r.get("title", "")).replace("|", "\\|")
        lines.append(f"| [{cid}]({cid}/) | {title} | {r.get('stage', '')} | {r.get('size') or 'not sized'} "
                     f"| {len(r.get('wi', []))} | {str(r.get('updated', ''))[:10]} |")
    if not rows:
        lines.append("| none yet | | | | | |")
    os.makedirs(pdir, exist_ok=True)
    path = os.path.join(pdir, "INDEX.md")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    return path, len(rows)


def new_change(ws, title, slug, date, now, user_arg=None):
    if date:
        try:
            datetime.date.fromisoformat(date)
        except ValueError:
            raise Fail(f"--date must be YYYY-MM-DD, got {date!r}")
    else:
        date = datetime.date.today().isoformat()
    base = f"{date}-{slugify(slug or title)}"
    pdir = plans_dir(ws, user_arg)
    cid, n = base, 1
    while os.path.exists(os.path.join(pdir, cid)):
        n += 1
        cid = f"{base}-{n}"
    ts = now_iso(now)
    state = {"id": cid, "title": title, "created": ts, "updated": ts, "stage": "plan", "size": None,
             "wi": [], "loops": {}, "approvals": [], "receipts": [], "declined": [],
             "test_runs": [], "ephemeral": [], "builds": [],
             "history": [{"at": ts, "stage": "plan"}]}
    cdir = os.path.join(pdir, cid)
    write_json(os.path.join(cdir, "state.json"), state)
    index, count = rebuild_index(ws, user_arg)
    return {"ok": True, "id": cid, "change_dir": cdir, "state": os.path.join(cdir, "state.json"),
            "index": index, "changes": count}


REPLY_LOG = os.path.join("skills", "dev-core", "state", "replies.jsonl")  # inside the plugin, as shown to users


def reply_log(ws=None):
    """The dev-reply-log hook's log, in this skill's own state/ folder (shared by every workspace that uses
    this copy of the plugin); ws is kept for callers and not used."""
    return os.environ.get("HOWTOAI_DEV_REPLY_LOG") or os.path.join(SKILL_DIR, "state", "replies.jsonl")


def reply_hash(text):
    """sha256 of a reply, normalized the same way by the dev-reply-log hook: NFC, whitespace
    collapsed, case folded."""
    norm = " ".join(unicodedata.normalize("NFC", str(text)).split()).casefold()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def _when(value):
    try:
        t = datetime.datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return t if t.tzinfo else t.astimezone()


def check_user_approval(entry, state, ws):
    """An approval in the user's name carries the user's reply; with the reply log, it must match
    a logged prompt newer than the change's last user approval (or its creation)."""
    reply = entry.get("reply")
    if not isinstance(reply, str) or not reply.strip():
        raise Fail('an approval "by": "user" needs "reply", the user\'s reply word for word: '
                   "ask, wait for the answer, then record it")
    log = reply_log(ws) if ws else None
    if not log or not os.path.isfile(log):
        entry["unverified"] = True
        entry["at"] = now_iso()  # the real clock here too
        return entry
    entry.pop("unverified", None)
    created = _when(state.get("created"))
    used = [t for t in (_when(a.get("at")) for a in state.get("approvals", []) if a.get("by") == "user") if t]
    since = max(used, default=None)

    def fresh(at):
        # a reply comes after the change was made (same second allowed) and strictly after the
        # last user approval, whose own reply came before it was stamped
        return (created is None or at >= created) and (since is None or at > since)
    want = reply_hash(reply)
    with open(log, encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            at = _when(rec.get("at")) if isinstance(rec, dict) else None
            if at:
                at = at.replace(microsecond=0)  # approvals are stamped to the second
            if rec.get("sha256") == want and at and fresh(at):
                entry["at"] = now_iso()  # the real clock: a patch's "at" or --now never backdates it
                return entry
    raise Fail('no user reply since the last user approval matches "reply": record an approval '
               "in the user's name only after the user answered, quoting that answer")


def tests_first_changes(state, ws, user_arg):
    """Files git shows changed since the tests-first stage outside the test globs, the plan folder, and
    AGENTS/; None when git cannot tell."""
    since = _when(next((h["at"] for h in reversed(state.get("history", [])) if h.get("stage") == "tests-first"), ""))
    git = ["git", "-c", "core.quotepath=off", "-c", f"safe.directory={ws}", "-C", ws]
    try:
        top = subprocess.run(git + ["rev-parse", "--show-toplevel"], capture_output=True, text=True, encoding="utf-8")
        status = subprocess.run(git + ["status", "--porcelain", "-z", "--untracked-files=all"],
                                capture_output=True, text=True, encoding="utf-8")
    except OSError:
        return None
    if since is None or top.returncode or status.returncode:
        return None
    settings, _ = load_settings(ws, user_arg)
    keep = ("AGENTS/", settings["plan_folder"] + "/")
    globs = settings["testing"]["test_globs"]
    found, parts = [], iter(status.stdout.split("\0"))
    for part in parts:
        if len(part) < 4:
            continue
        if "R" in part[:2] or "C" in part[:2]:
            next(parts, None)  # a rename or copy is followed by its old path
        path = os.path.join(top.stdout.strip(), part[3:])
        rel = os.path.relpath(path, ws).replace(os.sep, "/")
        if rel.startswith("../") or rel.startswith(keep) or rel.lower().startswith("agents/") or any(
                fnmatch.fnmatch(rel, g) or fnmatch.fnmatch("/" + rel, g) for g in globs):
            continue
        if not os.path.exists(path) or os.path.getmtime(path) > since.timestamp():
            found.append(rel)
    return found


def check_plan_cover(entry, state):
    """An approval "by": "plan" (a path the approved work item names) cites the user's plan approval."""
    plans = [a for a in state.get("approvals", []) if a.get("by") == "user" and a.get("what") == "plan"]
    if not plans:
        raise Fail('an approval "by": "plan" needs the user\'s plan approval in this change; '
                   'without it, ask the user and record "by": "user" with the reply')
    entry["covers"] = "plan approval at " + str(plans[-1].get("at"))
    return entry


def apply_patch(state, patch, ts, ws=None, warnings=None, user_arg=None):
    warnings = [] if warnings is None else warnings
    if not isinstance(patch, dict):
        raise Fail("--patch must be a JSON object")
    allowed = {"stage", "size", "title", "plan_item", "append", "increment"}
    extra = set(patch) - allowed
    if extra:
        raise Fail(f"unknown patch keys: {sorted(extra)}")
    if "plan_item" in patch:
        item = patch["plan_item"]
        if not isinstance(item, dict) or not str(item.get("tracker_key", "")).strip():
            raise Fail("plan_item must be an object with a tracker_key")
        if secrets_in(item):
            raise Fail("plan_item looks like it holds a secret; state files never store secrets")
        state["plan_item"] = {**item, "at": ts}
    if "stage" in patch:
        if patch["stage"] not in STAGES:
            raise Fail(f"stage must be one of {STAGES}")
        if patch["stage"] != state.get("stage"):
            move = {"at": ts, "stage": patch["stage"]}
            if state.get("stage") == "tests-first" and patch["stage"] == "build" and ws:
                changed = tests_first_changes(state, ws, user_arg)
                if changed is None:
                    move["unchecked"] = "no git history to show what changed at stage tests-first"
                    warnings.append("the move to build is unchecked: git cannot show what changed at stage tests-first")
                elif changed:
                    raise Fail("files outside testing.test_globs changed at stage tests-first: "
                               + "; ".join(changed[:10]) + ". Only tests, test data, and the change folder change "
                               "before the red check; revert them or ask the user")
            state["stage"] = patch["stage"]
            state.setdefault("history", []).append(move)
    if "size" in patch:
        if patch["size"] not in SIZES:
            raise Fail(f"size must be one of {SIZES}")
        state["size"] = patch["size"]
    if "title" in patch:
        if not isinstance(patch["title"], str) or not patch["title"].strip():
            raise Fail("title must be a non-empty string")
        state["title"] = patch["title"]
    for key, item in (patch.get("append") or {}).items():
        if key not in LISTS:
            raise Fail(f"append key must be one of {LISTS}")
        if not isinstance(item, dict):
            raise Fail(f"append.{key} must be an object")
        if secrets_in(item):
            raise Fail(f"append.{key} looks like it holds a secret; state files never store secrets")
        entry = dict(item)
        if key == "approvals" and entry.get("by") == "user":
            entry.pop("at", None)
            entry = check_user_approval(entry, state, ws)
            if entry.get("unverified"):
                warnings.append(f"approval {entry.get('what')!r} is recorded unverified: no reply log to check the "
                                "reply against; show it to the user in your next message")
        elif key == "approvals" and entry.get("by") == "plan":
            entry = check_plan_cover(entry, state)
        entry.setdefault("at", ts)
        state.setdefault(key, []).append(entry)
    for key, by in (patch.get("increment") or {}).items():
        if not re.fullmatch(r"[a-z][a-z0-9-]*", key) or isinstance(by, bool) or not isinstance(by, int):
            raise Fail("increment takes {name: integer} with lowercase names")
        loops = state.setdefault("loops", {})
        loops[key] = loops.get(key, 0) + by
    state["updated"] = ts
    return state


def workspace_of(change_dir):
    pdir = os.path.dirname(os.path.abspath(change_dir))
    return os.path.dirname(pdir)


# main -------------------------------------------------------------------------------------

def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(prog="devcore")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("root"); p.add_argument("--cwd", default=os.getcwd())
    p = sub.add_parser("settings"); p.add_argument("--workspace"); p.add_argument("--user-file")
    p = sub.add_parser("setup"); p.add_argument("--workspace", required=True); p.add_argument("--user-file")
    p.add_argument("--values"); p.add_argument("--values-file"); p.add_argument("--write", action="store_true")
    p.add_argument("--scope", choices=["project", "user"], default="project")
    p = sub.add_parser("new-change"); p.add_argument("--workspace", required=True)
    p.add_argument("--title", required=True); p.add_argument("--slug"); p.add_argument("--date")
    p.add_argument("--now"); p.add_argument("--user-file")
    p = sub.add_parser("state"); p.add_argument("change_dir"); p.add_argument("--patch"); p.add_argument("--now")
    p.add_argument("--user-file")
    p = sub.add_parser("index"); p.add_argument("--workspace", required=True); p.add_argument("--user-file")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "root":
            out({"ok": True, "workspace": find_root(a.cwd)})
        if a.cmd == "settings":
            ws = os.path.abspath(a.workspace) if a.workspace else None
            merged, sources = load_settings(ws, a.user_file)
            out({"ok": True, "workspace": ws, "configured": is_configured(ws),
                 "settings": merged, "sources": sources})
        if a.cmd == "setup":
            ws = os.path.abspath(a.workspace)
            if (a.values is None) == (a.values_file is None):
                raise Fail("setup needs exactly one of --values or --values-file")
            raw, source = a.values, "--values"
            if a.values_file is not None:
                source = "--values-file"
                try:
                    with open(a.values_file, encoding="utf-8-sig") as f:
                        raw = f.read()
                except (OSError, UnicodeDecodeError) as e:
                    raise Fail(f"--values-file cannot be read: {e}")
            try:
                values = json.loads(raw)
            except json.JSONDecodeError as e:
                raise Fail(f"{source} is not valid JSON: {e}")
            errs = validate(values, schema())
            if errs:
                raise Fail("; ".join(errs))
            hits = secrets_in(values)
            if hits:
                raise Fail("values look like they hold a secret (a token, key, or password in a URL); "
                           "settings never store secrets")
            path = user_file(a.user_file) if a.scope == "user" else project_file(ws)
            whole = read_json(path) or {}
            if not isinstance(whole, dict):
                raise Fail(f"{path} must hold a JSON object")
            existing = whole if a.scope == "user" else (whole.get(SETTINGS_KEY) or {})
            result = merge(existing, values)
            effective = merge(load_settings(ws, a.user_file)[0], values)
            if effective["plan"]["publish"] == "tracker" and effective["tracker"]["kind"] == "markdown":
                raise Fail("plan.publish tracker needs tracker.kind jira, github, or azure-devops; "
                           "with Markdown work items, use auto, artifact, html-file, or markdown")
            if a.write:
                # project scope: only this plugin's key changes; other tools' keys in the shared file stay
                write_json(path, result if a.scope == "user" else dict(whole, **{SETTINGS_KEY: result}))
            out({"ok": True, "written": a.write, "scope": a.scope, "path": path,
                 "key": None if a.scope == "user" else SETTINGS_KEY, "settings": result})
        if a.cmd == "new-change":
            ws = os.path.abspath(a.workspace)
            out(new_change(ws, a.title, a.slug, a.date, a.now, a.user_file))
        if a.cmd == "state":
            path = os.path.join(a.change_dir, "state.json")
            state = read_json(path)
            if state is None:
                raise Fail(f"no state.json in {a.change_dir}")
            if a.patch:
                try:
                    patch = json.loads(a.patch)
                except json.JSONDecodeError as e:
                    raise Fail(f"--patch is not valid JSON: {e}")
                warnings = []
                state = apply_patch(state, patch, now_iso(a.now), workspace_of(a.change_dir), warnings, a.user_file)
                write_json(path, state)
                rebuild_index(workspace_of(a.change_dir), a.user_file)
                if warnings:
                    out({"ok": True, "state": state, "warnings": warnings})
            out({"ok": True, "state": state})
        if a.cmd == "index":
            path, count = rebuild_index(os.path.abspath(a.workspace), a.user_file)
            out({"ok": True, "index": path, "changes": count})
    except Fail as e:
        out({"ok": False, "error": str(e)}, 1)


if __name__ == "__main__":
    main()
