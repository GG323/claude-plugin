"""Run file, report page, and run log for environment-audit.

Commands:
  init   <report.json> --discover <discover.json> --mode <scheduled|on request> --date YYYY-MM-DD
         Creates the run file with one entry per target from find_workspaces.py's
         JSON, as Discover edited it ("global": null leaves the global folder out;
         a named workspace is added as {"name": ..., "path": ...}).
  render <report.json> --log <run-log.md> --out <page.html> [--standalone]
         Validates the run file, numbers the findings (written back as "n"), and
         renders one HTML report for all targets. --standalone adds the document
         skeleton for a file opened directly in a browser.
  log    <report.json> --log <run-log.md> --report <link or path>
         Appends this run's row to the run log and keeps the newest 26 rows. Run
         again for the same report, it replaces that row instead.

The run file (report.json):
  {
    "date": "YYYY-MM-DD",
    "mode": "scheduled" | "on request",
    "targets": [{
      "id": "global" | "<workspace slug>",
      "name": "Global folder" | "<workspace folder name>",
      "kind": "global" | "workspace",
      "path": "C:/Users/<user>/.claude",
      "files": {"audited": 0, "exempt": 0, "excluded": 0},
      "not_run": ["L3: 2 web links rate-limited, not verified."],
      "notes": ["No workspace tools."]
    }],
    "skipped_targets": [{"path": "...", "reason": "..."}],
    "findings": [{
      "target": "<target id>",
      "domain": "tool" | "instruction" | "workspace",
      "check": "S3",
      "type": "defect" | "suggestion",
      "file": "~/.claude/skills/x/SKILL.md",
      "line": 12 | null,
      "evidence": "short quote from the file",
      "fix": "the proposed change",
      "action": "fix" | "skill-builder" | "decision",
      "status": "open" | "fixed" | "deferred" | "accepted",
      "tool": "x"            (optional; the skill or agent the finding belongs to)
    }],
    "recurring": [{"check": "G3", "proposal": "..."}]
  }
Text fields may use `backticks` for code. Writes only the files named on the command line.
"""

import argparse
import html
import json
import os
import re
import sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(SKILL_DIR, "assets", "report-template.html")
LOG_KEEP = 26  # about six months of weekly runs
LOG_SHOWN = 10

DOMAINS = [("tool", "Tool audit"), ("instruction", "Instruction audit"), ("workspace", "Workspace audit")]
ACTIONS = {"fix": "Fix in the audit", "skill-builder": "Use skill-builder", "decision": "Needs your decision"}
TYPES = {"defect", "suggestion"}
STATUSES = {"open", "fixed", "deferred", "accepted"}
LOG_HEADER = ["Date", "Mode", "Targets", "Audited", "Found", "Fixed", "Deferred", "Open by check", "Report"]


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(path, data):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "target"


# init ----------------------------------------------------------------------

def cmd_init(args):
    """Targets come from discover.json as edited by Discover: "global" set to
    null leaves the global folder out, and workspaces holds only the chosen ones."""
    found = load(args.discover)
    targets, used = [], set()
    if found.get("global"):
        targets.append({"id": "global", "name": "Global folder", "kind": "global", "path": found["global"],
                        "files": {"audited": 0, "exempt": 0, "excluded": 0}, "not_run": [], "notes": []})
        used.add("global")
    for w in found.get("workspaces", []):
        tid = slug(w["name"])
        while tid in used:
            tid += "-2"
        used.add(tid)
        targets.append({"id": tid, "name": w["name"], "kind": "workspace", "path": w["path"],
                        "files": {"audited": 0, "exempt": 0, "excluded": 0}, "not_run": [], "notes": []})
    data = {"date": args.date, "mode": args.mode, "targets": targets,
            "skipped_targets": [{"path": s.get("path") or s.get("history"), "reason": s["reason"]}
                                for s in found.get("skipped", [])],
            "findings": [], "recurring": []}
    save(args.report, data)
    print(json.dumps({"ok": True, "targets": [t["id"] for t in targets]}))


# validation and numbering --------------------------------------------------

def validate(data):
    errors = []
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(data.get("date", ""))):
        errors.append("date must be YYYY-MM-DD")
    if data.get("mode") not in ("scheduled", "on request"):
        errors.append("mode must be 'scheduled' or 'on request'")
    ids = [t.get("id") for t in data.get("targets", [])]
    if not ids:
        errors.append("no targets")
    for k, f in enumerate(data.get("findings", [])):
        where = "finding %d (%s %s)" % (k, f.get("check"), f.get("file"))
        if f.get("target") not in ids:
            errors.append("%s: unknown target %r" % (where, f.get("target")))
        if f.get("domain") not in dict(DOMAINS):
            errors.append("%s: domain must be tool, instruction, or workspace" % where)
        if not re.match(r"^[A-Z]\d+$", str(f.get("check", ""))):
            errors.append("%s: check must be an ID such as S3" % where)
        if f.get("type") not in TYPES:
            errors.append("%s: type must be defect or suggestion" % where)
        if f.get("action") not in ACTIONS:
            errors.append("%s: action must be fix, skill-builder, or decision" % where)
        if f.get("status") not in STATUSES:
            errors.append("%s: status must be open, fixed, deferred, or accepted" % where)
        for field in ("file", "evidence", "fix"):
            if not str(f.get(field) or "").strip():
                errors.append("%s: %s is empty" % (where, field))
        if f.get("line") is not None and not isinstance(f.get("line"), int):
            errors.append("%s: line must be a number or null" % where)
    return errors


def order(data):
    """Numbers findings in reading order on the first render. Later renders keep
    every number already given, because the user answers by number, and number
    new findings after the highest one."""
    tpos = {t["id"]: i for i, t in enumerate(data["targets"])}
    dpos = {d: i for i, (d, _) in enumerate(DOMAINS)}
    key = lambda f: (tpos[f["target"]], dpos[f["domain"]], f["type"] != "defect",
                     f["file"].lower(), f.get("line") or 0, f["check"])
    numbered = [f for f in data["findings"] if isinstance(f.get("n"), int)]
    new = sorted((f for f in data["findings"] if not isinstance(f.get("n"), int)), key=key)
    top = max((f["n"] for f in numbered), default=0)
    for k, f in enumerate(new, 1):
        f["n"] = top + k
    data["findings"].sort(key=lambda f: f["n"])


def counts(findings):
    c = {"defects": 0, "suggestions": 0, "fixed": 0, "open": 0, "deferred": 0, "accepted": 0}
    for f in findings:
        c["defects" if f["type"] == "defect" else "suggestions"] += 1
        c[f["status"]] += 1
    return c


def open_by_check(findings):
    by = {}
    for f in findings:
        if f["status"] in ("open", "deferred"):
            by[f["check"]] = by.get(f["check"], 0) + 1
    return ", ".join("%s×%d" % (k, v) for k, v in sorted(by.items(), key=lambda kv: (-kv[1], kv[0]))) or "none"


def tool_of(f):
    if f.get("tool"):
        return f["tool"]
    m = re.search(r"(?:^|/)(skills|agents|commands|output-styles)/([^/]+)", f["file"])
    if m:
        return m.group(2)[:-3] if m.group(2).endswith(".md") else m.group(2)
    return os.path.basename(f["file"])


# rendering -----------------------------------------------------------------

def text(value):
    """Escaped text with `code` spans (any number of backticks) and [text](https://...) links."""
    out = html.escape(str(value), quote=False)
    codes = []

    def keep(m):
        codes.append("<code>%s</code>" % m.group(2).strip())
        return "\x00%d\x00" % (len(codes) - 1)

    out = re.sub(r"(`+)(.+?)\1", keep, out)  # code first, so links inside code stay literal
    out = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", lambda m: "<a href=\"%s\">%s</a>" % (m.group(2), m.group(1)), out)
    return re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], out)


def finding_rows(findings):
    rows = []
    for f in findings:
        where = "<span class=\"mono\">%s</span>" % html.escape(f["file"])
        if f.get("line"):
            where += "<span class=\"mono\">:%d</span>" % f["line"]
        rows.append(
            "<tr id=\"f%d\"><td class=\"num\">#%d</td><td><span class=\"check\">%s</span></td>"
            "<td><span class=\"pill %s\">%s</span></td><td class=\"where\">%s</td>"
            "<td class=\"text\"><blockquote>%s</blockquote></td><td class=\"text\">%s</td>"
            "<td><span class=\"pill action\">%s</span></td><td><span class=\"pill %s\">%s</span></td></tr>"
            % (f["n"], f["n"], html.escape(f["check"]), f["type"], f["type"].capitalize(), where,
               text(f["evidence"]), text(f["fix"]), ACTIONS[f["action"]], f["status"], f["status"].capitalize()))
    return ("<div class=\"scroll\"><table><thead><tr><th>#</th><th>Check</th><th>Type</th><th>File</th>"
            "<th>Evidence</th><th>Proposed fix</th><th>Action</th><th>Status</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


def figure(value, label, cls=""):
    return "<div class=\"figure %s\"><b>%s</b><span>%s</span></div>" % (cls, value, label)


def read_log(path):
    """Rows of the run log's table, oldest first, as lists of cells."""
    if not path or not os.path.isfile(path):
        return [], []
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    header, rows = None, []
    for line in lines:
        if not line.startswith("|"):
            if header is not None and rows:
                break
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = cells
        elif not set("".join(cells)) <= set("-: "):
            rows.append(cells)
    return header or [], rows


def log_row(data, report):
    c = counts(data["findings"])
    names = ", ".join(t["name"] for t in data["targets"])
    audited = sum(t["files"].get("audited", 0) for t in data["targets"])
    return [data["date"], data["mode"], names, str(audited), str(len(data["findings"])), str(c["fixed"]),
            str(c["deferred"]), open_by_check(data["findings"]), report]


def cell_html(cell):
    m = re.match(r"^\[([^\]]+)\]\((https?://[^)]+)\)$", cell)
    if m:
        return "<a href=\"%s\">%s</a>" % (html.escape(m.group(2)), html.escape(m.group(1)))
    return text(cell)


def render(data, log_path):
    c = counts(data["findings"])
    audited = sum(t["files"].get("audited", 0) for t in data["targets"])
    parts = []
    nav = "".join("<li><a href=\"#%s\">%s</a></li>" % (t["id"], html.escape(t["name"])) for t in data["targets"])
    parts.append("<header><h1>Environment audit</h1><p class=\"meta\">%s · %s run · %d targets</p>"
                 "<ul class=\"targets\">%s</ul></header>" % (data["date"], data["mode"], len(data["targets"]), nav))
    parts.append("<section aria-label=\"Key figures\"><div class=\"figures\">%s</div></section>" % "".join([
        figure(len(data["targets"]), "Targets"), figure(audited, "Files audited"),
        figure(c["defects"], "Defects", "defect"), figure(c["suggestions"], "Suggestions", "suggest"),
        figure(c["fixed"], "Fixed", "ok"), figure(c["open"] + c["deferred"], "Open")]))

    sb = [f for f in data["findings"] if f["action"] == "skill-builder" and f["status"] in ("open", "deferred")]
    body = "<p class=\"empty\">None. No finding needs skill-builder.</p>"
    if sb:
        groups = {}
        for f in sb:
            groups.setdefault(tool_of(f), []).append(f)
        items = "".join("<li><code>%s</code>: %s</li>" % (
            html.escape(name), ", ".join("<a href=\"#f%d\">#%d %s</a>" % (f["n"], f["n"], html.escape(f["check"])) for f in fs))
            for name, fs in sorted(groups.items()))
        body = ("<p>These findings change what a tool does or how its workflow runs. Run <code>skill-builder</code> "
                "for each tool, with the findings as evidence; the audit does not apply them.</p><ul class=\"plain\">%s</ul>" % items)
    parts.append("<section><h2>Work for skill-builder</h2>%s</section>" % body)

    for t in data["targets"]:
        fs = [f for f in data["findings"] if f["target"] == t["id"]]
        tc = counts(fs)
        files = t.get("files", {})
        head = ("<div class=\"target-head\"><h2 id=\"%s\">%s</h2><p class=\"meta mono\">%s</p>"
                "<p class=\"meta\">%d files audited, %d exempt, %d excluded · %d defects, %d suggestions, %d fixed</p></div>"
                % (t["id"], html.escape(t["name"]), html.escape(t["path"]), files.get("audited", 0),
                   files.get("exempt", 0), files.get("excluded", 0), tc["defects"], tc["suggestions"], tc["fixed"]))
        blocks = [head]
        for note in t.get("notes", []):
            blocks.append("<p>%s</p>" % text(note))
        for dom, label in DOMAINS:
            if dom == "workspace" and t["kind"] != "workspace":
                continue
            dfs = [f for f in fs if f["domain"] == dom]
            content = finding_rows(dfs) if dfs else "<p class=\"empty\">No findings.</p>"
            blocks.append("<div class=\"domain\"><h3>%s</h3>%s</div>" % (label, content))
        not_run = t.get("not_run", [])
        nr = ("<ul class=\"plain\">%s</ul>" % "".join("<li>%s</li>" % text(x) for x in not_run)) if not_run \
            else "<p class=\"empty\">Every check ran.</p>"
        blocks.append("<div class=\"domain\"><h3>Checks that did not run</h3>%s</div>" % nr)
        parts.append("<section class=\"target\">%s</section>" % "".join(blocks))

    if data.get("skipped_targets"):
        parts.append("<section><h2>Skipped folders</h2><ul class=\"plain\">%s</ul></section>" % "".join(
            "<li><span class=\"mono\">%s</span>: %s</li>" % (html.escape(str(s["path"])), text(s["reason"]))
            for s in data["skipped_targets"]))

    rec = data.get("recurring", [])
    rec_html = ("<ul class=\"plain\">%s</ul>" % "".join(
        "<li><span class=\"check\">%s</span> %s</li>" % (html.escape(r["check"]), text(r["proposal"])) for r in rec)) \
        if rec else "<p class=\"empty\">None. No check has been open three runs in a row.</p>"
    parts.append("<section><h2>Recurring findings</h2>%s</section>" % rec_html)

    parts.append(
        "<section><h2>Built-in checks to run</h2><p>This audit cannot see Claude Code's own usage data or installation. "
        "Run these yourself in a Claude Code session:</p><ul class=\"plain\">"
        "<li><code>/skill-doctor</code>: what each skill costs in context and how often it is used, to find skills to turn off "
        "(<a href=\"https://code.claude.com/docs/en/skills#find-unused-skills\">docs</a>).</li>"
        "<li><code>/doctor</code>: installation health, unused extensions, slow hooks, and permissions "
        "(<a href=\"https://code.claude.com/docs/en/skills#check-your-setup-with-%2Fdoctor\">docs</a>).</li></ul></section>")

    header, rows = read_log(log_path)
    current = log_row(data, "this report")
    shown = [current] + list(reversed(rows))[:LOG_SHOWN - 1]
    cols = LOG_HEADER
    trs = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % cell_html(c) for c in (r + [""] * len(cols))[:len(cols)]) for r in shown)
    parts.append("<section><h2>Run log</h2><div class=\"scroll\"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div></section>"
                 % ("".join("<th>%s</th>" % c for c in cols), trs))
    parts.append("<footer>Generated by <code>environment-audit</code>. Finding numbers match the chat summary.</footer>")
    return "\n".join(parts)


def cmd_render(args):
    data = load(args.report)
    errors = validate(data)
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=1))
        sys.exit(1)
    order(data)
    save(args.report, data)
    with open(TEMPLATE, encoding="utf-8") as f:
        template = f.read()
    title = "Environment audit %s" % data["date"]
    page = template.replace("{{TITLE}}", html.escape(title)).replace("{{CONTENT}}", render(data, args.log))
    if args.standalone:
        head, _, body = page.partition("<!-- body -->")
        page = ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
                "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
                "%s</head>\n<body>%s</body>\n</html>\n" % (head, body))
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(page)
    c = counts(data["findings"])
    print(json.dumps({"ok": True, "out": args.out.replace(os.sep, "/"), "findings": len(data["findings"]),
                      "defects": c["defects"], "suggestions": c["suggestions"], "fixed": c["fixed"],
                      "open": c["open"] + c["deferred"]}, ensure_ascii=False))


# log -----------------------------------------------------------------------

def cmd_log(args):
    data = load(args.report)
    errors = validate(data)
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=1))
        sys.exit(1)
    report = args.report_link
    report = "[report](%s)" % report if re.match(r"^https?://", report) else "`%s`" % report.replace("\\", "/")
    with open(args.log, encoding="utf-8") as f:
        lines = f.read().splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith("| Date")), None)
    if start is None:
        print(json.dumps({"ok": False, "errors": ["run log has no table starting with '| Date'"]}))
        sys.exit(1)
    end = start + 2
    while end < len(lines) and lines[end].startswith("|"):
        end += 1
    rows = lines[start + 2:end]
    if rows and rows[-1].rstrip().endswith("| %s |" % report):
        rows.pop()  # the same run logged again after its fix rounds: replace its row
    rows = (rows + ["| " + " | ".join(c.replace("|", "/") for c in log_row(data, report)) + " |"])[-LOG_KEEP:]
    lines[start:end] = ["| " + " | ".join(LOG_HEADER) + " |", "|" + " --- |" * len(LOG_HEADER)] + rows
    with open(args.log, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(json.dumps({"ok": True, "rows": len(rows)}))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Run file, report page, and run log for environment-audit.")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init")
    p.add_argument("report")
    p.add_argument("--discover", required=True)
    p.add_argument("--mode", required=True, choices=["scheduled", "on request"])
    p.add_argument("--date", required=True)
    p = sub.add_parser("render")
    p.add_argument("report")
    p.add_argument("--log")
    p.add_argument("--out", required=True)
    p.add_argument("--standalone", action="store_true")
    p = sub.add_parser("log")
    p.add_argument("report")
    p.add_argument("--log", required=True)
    p.add_argument("--report", dest="report_link", required=True)
    args = parser.parse_args()
    {"init": cmd_init, "render": cmd_render, "log": cmd_log}[args.command](args)


if __name__ == "__main__":
    main()
