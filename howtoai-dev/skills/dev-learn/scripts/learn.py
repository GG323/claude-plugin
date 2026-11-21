"""learn - collect, lessons log, and record check for dev-learn.

Usage (Python 3, standard library only; every command prints one JSON object):
  py -3 -I -B learn.py start   CHANGE_DIR --round N
  py -3 -I -B learn.py collect CHANGE_DIR --round N --lessons LESSONS [--plans PLAN_FOLDER]
  py -3 -I -B learn.py lesson add LESSONS --stage S --change ID --finding RID --where W
                                 --text T --fix F [--date YYYY-MM-DD]
  py -3 -I -B learn.py lesson repeat LESSONS --id DL-001
  py -3 -I -B learn.py lesson remove LESSONS --id DL-001 [--id DL-004 ...]
  py -3 -I -B learn.py check LEARN_FILE --review REVIEW_FILE --lessons LESSONS [--state STATE]

start    Copies dev-core's learn template to <change>/learn-<N>.md with the title, change ID,
         and round filled in and no rows; refuses to overwrite an existing record.
collect  Reads <change>/review-<N>.md (Findings by area and Outside this change, with the
         Your choice cells), state.json's declined list, the lessons log, and the learn
         records of every other change in the plan folder (default: the change folder's
         parent). Collects each finding that is Critical or Major (kept), declined, or a likely
         repeat, and lists for each the lessons and earlier applied fixes that look like the
         same problem (same file, or at least three shared words). Matching is a candidate
         list; the agent judges it. Writes nothing.
lesson   add appends one line in dev-core's lesson format with the next DL ID (IDs are never
         reused); repeat raises a lesson's Repeats count by one; remove deletes the lines of
         settled lessons (fix applied, or fix or promotion declined) and their copies.
check    Validates learn-<N>.md: the table columns, each cell's allowed values, the fix level
         rules (level 2 changes only agents/goldfish-*.md, level 3 only a skill's own files and
         needs a "why not lower" reason), that every Critical or Major kept finding and every
         declined finding has a row, that no applied or declined row's lesson is still in the
         log, and a Drift section with at least one bullet. Its output lists checks_run and
         checks_skipped (with the reason, for example no --state given).

Exit code 0 when the command ran (check: "ok" says whether the record passed); 1 with
{"ok": false, "error": "..."} on any error. Writes only the lessons log (lesson commands).
"""

import argparse
import datetime
import glob
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.abspath(os.path.join(HERE, "..", "..", "dev-core", "assets", "templates", "learn.md"))
FINDINGS = os.path.abspath(os.path.join(HERE, "..", "..", "dev-core", "scripts", "findings.py"))
STAGES = ("plan", "tests", "workbook", "build", "review", "deploy", "one-off")
ROUTES = ("dev-workbook", "hook rule", "skill-builder", "none")
LEVELS = ("1", "2", "3", "-")
STATUS = re.compile(r"^(proposed|approved|applied(: .+)?|recorded|declined: .+)$")
COLUMNS = ("finding", "lesson", "repeats", "root cause stage", "evidence", "smallest fix", "level",
           "target file", "route", "why not lower", "status")
LESSON = re.compile(r"^- \*\*(DL-(\d+))\*\* · (.*)$")
STOP = set("""a an and are as at be because but by can does for from has have if in into is it
its not of on or that the then this to was were when where which while with without would
should could their there these those than only also more most same such very each every will
line file code value values change uses used using""".split())


class Fail(Exception):
    pass


def out(obj, code=0):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdout.write(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")
    sys.exit(code)


def load_findings():
    sys.dont_write_bytecode = True  # no __pycache__ in the plugin folders, even without -B
    if not os.path.isfile(FINDINGS):
        raise Fail(f"dev-core's findings.py is missing at {FINDINGS}")
    spec = importlib.util.spec_from_file_location("devfindings", FINDINGS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def words(text):
    return {w for w in re.findall(r"[a-z][a-z0-9_]{3,}", text.lower()) if w not in STOP}


def loc_file(location):
    """The file part of a location such as `src/A.cs:12` or src/A.cs:12-14."""
    s = location.strip().strip("`")
    return re.split(r":\d", s, maxsplit=1)[0].strip() if s else ""


def sections(text):
    """Split a review doc into {heading: body} on level-2 headings."""
    parts, cur, buf = {}, None, []
    for line in text.splitlines():
        if line.startswith("## "):
            if cur:
                parts[cur] = "\n".join(buf)
            cur, buf = line[3:].strip().lower(), []
        else:
            buf.append(line)
    if cur:
        parts[cur] = "\n".join(buf)
    return parts


def review_findings(fm, text):
    """Kept findings (Findings by area) and outside findings, with their choice cells."""
    sec = sections(text)
    found = []
    for name, where in (("findings by area", "kept"), ("outside this change", "outside")):
        for header, rows in fm.tables(sec.get(name, "")):
            if "id" not in header or "finding" not in header:
                continue
            for r in rows:
                rid = fm.cell(r.get("id", ""))
                if not re.match(r"^R\d+-", rid):
                    continue
                found.append({
                    "id": rid, "where": where,
                    "impact": fm.cell(r.get("impact") or r.get("severity") or ""),
                    "location": fm.cell(r.get("location", "")),
                    "finding": fm.cell(r.get("finding", "")),
                    "fix": fm.cell(r.get("proposed fix") or r.get("recommendation") or ""),
                    "choice": fm.cell(r.get("your choice", "")),
                })
    return found


def parse_lessons(path):
    if not os.path.isfile(path):
        return []
    items = []
    for line in read(path).splitlines():
        m = LESSON.match(line.strip())
        if not m:
            continue
        body = m.group(3)
        fields = dict(re.findall(r"(stage|change|finding|where): (`[^`]*`|[^·—]+?)\s*(?=·|—)", body))
        rep = re.search(r"Repeats: (\d+)\.", body)
        items.append({"id": m.group(1), "n": int(m.group(2)), "line": line.strip(),
                      "stage": fields.get("stage", "").strip(),
                      "where": fields.get("where", "").strip().strip("`"),
                      "text": body, "repeats": int(rep.group(1)) if rep else 0})
    return items


def past_fixes(fm, plans, this_change):
    """Applied rows from every other change's learn records."""
    fixes = []
    for path in sorted(glob.glob(os.path.join(plans, "*", "learn-*.md"))):
        change = os.path.basename(os.path.dirname(path))
        if os.path.abspath(os.path.dirname(path)) == os.path.abspath(this_change):
            continue
        for header, rows in fm.tables(read(path)):
            if "finding" not in header or "status" not in header:
                continue
            for r in rows:
                if fm.cell(r.get("status", "")).startswith("applied"):
                    fixes.append({"change": change, "file": os.path.basename(path),
                                  "finding": fm.cell(r.get("finding", "")),
                                  "target": fm.cell(r.get("target file", "")),
                                  "fix": fm.cell(r.get("smallest fix", "")),
                                  "text": " ".join(fm.cell(v) for v in r.values())})
    return fixes


def matches(f, lessons, fixes):
    fw = words(f["finding"] + " " + f["fix"])
    ffile = loc_file(f["location"])
    hits, held = [], []
    for les in lessons:
        shared = fw & words(les["text"])
        same_file = bool(ffile) and (ffile == les["where"] or ffile in les["text"])
        if same_file or len(shared) >= 3:
            hits.append({"lesson": les["id"], "same_file": same_file, "shared_words": sorted(shared)[:8],
                         "line": les["line"]})
    for fx in fixes:
        shared = fw & words(fx["text"])
        same_file = bool(ffile) and ffile in fx["text"]
        if same_file or len(shared) >= 3:
            held.append({"change": fx["change"], "record": fx["file"], "finding": fx["finding"],
                         "target": fx["target"], "fix": fx["fix"], "same_file": same_file,
                         "shared_words": sorted(shared)[:8]})
    return hits, held


def cmd_collect(a):
    fm = load_findings()
    cdir = os.path.abspath(a.change_dir)
    review = os.path.join(cdir, f"review-{a.round}.md")
    if not os.path.isfile(review):
        raise Fail(f"no review doc for round {a.round}: {review}")
    found = review_findings(fm, read(review))
    state_path = os.path.join(cdir, "state.json")
    declined = {}
    if os.path.isfile(state_path):
        for d in json.loads(read(state_path)).get("declined", []):
            rid = str(d.get("finding", "")).split(":", 1)[0].strip()
            declined[rid] = d.get("reason", "")
    lessons = parse_lessons(a.lessons)
    fixes = past_fixes(fm, a.plans or os.path.dirname(cdir), cdir)
    collected, skipped = [], []
    for f in found:
        why = []
        if f["where"] == "kept" and f["impact"] in ("Critical", "Major", "Blocker"):
            why.append(f["impact"].lower())
        if f["choice"].lower().startswith("decline") or f["id"] in declined:
            why.append("declined")
            f["reason"] = declined.get(f["id"]) or f["choice"].partition(":")[2].strip()
        hits, held = matches(f, lessons, fixes)
        if hits:
            why.append("repeats a lesson")
        if held:
            why.append("repeats an applied fix")
        f["lessons"], f["applied_fixes"] = hits, held
        (collected if why else skipped).append(dict(f, why=why) if why else f["id"])
    if "findings by area" not in sections(read(review)):
        raise Fail(f"no Findings by area section in {review}; is it a review doc from findings.py tally?")
    return {"ok": True, "round": a.round, "review": review, "collected": collected,
            "not_collected": skipped, "lessons_read": len(lessons), "applied_fixes_read": len(fixes),
            "nothing_to_learn": not collected}


def write_lines(path, lines):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines).rstrip("\n") + "\n")


def cmd_lesson(a):
    path = a.lessons
    lines = read(path).splitlines() if os.path.isfile(path) else ["# Lessons", ""]
    lessons = parse_lessons(path)
    if a.action == "add":
        if a.stage not in STAGES:
            raise Fail(f"--stage must be one of {STAGES}")
        for name in ("change", "finding", "where", "text", "fix"):
            v = getattr(a, name)
            if not v or "\n" in v or "·" in v:
                raise Fail(f"--{name} must be one line without '·'")
        date = a.date or datetime.date.today().isoformat()
        datetime.date.fromisoformat(date)
        highest = max([l["n"] for l in lessons] + [_highest_seen(lines)])
        lid = f"DL-{highest + 1:03d}"
        text = a.text.rstrip(".") + "."
        fix = a.fix.rstrip(".")
        lines.append(f"- **{lid}** · {date} · stage: {a.stage} · change: `{a.change}` · finding: "
                     f"{a.finding} · where: `{a.where}` — {text} Fix: {fix}. Repeats: 1.")
        write_lines(path, lines)
        return {"ok": True, "added": lid, "path": os.path.abspath(path)}
    ids = set(a.id or [])
    known = {l["id"] for l in lessons}
    missing = sorted(ids - known)
    if not ids:
        raise Fail("give at least one --id")
    if missing:
        raise Fail(f"no such lesson: {', '.join(missing)}")
    if a.action == "repeat":
        if len(ids) != 1:
            raise Fail("repeat takes one --id")
        lid = next(iter(ids))
        new = []
        for line in lines:
            m = LESSON.match(line.strip())
            if m and m.group(1) == lid:
                line = re.sub(r"Repeats: (\d+)\.", lambda r: f"Repeats: {int(r.group(1)) + 1}.", line)
            new.append(line)
        write_lines(path, new)
        count = next(l["repeats"] for l in parse_lessons(path) if l["id"] == lid)
        return {"ok": True, "repeated": lid, "repeats": count}
    kept = []
    for line in lines:
        m = LESSON.match(line.strip())
        if m and m.group(1) in ids:
            continue
        kept.append(line)
    highest = max([l["n"] for l in lessons] + [_highest_seen(lines)])
    if not any(l.startswith("<!-- highest DL:") for l in kept):
        kept.insert(1 if kept else 0, f"<!-- highest DL: {highest} (IDs are never reused) -->")
    else:
        kept = [f"<!-- highest DL: {highest} (IDs are never reused) -->" if l.startswith("<!-- highest DL:")
                else l for l in kept]
    write_lines(path, kept)
    return {"ok": True, "removed": sorted(ids), "path": os.path.abspath(path)}


def _highest_seen(lines):
    for l in lines:
        m = re.match(r"<!-- highest DL: (\d+)", l)
        if m:
            return int(m.group(1))
    return 0


def cmd_start(a):
    cdir = os.path.abspath(a.change_dir)
    state_path = os.path.join(cdir, "state.json")
    if not os.path.isfile(state_path):
        raise Fail(f"no state.json in {cdir}")
    state = json.loads(read(state_path))
    dest = os.path.join(cdir, f"learn-{a.round}.md")
    if os.path.exists(dest):
        raise Fail(f"{dest} exists already; edit it instead")
    lines = read(TEMPLATE).splitlines()
    out_lines = []
    for line in lines:
        if line.startswith("| {review ID}"):
            continue  # the sample row: rows are written per collected finding
        if line.startswith("- {where docs"):
            continue  # Drift bullets are written by the drift check
        out_lines.append(line.replace("{title}", state.get("title", "")).replace("{change_id}", state.get("id", ""))
                         .replace("{n}", str(a.round)))
    write_lines(dest, out_lines)
    return {"ok": True, "written": dest}


def cmd_check(a):
    fm = load_findings()
    text = read(a.learn_file)
    problems = []
    table = None
    for header, rows in fm.tables(text):
        if "finding" in header and "route" in header:
            table = (header, rows)
            break
    if not table:
        raise Fail("no learn table (columns Finding ... Status) in " + a.learn_file)
    header, rows = table
    for c in COLUMNS:
        if c not in header:
            problems.append(f"missing column: {c}")
    run_list = ["columns", "cell values", "fix levels", "coverage of Critical and Major kept findings",
                "coverage of findings declined in the review doc", "settled lessons out of the log",
                "open lessons in the log", "Drift section"]
    skipped = []
    review = review_findings(fm, read(a.review))
    must = {f["id"] for f in review if f["where"] == "kept" and f["impact"] in ("Critical", "Major", "Blocker")}
    must |= {f["id"] for f in review if f["choice"].lower().startswith("decline")}
    if not a.state:
        skipped.append({"check": "coverage of declines recorded in state.json", "reason": "no --state given"})
    elif not os.path.isfile(a.state):
        skipped.append({"check": "coverage of declines recorded in state.json", "reason": f"{a.state} not found"})
    else:
        run_list.append("coverage of declines recorded in state.json")
        must |= {str(d.get("finding", "")).split(":", 1)[0].strip()
                 for d in json.loads(read(a.state)).get("declined", [])}
    must.discard("")
    log_ids = {l["id"] for l in parse_lessons(a.lessons)}
    seen = set()
    for i, r in enumerate(rows, 1):
        g = lambda k: fm.cell(r.get(k, ""))
        rid = g("finding")
        seen.add(rid)
        where = f"row {i} ({rid})"
        if g("root cause stage") not in STAGES:
            problems.append(f"{where}: root cause stage must be one of {STAGES}")
        if g("route") not in ROUTES:
            problems.append(f"{where}: route must be one of {ROUTES}")
        lvl, target = g("level"), g("target file").strip("`")
        if lvl not in LEVELS:
            problems.append(f"{where}: level must be 1, 2, 3, or - (no fix)")
        if not STATUS.match(g("status")):
            problems.append(f"{where}: status must be proposed, approved, applied (or applied: <where it landed>), recorded, or declined: <reason>")
        if not g("evidence"):
            problems.append(f"{where}: evidence is empty")
        if (g("route") == "none") != (lvl == "-"):
            problems.append(f"{where}: a row with no fix has route none and level -, and only then")
        if g("root cause stage") == "one-off" and g("route") != "none":
            problems.append(f"{where}: a one-off is recorded with no fix (route none)")
        if lvl == "2" and not re.search(r"agents/goldfish-[a-z-]+\.md$", target):
            problems.append(f"{where}: level 2 changes a goldfish file (agents/goldfish-<name>.md)")
        if lvl == "3":
            if not re.search(r"skills/[a-z-]+/(SKILL\.md|routes/|stages/)", target):
                problems.append(f"{where}: level 3 changes a skill's own SKILL.md, routes/, or stages/ file")
            if g("why not lower") in ("", "-", "—", "n/a"):
                problems.append(f"{where}: level 3 needs evidence why a workbook, reference file, or goldfish cannot resolve it")
        if lvl == "1" and re.search(r"(agents/goldfish-|/SKILL\.md$|/routes/|/stages/)", target):
            problems.append(f"{where}: level 1 changes a workbook, a reference or template file, or a hook rule, not {target}")
        if g("route") == "dev-workbook" and lvl != "1":
            problems.append(f"{where}: a workbook fact is a level 1 fix")
        les = g("lesson")
        st = g("status")
        if (st.startswith("applied") or st.startswith("declined")) and les in log_ids:
            problems.append(f"{where}: lesson {les} is settled ({st.split(':')[0]}) but still in the lessons log; remove it")
        if st in ("proposed", "approved", "recorded") and les not in log_ids:
            problems.append(f"{where}: lesson {les} is open but not in the lessons log")
    for rid in sorted(must - seen):
        problems.append(f"missing row for collected finding {rid}")
    drift = sections(text).get("drift")
    if drift is None or not re.search(r"^\s*- \S", drift, re.M):
        problems.append("missing Drift section with at least one bullet (\"none found\" when clean)")
    return {"ok": not problems, "problems": problems, "rows": len(rows), "checks_run": run_list,
            "checks_skipped": skipped}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="learn.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    st = sub.add_parser("start")
    st.add_argument("change_dir"); st.add_argument("--round", type=int, required=True)
    c = sub.add_parser("collect")
    c.add_argument("change_dir"); c.add_argument("--round", type=int, required=True)
    c.add_argument("--lessons", required=True); c.add_argument("--plans")
    lp = sub.add_parser("lesson")
    lp.add_argument("action", choices=["add", "repeat", "remove"]); lp.add_argument("lessons")
    for k in ("stage", "change", "finding", "where", "text", "fix", "date"):
        lp.add_argument("--" + k)
    lp.add_argument("--id", action="append")
    k = sub.add_parser("check")
    k.add_argument("learn_file"); k.add_argument("--review", required=True)
    k.add_argument("--lessons", required=True); k.add_argument("--state")
    a = ap.parse_args(argv)
    try:
        res = {"start": cmd_start, "collect": cmd_collect, "lesson": cmd_lesson, "check": cmd_check}[a.cmd](a)
    except (Fail, ValueError, OSError, json.JSONDecodeError) as e:
        out({"ok": False, "error": str(e)}, 1)
    out(res, 0)


if __name__ == "__main__":
    main()
