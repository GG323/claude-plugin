"""Scripted checks for environment-audit's Workspace audit stage.

Checks a workspace's AGENTS.md against the Markdown conventions in this
skill's references/markdown-conventions.md, against the installed skills and agents, and against the
workspace's top-level folders and files, and prints the result as JSON.
Writes nothing.

Usage:
  py -3 check_agents.py --workspace <folder with AGENTS.md>
                        [--global-dir <~/.claude>] [--no-web]
"""

import argparse
import concurrent.futures
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFERENCE = os.path.join(SKILL_DIR, "references", "markdown-conventions.md")
MAX_LINES = 200  # the Claude Code memory docs' target for CLAUDE.md/AGENTS.md
LONG_PARAGRAPH_WORDS = 80
LONG_BULLET_WORDS = 50
WEB_TIMEOUT = 15  # seconds; official docs answer well within this

LINK_RE = re.compile(r"!?\[([^\]]*)\]\(\s*(?:<([^>]+)>|([^)\s]+))(?:\s+\"[^\"]*\")?\s*\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
CODE_SPAN_RE = re.compile(r"(`+)(.+?)\1")
BULLET_RE = re.compile(r"^\s*([-*+]|\d+\.)\s+")


def slug(text):
    text = CODE_SPAN_RE.sub(lambda m: m.group(2), text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[^\w\- ]", "", text.strip().lower())
    return text.replace(" ", "-")


class Doc:
    """A Markdown file split into lines, with fences and headings."""

    def __init__(self, path):
        with open(path, encoding="utf-8", errors="replace") as f:
            self.lines = f.read().splitlines()
        self.in_fence = []
        fence = False
        for line in self.lines:
            if FENCE_RE.match(line):
                self.in_fence.append(True)
                fence = not fence
                continue
            self.in_fence.append(fence)
        self.headings = []  # (line index, level, text)
        for i, line in enumerate(self.lines):
            m = None if self.in_fence[i] else HEADING_RE.match(line)
            if m:
                self.headings.append((i, len(m.group(1)), m.group(2)))
        self.anchors, counts = set(), {}
        for _, _, text in self.headings:
            s = slug(text)
            n = counts.get(s, 0)
            self.anchors.add(s if n == 0 else "%s-%d" % (s, n))
            counts[s] = n + 1

    def section(self, title, level=2):
        for idx, (i, lvl, text) in enumerate(self.headings):
            if lvl == level and text.strip().lower() == title.lower():
                end = next((j for j, l2, _ in self.headings[idx + 1:] if l2 <= level), len(self.lines))
                return i, end
        return None

    def links(self, start=0, end=None):
        for i in range(start, len(self.lines) if end is None else end):
            if self.in_fence[i]:
                continue
            line = CODE_SPAN_RE.sub(lambda m: " " * len(m.group(0)), self.lines[i])
            for m in LINK_RE.finditer(line):
                yield i, m.group(2) or m.group(3)


class Check:
    def __init__(self, args):
        self.workspace = os.path.abspath(args.workspace)
        self.global_dir = os.path.abspath(os.path.expanduser(args.global_dir))
        self.reference = REFERENCE
        self.no_web = args.no_web
        self.findings, self.skipped = [], []
        self.web_checked = 0

    def find(self, check, line, message, section=None):
        self.findings.append({"check": check, "line": None if line is None else line + 1,
                              "section": section, "message": message})

    def conventions(self, d):
        ref = Doc(self.reference)
        mine, theirs = d.section("Markdown conventions"), ref.section("Markdown conventions")
        if theirs is None:
            fail("The reference has no 'Markdown conventions' section: %s" % self.reference)
        if mine is None:
            self.find("W1", None, "No 'Markdown conventions' section; add the reference text.")
            return
        a = [l.rstrip() for l in d.lines[mine[0]:mine[1]]]
        b = [l.rstrip() for l in ref.lines[theirs[0]:theirs[1]]]
        while a and not a[-1]:
            a.pop()
        while b and not b[-1]:
            b.pop()
        for k in range(max(len(a), len(b))):
            x = a[k] if k < len(a) else "<missing>"
            y = b[k] if k < len(b) else "<missing>"
            if x != y:
                self.find("W1", mine[0] + k, "Differs from the reference.\n  AGENTS.md: %s\n  reference: %s" % (x, y), "Markdown conventions")
                return

    def length(self, d):
        if len(d.lines) >= MAX_LINES:
            self.find("W2", None, "%d lines; keep it under %d." % (len(d.lines), MAX_LINES))
        conv = d.section("Markdown conventions") or (0, 0)
        para, start = [], None

        def flush():
            words = len(" ".join(para).split())
            if para and words > LONG_PARAGRAPH_WORDS:
                self.find("W2", start, "Paragraph of %d words (over %d); propose a shorter version." % (words, LONG_PARAGRAPH_WORDS))

        for i, line in enumerate(d.lines + [""]):
            inside = i < len(d.lines) and (d.in_fence[i] or conv[0] <= i < conv[1])
            if inside or not line.strip() or HEADING_RE.match(line) or BULLET_RE.match(line) or line.lstrip().startswith("|"):
                flush()
                para, start = [], None
                if not inside and BULLET_RE.match(line):
                    words = len(BULLET_RE.sub("", line).split())
                    if words > LONG_BULLET_WORDS:
                        self.find("W2", i, "Bullet of %d words (over %d); propose a shorter version." % (words, LONG_BULLET_WORDS))
                continue
            if start is None:
                start = i
            para.append(line.strip())

    def structure(self, d):
        body = [i for i, l in enumerate(d.lines) if l.strip() and not d.in_fence[i]]
        if not d.headings or not body or d.headings[0][0] != body[0] or d.headings[0][1] != 1:
            self.find("W3", body[0] if body else None, "The file does not start with its # title.")
        elif len(d.headings) < 2 or d.headings[1][1] != 2 or d.headings[1][2].strip().lower() != "contents":
            self.find("W3", d.headings[0][0], "The title is not followed by a ## Contents section.")
        h1 = [h for h in d.headings if h[1] == 1]
        if len(h1) != 1:
            self.find("W3", h1[1][0] if len(h1) > 1 else None, "There are %d # headings; exactly one is allowed." % len(h1))
        prev = 1
        for i, lvl, text in d.headings:
            if lvl > prev + 1:
                self.find("W3", i, "Heading level skipped: '%s' is level %d under level %d." % (text, lvl, prev), text)
            prev = lvl
        contents = d.section("Contents")
        if contents is None:
            return
        listed = set()
        for i, target in d.links(*contents):
            if target.startswith("#"):
                listed.add(target[1:])
                if target[1:] not in d.anchors:
                    self.find("W3", i, "Contents entry '%s' matches no heading." % target, "Contents")
        h2 = [(i, t) for i, lvl, t in d.headings if lvl == 2 and t.strip().lower() != "contents"]
        for i, text in h2:
            if slug(text) not in listed:
                self.find("W3", i, "Section '%s' is missing from the contents list." % text, text)
        if "skills-and-agents" not in listed:
            self.find("W3", contents[0], "The contents list has no 'Skills and agents' entry.", "Contents")
        if h2 and h2[-1][1].strip().lower() != "skills and agents":
            self.find("W3", h2[-1][0], "'Skills and agents' is not the last section.", h2[-1][1])

    def links(self, d, path):
        contents = d.section("Contents") or (0, 0)
        web = {}
        for i, target in d.links():
            if target.startswith("#") and contents[0] <= i < contents[1]:
                continue  # contents entries are covered by the structure check
            if re.match(r"^https?://", target):
                web.setdefault(target.split("#")[0], []).append(i)
                continue
            if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):
                continue
            if "\\" in target:
                self.find("W3", i, "Relative link uses backslashes: %s" % target)
            file_part, _, anchor = target.replace("\\", "/").partition("#")
            file_part = urllib.parse.unquote(file_part)  # %20 and friends in link targets
            dest = os.path.normpath(os.path.join(os.path.dirname(path), file_part)) if file_part else path
            if file_part:
                real = os.path.realpath(dest)
                if not (real == self.workspace or real.startswith(self.workspace + os.sep)):
                    self.find("W3", i, "Link points outside the workspace; name it as code instead: %s" % target)
                if not os.path.exists(dest):
                    self.find("W3", i, "Link target does not exist: %s" % target)
                    continue
            if anchor and dest.endswith(".md") and os.path.isfile(dest) and anchor not in Doc(dest).anchors:
                self.find("W3", i, "Anchor '#%s' matches no heading in %s." % (anchor, os.path.basename(dest)))
        if self.no_web:
            if web:
                self.skipped.append("W3 web links: %d not checked (--no-web)." % len(web))
            return
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = dict(zip(web, pool.map(probe, web)))
        self.web_checked = len(results)
        for url, (ok, status) in sorted(results.items()):
            if ok:
                continue
            if status == "429":
                self.skipped.append("W3 web link rate-limited, not verified: %s" % url)
                continue
            for i in web[url]:
                self.find("W3", i, "Web link fails (%s): %s" % (status, url))

    def skills_list(self, d):
        installed = installed_skills(self.global_dir)
        installed.update(installed_skills(os.path.join(self.workspace, ".claude")))
        section = d.section("Skills and agents")
        if section is None:
            return installed
        listed = {}
        for i in range(*section):
            m = re.match(r"^\s*[-*]\s+\[?`([^`]+)`", d.lines[i]) or re.match(r"^\s*[-*]\s+\[([^\]`]+)\]", d.lines[i])
            if m:
                listed[m.group(1).strip()] = i
        for name in sorted(set(installed) - set(listed)):
            self.find("W4", section[0], "Installed but not listed: `%s`." % name, "Skills and agents")
        for name in sorted(set(listed) - set(installed)):
            self.find("W4", listed[name], "Listed but not installed: `%s`; propose removal." % name, "Skills and agents")
        return installed

    def layout(self, d):
        entries = layout_entries(self.workspace)
        section = d.section("Workspace layout")
        if section is None:
            self.find("W7", None, "No 'Workspace layout' section; propose one from the folder analysis.")
            return entries
        listed = {}
        for i, target in d.links(*section):
            name = target.rstrip("/").split("/")[0]
            if name and not target.startswith(("#", "http")):
                listed[name] = i
        on_disk = {e["name"] for e in entries}
        for name in sorted(on_disk - set(listed)):
            self.find("W7", section[0], "On disk but not in the layout: `%s`." % name, "Workspace layout")
        for name in sorted(set(listed) - on_disk):
            self.find("W7", listed[name], "In the layout but not on disk: `%s`." % name, "Workspace layout")
        return entries

    def run(self):
        if not os.path.isfile(self.reference):
            fail("The conventions reference is missing: %s. Restore it from the skill's source." % self.reference)
        path = os.path.join(self.workspace, "AGENTS.md")
        if not os.path.isfile(path):
            return {"agents_md": None, "reference": self.reference.replace(os.sep, "/"),
                    "installed": dict(installed_skills(self.global_dir), **installed_skills(os.path.join(self.workspace, ".claude"))),
                    "layout": layout_entries(self.workspace), "findings": [], "checks_run": [],
                    "skipped_checks": [], "message": "No AGENTS.md in the workspace; offer to create one."}
        d = Doc(path)
        self.conventions(d)
        self.length(d)
        self.structure(d)
        self.links(d, path)
        installed = self.skills_list(d)
        layout = self.layout(d)
        counts = {}
        for f in self.findings:
            counts[f["check"]] = counts.get(f["check"], 0) + 1
        return {
            "agents_md": path.replace(os.sep, "/"),
            "lines": len(d.lines),
            "reference": self.reference.replace(os.sep, "/"),
            "installed": installed,
            "layout": layout,
            "findings": self.findings,
            "checks_run": ["W1", "W2", "W3", "W4", "W7"],
            "web_links_checked": self.web_checked,
            "skipped_checks": self.skipped,
            "counts": dict(sorted(counts.items())),
        }


SKIP_DIRS = {"node_modules", "__pycache__", "venv", ".venv"}


def layout_entries(workspace):
    """Top-level folders and root Markdown files, with hints for describing them."""
    entries = []
    for name in sorted(os.listdir(workspace), key=str.lower):
        path = os.path.join(workspace, name)
        if name.startswith((".", "_")) or name in SKIP_DIRS or name == "AGENTS.md":
            continue
        if os.path.isdir(path):
            files, kinds = 0, {}
            for _, dirnames, filenames in os.walk(path):
                dirnames[:] = [x for x in dirnames if not x.startswith(".") and x not in SKIP_DIRS]
                files += len(filenames)
                for f in filenames:
                    ext = os.path.splitext(f)[1].lower() or "(none)"
                    kinds[ext] = kinds.get(ext, 0) + 1
                if files > 5000:
                    break  # enough to describe a large folder
            readme = next((name + "/" + f for f in ("README.md", "readme.md", "README") if os.path.isfile(os.path.join(path, f))), None)
            entries.append({"name": name, "kind": "folder", "files": files,
                            "top_types": sorted(kinds, key=kinds.get, reverse=True)[:5],
                            "readme": readme, "git_repo": os.path.isdir(os.path.join(path, ".git")),
                            "children": sorted(os.listdir(path))[:10]})
        elif name.lower().endswith(".md"):
            entries.append({"name": name, "kind": "file"})
    return entries


def installed_skills(global_dir):
    """Installed skills and agents, each with its one-line description."""
    installed = {}
    skills_root = os.path.join(global_dir, "skills")
    if os.path.isdir(skills_root):
        for n in sorted(os.listdir(skills_root)):
            skill_md = os.path.join(skills_root, n, "SKILL.md")
            if os.path.isfile(skill_md):
                installed[n] = description(skill_md)
    agents_root = os.path.join(global_dir, "agents")
    if os.path.isdir(agents_root):
        for n in sorted(os.listdir(agents_root)):
            if n.endswith(".md"):
                installed[n[:-3]] = description(os.path.join(agents_root, n))
    return installed


def description(path):
    """The frontmatter description, for a one-line entry in the skills list."""
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    if m:
        d = re.search(r"^description:\s*(.*)$", m.group(1), re.M)
        if d:
            return d.group(1).strip().strip("'\"")
    return ""


def probe(url):
    headers = {"User-Agent": "environment-audit link check"}
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, method=method, headers=headers)
            with urllib.request.urlopen(req, timeout=WEB_TIMEOUT) as resp:
                return True, str(resp.status)
        except urllib.error.HTTPError as e:
            if method == "GET" or e.code not in (403, 405, 501):
                return e.code < 400, str(e.code)
        except Exception as e:  # timeouts, DNS failures, TLS errors
            if method == "GET":
                return False, type(e).__name__
    return False, "unknown"


def fail(message):
    print(json.dumps({"error": message}, ensure_ascii=False))
    sys.exit(2)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Scripted checks for environment-audit's Workspace audit stage.")
    parser.add_argument("--workspace", required=True, help="folder that holds (or should hold) AGENTS.md")
    parser.add_argument("--global-dir", default="~/.claude", help="global Claude folder")
    parser.add_argument("--no-web", action="store_true", help="skip web link checks")
    args = parser.parse_args()
    if not os.path.isdir(args.workspace):
        fail("Workspace folder not found: %s" % args.workspace)
    print(json.dumps(Check(args).run(), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
