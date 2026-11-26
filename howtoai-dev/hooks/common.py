"""Shared helpers for the howtoai-dev hooks. Standard library only.

A hook reads Claude Code's PreToolUse input from stdin and prints at most one JSON decision. It
never exits with code 2 and never raises: any error ends silently (exit 0, no output), so a broken
hook never blocks work. Tests set HOWTOAI_DEV_USER_FILE so no real user settings are read.
"""

import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEVCORE = os.path.join(HERE, "..", "skills", "dev-core", "scripts", "devcore.py")
ACTIVE = ("tests-first", "build", "test")


def read_input():
    try:
        data = json.loads(sys.stdin.read() or "{}")
        return data if isinstance(data, dict) else {}
    except ValueError:
        return {}


def devcore():
    sys.dont_write_bytecode = True  # no __pycache__ in the plugin's dev-core folder, even without -B
    spec = importlib.util.spec_from_file_location("devcore", os.path.abspath(DEVCORE))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def workspace(start):
    """The nearest folder at or above start with AGENTS.md or CLAUDE.md, or None."""
    d = os.path.abspath(start)
    if not os.path.isdir(d):
        d = os.path.dirname(d)
    while True:
        if os.path.isfile(os.path.join(d, "AGENTS.md")) or os.path.isfile(os.path.join(d, "CLAUDE.md")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def settings(dc, ws):
    merged, _ = dc.load_settings(ws, os.environ.get("HOWTOAI_DEV_USER_FILE") or None)
    return merged


def configured(dc, ws):
    """True when the workspace's AGENTS/settings.json has a "howtoai-dev" key."""
    try:
        return dc.is_configured(ws)
    except Exception:
        return False


def changes(dc, ws):
    """Every change's state, newest update first."""
    try:
        pdir = dc.plans_dir(ws, os.environ.get("HOWTOAI_DEV_USER_FILE") or None)
    except Exception:
        return []
    states = []
    for d in dc.change_dirs(pdir):
        try:
            with open(os.path.join(d, "state.json"), encoding="utf-8") as f:
                st = json.load(f)
            st["_dir"] = d
            states.append(st)
        except (OSError, ValueError):
            continue
    return sorted(states, key=lambda s: s.get("updated", ""), reverse=True)


def active_change(dc, ws):
    for st in changes(dc, ws):
        if st.get("stage") in ACTIVE:
            return st
    return None


def rel(ws, path):
    try:
        r = os.path.relpath(os.path.abspath(path), ws)
    except ValueError:
        return None
    r = r.replace("\\", "/")
    return None if r.startswith("../") or r == ".." else r


def decide(decision, reason, context=None):
    """deny or ask: a permission decision. warn: context for Claude only, no decision, so the
    normal permission flow still runs (an allow would skip the user's permission prompt)."""
    out = {"hookEventName": "PreToolUse"}
    if decision in ("deny", "ask"):
        out["permissionDecision"] = decision
        out["permissionDecisionReason"] = reason
    else:
        out["additionalContext"] = reason
    if context:
        out["additionalContext"] = (out.get("additionalContext", "") + " " + context).strip()
    print(json.dumps({"hookSpecificOutput": out}))


def run(check):
    """Call check(data) -> None or (decision, reason); swallow every error."""
    try:
        data = read_input()
        result = check(data)
        if result:
            decide(*result)
    except Exception:
        pass
    sys.exit(0)
