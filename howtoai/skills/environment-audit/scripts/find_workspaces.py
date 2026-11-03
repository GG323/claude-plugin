"""Finds the Claude workspaces on this computer for environment-audit.

Claude Code keeps one session-history folder per working folder under
<global folder>/projects/. Each session file (*.jsonl) records the working
folder as "cwd". This script reads the newest session file of each history
folder, keeps the working folders that still exist, and prints them as JSON
with the skipped ones and the reason. Writes nothing.

Usage:
  py -3 find_workspaces.py [--global-dir <folder>]
"""

import argparse
import datetime
import fnmatch
import glob
import json
import os
import re
import sys
import tempfile

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCLUSIONS = os.path.join(SKILL_DIR, "state", "exclusions.md")
MAX_LINES = 500  # "cwd" appears in the first entries of a session file

# Throwaway folders the Claude apps create for one-off chats; never workspaces.
SCRATCH_MARKERS = ("/claude/scratch-workspaces/", "/claude-scratch/")


def default_global_dir():
    return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")


def session_cwd(history_dir):
    """The working folder of the newest session in a history folder."""
    sessions = sorted(glob.glob(os.path.join(history_dir, "*.jsonl")), key=os.path.getmtime, reverse=True)
    for path in sessions:
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                for n, line in enumerate(f):
                    if n >= MAX_LINES:
                        break
                    if '"cwd"' not in line:
                        continue
                    try:
                        cwd = json.loads(line).get("cwd")
                    except ValueError:
                        continue
                    if cwd:
                        return cwd, os.path.getmtime(path)
        except OSError:
            continue
    return None, None


def exclusion_patterns():
    if not os.path.isfile(EXCLUSIONS):
        return []
    with open(EXCLUSIONS, encoding="utf-8") as f:
        text = re.sub(r"^\s*(```|~~~).*?^\s*\1\s*$", "", f.read(), flags=re.M | re.S)
    return [m.group(1) for m in re.finditer(r"^\s*-\s+`([^`]+)`", text, re.M)]


def norm(path):
    return os.path.normpath(path).replace(os.sep, "/")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Find the Claude workspaces on this computer.")
    parser.add_argument("--global-dir", default=default_global_dir(), help="global Claude folder")
    args = parser.parse_args()
    global_dir = os.path.abspath(os.path.expanduser(args.global_dir))
    projects = os.path.join(global_dir, "projects")
    if not os.path.isdir(projects):
        print(json.dumps({"error": "No session history folder: %s" % norm(projects)}))
        sys.exit(2)

    home = os.path.realpath(os.path.expanduser("~"))
    temp = os.path.realpath(tempfile.gettempdir())
    patterns = exclusion_patterns()
    workspaces, skipped, seen = [], [], set()
    for name in sorted(os.listdir(projects)):
        history = os.path.join(projects, name)
        if not os.path.isdir(history):
            continue
        cwd, mtime = session_cwd(history)
        if not cwd:
            skipped.append({"history": name, "path": None, "reason": "no session file names a working folder"})
            continue
        real = os.path.realpath(cwd)
        key = os.path.normcase(real)
        if key in seen:
            continue
        seen.add(key)
        shown = norm(real)
        reason = None
        if any(m in shown.lower() + "/" for m in SCRATCH_MARKERS) or os.path.normcase(real).startswith(os.path.normcase(temp) + os.sep):
            reason = "scratch or temporary folder"
        elif os.path.normcase(real) in (os.path.normcase(home), os.path.normcase(os.path.realpath(global_dir))):
            reason = "home or global folder, not a workspace"
        elif any(fnmatch.fnmatch(shown, p) or fnmatch.fnmatch(shown + "/", p) for p in patterns):
            reason = "listed in state/exclusions.md"
        elif not os.path.isdir(real):
            reason = "folder no longer exists"
        if reason:
            skipped.append({"history": name, "path": shown, "reason": reason})
            continue
        workspaces.append({
            "name": os.path.basename(real),
            "path": shown,
            "last_used": datetime.date.fromtimestamp(mtime).isoformat(),
            "has_agents_md": os.path.isfile(os.path.join(real, "AGENTS.md")),
            "has_claude_md": os.path.isfile(os.path.join(real, "CLAUDE.md")),
            "has_claude_dir": os.path.isdir(os.path.join(real, ".claude")),
        })
    workspaces.sort(key=lambda w: w["name"].lower())
    print(json.dumps({"global": norm(global_dir), "workspaces": workspaces, "skipped": skipped},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
