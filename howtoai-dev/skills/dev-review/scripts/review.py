"""review - the diff and the receipt check for dev-review.

Usage (Python 3, standard library only; every command prints one JSON object):
  py -3 -I -B review.py diff     CHANGE_DIR --round N [--since-build B] [--user-file F]
  py -3 -I -B review.py receipts CHANGE_DIR --round N [--user-file F]

diff      Writes <change>/raw/review-<N>/diff.patch and changed.json for the round's reviewers.
          Round 1 (no --since-build) compares HEAD with the working tree as `git add -A` would
          stage it, so uncommitted tests and code are both included; with --since-build B it
          compares build B's snapshot (raw/build-B/snapshot.json, a fix build) with the working
          tree, so a re-review sees only the fix. The plan folder, AGENTS/ (tooling and howtoai state), and TESTING.md are
          left out, as in dev-build. changed.json holds {"base", "tree", "files": {path:
          [[start, end], ...]}, "hunks"}; findings.py tally --changed reads it. Nothing is
          staged or committed.
receipts  Checks that every stage the change went through (plan, tests-first, build, test, in
          state.json's history) has a workbook receipt for that stage, and writes
          <change>/raw/review-<N>/process.md: one Major finding per stage without one, in the
          reviewer table shape findings.py collect reads (ID R<N>-G<n>), or "No findings".

Exit code 0 when the command ran; 1 with {"ok": false, "error": "..."} on any error.
Writes only <change>/raw/review-<N>/ and git objects.
"""

import argparse
import importlib.util
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.abspath(os.path.join(HERE, "..", "..", "dev-build", "scripts", "build.py"))
RECEIPT_STAGES = ("plan", "tests-first", "build", "test")


class Fail(Exception):
    pass


def out(obj, code=0):
    sys.stdout.write(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")
    sys.exit(code)


def load_build():
    sys.dont_write_bytecode = True  # no __pycache__ in the plugin folders, even without -B
    if not os.path.isfile(BUILD):
        raise Fail(f"dev-build's build.py is missing at {BUILD}")
    spec = importlib.util.spec_from_file_location("devbuild", BUILD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def raw_dir(cdir, n):
    path = os.path.join(cdir, "raw", f"review-{n}")
    os.makedirs(path, exist_ok=True)
    return path


def cmd_diff(a, b):
    try:
        core, cdir, ws, settings, state = b.context(a.change_dir, a.user_file)
        now = b.tree_now(ws, settings)
        if a.since_build:
            snap = b.snapshot(cdir, a.since_build)
            if snap.get("route") != "fix":
                raise Fail(f"build {a.since_build} is not a Fix-route build; a re-review starts from a fix")
            base = snap["tree"]
        else:
            base = b.head_trees(ws, settings)
        hunks = b.diff_hunks(ws, settings, base, now)
        patch = b.patch_text(ws, settings, base, now)
    except b.Fail as e:
        raise Fail(str(e))
    files = {}
    for h in hunks:
        hid = h["id"][len(h["path"]) + 1:]
        if hid in ("binary", "repository-added", "repository-removed"):
            files.setdefault(h["path"], [])
            continue
        if hid.endswith("d"):
            line = int(hid[:-1])
            files.setdefault(h["path"], []).append([line, line + 1])
        else:
            lo, hi = (int(x) for x in hid.split("-"))
            files.setdefault(h["path"], []).append([lo, hi])
    rd = raw_dir(cdir, a.round)
    with open(os.path.join(rd, "diff.patch"), "w", encoding="utf-8", newline="\n") as f:
        f.write(patch)
    data = {"round": a.round, "base": base, "tree": now, "since_build": a.since_build, "files": files,
            "hunks": [h["id"] for h in hunks]}
    with open(os.path.join(rd, "changed.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")
    return {"ok": True, "patch": os.path.join(rd, "diff.patch").replace("\\", "/"),
            "changed": os.path.join(rd, "changed.json").replace("\\", "/"), "files": sorted(files),
            "hunks": len(hunks), "empty": not hunks}


def cmd_receipts(a, b):
    try:
        core, cdir, ws, settings, state = b.context(a.change_dir, a.user_file)
    except b.Fail as e:
        raise Fail(str(e))
    seen = [h for h in state.get("history") or [] if h.get("stage") in RECEIPT_STAGES]
    have = {r.get("stage") for r in state.get("receipts") or []}
    missing, done = [], set()
    for h in seen:
        st = h["stage"]
        if st in done:
            continue
        done.add(st)
        if st not in have:
            missing.append(h)
    rows = []
    for i, h in enumerate(missing, 1):
        rows.append(f"| R{a.round}-G{i} | Major | Process | state.json | \"history: {h['stage']} at {h.get('at', '?')}\" | "
                    f"Stage {h['stage']} ran without a workbook receipt, so its technology rules are unrecorded. | "
                    f"confirmed: no receipt with stage {h['stage']} in state.json | Rerun the stage's workbook resolve and record the receipt, or record why no technology applied. | ASK |")
    path = os.path.join(raw_dir(cdir, a.round), "process.md")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        if rows:
            f.write("| ID | Impact | Area | Location | Quote | Finding | Mark | Proposed fix | Handling |\n"
                    "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n" + "\n".join(rows) + "\n")
        else:
            f.write("No findings\n")
    return {"ok": True, "file": path.replace("\\", "/"), "stages": sorted(done), "missing": [h["stage"] for h in missing]}


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="dev-review diff and receipt check")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("diff", "receipts"):
        p = sub.add_parser(name)
        p.add_argument("change_dir")
        p.add_argument("--round", type=int, required=True)
        p.add_argument("--user-file")
        if name == "diff":
            p.add_argument("--since-build", type=int)
    a = ap.parse_args(argv)
    try:
        if a.round < 1:
            raise Fail("--round must be 1 or more")
        b = load_build()
        result = (cmd_diff if a.cmd == "diff" else cmd_receipts)(a, b)
    except Fail as e:
        out({"ok": False, "error": str(e)}, 1)
    out(result)


if __name__ == "__main__":
    main()
