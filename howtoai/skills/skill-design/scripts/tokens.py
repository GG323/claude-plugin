"""skill-design tokens tool: check, apply, or show the house design tokens.

  py -3 tokens.py [--root <skill folder>] check
  py -3 tokens.py [--root <skill folder>] apply <new.json>
  py -3 tokens.py [--root <skill folder>] show

`assets/design-tokens.json` is the only source of truth for design values. Two copies are generated
from it: the token block of `assets/house.css` (between `/* tokens:start */` and `/* tokens:end */`)
and, in `references/design-reference.html`, the same token block, the embedded
`<script type="application/json" id="design-tokens">`, the `token-fonts` link, and the version and date
shown on the page.

- `check` validates the schema, measures WCAG 2.2 contrast of every text and background pair in both
  themes for the resolved tokens and every palette option, and confirms both generated copies match.
  It prints every check it ran or skipped (PASS, FAIL, SKIP) and changes nothing. Exit 1 on any FAIL.
- `apply` validates a new file (for example one exported from the reference page's picker), sets its
  version to the current version + 1 and its date to today, and writes the tokens file and both copies.
  It writes nothing when validation fails.
- `show` prints the version, date, and choices.

Standard library only. `--root` points at a copy of the skill folder, for tests.

`design_studio.py` imports this module and reuses `validate`, `failures`, `resolve`, `parse_color`,
`ratio`, `css_block`, and the token name lists, so the studio refuses exactly what `apply` refuses.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html as htmllib
import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

SKILL = Path(__file__).resolve().parent.parent

COLORS = ["bg", "surface", "fg", "muted", "line", "line-strong", "accent", "accent-fg", "accent-bg",
          "danger", "danger-bg", "warn", "warn-bg", "ok", "ok-bg", "shade", "feature-bg", "feature-fg", "brand", "link"]
FONTS = ["font-display", "font-body", "font-mono"]
SIZES = ["text-xs", "text-sm", "text-md", "text-lg", "text-xl", "text-2xl", "text-figure", "text-display"]
TYPE_EXTRA = ["tracking-tight", "tracking-display", "leading-tight", "leading-body"]
SPACE = [f"s-{i}" for i in range(1, 10)]
RADIUS = ["r-1", "r-2", "r-3", "r-pill"]
BORDER = ["border-w", "border-w-strong"]
MOTION = ["dur-1", "dur-2", "ease"]
LAYOUT = ["page-max", "measure"]
OPTION_KEYS = {
    "palette": ["light", "dark"],
    "type": ["fonts_url"] + FONTS + TYPE_EXTRA,
    "shape": RADIUS + BORDER + ["shadow"],
    "density": SPACE + SIZES,
}
TOKEN_GROUPS = {"light": COLORS, "dark": COLORS, "font": FONTS, "type": SIZES + TYPE_EXTRA, "space": SPACE,
                "radius": RADIUS, "border": BORDER, "shadow": ["shadow"], "motion": MOTION, "layout": LAYOUT}
SURFACES = ["web-page", "artifact-report", "dashboard", "slide-deck", "mod", "word-document"]

# (foreground, background, minimum ratio, what it is). 4.5:1 is WCAG 2.2 AA for normal text;
# 7:1 is the house target for body text; 3:1 is the non-text minimum for control borders.
PAIRS = [("fg", "bg", 7.0, "body text on page (house target 7:1)"),
         ("fg", "surface", 7.0, "body text on cards (house target 7:1)"),
         ("muted", "bg", 4.5, "muted text on page"),
         ("muted", "surface", 4.5, "muted text on cards"),
         ("accent", "bg", 4.5, "accent text and links on page"),
         ("accent", "surface", 4.5, "accent text and links on cards"),
         ("accent-fg", "accent", 4.5, "primary button text"),
         ("accent", "accent-bg", 4.5, "accent badge"),
         ("fg", "accent-bg", 4.5, "info callout text")]
for _s in ("danger", "warn", "ok"):
    PAIRS += [(_s, f"{_s}-bg", 4.5, f"{_s} badge"),
              (_s, "bg", 4.5, f"{_s} text on page"),
              (_s, "surface", 4.5, f"{_s} figure on cards"),
              ("fg", f"{_s}-bg", 4.5, f"{_s} callout text")]
PAIRS += [("feature-fg", "feature-bg", 4.5, "feature card text"),
          ("link", "bg", 4.5, "link on page"),
          ("link", "surface", 4.5, "link on cards"),
          ("line-strong", "surface", 3.0, "control borders on cards (non-text)"),
          ("line-strong", "bg", 3.0, "control borders on page (non-text)")]

START, END = "/* tokens:start */", "/* tokens:end */"
EMBED_RE = re.compile(r'(<script type="application/json" id="design-tokens">)(.*?)(</script>)', re.S)
FONT_LINK_RE = re.compile(r'(<link rel="stylesheet" id="token-fonts" href=")([^"]*)(">)')
SPAN_RE = {k: re.compile(r'(<span data-tokens="%s">)([^<]*)(</span>)' % k) for k in ("version", "date")}


# ---------------------------------------------------------------- color

def parse_color(text: str):
    t = str(text).strip().lower()
    m = re.fullmatch(r"#([0-9a-f]{3}|[0-9a-f]{6})", t)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)) + (1.0,)
    m = re.fullmatch(r"rgba?\(\s*(\d+)[\s,]+(\d+)[\s,]+(\d+)\s*(?:[,/]\s*([\d.]+%?)\s*)?\)", t)
    if m:
        a = m.group(4)
        alpha = 1.0 if a is None else (float(a[:-1]) / 100 if a.endswith("%") else float(a))
        return tuple(int(m.group(i)) / 255 for i in (1, 2, 3)) + (alpha,)
    return None


def luminance(c):
    def lin(x):
        return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(x) for x in c[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(fg, bg):
    if fg[3] < 1:
        fg = tuple(fg[i] * fg[3] + bg[i] * (1 - fg[3]) for i in range(3)) + (1.0,)
    a, b = luminance(fg), luminance(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def rem_px(v: str):
    m = re.fullmatch(r"\s*(\d*\.?\d+)(px|rem)\s*", v)
    if not m:
        return None
    return float(m.group(1)) * (16 if m.group(2) == "rem" else 1)


# ---------------------------------------------------------------- report

class Report:
    def __init__(self):
        self.rows = []

    def add(self, status, cid, msg):
        self.rows.append((status, cid, msg))

    def ok(self, cond, cid, good, bad):
        self.add("PASS" if cond else "FAIL", cid, good if cond else bad)

    @property
    def failed(self):
        return any(s == "FAIL" for s, _, _ in self.rows)

    def print(self):
        for s, cid, msg in self.rows:
            print(f"{s:<5} {cid:<22} {msg}")
        counts = {k: sum(1 for s, _, _ in self.rows if s == k) for k in ("PASS", "FAIL", "SKIP")}
        print(f"\n{len(self.rows)} checks: {counts['PASS']} pass, {counts['FAIL']} fail, {counts['SKIP']} skipped")


# ---------------------------------------------------------------- resolve and validate

def find(options, group, oid):
    return next((o for o in options.get(group, []) if isinstance(o, dict) and o.get("id") == oid), None)


def resolve(doc: dict) -> dict:
    """The `tokens` object for doc['choices']; motion and layout are fixed and kept from doc['tokens']."""
    o, c = doc["options"], doc["choices"]
    p, t, s, n = (find(o, g, c[g]) for g in ("palette", "type", "shape", "density"))
    old = doc.get("tokens", {})
    return {
        "light": {k: p["light"][k] for k in COLORS},
        "dark": {k: p["dark"][k] for k in COLORS},
        "fonts_url": t["fonts_url"],
        "font": {k: t[k] for k in FONTS},
        "type": {**{k: n[k] for k in SIZES}, **{k: t[k] for k in TYPE_EXTRA}},
        "space": {k: n[k] for k in SPACE},
        "radius": {k: s[k] for k in RADIUS},
        "border": {k: s[k] for k in BORDER},
        "shadow": {"shadow": s["shadow"]},
        "motion": {k: old.get("motion", {}).get(k) for k in MOTION},
        "layout": {k: old.get("layout", {}).get(k) for k in LAYOUT},
    }


def validate_schema(doc, rep: Report) -> bool:
    """Schema checks; returns True when the structure is sound enough for contrast and copy checks."""
    if not isinstance(doc, dict):
        rep.add("FAIL", "schema", "top level is not a JSON object")
        return False
    missing = [k for k in ("version", "date", "source", "choices", "options", "tokens") if k not in doc]
    rep.ok(not missing, "schema-keys", "version, date, source, choices, options, tokens present",
           "missing top-level keys: " + ", ".join(missing))
    if missing:
        return False
    v = doc["version"]
    rep.ok(isinstance(v, int) and not isinstance(v, bool) and v >= 1, "version", f"version {v!r}", f"version must be an integer >= 1, got {v!r}")
    d = doc["date"]
    try:
        good_date = isinstance(d, str) and dt.date.fromisoformat(d).isoformat() == d
    except ValueError:
        good_date = False
    rep.ok(good_date, "date", f"date {d}", f"date must be YYYY-MM-DD, got {d!r}")
    src = doc["source"]
    rep.ok(isinstance(src, list) and src and all(isinstance(u, str) and u.startswith("https://") for u in src),
           "source", f"{len(src) if isinstance(src, list) else 0} https source URLs", "source must be a non-empty list of https URLs")

    sound = True
    opts = doc["options"]
    if not isinstance(opts, dict):
        rep.add("FAIL", "options", "options is not an object")
        return False
    for g, keys in OPTION_KEYS.items():
        lst = opts.get(g)
        if not isinstance(lst, list) or not 2 <= len(lst) <= 4:
            rep.add("FAIL", f"options-{g}", f"options.{g} must list 2-4 options")
            sound = False
            continue
        probs = []
        ids = [o.get("id") if isinstance(o, dict) else None for o in lst]
        if len(set(ids)) != len(ids) or not all(isinstance(i, str) and i for i in ids):
            probs.append("ids missing or not unique")
        for o in lst:
            if not isinstance(o, dict):
                probs.append("an option is not an object")
                continue
            if not isinstance(o.get("label"), str) or not o.get("label"):
                probs.append(f"{o.get('id')}: no label")
            miss = [k for k in keys if k not in o]
            if miss:
                probs.append(f"{o.get('id')}: missing " + ", ".join(miss))
                continue
            if g == "palette":
                for th in ("light", "dark"):
                    pal = o[th]
                    if not isinstance(pal, dict):
                        probs.append(f"{o['id']}.{th}: not an object")
                        continue
                    m2 = [k for k in COLORS if k not in pal]
                    extra = [k for k in pal if k not in COLORS]
                    bad = [k for k in COLORS if k in pal and parse_color(pal[k]) is None]
                    if m2:
                        probs.append(f"{o['id']}.{th}: missing " + ", ".join(m2))
                    if extra:
                        probs.append(f"{o['id']}.{th}: unknown " + ", ".join(extra))
                    if bad:
                        probs.append(f"{o['id']}.{th}: not #hex or rgb(): " + ", ".join(bad))
            elif g == "type":
                if not str(o["fonts_url"]).startswith("https://fonts.googleapis.com/css2?"):
                    probs.append(f"{o['id']}: fonts_url is not a Google Fonts css2 URL")
                for k in FONTS:
                    fam = str(o[k])
                    if not re.search(r"(sans-serif|serif|monospace)\s*$", fam):
                        probs.append(f"{o['id']}: {k} has no generic system fallback")
                    first = fam.split(",")[0].strip().strip("\"'")
                    if first.replace(" ", "+") not in str(o["fonts_url"]):
                        probs.append(f"{o['id']}: {k} first face {first!r} is not in fonts_url")
            elif g == "density":
                px = rem_px(str(o["text-xs"]))
                if px is None or px < 13:
                    probs.append(f"{o['id']}: text-xs {o['text-xs']} is below 13px")
            if any(not isinstance(o[k], (str, dict)) for k in keys):
                probs.append(f"{o['id']}: values must be strings")
        rep.ok(not probs, f"options-{g}", f"{len(lst)} {g} options: " + ", ".join(map(str, ids)), "; ".join(probs))
        sound = sound and not probs

    ch = doc["choices"]
    if not isinstance(ch, dict):
        rep.add("FAIL", "choices", "choices is not an object")
        return False
    bad = [f"{g}={ch.get(g)!r}" for g in OPTION_KEYS if find(opts, g, ch.get(g)) is None]
    extra = [k for k in ch if k not in OPTION_KEYS]
    rep.ok(not bad and not extra, "choices", ", ".join(f"{g}={ch[g]}" for g in OPTION_KEYS) if not bad else "",
           "; ".join((["choices not among the options: " + ", ".join(bad)] if bad else []) +
                     (["unknown choice keys: " + ", ".join(extra)] if extra else [])))
    if bad:
        return False

    tok = doc["tokens"]
    probs = []
    if not isinstance(tok, dict):
        rep.add("FAIL", "tokens-groups", "tokens is not an object")
        return False
    for g, keys in TOKEN_GROUPS.items():
        grp = tok.get(g)
        if not isinstance(grp, dict):
            probs.append(f"tokens.{g} missing")
            continue
        m2 = [k for k in keys if k not in grp]
        extra = [k for k in grp if k not in keys]
        if m2:
            probs.append(f"tokens.{g} missing " + ", ".join(m2))
        if extra:
            probs.append(f"tokens.{g} unknown " + ", ".join(extra))
        if any(not isinstance(v, str) or not v.strip() or re.search(r"[;{}]", v) for v in grp.values()):
            probs.append(f"tokens.{g} has an empty value or one with ; {{ }}")
    if not isinstance(tok.get("fonts_url"), str):
        probs.append("tokens.fonts_url missing")
    extra = [k for k in tok if k not in TOKEN_GROUPS and k != "fonts_url"]
    if extra:
        probs.append("unknown token groups: " + ", ".join(extra))
    rep.ok(not probs, "tokens-groups", f"{len(TOKEN_GROUPS)} token groups plus fonts_url, all names known", "; ".join(probs))
    if probs or not sound:
        return False

    want = resolve(doc)
    diff = []
    for g in TOKEN_GROUPS:
        for k in TOKEN_GROUPS[g]:
            if want[g][k] is not None and tok[g][k] != want[g][k]:
                diff.append(f"{g}.{k} is {tok[g][k]!r}, choices give {want[g][k]!r}")
    if tok["fonts_url"] != want["fonts_url"]:
        diff.append("fonts_url differs from the chosen type option")
    rep.ok(not diff, "tokens-resolved", "tokens equal the values the choices resolve to", "; ".join(diff[:8]))

    surf = doc.get("surfaces")
    if surf is None:
        rep.add("SKIP", "surfaces", "no surfaces notes (optional)")
    else:
        bad = isinstance(surf, dict) and [k for k in surf if k not in SURFACES or not isinstance(surf[k], str)]
        rep.ok(isinstance(surf, dict) and not bad, "surfaces", f"{len(surf)} surface notes: " + ", ".join(surf) if isinstance(surf, dict) else "",
               "surfaces must map " + ", ".join(SURFACES) + " to text" + (f"; bad: {', '.join(bad)}" if bad else ""))
    return not diff


def check_contrast(doc, rep: Report):
    sets = [("tokens", doc["tokens"]["light"], doc["tokens"]["dark"])]
    sets += [(f"palette {p['id']}", p["light"], p["dark"]) for p in doc["options"]["palette"]]
    for name, light, dark in sets:
        for theme, pal in (("light", light), ("dark", dark)):
            bad, n = [], 0
            for f, b, need, what in PAIRS:
                fg, bg = parse_color(pal[f]), parse_color(pal[b])
                r = ratio(fg, bg)
                n += 1
                if r < need:
                    bad.append(f"{f} on {b} {r:.2f}:1 < {need} ({what})")
            worst = min(ratio(parse_color(pal[f]), parse_color(pal[b])) / need for f, b, need, _ in PAIRS)
            rep.ok(not bad, f"contrast {name.split()[-1]} {theme}"[:22],
                   f"{name}, {theme}: {n} pairs pass (closest margin x{worst:.2f})", f"{name}, {theme}: " + "; ".join(bad))
    rep.add("SKIP", "contrast brand", "brand (#ff3c00 family) is decorative only: never text, so no text pair is measured")
    rep.add("SKIP", "contrast shade", "shade is the scroll-edge cue only, not text or a border")


def validate(doc) -> Report:
    """Run the schema and contrast checks that `check` and `apply` run on a tokens document, and return
    the Report. For other tools (such as design_studio.py) that must refuse the same documents."""
    rep = Report()
    try:
        sound = validate_schema(doc, rep)
    except (KeyError, TypeError, AttributeError, ValueError) as e:
        rep.add("FAIL", "schema", f"tokens document is malformed: {e}")
        return rep
    if sound:
        try:
            check_contrast(doc, rep)
        except (KeyError, TypeError, AttributeError, ZeroDivisionError) as e:
            rep.add("FAIL", "contrast", f"colors could not be measured: {e}")
    else:
        rep.add("SKIP", "contrast", "schema problems above: contrast not measured")
    return rep


def failures(rep: Report) -> list:
    """The messages of the FAIL rows of a Report, prefixed by their check id."""
    return [f"{cid}: {msg}" for s, cid, msg in rep.rows if s == "FAIL"]


# ---------------------------------------------------------------- generated copies

def css_block(doc) -> str:
    t = doc["tokens"]
    lines = [START, f"/* Generated by tokens.py from design-tokens.json v{doc['version']} ({doc['date']}). Do not edit by hand. */",
             ":root {", "  /* Color, light theme */"]
    lines += [f"  --{k}: {t['light'][k]};" for k in COLORS]
    lines += ["  color-scheme: light;", "", "  /* Type */"]
    lines += [f"  --{k}: {t['font'][k]};" for k in FONTS]
    lines += [f"  --{k}: {t['type'][k]};" for k in SIZES + TYPE_EXTRA]
    lines += ["", "  /* Space */"] + [f"  --{k}: {t['space'][k]};" for k in SPACE]
    lines += ["", "  /* Shape */"] + [f"  --{k}: {t['radius'][k]};" for k in RADIUS]
    lines += [f"  --{k}: {t['border'][k]};" for k in BORDER] + [f"  --shadow: {t['shadow']['shadow']};"]
    lines += ["", "  /* Motion and layout */"] + [f"  --{k}: {t['motion'][k]};" for k in MOTION]
    lines += [f"  --{k}: {t['layout'][k]};" for k in LAYOUT] + ["}"]
    dark = [f"--{k}: {t['dark'][k]};" for k in COLORS] + ["color-scheme: dark;"]
    lines += ["@media (prefers-color-scheme: dark) {", '  :root:not([data-theme="light"]) {']
    lines += [f"    {d}" for d in dark] + ["  }", "}", ':root[data-theme="dark"] {'] + [f"  {d}" for d in dark] + ["}", END]
    return "\n".join(lines)


def get_block(text: str):
    i, j = text.find(START), text.find(END)
    if i == -1 or j == -1 or j < i:
        return None
    return text[i:j + len(END)]


def set_block(text: str, block: str) -> str:
    i, j = text.find(START), text.find(END)
    return text[:i] + block + text[j + len(END):]


def norm(s: str) -> str:
    return "\n".join(line.strip() for line in s.strip().splitlines() if line.strip())


def embed_json(doc) -> str:
    return "\n" + json.dumps(doc, indent=2, ensure_ascii=False).replace("</", "<\\/") + "\n"


def check_copies(doc, paths, rep: Report):
    want = css_block(doc)
    css = paths["css"]
    if not css.is_file():
        rep.add("FAIL", "house.css block", f"{css} not found")
    else:
        got = get_block(css.read_text(encoding="utf-8"))
        rep.ok(got is not None and norm(got) == norm(want), "house.css block",
               "house.css token block matches design-tokens.json",
               "house.css has no tokens:start/tokens:end markers" if got is None
               else "house.css token block differs from design-tokens.json: run `tokens.py apply` or restore the file")
    ref = paths["ref"]
    if not ref.is_file():
        rep.add("FAIL", "reference", f"{ref} not found")
        return
    html = ref.read_text(encoding="utf-8")
    got = get_block(html)
    rep.ok(got is not None and norm(got) == norm(want), "reference block",
           "design-reference.html token block matches design-tokens.json",
           "design-reference.html has no token block markers" if got is None
           else "design-reference.html token block differs from design-tokens.json")
    m = EMBED_RE.search(html)
    if not m:
        rep.add("FAIL", "reference embed", 'no <script type="application/json" id="design-tokens"> in design-reference.html')
    else:
        try:
            emb = json.loads(m.group(2))
            rep.ok(emb == doc, "reference embed", "embedded design-tokens JSON equals design-tokens.json",
                   "embedded design-tokens JSON differs from design-tokens.json")
        except json.JSONDecodeError as e:
            rep.add("FAIL", "reference embed", f"embedded JSON does not parse: {e}")
    fl = FONT_LINK_RE.search(html)
    rep.ok(bool(fl) and htmllib.unescape(fl.group(2)) == doc["tokens"]["fonts_url"], "reference fonts",
           "design-reference.html loads tokens.fonts_url",
           'no <link rel="stylesheet" id="token-fonts"> in design-reference.html' if not fl
           else "design-reference.html font link differs from tokens.fonts_url")
    shown = {k: (r.search(html).group(2) if r.search(html) else None) for k, r in SPAN_RE.items()}
    rep.ok(shown["version"] == str(doc["version"]) and shown["date"] == doc["date"], "reference version",
           f"page shows v{shown['version']} ({shown['date']})",
           f"page shows version {shown['version']!r} and date {shown['date']!r}, file has {doc['version']} and {doc['date']}")


# ---------------------------------------------------------------- commands

def paths_for(root: Path) -> dict:
    return {"json": root / "assets" / "design-tokens.json", "css": root / "assets" / "house.css",
            "ref": root / "references" / "design-reference.html"}


def load(path: Path, rep: Report):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        rep.add("FAIL", "load", f"{path} not found")
    except json.JSONDecodeError as e:
        rep.add("FAIL", "load", f"{path} is not valid JSON: {e}")
    return None


def cmd_check(root: Path) -> int:
    p = paths_for(root)
    rep = Report()
    doc = load(p["json"], rep)
    if doc is not None:
        rep.add("PASS", "load", f"read {p['json']}")
        sound = validate_schema(doc, rep)
        if sound:
            check_contrast(doc, rep)
            check_copies(doc, p, rep)
        else:
            rep.add("SKIP", "contrast", "schema problems above: contrast not measured")
            rep.add("SKIP", "copies", "schema problems above: house.css and reference copies not compared")
    rep.add("SKIP", "rendered", "fonts loading, picker, export, and both themes at 320px need a browser: open references/design-reference.html")
    rep.print()
    return 1 if rep.failed else 0


def cmd_apply(root: Path, new_path: Path) -> int:
    p = paths_for(root)
    rep = Report()
    old = load(p["json"], rep)
    new = load(new_path, rep)
    if old is None or new is None:
        rep.print()
        print("Nothing written.")
        return 1
    sound = validate_schema(new, rep)
    if sound:
        check_contrast(new, rep)
    for k in ("css", "ref"):
        if not p[k].is_file():
            rep.add("FAIL", "target", f"{p[k]} not found")
        elif get_block(p[k].read_text(encoding="utf-8")) is None:
            rep.add("FAIL", "target", f"{p[k]} has no {START} ... {END} markers")
    ref_text = p["ref"].read_text(encoding="utf-8") if p["ref"].is_file() else ""
    if ref_text and not EMBED_RE.search(ref_text):
        rep.add("FAIL", "target", f"{p['ref']} has no embedded design-tokens script")
    if not sound or rep.failed:
        rep.print()
        print("Validation failed: nothing written.")
        return 1
    new["version"] = int(old.get("version", 0)) + 1
    new["date"] = dt.date.today().isoformat()
    block = css_block(new)
    css_text = set_block(p["css"].read_text(encoding="utf-8"), block)
    ref_text = set_block(ref_text, block)
    ref_text = EMBED_RE.sub(lambda m: m.group(1) + embed_json(new) + m.group(3), ref_text, count=1)
    ref_text = FONT_LINK_RE.sub(lambda m: m.group(1) + htmllib.escape(new["tokens"]["fonts_url"]) + m.group(3), ref_text, count=1)
    for k, r in SPAN_RE.items():
        ref_text = r.sub(lambda m, v=str(new[k]): m.group(1) + v + m.group(3), ref_text)
    p["json"].write_text(json.dumps(new, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    p["css"].write_text(css_text, encoding="utf-8")
    p["ref"].write_text(ref_text, encoding="utf-8")
    rep.print()
    print(f"\nApplied v{new['version']} ({new['date']}): wrote {p['json']}, the token block of {p['css']}, "
          f"and the token block, embedded copy, font link, and version of {p['ref']}.")
    return 0


def cmd_show(root: Path) -> int:
    rep = Report()
    doc = load(paths_for(root)["json"], rep)
    if doc is None:
        rep.print()
        return 1
    print(f"version  {doc.get('version')}")
    print(f"date     {doc.get('date')}")
    for g, oid in doc.get("choices", {}).items():
        o = find(doc.get("options", {}), g, oid)
        print(f"{g:<8} {oid}" + (f"  - {o['label']}" if o and o.get("label") else ""))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(SKILL), help="skill folder to work on (default: this skill)")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", default=argparse.SUPPRESS, help="skill folder to work on")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", parents=[common], help="validate tokens, contrast, and generated copies; changes nothing")
    a = sub.add_parser("apply", parents=[common], help="validate a new tokens file, bump the version, write it and its copies")
    a.add_argument("new")
    sub.add_parser("show", parents=[common], help="print version, date, and choices")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    if args.cmd == "check":
        return cmd_check(root)
    if args.cmd == "apply":
        return cmd_apply(root, Path(args.new))
    return cmd_show(root)


if __name__ == "__main__":
    sys.exit(main())
