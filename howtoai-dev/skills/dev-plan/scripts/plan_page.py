#!/usr/bin/env python3
"""Render a dev-plan change folder into its plan page (standard library only).

  py -3 -I plan_page.py render <change folder> [--out <file>] [--artifact]

Reads plan.md (the source of truth), the last plan-review-<n>.md, and wi/<n>.md, fills
assets/plan-page.html, and writes <change folder>/plan.html unless --out says otherwise.
--artifact leaves out the document skeleton (doctype, html, head, body), because the Artifact
tool wraps the page itself. Prints one JSON object; "ok": false carries the error.
"""
import argparse
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "assets", "plan-page.html")
HIGH = {"Blocker", "Major"}


class Fail(Exception):
    pass


# Markdown -----------------------------------------------------------------------------------

def inline(text):
    parts = re.split(r"(`[^`]*`)", text)
    out = []
    for p in parts:
        if len(p) >= 2 and p.startswith("`") and p.endswith("`"):
            out.append("<code>%s</code>" % html.escape(p[1:-1]))
            continue
        s = html.escape(p, quote=False)

        def link(m):
            label, url = m.group(1), html.unescape(m.group(2))
            if re.match(r"https?://", url):
                return '<a href="%s">%s</a>' % (html.escape(url), label)
            return label

        s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
        out.append(s)
    return "".join(out)


def split_row(line):
    s = line.strip().strip("|")
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


def is_sep(line):
    cells = split_row(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in cells)


def table_html(rows):
    head, body = rows[0], rows[1:]
    h = "".join('<th scope="col">%s</th>' % inline(c) for c in head)
    b = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % inline(c) for c in r) for r in body)
    return '<div class="scroll"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (h, b)


def blocks(md):
    """Convert a Markdown fragment (no H1 or H2) to HTML."""
    lines = md.splitlines()
    out, para, i = [], [], 0
    stack = []  # (indent, tag)

    class Frag(str):
        """A list fragment: joined to the fragment before it with no line break."""

    def emit(s):
        if out and isinstance(out[-1], Frag):
            out[-1] = Frag(out[-1] + s)
        else:
            out.append(Frag(s))

    def flush_para():
        if para:
            out.append("<p>%s</p>" % inline(" ".join(para)))
            para.clear()

    def close_lists(to=-1):
        while stack and stack[-1][0] > to:
            emit("</li></%s>" % stack.pop()[1])

    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if not s:
            flush_para()
            i += 1
            continue
        if s.startswith("```"):
            flush_para(); close_lists()
            code = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            out.append("<pre><code>%s</code></pre>" % html.escape("\n".join(code)))
            i += 1
            continue
        m = re.match(r"(#{3,4})\s+(.*)", s)
        if m:
            flush_para(); close_lists()
            lv = len(m.group(1))
            out.append("<h%d>%s</h%d>" % (lv, inline(m.group(2)), lv))
            i += 1
            continue
        if s.startswith("|") and i + 1 < len(lines) and is_sep(lines[i + 1]):
            flush_para(); close_lists()
            rows = [split_row(s)]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(split_row(lines[i]))
                i += 1
            out.append(table_html(rows))
            continue
        m = re.match(r"(\s*)([-*]|\d+\.)\s+(.*)", line)
        if m:
            flush_para()
            indent = len(m.group(1).replace("\t", "    "))
            tag = "ol" if m.group(2)[0].isdigit() else "ul"
            if stack and indent > stack[-1][0]:
                emit("<%s><li>" % tag)
                stack.append((indent, tag))
            else:
                close_lists(indent)
                if stack and stack[-1][0] == indent:
                    emit("</li><li>")
                else:
                    emit("<%s><li>" % tag)
                    stack.append((indent, tag))
            emit(inline(m.group(3)))
            i += 1
            continue
        if stack and line.startswith(" "):
            emit(" " + inline(s))
            i += 1
            continue
        close_lists()
        para.append(s)
        i += 1
    flush_para()
    close_lists()
    return "\n".join(out)


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "section"


def sections(md):
    """Split plan.md into (preamble, [(heading, body)])."""
    parts = re.split(r"^## +(.+)$", md, flags=re.M)
    pre, secs = parts[0], []
    for k in range(1, len(parts), 2):
        secs.append((parts[k].strip(), parts[k + 1]))
    return pre, secs


def first_table_rows(body):
    lines = body.splitlines()
    for i, l in enumerate(lines):
        if l.strip().startswith("|") and i + 1 < len(lines) and is_sep(lines[i + 1]):
            head = [c.lower() for c in split_row(l)]
            rows = []
            for r in lines[i + 2:]:
                if not r.strip().startswith("|"):
                    break
                rows.append(dict(zip(head, split_row(r))))
            return head, rows
    return [], []


# Page ----------------------------------------------------------------------------------------

def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def review_info(folder):
    files = []
    for name in os.listdir(folder):
        m = re.fullmatch(r"plan-review-(\d+)\.md", name)
        if m:
            files.append((int(m.group(1)), name))
    if not files:
        return 0, None
    files.sort()
    n, name = files[-1]
    return n, read(os.path.join(folder, name))


def open_high(review):
    count = 0
    # the heading itself: the Problems list above it quotes claims, which can name it
    sec = re.split(r"(?m)^## Findings[ \t]*$", review, maxsplit=1)[-1].split("\n## ", 1)[0]
    lines = sec.splitlines()
    for i, l in enumerate(lines):
        if l.strip().startswith("|") and i + 1 < len(lines) and is_sep(lines[i + 1]):
            head = [c.lower() for c in split_row(l)]
            for r in lines[i + 2:]:
                if not r.strip().startswith("|"):
                    break
                row = dict(zip(head, split_row(r)))
                res = row.get("resolution", "").strip().lower()
                if row.get("severity") in HIGH and (not res or res == "open"):
                    count += 1
    return count


def work_items(folder):
    wdir = os.path.join(folder, "wi")
    items = []
    if not os.path.isdir(wdir):
        return items
    for name in os.listdir(wdir):
        m = re.fullmatch(r"(\d+)\.md", name)
        if not m:
            continue
        text = read(os.path.join(wdir, name))
        t = re.search(r"^# WI \d+:\s*(.+)$", text, flags=re.M)
        dep = re.search(r"Depends on:\s*([^·\n]+)", text)
        trk = re.search(r"Tracker:\s*([^·\n]+)", text)
        goal = re.search(r"^## Goal\s*\n+(.+?)(?:\n\n|\n##|$)", text, flags=re.M | re.S)
        items.append((int(m.group(1)), t.group(1).strip() if t else name,
                      goal.group(1).strip() if goal else "", dep.group(1).strip() if dep else "none",
                      trk.group(1).strip() if trk else "Markdown"))
    return sorted(items)


def fill(template, values, drop):
    for name in drop:
        template = re.sub(r"[ \t]*<!-- section:%s -->.*?<!-- /section:%s -->\n?" % (name, name), "", template, flags=re.S)
    template = re.sub(r"[ \t]*<!-- /?section:\w+ -->\n?", "", template)
    for k, v in values.items():
        template = template.replace("{{%s}}" % k, v)
    left = re.findall(r"\{\{[A-Z_]+\}\}", template)
    if left:
        raise Fail("template slots left unfilled: %s" % sorted(set(left)))
    return template


def strip_skeleton(page):
    head = re.search(r"<head>(.*?)</head>", page, flags=re.S).group(1)
    body = re.search(r"<body>(.*?)</body>", page, flags=re.S).group(1)
    head = re.sub(r'<meta charset="utf-8">\n|<meta name="viewport"[^>]*>\n', "", head)
    return head.strip() + "\n" + body.strip() + "\n"


def render(folder, out, artifact):
    pp = os.path.join(folder, "plan.md")
    if not os.path.exists(pp):
        raise Fail("no plan.md in %s" % folder)
    md = read(pp)
    m = re.search(r"^# (.+?)(?::\s*plan)?\s*$", md, flags=re.M)
    if not m:
        raise Fail("plan.md has no '# <title>: plan' heading")
    title = m.group(1).strip()
    pre, secs = sections(md)
    status_line = re.search(r"^Change `([^`]+)`(.*)$", pre, flags=re.M)
    change_id = status_line.group(1) if status_line else os.path.basename(os.path.abspath(folder))
    tail = status_line.group(2) if status_line else ""
    size_m = re.search(r"Size:\s*([A-Za-z{}/ ]+?)\s*(?:·|$)", tail)
    status_m = re.search(r"Status:\s*(.+)$", tail)
    size = size_m.group(1).strip() if size_m else "?"
    sp = os.path.join(folder, "state.json")
    if os.path.exists(sp):
        st = json.loads(read(sp))
        size = st.get("size") or size
    status = status_m.group(1).strip() if status_m else "waiting for approval"

    goal, decisions, open_items, body_html = "", 0, [], []
    for head, body in secs:
        key = head.lower()
        if key == "goal":
            goal = " ".join(l.strip() for l in body.strip().split("\n\n")[0].splitlines())
            continue
        if key == "decisions":
            _, rows = first_table_rows(body)
            decisions = sum(1 for r in rows if r and not list(r.values())[0].startswith("{"))
        if key.startswith("assumptions"):
            for l in body.splitlines():
                om = re.match(r"\s*[-*]\s+\*\*Open:?\*\*:?\s*(.+)", l)
                if om and om.group(1).strip().lower().rstrip(".") not in ("none", "{question still waiting for an answer; \"none\"}"):
                    open_items.append(om.group(1).strip())
        sid = "s-" + slug(head)
        body_html.append('  <section class="section-rule plan-section" aria-labelledby="%s">\n    <h2 id="%s">%s</h2>\n%s\n  </section>'
                         % (sid, sid, inline(head), blocks(body)))

    rounds, review = review_info(folder)
    left = open_high(review) if review else 0
    wis = work_items(folder)
    drop = []
    if not open_items:
        drop.append("open")
    review_table, review_note = "", ""
    if review:
        res = re.search(r"Result:\s*(clean|not clean)", review)
        resolved = {k: len(re.findall(r"\|\s*%s:" % k, review)) for k in ("fixed", "decided", "asked", "declined")}
        review_note = "Round %d, result %s. Resolutions: %s." % (
            rounds, res.group(1) if res else "unknown",
            ", ".join("%d %s" % (v, k) for k, v in resolved.items()))
        summ = review.split("## Summary", 1)[-1].split("\n## ", 1)[0]
        review_table = blocks("\n".join(l for l in summ.splitlines() if l.strip().startswith("|")))
    else:
        drop.append("review")
    if wis:
        rows = [["#", "Title", "Goal", "Depends on", "Tracker"]] + [[str(n), t, g, d, k] for n, t, g, d, k in wis]
        wi_table = table_html(rows)
    else:
        drop.append("wi")
        wi_table = ""

    values = {
        "TITLE": html.escape(title), "GOAL": inline(goal) if goal else "No goal written yet.",
        "CHANGE_ID": html.escape(change_id), "STATUS": inline(status),
        "SIZE": html.escape(size), "DECISIONS": str(decisions),
        "OPEN": str(len(open_items)), "OPEN_CLASS": "warn" if open_items else "ok",
        "OPEN_LIST": "<ul>%s</ul>" % "".join("<li>%s</li>" % inline(x) for x in open_items),
        "ROUNDS": str(rounds), "FINDINGS": str(left), "FINDINGS_CLASS": "danger" if left else "ok",
        "WI_COUNT": str(len(wis)), "PLAN_SECTIONS": "\n\n".join(body_html),
        "REVIEW_NOTE": html.escape(review_note), "REVIEW_TABLE": review_table, "WI_TABLE": wi_table,
    }
    page = fill(read(TEMPLATE), values, drop)
    if artifact:
        page = strip_skeleton(page)
    out = out or os.path.join(folder, "plan.html")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(page)
    return {"ok": True, "out": os.path.abspath(out).replace(os.sep, "/"), "artifact": artifact,
            "title": title, "size": size, "decisions": decisions, "open_questions": len(open_items),
            "review_rounds": rounds, "open_blockers_majors": left, "work_items": len(wis)}


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Render a dev-plan change folder into its plan page.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render")
    r.add_argument("folder")
    r.add_argument("--out")
    r.add_argument("--artifact", action="store_true")
    a = ap.parse_args(argv)
    try:
        res = render(a.folder, a.out, a.artifact)
    except Fail as e:
        res = {"ok": False, "error": str(e)}
    except Exception as e:  # an unexpected shape is a plan error, never a traceback
        res = {"ok": False, "error": "cannot render: %s" % e}
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
