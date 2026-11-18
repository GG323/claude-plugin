"""Render a skill-builder plan (plan.json) into the plan page.

Usage:
  py -3 render_plan.py <plan.json> [--out <page.html>] [--artifact]

  --out       Where to write the page. Default: plan.html next to the plan file (the sandbox,
              _sandbox/<name>/). A revised plan is written to the same path, replacing the
              earlier page.
  --artifact  Leave out the document skeleton (doctype, html, head, body), because the Artifact
              tool adds its own when it publishes. Without it the page is a standalone file that
              opens directly in a browser.

The plan is validated first (dates, and the type of every key); on any error the script prints
{"ok": false, "errors": [...]} and exits 1 without writing. Standard library only. Writes only
the output file and its folder. All text is HTML-escaped. Text fields may use `code` spans and
[text](https://...) links. Reuse cards are read by the user: write them in plain words.

The plan file (plan.json). Keys marked * are required; every other key may be left out,
and a section whose keys are all missing shows a stated empty text instead.
  {
    "name"*: "weekly-sales-report",       slug: lowercase letters, digits, hyphens; names the
                                           default output folder
    "display_name": "Weekly sales report", shown on the page; default: name
    "title": "Weekly sales report plan",   page and artifact title; default: "<display_name> plan"
    "kind"*: "skill",                      plain word for what is built: skill, tool, subagent,
                                           hook, mod, plugin, procedure, scheduled procedure, ...
    "change"*: "new" | "change" | "repair" | "remake",
    "date"*: "YYYY-MM-DD",                 from the system clock
    "revision": 1,                         plan revision shown on the page; default 1
    "status": "waiting" | "approved",      default "waiting"; "approved" needs "approved_on"
    "approved_on": "YYYY-MM-DD",
    "summary"*: {
      "goal"*: "one or two sentences: what it is for",
      "used_by": "who uses the result",
      "starts": "when it runs: on request, every Monday at 8:00, ...",
      "from_where"*: "where the input comes from",
      "to_where"*: "where the result goes",
      "from_what"*: "what goes in",
      "to_what"*: "what comes out",
      "changes": ["for a change or repair: what changes from today, one line each"]
    },
    "reuse": null | {                      leave out or null when no Reuse decision applies
                                           (a change to an existing skill or tool); the
                                           section is then removed from the page
      "recommendation"*: "Build new, because ...",
      "choice": "reuse <name>" | "adapt <name>" | "build new",   the user's answer, once given
      "candidates": [{
        "name"*: "...", "kind": "what it is, at the user's level: 'a pack of 27 tools', 'a skill'",
        "fit"*: "covers" | "partly covers" | "related",
        "does": "what it does, one line", "lacks": "what it lacks for this plan",
        "mark": "anthropic | curated | reviewed | local | unaudited",   shown in plain words
        "source": "https://... or a path", "takes": "what reusing it takes"
      }],
      "searched": "sources searched and the index date; shown when there are no candidates",
      "failed_sources": ["a source that could not be searched, with the reason"]
    },
    "steps"*: [{"what"*: "step, in plain words", "goal"*: "what the step is for"}],
    "will": ["what it will do"],
    "wont": ["what it will not do"],
    "actions": [{                          everything that changes something outside the chat
      "action"*: "Saves the report as a draft in your Gmail",
      "control"*: "reads" | "draft" | "asks" | "auto",
                                           reads only | draft only, never sends | asks you
                                           first | runs without asking
      "note": "..."
    }],
    "access": ["what it needs access to: a folder, an account, a connector"],
    "assumed": [{"item"*: "Language", "value"*: "English", "why": "you wrote in English"}],
    "questions": [{                        numbers are stable: a revised plan keeps every
                                           number already given and adds new ones after them
      "n"*: 1, "question"*: "...", "recommended"*: "...", "why": "...",
      "status": "open" | "answered",       default "open"
      "answer": "the user's answer, once given"
    }],
    "details": {
      "route": "main route | hand off to update-config | ...",
      "types": ["skill type and the requirements applied, one line each"],
      "placement": "where the files go and why",
      "effort": "thinking effort and model per step",
      "design": "look and design decision",
      "files": [{"path"*: "SKILL.md", "purpose"*: "..."}],
      "lessons": [{"id"*: "L-055", "note"*: "how it is applied"}],
      "installs": [{"name"*: "...", "why"*: "...", "license": "..."}],
      "notes": ["anything else the builder or checker needs"]
    }
  }
"""

import argparse
import datetime
import html
import json
import os
import re
import sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(SKILL_DIR, "assets", "plan.html")

CHANGES = {"new": "A plan to build a new {kind}.", "change": "A plan to change this {kind}.",
           "repair": "A plan to fix this {kind}.", "remake": "A plan to rebuild this {kind} from the start."}
LABELS = {"new": "Plan · new {kind}", "change": "Plan · change", "repair": "Plan · fix",
          "remake": "Plan · rebuild"}
FITS = {"covers": ("ok", "Covers"), "partly covers": ("warn", "Partly covers"), "related": ("", "Related")}
CONTROLS = {"reads": ("", "Reads only"), "draft": ("", "Draft only, never sends"),
            "asks": ("accent", "Asks you first"), "auto": ("warn", "Runs without asking")}
MARKS = {"anthropic": "Made by Anthropic", "curated": "On a checked list", "reviewed": "Reviewed",
         "local": "Already on this computer", "unaudited": "Not yet safety-checked"}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]


# validation ----------------------------------------------------------------

def _str(v):
    return isinstance(v, str) and v.strip() != ""


def _date(v):
    if not (isinstance(v, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", v)):
        return False
    try:
        datetime.date.fromisoformat(v)
    except ValueError:
        return False
    return True


def _int(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 1


def _items(obj, key):
    """The list at obj[key], or [] when it is missing or not a list (typed() reports the latter)."""
    v = obj.get(key) if isinstance(obj, dict) else None
    return v if isinstance(v, list) else []


def typed(e, obj, where, texts=(), lists=(), objects=()):
    """Optional keys: texts must be strings, lists lists of non-empty strings, objects lists of objects."""
    if not isinstance(obj, dict):
        return
    for key in texts:
        if obj.get(key) is not None and not isinstance(obj[key], str):
            e.append("%s: %s must be text" % (where, key))
    for key in lists:
        v = obj.get(key)
        if v is not None and not (isinstance(v, list) and all(_str(x) for x in v)):
            e.append("%s: %s must be a list of texts, one item each" % (where, key))
    for key in objects:
        v = obj.get(key)
        if v is not None and not (isinstance(v, list) and all(isinstance(x, dict) for x in v)):
            e.append("%s: %s must be a list of objects" % (where, key))


def validate(p):
    e = []
    need = lambda obj, key, where: e.append("%s: %s is missing or empty" % (where, key)) \
        if not (isinstance(obj, dict) and _str(obj.get(key))) else None
    if not isinstance(p, dict):
        return ["the plan must be a JSON object"]
    if not (isinstance(p.get("name"), str) and re.match(r"^[a-z0-9][a-z0-9-]*$", p["name"])):
        e.append("name must be a slug: lowercase letters, digits, and hyphens")
    need(p, "kind", "plan")
    for key in ("display_name", "title"):
        if key in p and not _str(p[key]):
            e.append("%s must be non-empty text" % key)
    if p.get("change") not in CHANGES:
        e.append("change must be new, change, repair, or remake")
    for key in ("date", "approved_on"):
        if key in p and not _date(p[key]):
            e.append("%s must be a real date, YYYY-MM-DD" % key)
    if "date" not in p:
        e.append("date is missing (YYYY-MM-DD, from the system clock)")
    if p.get("status", "waiting") not in ("waiting", "approved"):
        e.append("status must be waiting or approved")
    if p.get("status") == "approved" and "approved_on" not in p:
        e.append("an approved plan needs approved_on")
    if "revision" in p and not _int(p["revision"]):
        e.append("revision must be a whole number from 1")
    typed(e, p, "plan", lists=("will", "wont", "access"), objects=("actions", "assumed", "questions"))
    s = p.get("summary")
    if not isinstance(s, dict):
        e.append("summary is missing")
    else:
        for key in ("goal", "from_where", "to_where", "from_what", "to_what"):
            need(s, key, "summary")
        typed(e, s, "summary", texts=("used_by", "starts"), lists=("changes",))
    r = p.get("reuse")
    if r is not None:
        if not isinstance(r, dict):
            e.append("reuse must be an object or null")
        else:
            need(r, "recommendation", "reuse")
            typed(e, r, "reuse", texts=("choice", "searched"), lists=("failed_sources",), objects=("candidates",))
            for k, c in enumerate(_items(r, "candidates")):
                need(c, "name", "reuse candidate %d" % (k + 1))
                if not isinstance(c, dict) or c.get("fit") not in FITS:
                    e.append("reuse candidate %d: fit must be covers, partly covers, or related" % (k + 1))
                typed(e, c, "reuse candidate %d" % (k + 1), texts=("kind", "does", "lacks", "mark", "source", "takes"))
    steps = p.get("steps")
    if not isinstance(steps, list) or not steps:
        e.append("steps must list at least one step")
    else:
        for k, st in enumerate(steps):
            need(st, "what", "step %d" % (k + 1))
            need(st, "goal", "step %d" % (k + 1))
    for k, a in enumerate(_items(p, "actions")):
        need(a, "action", "action %d" % (k + 1))
        if not isinstance(a, dict) or a.get("control") not in CONTROLS:
            e.append("action %d: control must be reads, draft, asks, or auto" % (k + 1))
        typed(e, a, "action %d" % (k + 1), texts=("note",))
    for k, a in enumerate(_items(p, "assumed")):
        need(a, "item", "assumed %d" % (k + 1))
        need(a, "value", "assumed %d" % (k + 1))
        typed(e, a, "assumed %d" % (k + 1), texts=("why",))
    seen = set()
    for k, q in enumerate(_items(p, "questions")):
        where = "question %d" % (k + 1)
        if not isinstance(q, dict) or not _int(q.get("n")):
            e.append("%s: n must be a whole number from 1" % where)
            continue
        if q["n"] in seen:
            e.append("%s: number %d is used twice; numbers are stable and unique" % (where, q["n"]))
        seen.add(q["n"])
        need(q, "question", where)
        need(q, "recommended", where)
        if q.get("status", "open") not in ("open", "answered"):
            e.append("%s: status must be open or answered" % where)
        if q.get("status") == "answered":
            need(q, "answer", where)
        typed(e, q, where, texts=("why", "answer"))
    d = p.get("details")
    if d is not None and not isinstance(d, dict):
        e.append("details must be an object")
        d = {}
    d = d or {}
    typed(e, d, "details", texts=("route", "placement", "effort", "design"), lists=("types", "notes"),
          objects=("files", "lessons", "installs"))
    for k, f in enumerate(_items(d, "files")):
        need(f, "path", "file %d" % (k + 1))
        need(f, "purpose", "file %d" % (k + 1))
    for k, l in enumerate(_items(d, "lessons")):
        need(l, "id", "lesson %d" % (k + 1))
        need(l, "note", "lesson %d" % (k + 1))
    for k, i in enumerate(_items(d, "installs")):
        need(i, "name", "install %d" % (k + 1))
        need(i, "why", "install %d" % (k + 1))
        typed(e, i, "install %d" % (k + 1), texts=("license",))
    return e


# rendering -----------------------------------------------------------------

def text(value):
    """Escaped text with `code` spans and [text](https://...) links."""
    # NUL is removed from the input first, so the NUL-delimited placeholders below cannot collide.
    out = html.escape(str(value).replace("\x00", ""), quote=False)
    codes = []

    def keep(m):
        codes.append("<code>%s</code>" % m.group(2).strip())
        return "\x00%d\x00" % (len(codes) - 1)

    out = re.sub(r"(`+)(.+?)\1", keep, out)
    # The URL is already escaped above (& is &amp;), so it goes into href as it is.
    out = re.sub(r"\[([^\]]+)\]\((https?://[^)\s\"]+)\)",
                 lambda m: '<a href="%s">%s</a>' % (m.group(2), m.group(1)), out)
    return re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], out)


def source_link(src):
    if re.match(r"^https?://\S+$", src or ""):
        return '<a href="%s">%s</a>' % (html.escape(src), html.escape(re.sub(r"^https?://", "", src).rstrip("/")))
    return '<span class="mono">%s</span>' % html.escape(src)


def long_date(iso):
    y, m, d = (int(x) for x in iso.split("-"))
    return "%d %s %d" % (d, MONTHS[m - 1], y)


def badge(cls, word):
    return '<span class="badge%s">%s</span>' % (" " + cls if cls else "", html.escape(word))


def bullets(items):
    return '<ul class="list">%s</ul>' % "".join("<li>%s</li>" % text(i) for i in items)


def empty(msg):
    return '<p class="muted">%s</p>' % text(msg)


def open_questions(p):
    return [q for q in p.get("questions") or [] if q.get("status", "open") == "open"]


def needs(p):
    if p.get("status") == "approved":
        return ('<div class="callout ok" role="note"><strong>Approved</strong><p>You approved this plan in chat on %s. '
                'The build follows it; any change to it is planned and approved again.</p></div>'
                % long_date(p["approved_on"]))
    qs = open_questions(p)
    r = p.get("reuse")
    parts = []
    if r and not _str(r.get("choice")):
        parts.append('<a href="#reuse">Reuse decision</a>')
    if qs:
        parts.append('<a href="#questions">%d open question%s</a>' % (len(qs), "" if len(qs) == 1 else "s"))
    what = ("The " + " and ".join(parts) + " need your answer. ") if parts else ""
    return ('<div class="callout" role="note"><strong>Waiting for your approval</strong><p>%sReply in chat with your answers '
            'and &ldquo;approve&rdquo;, or say what to change. Nothing is built until you approve the plan in chat.</p></div>'
            % what)


def summary(s):
    kv = [("Goal", s["goal"])]
    if _str(s.get("used_by")):
        kv.append(("Used by", s["used_by"]))
    if _str(s.get("starts")):
        kv.append(("Starts", s["starts"]))
    out = ['<p class="goal">%s</p>' % text(s["goal"])]
    extra = [(k, v) for k, v in kv[1:]]
    if extra:
        out.append('<dl class="kv">%s</dl>' % "".join("<div><dt>%s</dt><dd>%s</dd></div>" % (k, text(v)) for k, v in extra))

    def row(heading, a, b, la, lb):
        return ('<div class="flow-row"><h3>%s</h3><div class="flow-pair"><div class="flow-end"><span class="label">%s</span>'
                '<p>%s</p></div><span class="flow-arrow" aria-hidden="true">&rarr;</span><div class="flow-end">'
                '<span class="label">%s</span><p>%s</p></div></div></div>' % (heading, la, text(a), lb, text(b)))
    out.append('<div class="flow">%s%s</div>' % (
        row("From where, to where", s["from_where"], s["to_where"], "Takes its input from", "Puts the result in"),
        row("From what, to what", s["from_what"], s["to_what"], "Starts with", "Gives you")))
    if s.get("changes"):
        out.append('<div class="flow-row"><h3>What changes from today</h3>%s</div>' % bullets(s["changes"]))
    return "\n".join(out)


def reuse(r):
    out = []
    choice = r.get("choice")
    if _str(choice):
        out.append('<div class="callout ok" role="note"><strong>Your choice: %s</strong><p>Recommended was: %s</p></div>'
                   % (text(choice), text(r["recommendation"])))
    else:
        out.append('<div class="callout" role="note"><strong>Recommended</strong><p>%s</p></div>' % text(r["recommendation"]))
    cands = r.get("candidates") or []
    if cands:
        cards = []
        for c in cands:
            cls, word = FITS[c["fit"]]
            head = ['<h3>%s</h3>' % text(c["name"]), badge(cls, word)]
            if _str(c.get("kind")):
                head.append('<span class="meta">%s</span>' % text(c["kind"]))
            if _str(c.get("mark")):
                head.append(badge("", MARKS.get(c["mark"].strip(), c["mark"])))
            body = []
            for key, label in (("does", "What it does"), ("lacks", "What it lacks for this plan"), ("takes", "What reusing it takes")):
                if _str(c.get(key)):
                    body.append('<div><p class="label">%s</p><p>%s</p></div>' % (label, text(c[key])))
            if _str(c.get("source")):
                body.append('<div><p class="label">Where it comes from</p><p>%s</p></div>' % source_link(c["source"]))
            cards.append('<li class="card"><div class="card-head">%s</div><div class="card-body">%s</div></li>'
                         % ("".join(head), "".join(body)))
        out.append('<ul class="cards plain-list">%s</ul>' % "".join(cards))
    else:
        msg = "No existing skill, tool, or procedure covers or partly covers this plan, so it will be built new."
        if _str(r.get("searched")):
            msg += " Searched: " + r["searched"]
        out.append(empty(msg))
    if r.get("failed_sources"):
        out.append('<div class="callout warn" role="note"><strong>Sources that could not be searched</strong>%s</div>'
                   % bullets(r["failed_sources"]))
    return "\n".join(out)


def steps(st):
    return '<ol class="steps">%s</ol>' % "".join(
        '<li><h3>%s</h3><p class="muted">Goal: %s</p></li>' % (text(s["what"]), text(s["goal"])) for s in st)


def scope(p):
    out = []
    will, wont = p.get("will") or [], p.get("wont") or []
    if will or wont:
        out.append('<div class="two-col"><div><h3>It will</h3>%s</div><div><h3>It won&rsquo;t</h3>%s</div></div>' % (
            bullets(will) if will else empty("Nothing listed yet. Tell me in chat what it should do."),
            bullets(wont) if wont else empty("No limits listed yet. Tell me in chat anything it must leave alone.")))
    acts = p.get("actions") or []
    out.append('<h3>What it changes or sends</h3>')
    if acts:
        rows = []
        for a in acts:
            cls, word = CONTROLS[a["control"]]
            note = '<p class="meta">%s</p>' % text(a["note"]) if _str(a.get("note")) else ""
            rows.append('<li><div><p>%s</p>%s</div>%s</li>' % (text(a["action"]), note, badge(cls, word)))
        out.append('<ul class="rows">%s</ul>' % "".join(rows))
    else:
        out.append(empty("It changes and sends nothing outside this conversation. If that is wrong, say so in chat."))
    if p.get("access"):
        out.append('<h3>What it needs access to</h3>%s' % bullets(p["access"]))
    return "\n".join(out)


def assumed(items):
    if not items:
        return empty("Nothing was assumed: every choice came from your answers.")
    rows = "".join('<tr><th scope="row">%s</th><td>%s%s</td></tr>' % (
        text(a["item"]), text(a["value"]), ('<br><span class="meta">%s</span>' % text(a["why"])) if _str(a.get("why")) else "")
        for a in items)
    return ('<div class="scroll" role="region" aria-label="Assumed defaults" tabindex="0"><table>'
            '<caption class="visually-hidden">Assumed defaults and why</caption><thead><tr><th scope="col">Choice</th>'
            '<th scope="col">Assumed</th></tr></thead><tbody>%s</tbody></table></div>' % rows)


def questions(qs, approved=False):
    if not qs:
        if approved:
            return empty("No questions are open.")
        return empty("No questions are open. Reply “approve” in chat to start the build, or say what to change.")
    cards = []
    for q in sorted(qs, key=lambda q: q["n"]):
        answered = q.get("status") == "answered"
        rec = '<div class="recommend"><p class="label">Recommended</p><p>%s</p>%s</div>' % (
            text(q["recommended"]), ('<p class="meta">Why: %s</p>' % text(q["why"])) if _str(q.get("why")) else "")
        ans = '<div><p class="label">Your answer</p><p>%s</p></div>' % text(q["answer"]) if answered else ""
        cards.append('<li class="card" id="q%d"><div class="card-head"><h3>Question %d</h3>%s</div><p>%s</p>%s%s</li>' % (
            q["n"], q["n"], badge("ok", "Answered") if answered else badge("accent", "Open"), text(q["question"]), rec, ans))
    return '<ol class="cards plain-list">%s</ol>' % "".join(cards)


def details(d):
    out = []

    def block(heading, inner):
        out.append("<div><h3>%s</h3>%s</div>" % (heading, inner))
    if _str(d.get("route")):
        block("Route", "<p>%s</p>" % text(d["route"]))
    if d.get("types"):
        block("Type and requirements", bullets(d["types"]))
    for key, heading in (("placement", "Placement"), ("effort", "Thinking effort"), ("design", "Look and design")):
        if _str(d.get(key)):
            block(heading, "<p>%s</p>" % text(d[key]))
    if d.get("files"):
        block("Files", '<ul class="list">%s</ul>' % "".join(
            '<li><span class="mono">%s</span>: %s</li>' % (html.escape(f["path"]), text(f["purpose"])) for f in d["files"]))
    if d.get("lessons"):
        block("Lessons applied", '<ul class="list">%s</ul>' % "".join(
            '<li><span class="mono">%s</span>: %s</li>' % (html.escape(l["id"]), text(l["note"])) for l in d["lessons"]))
    if d.get("installs"):
        block("Installs after approval", '<ul class="list">%s</ul>' % "".join(
            "<li><strong>%s</strong>: %s%s</li>" % (text(i["name"]), text(i["why"]),
                                                    (" License: %s." % text(i["license"])) if _str(i.get("license")) else "")
            for i in d["installs"]))
    if d.get("notes"):
        block("Notes", bullets(d["notes"]))
    return "\n".join(out) or empty("No technical details recorded yet. Ask in chat for them before you approve, if you want them.")


def render(p, template):
    name = p.get("display_name") or p["name"]
    title = p.get("title") or "%s plan" % name
    kind = p["kind"].strip()
    lead = CHANGES[p["change"]].format(kind=kind) + " " + "It shows what it is for, how it will work, and what needs your answer."
    meta = "Revision %d &middot; %s &middot; prepared by <code>skill-builder</code>" % (p.get("revision", 1), long_date(p["date"]))
    foot = ("<p>Prepared by <code>skill-builder</code> on %s from this conversation. This page shows the plan; "
            "your answers and approval are given in chat.</p>" % long_date(p["date"]))
    page = template
    if p.get("reuse") is None:
        page = re.sub(r"\s*<!-- section:reuse -->.*?<!-- /section:reuse -->", "", page, flags=re.S)
    else:
        page = page.replace("  <!-- section:reuse -->\n", "").replace("  <!-- /section:reuse -->\n", "")
    slots = {
        "TITLE": html.escape(title), "KIND_LABEL": html.escape(LABELS[p["change"]].format(kind=kind)),
        "LEAD": html.escape(lead), "META": meta, "NEEDS": needs(p), "SUMMARY": summary(p["summary"]),
        "REUSE": reuse(p["reuse"]) if p.get("reuse") is not None else "", "STEPS": steps(p["steps"]), "SCOPE": scope(p),
        "ASSUMED": assumed(p.get("assumed") or []), "QUESTIONS": questions(p.get("questions") or [], p.get("status") == "approved"),
        "DETAILS": details(p.get("details") or {}), "FOOT": foot,
    }
    # One pass, so text that itself contains a double-brace word is never treated as a slot.
    return re.sub(r"\{\{([A-Z_]+)\}\}", lambda m: slots.get(m.group(1), m.group(0)), page)


def strip_skeleton(page):
    """Head content without charset and viewport metas, then body content: what the Artifact tool wraps."""
    head = re.search(r"<head>(.*?)</head>", page, flags=re.S).group(1)
    body = re.search(r"<body>(.*?)</body>", page, flags=re.S).group(1)
    head = re.sub(r'<meta charset="utf-8">\n|<meta name="viewport"[^>]*>\n', "", head)
    return head.strip() + "\n" + body.strip() + "\n"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Render a skill-builder plan.json into the plan page.")
    ap.add_argument("plan")
    ap.add_argument("--out", help="output file; default plan.html next to the plan file")
    ap.add_argument("--artifact", action="store_true", help="leave out the document skeleton for an Artifact publish")
    a = ap.parse_args()
    try:
        with open(a.plan, encoding="utf-8") as f:
            plan = json.load(f)
    except (OSError, ValueError) as ex:
        print(json.dumps({"ok": False, "errors": ["cannot read %s: %s" % (a.plan, ex)]}, ensure_ascii=False))
        sys.exit(1)
    try:
        errors = validate(plan)
    except Exception as ex:  # a shape validate() did not foresee is still a plan error, never a traceback
        errors = ["the plan could not be checked: %s" % ex]
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=1))
        sys.exit(1)
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.plan)), "plan.html")
    try:
        with open(TEMPLATE, encoding="utf-8") as f:
            page = render(plan, f.read())
        if a.artifact:
            page = strip_skeleton(page)
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write(page)
    except Exception as ex:
        print(json.dumps({"ok": False, "errors": ["cannot render or write %s: %s" % (out, ex)]}, ensure_ascii=False))
        sys.exit(1)
    print(json.dumps({"ok": True, "out": os.path.abspath(out).replace(os.sep, "/"), "artifact": a.artifact,
                      "open_questions": len(open_questions(plan)),
                      "reuse_open": bool(plan.get("reuse") is not None and not _str(plan["reuse"].get("choice")))},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
