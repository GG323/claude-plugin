#!/usr/bin/env python3
"""Review findings tally for the howtoai-dev skills (standard library only).

Shared by dev-plan's plan review loop and dev-review's code review loop. The model never
counts findings itself: reviewers' tables go into a raw folder, this script merges them,
applies the scorer's confidence and the verifier's verdicts, and writes the round's review
document from dev-core's template shape.

Commands (each prints one JSON object; "ok": false carries the error):

  collect <raw dir> [--kind plan|code]
      Parse every reviewer table in <raw dir>/*.md (all files except declined.md, inspection.md, workbook-statements.md, findings.md,
      high-impact.md, scores.md, verdicts.md; the file stem is the viewpoint), check IDs and
      severities, and write findings.json, findings.md (for the scorer), and high-impact.md
      (Blocker/Critical and Major findings, for the verifier; removed when there are none).
      Two findings with the same location and the same quote are one problem raised twice:
      the one with the higher impact (else the first) is kept and names the other, which tally
      lists in the appendix as a duplicate. A table's Change column says whether a finding is
      in the change under review ("in", the default) or outside it ("outside").

  tally <raw dir> --round N --out <file> [--kind plan|code] [--threshold 80]
        [--title T] [--change-id ID] [--size S] [--diff BASE..HEAD] [--force]
        [--changed CHANGED.json] [--inspection FILE.md]
      Merge findings.json with scores.md and verdicts.md and write the review document.
      A finding scored 20 or less whose whole reason is "Duplicate of <ID>" (a final period may follow)
      goes to the appendix when that finding is shown, is at least as severe, and is in the same file on
      the same side of the change; that finding then names its ID, location, and claim. Otherwise:
      A finding the verifier says stands is kept whatever its score, and so is one in confirmed.md
      (test inspection; confidence 100). A held-back Correctness, Risk, or Security finding scored 70
      or more is returned in "possible". "Not run:" lines of the reviewers are returned in "not_run".
      Below-threshold and refuted findings go to the appendix; weakened ones take their new
      impact. A finding is outside the change when its Change cell says so or, in code reviews
      with --changed (dev-review's review.py diff output), when its location is a file:line
      outside this round's changed lines (3 lines of slack; spec and process findings are never
      moved, because they may point at what is missing). An outside finding that is
      Blocker/Critical or Major after the verifier (stands, or weakened but still that high)
      goes to the Outside this change section whatever its score, with the score shown, where
      the user decides it, so an important problem is never lost to a low score; other outside
      findings go to the appendix. Outside
      findings never make a round not clean. --inspection fills the Test inspection section
      from a Markdown file instead of placeholders. "clean" is true when no Blocker/Critical or
      Major finding is kept in the Findings section. Refuses to overwrite a review whose
      resolutions were already filled, unless --force.

  check <review file>
      Report the findings in the Findings and Outside this change sections whose Resolution
      (plan) or Your choice (code) is still open.

  stop <change folder> [--prefix plan-review] [--clean-rounds 2] [--max-rounds 5]
      Read the Result line of every <prefix>-<n>.md and decide: "clean" when the last
      --clean-rounds rounds were clean in a row, "cap" at --max-rounds, else "continue".
"""
import argparse
import json
import os
import re
import sys

KINDS = {
    "plan": {"levels": ["Blocker", "Major", "Nit"], "high": {"Blocker", "Major"}},
    "code": {"levels": ["Critical", "Major", "Minor", "Nit"], "high": {"Critical", "Major"}},
}
RESERVED = {"findings.md", "high-impact.md", "scores.md", "verdicts.md",
            "declined.md", "inspection.md", "workbook-statements.md"}  # the elephant's own notes, not reviewers
NOTE_LINE = re.compile(r"^[\s>*_`+\-]*(blocked|not run)[*_`\s]*:[*_`\s]*(.*)$", re.I)
CONFIRMED = "confirmed"  # confirmed.md: bugs dev-review's test inspection proved; they need no score or verdict
POSSIBLE_FROM = 70  # the scorer's "likely" band
POSSIBLE_AREAS = {"correctness", "risk", "security"}
DUPLICATE_OF = re.compile(r"Duplicate of ([PR]\d+-[A-Z]\d+)\.?")  # the scorer's whole reason for a repeat
DUPLICATE_UP_TO = 20  # the most the scorer gives a repeat
PLAN_RESOLUTIONS = ("fixed:", "decided:", "asked:", "declined:", "outside:")
CODE_CHOICES = ("fix now", "later", "decline")


class Fail(Exception):
    pass


# Markdown tables ---------------------------------------------------------------------------

def split_row(line):
    """Split a Markdown table row on pipes outside backticks; honour \\| escapes."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    cells, cur, tick, i = [], [], False, 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s) and s[i + 1] == "|":
            cur.append("|")
            i += 2
            continue
        if c == "`":
            tick = not tick
        if c == "|" and not tick:
            cells.append("".join(cur).strip())
            cur = []
        else:
            cur.append(c)
        i += 1
    cells.append("".join(cur).strip())
    return cells


def is_sep(cells):
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in cells if c) and any(cells)


def tables(text):
    """Yield (header, rows) for every pipe table in text; rows are dicts by lowercased header."""
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith("|") and i + 1 < len(lines) and is_sep(split_row(lines[i + 1])):
            header = [h.strip().lower() for h in split_row(lines[i])]
            rows = []
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = split_row(lines[i])
                cells += [""] * (len(header) - len(cells))
                rows.append(dict(zip(header, cells)))
                i += 1
            yield header, rows
        else:
            i += 1


def first_table(text, need):
    for header, rows in tables(text):
        if all(any(h == n or h.startswith(n) for h in header) for n in need):
            return header, rows
    return None, []


def col(row, *names):
    for n in names:
        for k, v in row.items():
            if k == n or k.startswith(n):
                return v
    return ""


def cell(text):
    return (text or "").replace("|", "\\|").replace("\n", " ").strip()


# collect -----------------------------------------------------------------------------------

def norm_change(value):
    return "outside" if re.sub(r"[*`]", "", value or "").strip().lower().startswith("outside") else "in"


def norm_level(value, kind, where):
    levels = KINDS[kind]["levels"]
    v = re.sub(r"[*`]", "", value or "").strip()
    for lv in levels:
        if v.lower() == lv.lower():
            return lv
    raise Fail(f"{where}: severity '{value}' is not one of {levels}")


def collect(raw, kind):
    if not os.path.isdir(raw):
        raise Fail(f"no raw folder at {raw}")
    findings, viewpoints, seen, not_run = [], [], {}, []
    for name in sorted(os.listdir(raw)):
        if not name.endswith(".md") or name in RESERVED:
            continue
        vp = name[:-3]
        viewpoints.append(vp)
        text = open(os.path.join(raw, name), encoding="utf-8").read()
        for line in text.splitlines():
            note = NOTE_LINE.match(line)
            if not note:
                continue
            said = note.group(2).rstrip(" *_`")
            if note.group(1).lower() == "blocked":
                raise Fail(f"{vp} review is blocked ({said}); fix the cause and run that reviewer again")
            not_run.append(f"{vp}: {said}")
        header, rows = first_table(text, ["id", "finding"])
        if header is None and not re.search(r"\bno findings\b", text, re.I):
            raise Fail(f"{vp}.md has neither a findings table nor 'No findings'; ask that reviewer for its Output again")
        for r in rows:
            fid = re.sub(r"[*`]", "", col(r, "id")).strip()
            if not fid:
                continue
            if fid in seen:
                raise Fail(f"duplicate finding ID {fid} in {seen[fid]} and {name}")
            seen[fid] = name
            sev = norm_level(col(r, "severity", "impact"), kind, f"{name} {fid}")
            findings.append({
                "id": fid, "viewpoint": vp, "severity": sev,
                "area": col(r, "area") or vp,
                "location": col(r, "location"), "quote": col(r, "quote"),
                "finding": col(r, "finding"), "mark": col(r, "mark"),
                "recommendation": col(r, "recommendation", "proposed fix", "fix"),
                "handling": (col(r, "handling") or "ASK").upper(),
                "change": norm_change(col(r, "change")),
            })
    if not viewpoints:
        raise Fail(f"no reviewer files in {raw}")
    findings, merged = merge_duplicates(findings, kind)
    data = {"kind": kind, "viewpoints": viewpoints, "findings": findings, "merged": merged, "not_run": not_run}
    with open(os.path.join(raw, "findings.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    to_judge = [x for x in findings if not is_proven(x)]
    high = [x for x in to_judge if x["severity"] in KINDS[kind]["high"]]

    def table(items):
        out = ["| ID | Severity | Location | Quote | Claim |", "| --- | --- | --- | --- | --- |"]
        out += ["| %s | %s | %s | %s | %s |" % (x["id"], x["severity"], cell(x["location"]), cell(x["quote"]), cell(x["finding"])) for x in items]
        return "\n".join(out) + "\n"

    with open(os.path.join(raw, "findings.md"), "w", encoding="utf-8") as f:
        f.write(table(to_judge))
    hp = os.path.join(raw, "high-impact.md")
    if high:
        with open(hp, "w", encoding="utf-8") as f:
            f.write(table(high))
    elif os.path.exists(hp):
        os.remove(hp)
    counts = {lv: sum(1 for x in findings if x["severity"] == lv) for lv in KINDS[kind]["levels"]}
    return {"ok": True, "count": len(findings), "by_severity": counts,
            "high_impact": [x["id"] for x in high], "viewpoints": viewpoints,
            "outside_change": [x["id"] for x in findings if x["change"] == "outside"], "merged": [{"id": m["id"], "into": m["into"]} for m in merged]}


def dup_key(x):
    loc = re.sub(r"[`*\s]", "", x.get("location") or "").lower()
    quote = re.sub(r"\s+", " ", re.sub(r"[`*\"'“”]", "", x.get("quote") or "")).strip().lower()
    return (loc, quote) if loc and quote else None


def is_proven(x):
    return bool(x.get("proven")) or x["viewpoint"] == CONFIRMED


def merge_duplicates(findings, kind):
    rank = {lv: i for i, lv in enumerate(KINDS[kind]["levels"])}
    keep, merged, by_key = [], [], {}
    for x in findings:
        k = dup_key(x)
        if k is None or k not in by_key:
            keep.append(x)
            if k is not None:
                by_key[k] = x
            continue
        first = by_key[k]
        if rank[x["severity"]] < rank[first["severity"]]:
            keep[keep.index(first)] = x
            by_key[k] = x
            first, x = x, first
        if is_proven(first) or is_proven(x):
            first["proven"] = True  # a test proved it; the merge must not send it back to scoring
            if "in" in (first.get("change"), x.get("change")):
                first["change"] = "in"
        first.setdefault("also", []).append(x["id"])
        first["finding"] = first["finding"].rstrip() + " Also raised by %s (%s)." % (x["id"], x["viewpoint"])
        merged.append(dict(x, into=first["id"]))
    return keep, merged


# tally -------------------------------------------------------------------------------------

def read_table_file(path, need):
    if not os.path.exists(path):
        return None
    _, rows = first_table(open(path, encoding="utf-8").read(), need)
    return {re.sub(r"[*`]", "", col(r, "id")).strip(): r for r in rows if col(r, "id").strip()}


LOC = re.compile(r"^(?P<path>[^:]+?):(?P<start>\d+)(?:-(?P<end>\d+))?$")
NO_LINE_FILTER = ("spec", "process")
SLACK = 3


def load_changed(path):
    if not path:
        return None
    if not os.path.exists(path):
        raise Fail(f"no changed-lines file at {path}")
    data = json.load(open(path, encoding="utf-8"))
    files = data.get("files")
    if not isinstance(files, dict):
        raise Fail("--changed file must hold {\"files\": {path: [[start, end], ...]}}")
    return {k.replace("\\", "/"): v for k, v in files.items()}


def unchanged(x, changed):
    if changed is None or x["viewpoint"] in NO_LINE_FILTER:
        return False
    loc = re.sub(r"[`*]", "", x.get("location") or "").strip().replace("\\", "/")
    m = LOC.match(loc)
    if not m:
        return False
    start = int(m.group("start"))
    end = int(m.group("end") or start)
    path = m.group("path")
    ranges = changed.get(path[2:] if path.startswith("./") else path)
    if not ranges:
        return True
    return not any(start <= hi + SLACK and end >= lo - SLACK for lo, hi in ranges)


def is_possible(x):
    """A held-back likely bug, risk, or security problem the user still hears about."""
    return x["confidence"] >= POSSIBLE_FROM and x.get("area", "").strip().lower() in POSSIBLE_AREAS


def files_of(x):
    """The files a location names, without lines and notes."""
    files = set()
    for part in re.split(r"[;,]", re.sub(r"\([^)]*\)|[`*]", "", x.get("location") or "")):
        path = re.sub(r":\d+(-\d+)?$", "", part.strip()).replace("\\", "/")
        if path:
            files.add(path[2:] if path.startswith("./") else path)
    return files


def same_file(a, b):
    if a == b:
        return True
    short, long = sorted((a, b), key=len)  # one reviewer writes workspace-relative paths, another absolute ones
    absolute = re.compile(r"^([A-Za-z]:/|/)")
    return bool("/" in short and not absolute.match(short) and absolute.match(long) and long.endswith("/" + short))


def in_the_same_files(x, first):
    mine, its = files_of(x), files_of(first)
    return bool(mine) and all(any(same_file(m, i) for i in its) for m in mine)


def collapse_repeats(kept, outside, held, summary, levels):
    """Hold back a scored repeat only when what it repeats is itself shown, at least as severe, and no repeat.

    Both must be in the same file and on the same side of the change. The shown row then carries the repeat."""
    rank = {lv: i for i, lv in enumerate(levels)}
    shown = {x["id"]: ("in", x) for x in kept}
    shown.update({x["id"]: ("outside", x) for x in outside})
    for place, items, count in (("in", kept, "kept"), ("outside", outside, "outside")):
        for x in list(items):
            where, first = shown.get(x.get("repeats"), (None, None))
            if not first or first.get("repeats") or rank[first["severity"]] > rank[x["severity"]]:
                continue
            if place != where or not in_the_same_files(x, first):
                continue
            first.setdefault("also", []).append(x["id"])
            first["finding"] = first["finding"].rstrip() + " Also raised by %s (%s) at %s: %s" % (
                x["id"], x["viewpoint"], x["location"], x["finding"].strip())
            items.remove(x)
            summary[x["raised_as"]][count] -= 1
            summary[x["raised_as"]]["held"] += 1
            held.append(dict(x, reason="duplicate of %s, which is shown" % first["id"]))


def tally(raw, a):
    jp = os.path.join(raw, "findings.json")
    if not os.path.exists(jp):
        raise Fail("findings.json missing; run collect first")
    data = json.load(open(jp, encoding="utf-8"))
    kind = data["kind"]
    if a.kind and a.kind != kind:
        raise Fail(f"findings.json was collected as {kind}, not {a.kind}")
    levels, high = KINDS[kind]["levels"], KINDS[kind]["high"]
    findings = data["findings"]
    to_judge = [x for x in findings if not is_proven(x)]
    scores = read_table_file(os.path.join(raw, "scores.md"), ["id", "score"]) if to_judge else {}
    if to_judge and scores is None:
        raise Fail("scores.md missing; save the scorer's table there")
    missing = [x["id"] for x in to_judge if x["id"] not in scores]
    if missing:
        raise Fail(f"no score for {missing}")
    hi = [x for x in to_judge if x["severity"] in high]
    verdicts = read_table_file(os.path.join(raw, "verdicts.md"), ["id", "verdict"]) or {}
    if hi and not verdicts:
        raise Fail("verdicts.md missing; save the verifier's table there")
    vmiss = [x["id"] for x in hi if x["id"] not in verdicts]
    if vmiss:
        raise Fail(f"no verdict for {vmiss}")

    changed = load_changed(getattr(a, "changed", None)) if kind == "code" else None
    kept, held, outside = [], [], []
    summary = {lv: {"raised": 0, "kept": 0, "outside": 0, "weakened": 0, "held": 0, "refuted": 0} for lv in levels}  # by raised severity
    for x in findings:
        orig = x["severity"]
        proven = is_proven(x)
        summary[orig]["raised"] += 1
        s = {"score": "100", "reason": "confirmed by test inspection"} if proven else scores[x["id"]]
        raw_score = re.sub(r"[^0-9]", "", col(s, "score"))
        if not raw_score:
            raise Fail(f"score for {x['id']} is not a number")
        score = int(raw_score)
        x["confidence"] = score
        may_repeat = not proven and score <= DUPLICATE_UP_TO and score < a.threshold
        repeat = DUPLICATE_OF.fullmatch(col(s, "reason").strip()) if may_repeat else None
        x["repeats"], x["raised_as"] = repeat.group(1) if repeat else None, orig
        x["verdict"] = "not verified"
        v = verdicts.get(x["id"]) if orig in high and not proven else None
        if proven:
            x["verdict"] = "stands"
        if v:
            word = col(v, "verdict").strip().lower().strip("*")
            evidence = col(v, "evidence")
            if word.startswith("refuted"):
                summary[orig]["refuted"] += 1
                held.append(dict(x, reason="refuted: " + evidence))
                continue
            if word.startswith("weakened"):
                now = col(v, "impact now").strip()
                if now.lower() in ("", "none"):
                    summary[orig]["refuted"] += 1
                    held.append(dict(x, reason="weakened to none: " + evidence))
                    continue
                x["severity"] = norm_level(now, kind, f"verdict {x['id']}")
                x["verdict"] = f"weakened from {orig}"
                summary[orig]["weakened"] += 1
            elif word.startswith("stands"):
                x["verdict"] = "stands"
            else:
                raise Fail(f"verdict for {x['id']} must be Stands, Weakened, or Refuted")
        if x.get("change") == "outside":
            where = "marked outside the change by the reviewer"
        elif unchanged(x, changed):
            where = "unchanged line: not in this round's diff"
        else:
            where = None
        verified_high = where and x["severity"] in high and x["verdict"] != "not verified"
        if score < a.threshold and not verified_high and x["verdict"] != "stands":
            summary[orig]["held"] += 1
            held.append(dict(x, possible=is_possible(x), reason="below threshold: " + col(s, "reason") + (" (%s)" % where if where else "")))
            continue
        if where:
            if x["severity"] in high:
                summary[orig]["outside"] += 1
                outside.append(dict(x, where=where))
            else:
                summary[orig]["held"] += 1
                held.append(dict(x, possible=is_possible(x), reason="outside the change, %s: %s" % (x["severity"], where)))
            continue
        summary[orig]["kept"] += 1
        kept.append(x)

    collapse_repeats(kept, outside, held, summary, levels)
    for m in data.get("merged", []):
        summary[m["severity"]]["raised"] += 1
        summary[m["severity"]]["held"] += 1
        held.append(dict(m, confidence="-", reason="duplicate of %s" % m["into"]))

    for x in held:
        if x.get("possible"):
            x["reason"] = "possible, not confirmed: " + x["reason"]
    rank = {lv: i for i, lv in enumerate(levels)}
    kept.sort(key=lambda x: (rank[x["severity"]], x["id"]))
    outside.sort(key=lambda x: (rank[x["severity"]], x["id"]))
    clean = not any(x["severity"] in high for x in kept)

    if os.path.exists(a.out) and not a.force:
        prev = open(a.out, encoding="utf-8").read()
        if re.search(r"\|\s*(fixed:|decided:|asked:|declined:|outside:|fix now|later|decline)", prev):
            raise Fail(f"{a.out} already has resolutions; pass --force to overwrite")

    render = render_plan if kind == "plan" else render_code
    md = render(a, data, kept, outside, held, summary, clean)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(md)
    count = {lv: sum(1 for x in kept if x["severity"] == lv) for lv in levels}
    return {"ok": True, "out": a.out.replace("\\", "/"), "clean": clean, "kept": len(kept),
            "kept_by_severity": count, "outside_change": [x["id"] for x in outside], "held_back": len(held),
            "possible": [x["id"] for x in held if x.get("possible")], "not_run": data.get("not_run", []),
            "refuted": sum(summary[lv]["refuted"] for lv in levels)}


def grouped(kept, key):
    groups = {}
    for x in kept:
        groups.setdefault(x[key], []).append(x)
    return groups


def outside_md(kind, outside):
    """The Outside this change section: verified high-impact findings the user decides on."""
    last = "Resolution" if kind == "plan" else "Your choice"
    L = ["Verified Blocker, Critical, or Major findings outside the change under review. They do not count against this round; each needs a decision.", "",
         "| ID | Severity | Confidence | Verdict | Viewpoint | Location | Finding | Recommendation | Why outside | %s |" % last,
         "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    if not outside:
        return ["none"]
    for x in outside:
        L.append("| %s | %s | %d | %s | %s | %s | %s | %s | %s | open |" % (
            x["id"], x["severity"], x["confidence"], x["verdict"], x["viewpoint"], cell(x["location"]),
            finding_text(x), cell(x["recommendation"]), cell(x["where"])))
    return L


def appendix(held, not_run=()):
    out = ["| ID | Severity | Confidence | Reason held back | Finding |", "| --- | --- | --- | --- | --- |"]
    if not held:
        out.append("| none | | | | |")
    for x in held:
        out.append("| %s | %s | %s | %s | %s |" % (x["id"], x["severity"], x["confidence"], cell(x["reason"]), cell(x["finding"])))
    if not_run:
        out += [""] + [f"- **Not run:** {note}" for note in not_run]
    return out


def finding_text(x):
    q = x.get("quote", "").strip()
    return cell(x["finding"] + (" (quote: %s)" % q if q else ""))


def render_plan(a, data, kept, outside, held, summary, clean):
    L = ["# %s: plan review round %s" % (a.title or "Plan", a.round), "",
         "Change `%s` · Size: %s · Reviewers: %s · Threshold: %s · Result: %s" % (
             a.change_id or "-", a.size or "-", ", ".join(data["viewpoints"]), a.threshold,
             "clean" if clean else "not clean"), "",
         "Written by `findings.py tally`; only the Resolution cells are filled by hand.", "",
         "## Summary", "",
         "Counted by the severity each finding was raised with; Raised = Kept + Outside + Held back + Refuted, and Weakened counts the kept, outside, or held-back findings the verifier lowered.", "",
         "| Severity | Raised | Kept | Outside | Held back | Refuted | Weakened |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for lv in KINDS["plan"]["levels"]:
        s = summary[lv]
        L.append("| %s | %d | %d | %d | %d | %d | %d |" % (lv, s["raised"], s["kept"], s["outside"], s["held"], s["refuted"], s["weakened"]))
    L += ["", "## Findings", ""]
    if not kept:
        L += ["No findings kept.", ""]
    for vp, items in grouped(kept, "viewpoint").items():
        L += ["### %s" % vp, "",
              "| ID | Severity | Confidence | Verdict | Mark | Location | Finding | Recommendation | Resolution |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for x in items:
            L.append("| %s | %s | %d | %s | %s | %s | %s | %s | open |" % (
                x["id"], x["severity"], x["confidence"], x["verdict"], cell(x["mark"]),
                cell(x["location"]), finding_text(x), cell(x["recommendation"])))
        L.append("")
    L += ["## Outside this change", ""] + outside_md("plan", outside) + ["", "## Appendix: held back", ""] + appendix(held, data.get("not_run", []))
    return "\n".join(L) + "\n"


def render_code(a, data, kept, outside, held, summary, clean):
    crit = any(x["severity"] == "Critical" for x in kept)
    major = any(x["severity"] == "Major" for x in kept)
    verdict = "blocked" if crit else ("changes requested" if major else "approved")
    L = ["# %s: review round %s" % (a.title or "Change", a.round), "",
         "Change `%s` · Diff: %s · Reviewers: %s · Verdict: %s · Result: %s" % (
             a.change_id or "-", a.diff or "-", ", ".join(data["viewpoints"]), verdict,
             "clean" if clean else "not clean"), "",
         "## Summary", "", "| Impact | Findings | AUTO-FIX | ASK |", "| --- | --- | --- | --- |"]
    for lv in KINDS["code"]["levels"]:
        items = [x for x in kept if x["severity"] == lv]
        auto = sum(1 for x in items if x["handling"] == "AUTO-FIX")
        L.append("| %s | %d | %d | %d |" % (lv, len(items), auto, len(items) - auto))
    L += ["", "Counts come from the tally script. Outside this change: %d (not counted above). Findings scored under the confidence threshold are in the appendix." % len(outside), "",
          "## Findings by area", ""]
    if not kept:
        L += ["No findings kept.", ""]
    for area, items in grouped(kept, "area").items():
        L += ["### %s" % area, "",
              "| ID | Impact | Confidence | Mark | Location | Finding | Proposed fix | Handling | Your choice |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for x in items:
            L.append("| %s | %s | %d | %s | %s | %s | %s | %s | open |" % (
                x["id"], x["severity"], x["confidence"], cell(x["mark"]), cell(x["location"]),
                finding_text(x), cell(x["recommendation"]), x["handling"]))
        L.append("")
    inspection = ["- **Runs:** {filled by dev-review}", "- **Temporary tests:** {filled by dev-review}",
                  "- **Coverage gaps:** {filled by dev-review}"]
    if getattr(a, "inspection", None):
        if not os.path.exists(a.inspection):
            raise Fail(f"no inspection file at {a.inspection}")
        inspection = open(a.inspection, encoding="utf-8").read().strip().splitlines()
    L += ["## Test inspection", ""] + inspection + ["", "## Outside this change", ""] + outside_md("code", outside)
    L += ["", "## Appendix: low confidence and filtered", ""] + appendix(held, data.get("not_run", []))
    return "\n".join(L) + "\n"


# check and stop ----------------------------------------------------------------------------

def check(path):
    if not os.path.exists(path):
        raise Fail(f"no review at {path}")
    text = open(path, encoding="utf-8").read()
    secs = []
    for name in ("Findings", "Findings by area", "Outside this change"):
        m = re.search(r"^## %s\s*$" % re.escape(name), text, re.M)
        if m:
            rest = text[m.end():]
            secs.append(re.split(r"\n## ", rest, maxsplit=1)[0])
    open_ids, bad, total = [], [], 0
    for header, rows in (t for sec in secs for t in tables(sec)):
        if "resolution" in header:
            colname, allowed = "resolution", PLAN_RESOLUTIONS
        elif "your choice" in header:
            colname, allowed = "your choice", CODE_CHOICES
        else:
            continue
        for r in rows:
            fid = col(r, "id")
            total += 1
            v = r.get(colname, "").strip()
            if not v or v.lower() == "open" or v.startswith("{"):
                open_ids.append(fid)
            elif not v.lower().startswith(allowed):
                bad.append(fid)
    return {"ok": not open_ids and not bad, "findings": total, "open": open_ids,
            "invalid": bad, "allowed": list(PLAN_RESOLUTIONS + CODE_CHOICES)}


def stop(folder, prefix, clean_rounds, max_rounds):
    if not os.path.isdir(folder):
        raise Fail(f"no change folder at {folder}")
    rounds = {}
    for name in os.listdir(folder):
        m = re.fullmatch(re.escape(prefix) + r"-(\d+)\.md", name)
        if not m:
            continue
        text = open(os.path.join(folder, name), encoding="utf-8").read()
        r = re.search(r"Result:\s*(clean|not clean)", text)
        if not r:
            raise Fail(f"{name} has no Result line; write it with findings.py tally")
        rounds[int(m.group(1))] = r.group(1) == "clean"
    if not rounds:
        raise Fail(f"no {prefix}-<n>.md in {folder}")
    order = sorted(rounds)
    streak = 0
    for n in reversed(order):
        if not rounds[n]:
            break
        streak += 1
    last = order[-1]
    if streak >= clean_rounds:
        decision = "clean"
    elif last >= max_rounds:
        decision = "cap"
    else:
        decision = "continue"
    return {"ok": True, "rounds": last, "consecutive_clean": streak, "last_clean": rounds[last], "stop": decision,
            "clean_rounds_to_stop": clean_rounds, "max_rounds": max_rounds}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect")
    c.add_argument("raw")
    c.add_argument("--kind", choices=KINDS, default="plan")
    t = sub.add_parser("tally")
    t.add_argument("raw")
    t.add_argument("--kind", choices=KINDS)
    t.add_argument("--round", required=True)
    t.add_argument("--out", required=True)
    t.add_argument("--threshold", type=int, default=80)
    t.add_argument("--title")
    t.add_argument("--change-id")
    t.add_argument("--size")
    t.add_argument("--diff")
    t.add_argument("--changed")
    t.add_argument("--inspection")
    t.add_argument("--force", action="store_true")
    k = sub.add_parser("check")
    k.add_argument("review")
    s = sub.add_parser("stop")
    s.add_argument("folder")
    s.add_argument("--prefix", default="plan-review")
    s.add_argument("--clean-rounds", type=int, default=2)
    s.add_argument("--max-rounds", type=int, default=5)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "collect":
            out = collect(a.raw, a.kind)
        elif a.cmd == "tally":
            out = tally(a.raw, a)
        elif a.cmd == "check":
            out = check(a.review)
        else:
            out = stop(a.folder, a.prefix, a.clean_rounds, a.max_rounds)
    except Fail as e:
        out = {"ok": False, "error": str(e)}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if out.get("ok") or a.cmd == "check" else 1


if __name__ == "__main__":
    sys.exit(main())
