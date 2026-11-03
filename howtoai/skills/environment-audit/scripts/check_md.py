"""Scripted checks for environment-audit's Tool audit stage.

Finds the user-made Markdown instruction files in a .claude folder (the global
~/.claude by default, or a workspace's .claude, together with the workspace's
root CLAUDE.md and CLAUDE.local.md), runs the deterministic checks from
references/checks.md on them (S, L, D, plus I2 for ${CLAUDE_SKILL_DIR} paths
and I5 for settings files), and prints the result as JSON. Writes nothing.

Usage:
  py -3 check_md.py [--root <.claude folder>] [--since YYYY-MM-DD]
                    [--files <path> ...] [--no-web] [--as-of YYYY-MM-DD]
"""

import argparse
import concurrent.futures
import datetime
import fnmatch
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCLUSIONS = os.path.join(SKILL_DIR, "state", "exclusions.md")
EXCEPTIONS = os.path.join(SKILL_DIR, "state", "exceptions.md")

# Folders whose files have a format fixed by a tool, a deliverable, or the
# skill that owns them; an added title or contents list would break them.
FIXED_FORMAT_DIRS = {"evals", "state", "assets"}
SKILL_MAX_LINES = 500
WEB_TIMEOUT = 15  # seconds; official docs answer well within this

LINK_RE = re.compile(r"!?\[([^\]]*)\]\(\s*(?:<([^>]+)>|([^)\s]+))(?:\s+\"[^\"]*\")?\s*\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
CODE_SPAN_RE = re.compile(r"(`+)(.+?)\1")
SKILL_DIR_RE = re.compile(r"\$\{CLAUDE_SKILL_DIR\}/([^\s\"'`)<>*…]+)")  # "…" marks a placeholder
SETTINGS_FILES = ("settings.json", "settings.local.json")


def display(path, global_dir, workspace_root=None):
    real = os.path.abspath(path)
    if workspace_root:
        # Workspace files are shown relative to the workspace, as the report shows them.
        ws = os.path.abspath(workspace_root)
        if real.startswith(ws + os.sep):
            return os.path.relpath(real, ws).replace(os.sep, "/")
    root = os.path.abspath(global_dir)
    # The ~/.claude label only for the real default folder, so a report on
    # another folder never suggests it is about the user's own files.
    label = "~/.claude" if root == os.path.abspath(os.path.expanduser("~/.claude")) else root.replace(os.sep, "/")
    if real == root or real.startswith(root + os.sep):
        return label + "/" + os.path.relpath(real, root).replace(os.sep, "/")
    return real.replace(os.sep, "/")


def slug(text):
    text = CODE_SPAN_RE.sub(lambda m: m.group(2), text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = text.strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


class Doc:
    """A Markdown file split into lines, with fences, frontmatter, and headings."""

    def __init__(self, path):
        self.path = path
        with open(path, encoding="utf-8", errors="replace") as f:
            self.text = f.read()
        self.lines = self.text.splitlines()
        self.frontmatter = None
        self.body_start = 0
        if self.lines and self.lines[0].strip() == "---":
            for i in range(1, len(self.lines)):
                if self.lines[i].strip() == "---":
                    self.frontmatter = self.lines[1:i]
                    self.body_start = i + 1
                    break
        self.in_fence = [False] * len(self.lines)
        fence = False
        for i, line in enumerate(self.lines):
            if FENCE_RE.match(line):
                self.in_fence[i] = True
                fence = not fence
                continue
            self.in_fence[i] = fence
        self.headings = []  # (line index, level, text)
        for i in range(self.body_start, len(self.lines)):
            if self.in_fence[i]:
                continue
            m = HEADING_RE.match(self.lines[i])
            if m:
                self.headings.append((i, len(m.group(1)), m.group(2)))
        self.anchors = set()
        counts = {}
        for _, _, text in self.headings:
            s = slug(text)
            n = counts.get(s, 0)
            self.anchors.add(s if n == 0 else "%s-%d" % (s, n))
            counts[s] = n + 1

    def section(self, title, level=2):
        """Line range of the section with this heading title, or None."""
        for idx, (i, lvl, text) in enumerate(self.headings):
            if lvl == level and text.strip().lower() == title.lower():
                end = len(self.lines)
                for j, lvl2, _ in self.headings[idx + 1:]:
                    if lvl2 <= level:
                        end = j
                        break
                return i, end
        return None

    def links(self, start=0, end=None):
        end = len(self.lines) if end is None else end
        for i in range(start, end):
            if self.in_fence[i]:
                continue
            line = CODE_SPAN_RE.sub(lambda m: " " * len(m.group(0)), self.lines[i])
            for m in LINK_RE.finditer(line):
                yield i, m.group(1), m.group(2) or m.group(3)

    def field(self, key):
        for line in self.frontmatter or []:
            m = re.match(r"^%s:\s*(.*)$" % re.escape(key), line)
            if m:
                return m.group(1).strip().strip("'\"")
        return None


class Audit:
    def __init__(self, args):
        self.args = args
        self.global_dir = os.path.abspath(os.path.expanduser(args.global_dir))
        # A .claude folder other than the global one belongs to a workspace (its
        # parent); skills there may link that workspace's files.
        default = os.path.abspath(os.path.expanduser("~/.claude"))
        is_workspace = os.path.basename(self.global_dir) == ".claude" and self.global_dir != default
        self.workspace_root = os.path.realpath(os.path.dirname(self.global_dir)) if is_workspace else None
        self.findings = []
        self.skipped_checks = []
        self.web_links = {}  # url -> list of (path, line)
        self.docs = {}
        # The target's name as the report and state/exceptions.md show it.
        self.target = os.path.basename(self.workspace_root) if self.workspace_root else "Global folder"

    def show(self, path):
        return display(path, self.global_dir, self.workspace_root)

    def find(self, check, path, line, message, section=None):
        self.findings.append({
            "check": check,
            "file": self.show(path),
            "line": None if line is None else line + 1,
            "section": section,
            "message": message,
        })

    def doc(self, path):
        key = os.path.realpath(path)
        if key not in self.docs:
            self.docs[key] = Doc(path)
        return self.docs[key]

    # Inventory -----------------------------------------------------------

    def inventory(self):
        patterns = read_code_bullets(EXCLUSIONS)
        audited, exempt, excluded, seen = [], [], [], set()
        roots = [os.path.join(self.global_dir, d) for d in ("skills", "agents", "commands", "output-styles", "rules")]
        candidates = []
        for root in roots:
            for dirpath, dirnames, filenames in os.walk(root, followlinks=True):
                dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
                candidates += [os.path.join(dirpath, f) for f in sorted(filenames) if f.endswith(".md")]
        loose = [os.path.join(self.global_dir, "CLAUDE.md")]
        if self.workspace_root:
            # A workspace's own CLAUDE.md files sit next to its .claude folder.
            loose += [os.path.join(self.workspace_root, n) for n in ("CLAUDE.md", "CLAUDE.local.md")]
        candidates += [p for p in loose if os.path.isfile(p)]
        if self.args.files:
            wanted = {os.path.realpath(os.path.expanduser(f)) for f in self.args.files}
            candidates = [c for c in candidates if os.path.realpath(c) in wanted]
        since = None
        if self.args.since:
            since = datetime.datetime.strptime(self.args.since, "%Y-%m-%d").timestamp()
        for path in candidates:
            real = os.path.realpath(path)
            if real in seen:
                continue
            seen.add(real)
            shown = self.show(path)
            if any(fnmatch.fnmatch(shown, p) for p in patterns):
                excluded.append(shown)
                continue
            if since and os.path.getmtime(path) < since:
                continue
            rel = os.path.relpath(path, self.global_dir).replace(os.sep, "/").split("/")
            if FIXED_FORMAT_DIRS.intersection(rel[:-1]):
                exempt.append(path)
            else:
                audited.append(path)
        return audited, exempt, excluded

    # General checks --------------------------------------------------------

    def owner_root(self, path):
        """The skill, agent, or command folder a file belongs to."""
        rel = os.path.relpath(path, self.global_dir).split(os.sep)
        if rel[0] == "skills" and len(rel) > 2:
            return os.path.realpath(os.path.join(self.global_dir, rel[0], rel[1]))
        return os.path.realpath(os.path.dirname(path))

    def check_structure(self, path):
        d = self.doc(path)
        body = [i for i in range(d.body_start, len(d.lines)) if d.lines[i].strip() and not d.in_fence[i]]
        needs_frontmatter = os.path.basename(path) == "SKILL.md" or "agents" in os.path.relpath(path, self.global_dir).split(os.sep)[:1]
        if needs_frontmatter and d.frontmatter is None:
            self.find("S1", path, 0, "Frontmatter is required here and must come first.")
        if not d.headings or not body or d.headings[0][0] != body[0] or d.headings[0][1] != 1:
            self.find("S1", path, body[0] if body else 0, "The file does not start with its # title.")
        elif len(d.headings) < 2 or d.headings[1][1] != 2 or d.headings[1][2].strip().lower() != "contents":
            self.find("S1", path, d.headings[0][0], "The title is not followed by a ## Contents section.")
        h1 = [h for h in d.headings if h[1] == 1]
        if len(h1) != 1:
            self.find("S2", path, h1[1][0] if len(h1) > 1 else 0, "There are %d # headings; exactly one is allowed." % len(h1))
        prev = 1
        for i, lvl, text in d.headings:
            if lvl > prev + 1:
                self.find("S2", path, i, "Heading level skipped: '%s' is level %d under level %d." % (text, lvl, prev), text)
            prev = lvl
        h2 = [(i, t) for i, lvl, t in d.headings if lvl == 2 and t.strip().lower() != "contents"]
        if h2 and h2[-1][1].strip().lower() != "skills and agents":
            self.find("S4", path, h2[-1][0], "'Skills and agents' is not the last section.", h2[-1][1])
        contents = d.section("Contents")
        if contents is None:
            return  # S1 already reports the missing contents list
        listed = set()
        for i, _, target in d.links(*contents):
            if target.startswith("#"):
                listed.add(target[1:])
                if target[1:] not in d.anchors:
                    self.find("S3", path, i, "Contents entry '%s' matches no heading." % target, "Contents")
        for i, text in h2:
            if slug(text) not in listed:
                self.find("S3", path, i, "Section '%s' is missing from the contents list." % text, text)
        if "skills-and-agents" not in listed:
            self.find("S4", path, contents[0], "The contents list has no 'Skills and agents' entry.", "Contents")

    def check_links(self, path, root):
        d = self.doc(path)
        contents = d.section("Contents") or (0, 0)
        for i, _, target in d.links():
            if target.startswith("#") and contents[0] <= i < contents[1]:
                continue  # contents entries are S3's job; reporting them twice adds noise
            if re.match(r"^(https?:)//", target):
                self.web_links.setdefault(target.split("#")[0], []).append((path, i))
                continue
            if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):
                continue  # mailto:, file:, and other schemes are not checked
            if "\\" in target:
                self.find("L2", path, i, "Relative link uses backslashes: %s" % target)
            file_part, _, anchor = target.replace("\\", "/").partition("#")
            file_part = urllib.parse.unquote(file_part)  # %20 and friends in link targets
            dest = os.path.normpath(os.path.join(os.path.dirname(path), file_part)) if file_part else path
            if file_part and not self.link_allowed(os.path.realpath(dest), root):
                where = "its workspace" if self.workspace_root else "its own skill or tool"
                self.find("L4", path, i, "Link points outside %s, or into another skill; name it as code instead: %s" % (where, target))
            if file_part:
                if not os.path.exists(dest):
                    self.find("L1", path, i, "Link target does not exist: %s" % target)
                    continue
            if anchor and dest.endswith(".md") and os.path.isfile(dest):
                if anchor not in self.doc(dest).anchors:
                    self.find("L1", path, i, "Anchor '#%s' matches no heading in %s." % (anchor, os.path.basename(dest)))

    def check_skill_paths(self, path, root):
        """I2 (scripted part): ${CLAUDE_SKILL_DIR}/... paths name real files."""
        d = self.doc(path)
        for i, line in enumerate(d.lines):
            if re.search(r"\b(for example|e\.g\.)", line, re.I):
                continue  # a sample command for another skill, not this skill's own path
            missing = []
            for m in SKILL_DIR_RE.finditer(line):
                target = m.group(1).rstrip(".,;:")
                if target not in missing and not os.path.exists(os.path.join(root, target)):
                    missing.append(target)
            for target in missing:
                self.find("I2", path, i, "Path does not exist in the skill: ${CLAUDE_SKILL_DIR}/%s" % target)

    def check_settings(self):
        """I5: settings files in the .claude folder parse as JSON."""
        for name in SETTINGS_FILES:
            path = os.path.join(self.global_dir, name)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, encoding="utf-8-sig") as f:
                    json.load(f)
            except ValueError as e:
                line = getattr(e, "lineno", None)
                self.find("I5", path, None if line is None else line - 1, "Settings file does not parse as JSON: %s" % e)

    def link_allowed(self, real, root):
        """Global skills link only inside themselves; workspace skills may link
        anywhere in their workspace except into another skill's folder."""
        def within(base):
            return real == base or real.startswith(base + os.sep)
        if within(root):
            return True
        if self.workspace_root is None or not within(self.workspace_root):
            return False
        skills = os.path.realpath(os.path.join(self.global_dir, "skills"))
        return not within(skills)

    def check_web(self):
        if self.args.no_web:
            if self.web_links:
                self.skipped_checks.append("L3: %d web links not checked (--no-web)." % len(self.web_links))
            return
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = dict(zip(self.web_links, pool.map(probe, self.web_links)))
        for url, (ok, status) in sorted(results.items()):
            if ok:
                continue
            if status == "429":
                self.skipped_checks.append("L3: %s was rate-limited and not verified." % url)
                continue
            for path, i in self.web_links[url]:
                self.find("L3", path, i, "Web link fails (%s): %s" % (status, url))

    # Skill and agent definitions ---------------------------------------------

    def check_skill(self, skill_dir, audited):
        skill_md = os.path.join(skill_dir, "SKILL.md")
        if not os.path.isfile(skill_md):
            return
        d = self.doc(skill_md)
        folder = os.path.basename(skill_dir.rstrip(os.sep))
        name = d.field("name")
        if d.frontmatter is None or not name or not d.field("description"):
            self.find("D1", skill_md, 0, "Frontmatter is missing or lacks name or description.")
        elif name != folder:
            self.find("D1", skill_md, 0, "Frontmatter name '%s' does not match folder '%s'." % (name, folder))
        if len(d.lines) - d.body_start >= SKILL_MAX_LINES:
            self.find("D2", skill_md, None, "SKILL.md body has %d lines; keep it under %d." % (len(d.lines) - d.body_start, SKILL_MAX_LINES))
        linked = set()
        for _, _, target in d.links():
            part = target.split("#")[0]
            if part and not re.match(r"^[a-z][a-z0-9+.-]*:", part, re.I):
                linked.add(os.path.realpath(os.path.join(skill_dir, part)))
        real_dir = os.path.realpath(skill_dir)
        for path in audited:
            if os.path.realpath(path).startswith(real_dir + os.sep) and os.path.basename(path) != "SKILL.md":
                if os.path.realpath(path) not in linked:
                    self.find("D2", path, None, "Not linked directly from SKILL.md (references stay one level deep).")
        if folder != "skill-builder":
            feedback = d.section("Feedback")
            if feedback is None or "skill-builder" not in "\n".join(d.lines[feedback[0]:feedback[1]]):
                self.find("D3", skill_md, None, "No Feedback section that sends changes to `skill-builder`.")

    # Run -------------------------------------------------------------------

    def run(self):
        audited, exempt, excluded = self.inventory()
        for path in audited:
            self.check_structure(path)
        for path in audited + exempt:
            if not is_fixture(os.path.relpath(path, self.global_dir)):  # test inputs may be broken on purpose
                self.check_links(path, self.owner_root(path))
        for path in audited:
            if os.path.relpath(path, self.global_dir).split(os.sep)[0] == "skills":
                self.check_skill_paths(path, self.owner_root(path))
        if not self.args.files:
            self.check_settings()
        skills_root = os.path.join(self.global_dir, "skills")
        if os.path.isdir(skills_root):
            for name in sorted(os.listdir(skills_root)):
                real_skill = os.path.realpath(os.path.join(skills_root, name))
                if self.args.files and not any(os.path.realpath(p).startswith(real_skill + os.sep) for p in audited + exempt):
                    continue  # a --files re-check covers only the skills it touches
                shown = self.show(os.path.join(skills_root, name, "SKILL.md"))
                if not any(fnmatch.fnmatch(shown, p) for p in read_code_bullets(EXCLUSIONS)):
                    self.check_skill(os.path.join(skills_root, name), audited)
        self.check_web()
        accepted = read_exceptions()
        kept, waived = [], []
        for f in self.findings:
            (waived if (f["check"], self.target, f["file"]) in accepted else kept).append(f)
        return {
            "as_of": self.args.as_of or datetime.date.today().isoformat(),
            "root": self.global_dir.replace(os.sep, "/"),
            "target": self.target,
            "audited": [self.show(p) for p in audited],
            "exempt": [self.show(p) for p in exempt],
            "excluded": excluded,
            "findings": kept,
            "accepted_exceptions": waived,
            "checks_run": ["S1", "S2", "S3", "S4", "L1", "L2", "L4", "D1", "D2", "D3", "I2"]
                          + ([] if self.args.files else ["I5"])
                          + ([] if self.args.no_web else ["L3"]),
            "skipped_checks": self.skipped_checks,
            "counts": count_by_check(kept),
        }


def is_fixture(path):
    """An input file of a saved test case (evals/<case>/files/...), judged by
    the path relative to the target folder, so a target that itself sits inside
    a test case is still checked."""
    parts = os.path.normpath(path).split(os.sep)
    return any(parts[i] == "evals" and i + 2 < len(parts) - 1 and parts[i + 2] == "files"
               for i in range(len(parts)))


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


def read_state(path):
    """A state file's text without fenced blocks, which hold format examples."""
    if not os.path.isfile(path):
        return ""
    with open(path, encoding="utf-8") as f:
        return re.sub(r"^\s*(```|~~~).*?^\s*\1\s*$", "", f.read(), flags=re.M | re.S)


def read_code_bullets(path):
    """Patterns from list items written as `pattern`."""
    return [m.group(1) for m in re.finditer(r"^\s*-\s+`([^`]+)`", read_state(path), re.M)]


def read_exceptions():
    """(check, target, file) from list items written as `check` · `target` · `file` · reason."""
    return set(re.findall(r"^\s*-\s+`([A-Z]\d+)`[^`]*`([^`]+)`[^`]*`([^`]+)`", read_state(EXCEPTIONS), re.M))


def count_by_check(findings):
    counts = {}
    for f in findings:
        counts[f["check"]] = counts.get(f["check"], 0) + 1
    return dict(sorted(counts.items()))


def fail(message):
    print(json.dumps({"error": message}, ensure_ascii=False))
    sys.exit(2)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Scripted checks for environment-audit's Tool audit stage.")
    parser.add_argument("--root", "--global-dir", dest="global_dir", default="~/.claude",
                        help=".claude folder to audit (default: the global ~/.claude)")
    parser.add_argument("--since", help="only files changed on or after this date (YYYY-MM-DD)")
    parser.add_argument("--files", nargs="*", help="only these files (re-check after fixes)")
    parser.add_argument("--no-web", action="store_true", help="skip web link checks")
    parser.add_argument("--as-of", help="date to report as the run date (YYYY-MM-DD)")
    args = parser.parse_args()
    if not os.path.isdir(os.path.expanduser(args.global_dir)):
        fail(".claude folder not found: %s" % args.global_dir)
    print(json.dumps(Audit(args).run(), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
