"""skill-design page tool: create a page from the house design, or check a page.

  py -3 page.py new <out.html> --title "Title" [--lang en] [--profile design/client-profile.md] [--no-web-fonts] [--force]
  py -3 page.py check <page.html> [--css extra.css ...] [--json]
  py -3 page.py contrast <fg> <bg> [<fg> <bg> ...]
  py -3 page.py adherence <page.html> [--tokens assets/design-tokens.json] [--profile design/client-profile.md]

Standard library only. `check` and `adherence` read files and print one line per check (PASS, WARN,
FAIL, SKIP); they never change them. Exit code 1 when any check fails.

`adherence` checks that the page follows the design reference: every color (hex, rgb, hsl and other
color functions, named colors), font family, and border-radius value in the page's CSS, inline styles,
and SVG fill/stroke attributes is a design token. Allowed: colors from any value in the tokens file's
`tokens` and `options`; font families from their font values; radii from `tokens.radius` and the
`options.shape` radii; plus `var(--...)`, `inherit`, `initial`, `unset`, `currentColor`, `transparent`,
`0`, and `none`. A client profile's ```css overrides extend the allowed values. Print styles are skipped.
"""
from __future__ import annotations

import argparse
import colorsys
import json
import math
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
ASSETS = SKILL / "assets"
TOKENS_FILE = ASSETS / "design-tokens.json"

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

FONTS_LINK = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
              '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
              '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500'
              '&family=IBM+Plex+Sans+Condensed:wght@600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">')


def house_fonts_link() -> str:
    """The font link for house pages: `tokens.fonts_url` from design-tokens.json when present, else FONTS_LINK."""
    try:
        url = json.loads(TOKENS_FILE.read_text(encoding="utf-8")).get("tokens", {}).get("fonts_url")
    except (OSError, ValueError, AttributeError):
        url = None
    if not url or not isinstance(url, str):
        return FONTS_LINK
    return ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            f'<link rel="stylesheet" href="{url}">')


# ---------------------------------------------------------------- new

def css_blocks_from_profile(text: str) -> str:
    blocks = re.findall(r"```css\s*\n(.*?)```", text, flags=re.S)
    return "\n".join(b.strip() for b in blocks if b.strip())


def cmd_new(a) -> int:
    out = Path(a.out)
    if out.exists() and not a.force:
        print(f"FAIL  {out} already exists; pass --force to replace it (make a copy first).")
        return 1
    starter = (ASSETS / "starter.html").read_text(encoding="utf-8")
    css = (ASSETS / "house.css").read_text(encoding="utf-8").strip()
    fonts = house_fonts_link()
    if a.profile:
        p = Path(a.profile)
        if not p.is_file():
            print(f"FAIL  client profile not found: {p}")
            return 1
        ptext = p.read_text(encoding="utf-8")
        over = css_blocks_from_profile(ptext)
        if over:
            css += f"\n\n/* Client profile overrides: {p.as_posix()} */\n{over}"
        else:
            print(f"WARN  {p} has no ```css block; house tokens used unchanged.")
        blocks = [re.sub(r"<!--.*?-->", "", b, flags=re.S).strip() for b in re.findall(r"```html\s*\n(.*?)```", ptext, flags=re.S)]
        links = "\n".join(b for b in blocks if "<link" in b)
        if links:
            fonts = links
        elif re.search(r"--font-(display|body)\s*:", over or ""):
            print("WARN  the profile changes --font-display or --font-body but has no ```html font-link block; "
                  "the house font link is used, so the client fonts load only if installed.")
    page = (starter.replace("{{LANG}}", a.lang)
                   .replace("{{TITLE}}", a.title)
                   .replace("{{FONTS}}", "" if a.no_web_fonts else fonts)
                   .replace("/*HOUSE_CSS*/", css))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"OK    wrote {out} ({len(page)} bytes){' with profile ' + a.profile if a.profile else ''}")
    return 0


# ---------------------------------------------------------------- CSS parsing

def strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def parse_css(css: str, context: tuple = ()) -> list[dict]:
    """Return rules: {selector, decls: [(prop, value)], context: tuple of at-rule preludes}."""
    rules, i, n = [], 0, len(css)
    while i < n:
        j = css.find("{", i)
        if j == -1:
            break
        prelude = css[i:j].strip()
        depth, k = 1, j + 1
        while k < n and depth:
            if css[k] == "{":
                depth += 1
            elif css[k] == "}":
                depth -= 1
            k += 1
        body = css[j + 1:k - 1]
        if prelude.startswith("@"):
            if re.match(r"@(media|supports|layer|container)", prelude):
                rules += parse_css(body, context + (prelude,))
            elif prelude.startswith("@keyframes"):
                rules.append({"selector": prelude, "decls": [], "context": context})
        else:
            decls = []
            for d in split_decls(body):
                if ":" in d:
                    p, v = d.split(":", 1)
                    decls.append((p.strip().lower(), v.strip()))
            rules.append({"selector": prelude, "decls": decls, "context": context})
        i = k
    return rules


def split_decls(body: str) -> list[str]:
    out, buf, depth = [], [], 0
    for ch in body:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == ";" and depth == 0:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if "".join(buf).strip():
        out.append("".join(buf))
    return out


def tokens_for(rules, theme: str) -> dict:
    """Custom properties for 'light' or 'dark', dark falling back to light."""
    light, dark_media, dark_attr = {}, {}, {}
    for r in rules:
        sel = re.sub(r"\s+", "", r["selector"])
        ctx = " ".join(r["context"])
        props = {p: v for p, v in r["decls"] if p.startswith("--")}
        if not props or "print" in ctx:
            continue
        if sel == ":root" and not ctx:
            light.update(props)
        elif "prefers-color-scheme:dark" in ctx.replace(" ", "") and ":root" in sel:
            dark_media.update(props)
        elif sel.replace("'", '"') == ':root[data-theme="dark"]':
            dark_attr.update(props)
    if theme == "light":
        return light
    merged = dict(light)
    merged.update(dark_media or dark_attr)
    return merged


def theme_blocks(rules):
    media = attr = None
    for r in rules:
        sel = re.sub(r"\s+", "", r["selector"]).replace("'", '"')
        ctx = " ".join(r["context"]).replace(" ", "")
        props = {p: v for p, v in r["decls"] if p.startswith("--")}
        if not props or "print" in ctx:
            continue
        if "prefers-color-scheme:dark" in ctx and sel.startswith(":root"):
            media = {**(media or {}), **props}
        elif sel == ':root[data-theme="dark"]' and not ctx:
            attr = {**(attr or {}), **props}
    return media, attr


def resolve(value: str, tokens: dict, depth: int = 0) -> str:
    if depth > 8:
        return value
    def rep(m):
        name, fallback = m.group(1).strip(), (m.group(2) or "").strip()
        if name in tokens:
            return resolve(tokens[name], tokens, depth + 1)
        return fallback or m.group(0)
    return re.sub(r"var\(\s*(--[\w-]+)\s*(?:,\s*([^()]*))?\)", rep, value)


# ---------------------------------------------------------------- color

NAMED = {"white": (255, 255, 255), "black": (0, 0, 0)}
SYSTEM_FONTS = {"system-ui", "-apple-system", "segoe ui", "arial", "helvetica", "georgia", "times new roman",
                "consolas", "courier new", "verdana", "tahoma", "trebuchet ms", "sans-serif", "serif", "monospace",
                "arial narrow", "calibri", "cambria", "ui-sans-serif", "ui-serif", "ui-monospace"}
NAMED_RE = re.compile(r"(?<![\w-])(white|black|red|green|blue|gray|grey|orange|yellow|purple|pink|brown|navy|teal|silver)(?![\w-])", re.I)
COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?|oklch|oklab|lab|lch|hwb|color)\([^)]*\)")


def parse_color(text: str):
    """Return (r, g, b, alpha) with r, g, b in 0..1, or None when unsupported."""
    t = text.strip().lower()
    if t in NAMED:
        r, g, b = NAMED[t]
        return r / 255, g / 255, b / 255, 1.0
    m = re.fullmatch(r"#([0-9a-f]{3,8})", t)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        if len(h) not in (6, 8):
            return None
        vals = [int(h[i:i + 2], 16) / 255 for i in range(0, len(h), 2)]
        return vals[0], vals[1], vals[2], vals[3] if len(vals) == 4 else 1.0
    m = re.fullmatch(r"(rgba?|hsla?|oklch)\((.*)\)", t)
    if not m:
        return None
    fn, args = m.group(1), re.split(r"[\s,/]+", m.group(2).strip())
    args = [x for x in args if x]
    def num(x, scale=1.0):
        return float(x[:-1]) / 100 * scale if x.endswith("%") else float(x.replace("deg", ""))
    try:
        alpha = num(args[3]) if len(args) > 3 else 1.0
        if args[3:] and args[3].endswith("%"):
            alpha = float(args[3][:-1]) / 100
        if fn.startswith("rgb"):
            r, g, b = (num(x, 255) / 255 for x in args[:3])
            return r, g, b, alpha
        if fn.startswith("hsl"):
            h = num(args[0]) / 360
            s = float(args[1].rstrip("%")) / 100
            l = float(args[2].rstrip("%")) / 100
            r, g, b = colorsys.hls_to_rgb(h, l, s)
            return r, g, b, alpha
        if fn == "oklch":
            L = float(args[0][:-1]) / 100 if args[0].endswith("%") else float(args[0])
            C = float(args[1].rstrip("%")) * (0.004 if args[1].endswith("%") else 1)
            H = math.radians(float(args[2].replace("deg", "")))
            a_, b_ = C * math.cos(H), C * math.sin(H)
            l_ = (L + 0.3963377774 * a_ + 0.2158037573 * b_) ** 3
            m_ = (L - 0.1055613458 * a_ - 0.0638541728 * b_) ** 3
            s_ = (L - 0.0894841775 * a_ - 1.2914855480 * b_) ** 3
            lin = (4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
                   -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
                   -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_)
            def enc(c):
                c = min(max(c, 0.0), 1.0)
                return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
            r, g, b = (enc(c) for c in lin)
            return r, g, b, alpha
    except (ValueError, IndexError):
        return None
    return None


def luminance(rgb):
    def lin(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg, bg):
    if fg[3] < 1:  # composite fg over bg
        fg = tuple(fg[i] * fg[3] + bg[i] * (1 - fg[3]) for i in range(3)) + (1.0,)
    a, b = luminance(fg), luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


# Token pairs of the house design: (foreground, background, required ratio, house target, what it is)
PAIRS = [
    ("--fg", "--bg", 4.5, 7.0, "body text on page"),
    ("--fg", "--surface", 4.5, 7.0, "body text on cards"),
    ("--muted", "--bg", 4.5, 4.5, "muted text on page"),
    ("--muted", "--surface", 4.5, 4.5, "muted text on cards"),
    ("--accent", "--bg", 4.5, 4.5, "links on page"),
    ("--accent", "--surface", 4.5, 4.5, "links on cards"),
    ("--accent-fg", "--accent", 4.5, 4.5, "primary button text"),
    ("--accent", "--accent-bg", 4.5, 4.5, "accent badge"),
    ("--fg", "--accent-bg", 4.5, 4.5, "info callout text"),
    ("--danger", "--danger-bg", 4.5, 4.5, "danger badge"),
    ("--danger", "--surface", 4.5, 4.5, "danger figure"),
    ("--fg", "--danger-bg", 4.5, 4.5, "danger callout text"),
    ("--warn", "--warn-bg", 4.5, 4.5, "warning badge"),
    ("--warn", "--surface", 4.5, 4.5, "warning figure"),
    ("--fg", "--warn-bg", 4.5, 4.5, "warning callout text"),
    ("--ok", "--ok-bg", 4.5, 4.5, "ok badge"),
    ("--ok", "--surface", 4.5, 4.5, "ok figure"),
    ("--fg", "--ok-bg", 4.5, 4.5, "ok callout text"),
    ("--line-strong", "--surface", 3.0, 3.0, "control borders"),
    ("--accent", "--surface", 3.0, 3.0, "focus ring"),
]


# ---------------------------------------------------------------- HTML parsing

INTERACTIVE = {"a", "button", "summary", "select", "textarea"}
BANNED_LINKS = {"click here", "here", "learn more", "read more", "more", "submit", "link"}


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lang = None
        self.viewport = False
        self.title = ""
        self.styles, self.links = [], []
        self.headings = []
        self.images = []
        self.hrefs = []           # (line, href)
        self.media = []           # (line, src)
        self.controls = []        # (tag, line, name, attrs)
        self.inputs = []          # (line, attrs)
        self.label_for = set()
        self.inline_colors = []   # (line, value)
        self.autoplay = []
        self.primary_buttons = 0
        self.tables = []          # max columns per table
        self.text = []
        self._stack = []          # open interactive elements: [tag, line, attrs, text]
        self._in = None
        self._buf = []
        self._label_depth = 0
        self._row_cols = 0
        self._table_cols = None

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        line = self.getpos()[0]
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "meta" and a.get("name", "").lower() == "viewport":
            self.viewport = True
        if tag in ("style", "title", "script"):
            self._in, self._buf = tag, []
        if tag == "link" and "stylesheet" in a.get("rel", "").lower():
            self.links.append(a.get("href", ""))
        if re.fullmatch(r"h[1-6]", tag):
            self.headings.append((int(tag[1]), line))
        if tag == "a" and "href" in a:
            self.hrefs.append((line, a["href"]))
        if tag in ("img", "video", "audio", "source") and a.get("src"):
            self.media.append((line, a["src"]))
        if tag == "img":
            self.images.append((line, a))
            for s in self._stack:
                s[3].append(a.get("alt", ""))
        if tag in ("video", "audio") and "autoplay" in a:
            self.autoplay.append(line)
        if tag == "label":
            self._label_depth += 1
            if a.get("for"):
                self.label_for.add(a["for"])
        if tag == "input" and a.get("type", "text").lower() != "hidden":
            self.inputs.append((line, a, self._label_depth > 0))
        if "style" in a:
            for m in COLOR_RE.finditer(a["style"]):
                self.inline_colors.append((line, m.group(0)))
        cls = a.get("class", "").split()
        if "button" in cls and "primary" in cls:
            self.primary_buttons += 1
        if tag == "table":
            self._table_cols = 0
        if tag == "tr":
            self._row_cols = 0
        if tag in ("td", "th"):
            try:
                self._row_cols += int(a.get("colspan", "1") or 1)
            except ValueError:
                self._row_cols += 1
        is_control = tag in INTERACTIVE or a.get("role") in ("button", "link", "tab", "menuitem", "checkbox", "switch")
        if tag == "a" and "href" not in a and "role" not in a:
            is_control = False
        if is_control:
            self._stack.append([tag, line, a, []])

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag == self._in:
            content = "".join(self._buf)
            if tag == "style":
                self.styles.append(content)
            elif tag == "title":
                self.title = content.strip()
            self._in = None
        if tag == "label":
            self._label_depth = max(0, self._label_depth - 1)
        if tag == "tr" and self._table_cols is not None:
            self._table_cols = max(self._table_cols, self._row_cols)
        if tag == "table" and self._table_cols is not None:
            self.tables.append((self.getpos()[0], self._table_cols))
            self._table_cols = None
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == tag:
                t, line, a, txt = self._stack.pop(i)
                name = (a.get("aria-label") or a.get("title") or ("labelledby" if a.get("aria-labelledby") else "")
                        or " ".join(" ".join(txt).split()))
                self.controls.append((t, line, name, a))
                for s in self._stack:
                    s[3].extend(txt)
                break

    def handle_data(self, data):
        if self._in:
            self._buf.append(data)
            return
        self.text.append(data)
        for s in self._stack:
            s[3].append(data)


# ---------------------------------------------------------------- checks

class Report:
    def __init__(self):
        self.rows = []

    def add(self, status, cid, rule, msg):
        self.rows.append({"status": status, "id": cid, "rule": rule, "message": msg})


def px_of(size: str):
    m = re.match(r"\s*(\d*\.?\d+)(px|rem|em)\b", size)
    if not m:
        return None
    v, unit = float(m.group(1)), m.group(2)
    return v if unit == "px" else v * 16


def font_size_of(prop, value):
    if prop == "font-size":
        return value
    if prop == "font":
        m = re.search(r"(\d*\.?\d+(?:px|rem|em))(?:\s*/|\s+[\"'\w-])", value)
        return m.group(1) if m else None
    return None


def cmd_check(a) -> int:
    path = Path(a.page)
    if not path.is_file():
        print(f"FAIL  page not found: {path}")
        return 1
    html = path.read_text(encoding="utf-8", errors="replace")
    pg = Page()
    pg.feed(html)
    rep = Report()

    css_parts = list(pg.styles)
    for href in pg.links:
        if re.match(r"https?:|//", href):
            rep.add("SKIP", "css-remote", "-", f"remote stylesheet not read: {href}")
            continue
        f = (path.parent / href).resolve()
        if f.is_file():
            css_parts.append(f.read_text(encoding="utf-8", errors="replace"))
        else:
            rep.add("WARN", "css-missing", "-", f"linked stylesheet not found: {href}")
    for extra in a.css or []:
        css_parts.append(Path(extra).read_text(encoding="utf-8", errors="replace"))
    css = strip_comments("\n".join(css_parts))
    rules = parse_css(css)

    # Document (H13)
    rep.add("PASS" if pg.lang else "FAIL", "lang", "H13", f"<html lang> is {pg.lang!r}" if pg.lang else "<html> has no lang attribute")
    rep.add("PASS" if pg.viewport else "FAIL", "viewport", "H13",
            "viewport meta present" if pg.viewport else "no viewport meta: the file lays out at ~980px on phones; test narrow widths on a copy with the meta added")
    rep.add("PASS" if pg.title else "WARN", "title", "-", f"title {pg.title!r}" if pg.title else "no <title>")

    # Headings (H13)
    levels = [lvl for lvl, _ in pg.headings]
    h1 = levels.count(1)
    skips = [(pg.headings[i][1], levels[i - 1], levels[i]) for i in range(1, len(levels)) if levels[i] > levels[i - 1] + 1]
    if h1 != 1 or skips:
        msg = f"{h1} h1 element(s)" + ("; skipped levels: " + ", ".join(f"line {ln}: h{p} to h{c}" for ln, p, c in skips) if skips else "")
        rep.add("FAIL", "headings", "H13", msg)
    else:
        rep.add("PASS", "headings", "H13", f"one h1, {len(levels)} headings, no skipped levels")

    # Names (H1)
    unnamed = [f"line {ln} <{t}>" for t, ln, name, at in pg.controls if not name.strip() and t != "select"]
    for ln, at, wrapped in pg.inputs:
        typ = at.get("type", "text").lower()
        if typ in ("submit", "button", "reset"):
            if not (at.get("value") or at.get("aria-label")):
                unnamed.append(f"line {ln} <input type={typ}>")
        elif not (wrapped or at.get("id") in pg.label_for or at.get("aria-label") or at.get("aria-labelledby") or at.get("title")):
            unnamed.append(f"line {ln} <input type={typ}>" + (" (placeholder is not a label)" if at.get("placeholder") else ""))
    rep.add("FAIL" if unnamed else "PASS", "names", "H1",
            ("controls without an accessible name: " + "; ".join(unnamed[:12])) if unnamed
            else f"{len(pg.controls) + len(pg.inputs)} links, buttons, summaries and form fields named")

    vague = [f"line {ln} {name.strip()!r}" for t, ln, name, at in pg.controls if t == "a" and name.strip().lower() in BANNED_LINKS]
    rep.add("WARN" if vague else "PASS", "link-text", "Taste",
            ("links that do not say where they go: " + "; ".join(vague)) if vague else "link texts name their destination")

    # Images (H12)
    no_alt = [f"line {ln}" for ln, at in pg.images if "alt" not in at]
    rep.add("FAIL" if no_alt else "PASS", "images", "H12",
            ("images without alt: " + ", ".join(no_alt)) if no_alt else f"{len(pg.images)} images have alt")

    # Placeholder text (no invented or unfinished content)
    body_text = " ".join(pg.text)
    ph = sorted(set(m.group(0) for m in re.finditer(r"lorem ipsum|\{\{[^}]*\}\}|\bTODO\b|\bTBD\b|\bXXX\b", body_text, flags=re.I)))
    bad_links = [f"line {ln} href={h!r}" for ln, h in pg.hrefs
                 if not h.strip() or re.search(r"(^|[/.])example\.(com|org|net)\b|\.example\b|\.invalid\b", h)]
    missing = [f"line {ln} {s}" for ln, s in pg.media
               if not re.match(r"(https?:|data:|//)", s) and not (path.parent / s.split("?")[0].split("#")[0]).exists()]
    probs = (["placeholder text: " + ", ".join(ph)] if ph else []) + \
            (["placeholder or empty link targets: " + "; ".join(bad_links[:6])] if bad_links else []) + \
            (["local media files not found: " + "; ".join(missing[:6])] if missing else [])
    rep.add("FAIL" if probs else "PASS", "content", "H14",
            "; ".join(probs) or "no placeholder text, link targets or missing local media")

    # Themes
    media, attr = theme_blocks(rules)
    if not rules:
        rep.add("SKIP", "themes", "Taste", "no CSS found")
    elif media and attr:
        diff = sorted(k for k in set(media) | set(attr) if media.get(k) != attr.get(k))
        rep.add("WARN" if diff else "PASS", "themes", "Taste",
                ("dark values differ between the media query and [data-theme=dark]: " + ", ".join(diff)) if diff
                else "dark theme via prefers-color-scheme and [data-theme=dark], values match")
    else:
        rep.add("WARN", "themes", "Taste", "no dark theme block" if not (media or attr)
                else "dark theme defined only via " + ("prefers-color-scheme" if media else "[data-theme=dark]"))

    # Contrast (H4)
    any_pair = False
    used = any("var(--" in v for r in rules for p, v in r["decls"] if not p.startswith("--")) or "var(--" in html.split("</style>")[-1]
    if rules and not used:
        rep.add("SKIP", "contrast", "H4", "tokens are declared but no rule uses them: measure the colors the page applies with `page.py contrast <fg> <bg>`")
        any_pair = True
    for theme in (("light", "dark") if (media or attr) else ("light",)) if used else ():
        toks = tokens_for(rules, theme)
        bad, low, checked, skipped = [], [], 0, []
        for fgk, bgk, need, target, what in PAIRS:
            if fgk not in toks or bgk not in toks:
                continue
            fg, bg = parse_color(resolve(toks[fgk], toks)), parse_color(resolve(toks[bgk], toks))
            if not fg or not bg:
                skipped.append(f"{fgk}/{bgk}")
                continue
            checked += 1
            r = contrast(fg, bg)
            if r < need:
                bad.append(f"{fgk} on {bgk} {r:.2f}:1 < {need} ({what})")
            elif r < target:
                low.append(f"{fgk} on {bgk} {r:.2f}:1 < house target {target}")
        if checked:
            any_pair = True
            status = "FAIL" if bad else ("WARN" if low else "PASS")
            msg = "; ".join(bad + low) or f"{checked} token pairs pass"
            if skipped:
                msg += f"; unsupported notation skipped: {', '.join(skipped)}"
            rep.add(status, f"contrast-{theme}", "H4", msg)
    if not any_pair:
        rep.add("SKIP", "contrast", "H4", "no house token pairs found (page uses other token names): measure its text and background pairs with `page.py contrast <fg> <bg>`")

    # Raw colors outside tokens (Taste: tokens only)
    raw = []
    for r in rules:
        for p, v in r["decls"]:
            if p.startswith("--"):
                continue
            for m in COLOR_RE.finditer(re.sub(r"url\([^)]*\)", "", v)):
                raw.append(f"{r['selector'][:40]} {{{p}: {m.group(0)}}}")
            if re.fullmatch(r"(background(-color)?|color|border(-\w+)*|outline(-color)?|fill|stroke|text-decoration-color)", p):
                for m in NAMED_RE.finditer(v):
                    raw.append(f"{r['selector'][:40]} {{{p}: {m.group(0)}}}")
    raw += [f"line {ln} style=\"{v}\"" for ln, v in pg.inline_colors]
    rep.add("WARN" if raw else "PASS", "raw-colors", "Taste",
            (f"{len(raw)} raw color values outside tokens: " + "; ".join(raw[:8])) if raw else "colors come from tokens")

    # Text size (H4 floor 12px, house 13px)
    toks = tokens_for(rules, "light")
    small = []
    for r in rules:
        if "print" in " ".join(r["context"]):
            continue  # print sizes follow paper, not screens
        for p, v in r["decls"]:
            fs = font_size_of(p, resolve(v, toks))
            px = px_of(fs) if fs else None
            if px is not None and px < 13:
                small.append((px, f"{r['selector'][:40]} {px:.1f}px"))
    worst = min((s[0] for s in small), default=None)
    floor = worst is not None and worst < 12
    rep.add("FAIL" if floor else ("WARN" if small else "PASS"), "text-size", "H4" if floor else "Taste",
            ("text below " + ("the 12px floor" if floor else "the house 13px") + ": " + "; ".join(s[1] for s in small[:8])) if small
            else "no screen text below 13px")

    # Fonts: a named display or body face that nothing loads falls back silently
    link_text = " ".join(pg.links)
    face_blocks = " ".join(re.findall(r"@font-face\s*\{[^}]*\}", "\n".join(css_parts)))
    unloaded = []
    for key in ("--font-display", "--font-body"):
        fam = toks.get(key, "")
        first = fam.split(",")[0].strip().strip("\"'") if fam else ""
        if not first or first.lower() in SYSTEM_FONTS:
            continue
        if first.replace(" ", "+") not in link_text and first not in face_blocks:
            unloaded.append(f"{key} {first!r}")
    rep.add("WARN" if unloaded else "PASS", "fonts", "Taste",
            ("no font link or @font-face loads " + ", ".join(unloaded) + "; readers see the fallback face") if unloaded
            else "display and body faces are loaded or system fonts")

    # Focus (H2)
    removed = [r["selector"] for r in rules for p, v in r["decls"]
               if p == "outline" and re.fullmatch(r"(none|0)(\s.*)?", v.strip())
               or p == "outline-style" and v.strip() == "none"]
    restored = any(":focus-visible" in r["selector"] and any(p in ("outline", "box-shadow", "border-color") for p, _ in r["decls"]) for r in rules)
    if removed and not restored:
        rep.add("FAIL", "focus", "H2", "outline removed with no :focus-visible replacement: " + "; ".join(s[:40] for s in removed[:5]))
    else:
        rep.add("PASS", "focus", "H2", ":focus-visible style present" if restored else "browser focus ring kept")

    # Motion (H9)
    ungated = [r["selector"][:40] for r in rules
               if "prefers-reduced-motion" not in " ".join(r["context"])
               and (r["selector"].startswith("@keyframes")
                    or any(p in ("animation", "animation-name", "transition", "transition-property") and v.strip() not in ("none", "0s")
                           for p, v in r["decls"]))]
    t_all = [r["selector"][:40] for r in rules for p, v in r["decls"] if p in ("transition", "transition-property") and re.match(r"all\b", v.strip())]
    msgs = []
    if ungated:
        msgs.append("motion outside a prefers-reduced-motion query: " + "; ".join(ungated[:6]))
    if t_all:
        msgs.append("transition: all on " + "; ".join(t_all[:4]))
    if pg.autoplay:
        msgs.append("autoplaying media at lines " + ", ".join(map(str, pg.autoplay)))
    rep.add("FAIL" if pg.autoplay else ("WARN" if msgs else "PASS"), "motion", "H9", "; ".join(msgs) or "motion gated or absent")

    # One primary action
    rep.add("WARN" if pg.primary_buttons > 1 else "PASS", "primary-action", "Taste",
            f"{pg.primary_buttons} .button.primary elements: keep one per view" if pg.primary_buttons > 1 else f"{pg.primary_buttons} primary button(s)")

    # Wide tables (L-119)
    wide = [f"line {ln}: {c} columns" for ln, c in pg.tables if c > 5]
    rep.add("WARN" if wide else "PASS", "wide-tables", "Taste",
            ("tables to check at 320px (cards may fit better): " + "; ".join(wide)) if wide else f"{len(pg.tables)} tables, none wider than 5 columns")

    rep.add("SKIP", "rendered", "H3 H5 H6 H7 H8 H10 H11",
            "keyboard walk, 320px and desktop renders, both themes, color-only meaning, truncation, error text and destructive actions need the browser and a read")

    counts = {s: sum(1 for r in rep.rows if r["status"] == s) for s in ("PASS", "WARN", "FAIL", "SKIP")}
    if a.json:
        print(json.dumps({"page": str(path), "counts": counts, "checks": rep.rows}, indent=2, ensure_ascii=False))
    else:
        for r in rep.rows:
            print(f"{r['status']:<5} {r['id']:<15} {r['rule']:<6} {r['message']}")
        print(f"\n{len(rep.rows)} checks: {counts['PASS']} pass, {counts['WARN']} warn, {counts['FAIL']} fail, {counts['SKIP']} skipped")
    return 1 if counts["FAIL"] else 0


def cmd_contrast(a) -> int:
    """Contrast of color pairs: fg bg [fg bg ...]. Text needs 4.5 (3 at large size); borders and focus rings 3."""
    vals = a.colors
    if len(vals) % 2:
        print("FAIL  give colors in pairs: <fg> <bg> [<fg> <bg> ...]")
        return 1
    worst = 99.0
    for fgs, bgs in zip(vals[::2], vals[1::2]):
        fg, bg = parse_color(fgs), parse_color(bgs)
        if not fg or not bg:
            print(f"SKIP  {fgs} on {bgs}: unsupported color notation")
            continue
        r = contrast(fg, bg[:3] + (1.0,))
        worst = min(worst, r)
        verdict = "text ok" if r >= 4.5 else ("large text and borders only" if r >= 3 else "fails")
        print(f"{r:5.2f}:1  {fgs} on {bgs}  ({verdict})")
    return 0 if worst >= 3 else 1


# ---------------------------------------------------------------- adherence

KEYWORDS = {"inherit", "initial", "unset", "revert", "currentcolor", "transparent", "none", "0"}
GENERIC_FAMILIES = {"inherit", "initial", "unset", "revert"}
COLOR_PROPS = re.compile(r"(background(-color)?|color|border(-\w+)*|outline(-color)?|fill|stroke|stop-color|text-decoration-color|caret-color|accent-color|box-shadow|text-shadow|--[\w-]+)")
RADIUS_PROPS = re.compile(r"border(-(top|bottom|start|end)-(left|right|start|end))?-radius")


def color_key(text: str):
    c = parse_color(text)
    if not c:
        return None
    return tuple(round(v * 255) for v in c[:3]) + (round(c[3] * 100),)


def all_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from all_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from all_strings(v)


def families(value: str) -> list[str]:
    return [f.strip().strip("\"'").lower() for f in value.split(",") if f.strip()]


def norm_len(v: str) -> str:
    v = v.strip().lower()
    return "0" if re.fullmatch(r"0+(\.0+)?(px|rem|em|%)?", v) else v


def split_top(value: str) -> list[str]:
    """Split a value on whitespace and '/' outside parentheses."""
    out, buf, depth = [], [], 0
    for ch in value:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if depth == 0 and (ch.isspace() or ch == "/"):
            if buf:
                out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        out.append("".join(buf))
    return out


class StyleAttrs(HTMLParser):
    """Inline style attributes and SVG color attributes, with line numbers."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.styles, self.paint = [], []

    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        for k, v in attrs:
            if k == "style" and v:
                self.styles.append((line, v))
            elif k in ("fill", "stroke", "stop-color", "flood-color", "color") and v:
                self.paint.append((line, k, v))

    handle_startendtag = handle_starttag


def load_allowed(tokens_path: Path, profile: Path | None):
    data = json.loads(tokens_path.read_text(encoding="utf-8"))
    toks, opts = data.get("tokens", {}) or {}, data.get("options", {}) or {}
    colors, fams, radii = set(), set(), set()
    for s in all_strings({"tokens": toks, "options": opts}):
        for m in COLOR_RE.finditer(s):
            k = color_key(m.group(0))
            if k:
                colors.add(k)
        k = color_key(s)
        if k:
            colors.add(k)
    font_values = list(all_strings(toks.get("font", {})))
    for o in opts.get("type", []) or []:
        if isinstance(o, dict):
            font_values += [v for key, v in o.items() if key.startswith("font-") and isinstance(v, str)]
    for v in font_values:
        fams.update(families(v))
    radius_values = list(all_strings(toks.get("radius", {})))
    for o in opts.get("shape", []) or []:
        if isinstance(o, dict):
            radius_values += [v for key, v in o.items() if key.startswith("r-") and isinstance(v, str)]
    for v in radius_values:
        radii.update(norm_len(p) for p in split_top(v))
    source = f"design-tokens.json v{data.get('version', '?')} ({data.get('date', '?')}) at {tokens_path}"
    if profile:
        text = profile.read_text(encoding="utf-8")
        over = strip_comments(css_blocks_from_profile(text))
        n = 0
        for r in parse_css(over):
            for p, v in r["decls"]:
                if not p.startswith("--"):
                    continue
                n += 1
                for m in COLOR_RE.finditer(v):
                    k = color_key(m.group(0))
                    if k:
                        colors.add(k)
                k = color_key(v)
                if k:
                    colors.add(k)
                if p.startswith("--font-"):
                    fams.update(families(v))
                if re.fullmatch(r"--r-[\w-]+", p):
                    radii.update(norm_len(x) for x in split_top(v))
        source += f"; client profile {profile} ({n} token overrides)"
    return colors, fams, radii, source


def color_problems(where: str, value: str, colors: set, named_too: bool) -> list[str]:
    out = []
    v = re.sub(r"url\([^)]*\)", "", value)
    v_novar = re.sub(r"var\(\s*--[\w-]+\s*(?:,[^()]*)?\)", "", v)
    for m in COLOR_RE.finditer(v_novar):
        if color_key(m.group(0)) not in colors:
            out.append(f"{where}: {m.group(0)}")
    if named_too:
        for m in NAMED_RE.finditer(v_novar):
            if color_key(m.group(0)) not in colors:
                out.append(f"{where}: {m.group(0)}")
    return out


def font_problems(where: str, prop: str, value: str, fams: set) -> list[str]:
    v = re.sub(r"var\(\s*--[\w-]+\s*(?:,[^()]*)?\)", "", value).strip()
    if prop == "font":
        m = re.search(r"\d*\.?\d+(?:px|rem|em|%|pt)(?:\s*/\s*[\d.]+\w*)?\s+(.+)$", v)
        if not m:
            return []
        v = m.group(1)
    if not v or v.lower() in GENERIC_FAMILIES:
        return []
    return [f"{where}: {f!r}" for f in families(v) if f not in fams and f not in GENERIC_FAMILIES]


def radius_problems(where: str, value: str, radii: set) -> list[str]:
    out = []
    for part in split_top(value):
        p = part.strip().lower()
        if "var(" in p or norm_len(p) in KEYWORDS or norm_len(p) in radii:
            continue
        out.append(f"{where}: {part}")
    return out


def cmd_adherence(a) -> int:
    path = Path(a.page)
    tokens_path = Path(a.tokens) if a.tokens else TOKENS_FILE
    profile = Path(a.profile) if a.profile else None
    rep = Report()
    if not path.is_file():
        print(f"FAIL  page not found: {path}")
        return 1
    if not tokens_path.is_file():
        print(f"FAIL  tokens file not found: {tokens_path}; pass --tokens <design-tokens.json>")
        return 1
    if profile and not profile.is_file():
        print(f"FAIL  client profile not found: {profile}")
        return 1
    try:
        colors, fams, radii, source = load_allowed(tokens_path, profile)
    except (ValueError, OSError) as e:
        print(f"FAIL  tokens file could not be read: {tokens_path}: {e}")
        return 1
    rep.add("PASS", "reference", "R1", f"judged against {source}: {len(colors)} colors, {len(fams)} font families, {len(radii)} radii allowed")

    html = path.read_text(encoding="utf-8", errors="replace")
    pg = Page()
    pg.feed(html)
    attrs = StyleAttrs()
    attrs.feed(html)
    css_parts = list(pg.styles)
    for href in pg.links:
        if re.match(r"https?:|//", href):
            rep.add("SKIP", "css-remote", "-", f"remote stylesheet not read: {href}")
            continue
        f = (path.parent / href).resolve()
        if f.is_file():
            css_parts.append(f.read_text(encoding="utf-8", errors="replace"))
        else:
            rep.add("WARN", "css-missing", "-", f"linked stylesheet not found: {href}")
    rules = parse_css(strip_comments("\n".join(css_parts)))

    bad_c, bad_f, bad_r, printed = [], [], [], 0
    for r in rules:
        if "print" in " ".join(r["context"]):
            printed += 1
            continue
        sel = r["selector"][:40]
        for p, v in r["decls"]:
            where = f"{sel} {{{p}}}"
            named = bool(COLOR_PROPS.fullmatch(p))
            bad_c += color_problems(where, v, colors, named)
            if p == "font-family" or p == "font" or p.startswith("--font-"):
                bad_f += font_problems(where, "font" if p == "font" else "font-family", v, fams)
            if RADIUS_PROPS.fullmatch(p) or re.fullmatch(r"--r-[\w-]+", p):
                bad_r += radius_problems(where, v, radii)
    for ln, style in attrs.styles:
        for d in split_decls(style):
            if ":" not in d:
                continue
            p, v = (x.strip() for x in d.split(":", 1))
            p = p.lower()
            where = f"line {ln} style {p}"
            bad_c += color_problems(where, v, colors, bool(COLOR_PROPS.fullmatch(p)))
            if p in ("font-family", "font"):
                bad_f += font_problems(where, p, v, fams)
            if RADIUS_PROPS.fullmatch(p):
                bad_r += radius_problems(where, v, radii)
    for ln, k, v in attrs.paint:
        if v.strip().lower() in KEYWORDS or v.strip().lower().startswith(("url(", "var(")):
            continue
        bad_c += color_problems(f"line {ln} {k}", v, colors, True)

    rep.add("FAIL" if bad_c else "PASS", "colors", "R1",
            (f"{len(bad_c)} color values not in the tokens: " + "; ".join(bad_c[:10]) + (" ..." if len(bad_c) > 10 else ""))
            if bad_c else "every color is a token value or a var(--...) reference")
    rep.add("FAIL" if bad_f else "PASS", "fonts", "R1",
            (f"{len(bad_f)} font families not in the tokens: " + "; ".join(bad_f[:10])) if bad_f
            else "every font family is a token family or a var(--...) reference")
    rep.add("FAIL" if bad_r else "PASS", "radius", "R1",
            (f"{len(bad_r)} border-radius values not in the tokens: " + "; ".join(bad_r[:10])) if bad_r
            else "every border-radius is a token value or a var(--...) reference")
    if printed:
        rep.add("SKIP", "print", "-", f"{printed} print-only rules not checked (print follows paper, not the screen design)")
    if not rules and not attrs.styles:
        rep.add("SKIP", "css", "-", "no CSS or inline styles found")
    rep.add("SKIP", "not-scripted", "R1",
            "spacing, font sizes, shadows, motion, and components are not checked by script: compare a screenshot with the design reference")

    counts = {s: sum(1 for r in rep.rows if r["status"] == s) for s in ("PASS", "WARN", "FAIL", "SKIP")}
    for r in rep.rows:
        print(f"{r['status']:<5} {r['id']:<15} {r['rule']:<6} {r['message']}")
    print(f"\n{len(rep.rows)} checks: {counts['PASS']} pass, {counts['WARN']} warn, {counts['FAIL']} fail, {counts['SKIP']} skipped")
    return 1 if counts["FAIL"] else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new", help="create a page from the house starter")
    n.add_argument("out")
    n.add_argument("--title", required=True)
    n.add_argument("--lang", default="en")
    n.add_argument("--profile", help="client profile Markdown with ```css token overrides")
    n.add_argument("--no-web-fonts", action="store_true", help="leave out the Google Fonts link (offline files)")
    n.add_argument("--force", action="store_true")
    c = sub.add_parser("check", help="check a page; changes nothing")
    c.add_argument("page")
    c.add_argument("--css", nargs="*", help="extra stylesheet files to include")
    c.add_argument("--json", action="store_true")
    k = sub.add_parser("contrast", help="contrast ratio of color pairs: fg bg [fg bg ...]")
    k.add_argument("colors", nargs="+")
    d = sub.add_parser("adherence", help="check that colors, fonts, and radii are design tokens; changes nothing")
    d.add_argument("page")
    d.add_argument("--tokens", help="design-tokens.json (default: assets/design-tokens.json next to this script)")
    d.add_argument("--profile", help="client profile Markdown whose ```css overrides extend the allowed values")
    a = ap.parse_args(argv)
    return {"new": cmd_new, "check": cmd_check, "contrast": cmd_contrast, "adherence": cmd_adherence}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
