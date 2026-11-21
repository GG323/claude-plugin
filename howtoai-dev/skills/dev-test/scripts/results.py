"""Read test result files (TRX and JUnit XML) into counts. Standard library only.

Usage:
  py -3 -I results.py parse <file or glob> ...
  py -3 -I results.py merge --first <file or glob> ... [--rerun <file or glob> ...] ...

parse  Counts passed, failed, and skipped tests and lists each failure's first message line.
merge  Combines a first run with its reruns of the failed tests. A test that failed first and
       passed in any rerun is flaky; one that failed in every run is failed. Each --rerun flag
       starts one rerun group.

Prints one JSON object: {"ok", "passed", "failed", "skipped", "flaky", "total", "duration_s",
"failed_tests": [{"name", "message"}], "flaky_tests": [{"name", "reruns"}], "files": [...]}.
Messages are cut to one line of at most 200 characters, and text that looks like a secret is
replaced with [redacted].
"""

import argparse
import glob
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

SECRET = re.compile(r"(password|pwd|secret|token|apikey|api_key)\s*[=:]\s*[^;\s\"']+|\b(sk|ghp|xox[abprs])[-_][A-Za-z0-9_-]{10,}", re.I)


class Fail(Exception):
    pass


def out(obj, code=0):
    print(json.dumps(obj, ensure_ascii=False, indent=1))
    sys.exit(code)


def expand(patterns):
    files = []
    for p in patterns:
        hits = sorted(glob.glob(p, recursive=True))
        if not hits and os.path.isfile(p):
            hits = [p]
        files.extend(h for h in hits if h not in files)
    return files


def clean(msg):
    line = (msg or "").strip().splitlines()[0] if (msg or "").strip() else ""
    return SECRET.sub("[redacted]", line)[:200]


def local(tag):
    return tag.rsplit("}", 1)[-1]


def read_trx(root):
    tests = {}
    for r in root.iter():
        if local(r.tag) != "UnitTestResult":
            continue
        name = r.get("testName", "?")
        outcome = (r.get("outcome") or "").lower()
        status = "passed" if outcome == "passed" else "failed" if outcome in ("failed", "error", "timeout", "aborted") else "skipped"
        msg = ""
        for m in r.iter():
            if local(m.tag) == "Message" and m.text:
                msg = m.text
                break
        tests[name] = {"status": status, "message": clean(msg), "duration": parse_duration(r.get("duration"))}
    return tests


def parse_duration(d):
    if not d:
        return 0.0
    m = re.match(r"(\d+):(\d+):([\d.]+)", d)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 0.0


def read_junit(root):
    tests = {}
    for c in root.iter("testcase"):
        name = ".".join(x for x in (c.get("classname"), c.get("name")) if x) or "?"
        status, msg = "passed", ""
        for child in c:
            t = local(child.tag)
            if t in ("failure", "error"):
                status, msg = "failed", child.get("message") or child.text or ""
            elif t == "skipped":
                status = "skipped"
        try:
            dur = float(c.get("time") or 0)
        except ValueError:
            dur = 0.0
        tests[name] = {"status": status, "message": clean(msg), "duration": dur}
    return tests


def read_file(path):
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as e:
        raise Fail(f"cannot read {path}: {e}")
    tag = local(root.tag)
    if tag == "TestRun":
        return read_trx(root)
    if tag in ("testsuites", "testsuite"):
        return read_junit(root)
    raise Fail(f"{path}: not a TRX or JUnit XML file (root <{tag}>)")


def read_group(patterns):
    files = expand(patterns)
    if not files:
        raise Fail(f"no result files match {patterns}")
    tests = {}
    for f in files:
        tests.update(read_file(f))
    return tests, files


def summary(tests, files, flaky=None):
    flaky = flaky or {}
    counts = {"passed": 0, "failed": 0, "skipped": 0}
    for t in tests.values():
        counts[t["status"]] += 1
    return {"ok": True, **counts, "flaky": len(flaky), "total": len(tests),
            "duration_s": round(sum(t["duration"] for t in tests.values()), 2),
            "failed_tests": [{"name": n, "message": t["message"]} for n, t in sorted(tests.items()) if t["status"] == "failed"],
            "flaky_tests": [{"name": n, "reruns": r} for n, r in sorted(flaky.items())],
            "files": [f.replace("\\", "/") for f in files]}


def merge(first, reruns):
    tests, files = read_group(first)
    flaky = {}
    for n, group in enumerate(reruns, 1):
        again, more = read_group(group)
        files += more
        for name, t in again.items():
            if name in tests and tests[name]["status"] == "failed" and name not in flaky:
                if t["status"] == "passed":
                    flaky[name] = n
                    tests[name] = dict(t, status="passed")
    return summary(tests, files, flaky)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Read TRX and JUnit XML test results.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("parse")
    p.add_argument("paths", nargs="+")
    m = sub.add_parser("merge")
    m.add_argument("--first", nargs="+", required=True)
    m.add_argument("--rerun", nargs="+", action="append", default=[])
    a = ap.parse_args(argv)
    try:
        if a.cmd == "parse":
            tests, files = read_group(a.paths)
            out(summary(tests, files))
        out(merge(a.first, a.rerun))
    except Fail as e:
        out({"ok": False, "error": str(e)}, 1)


if __name__ == "__main__":
    main()
