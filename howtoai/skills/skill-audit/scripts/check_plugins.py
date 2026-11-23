"""check_plugins - find every AUDIT.md of the installed and linked tools and run its checks.

  check_plugins.py [--workspace W] [--global-dir G] [--audit FILE]

Without --workspace it runs the checks of scope global, with it those of scope workspace. With --audit it runs
only that file, both scopes (an INSTALL.md calls it so). Format: references/plugin-audit-format.md in this skill.

The files come from any owner, so they are data: this script reads and compares. It never runs a command and never
writes. Every path, resolved through links, stays inside {plugin}, {workspace}, or {global}. Outside the tool's own
folder it reads the text of AGENTS.md and CLAUDE.md files only, and of a JSON file it tells only whether a key or a hook is there.
It never opens secret-like files and prints no checked file's text, only the tool's own text to install. A check of
kind command or review is returned for the agent to handle.

No filter decides what is too slow: each file is checked in its own process, killed after SECONDS, so no input can
hang the audit. A file that runs out is one invalid result, and the others still run. The run as a whole has
RUN_SECONDS, shared fairly: each tool's first file runs before any tool's second, and one tool has OWNER_FILES and
OWNER_SECONDS. What does not fit is reported as not run. A link to a network path is never followed.

Prints JSON: audits, results (status pass, fail, not-applicable, needs-approval, review, or invalid), and counts.
Exit 0 when it ran, 1 on a usage error.
"""

import argparse
import faulthandler
import fnmatch
import glob
import itertools
import json
import os
import re
import subprocess
import sys
import time
import unicodedata

COLUMNS = ["id", "scope", "applies", "kind", "target", "expect", "fix"]
KINDS = ("exists", "section", "line", "import", "contains", "absent", "json", "hook", "allow", "link", "command", "review")
ROOT = re.compile(r"^\{(plugin|workspace|global)\}(/|$)")
VALUE = re.compile(r"\{json:([^#}]+)#([A-Za-z0-9_./@-]+)\}")
SECRET = (".env*", "*.env", "*credential*", "*secret*", "*.pem", "*.key", "*.pfx", "*.p12", "id_rsa*", "id_ed25519*",
          ".netrc", ".npmrc", ".pypirc", "*token*.json", "*.tfvars", "*.tfstate*", "appsettings.*.json", ".claude.json")
INSTRUCTION_FILES = ("AGENTS.md", "CLAUDE.md", "CLAUDE.local.md", ".claude/CLAUDE.md")  # the only files text is installed in
MAX_FILES, MAX_BYTES, MAX_AUDIT = 2000, 2000000, 65536
SECONDS = 5  # per audit file, in its own process
RUN_SECONDS, OWNER_SECONDS, OWNER_FILES = 60, 10, 16  # the whole run stays well under a shell's 120 second limit
MAX_BLOCK, MAX_CHECKS, MAX_WILDCARDS = 4096, 64, 2
MAX_DEPTH = 6  # folders below agents/ or commands/


class Invalid(Exception):
    pass


class NotSetUp(Exception):
    pass


def invisible(char):
    """Control, formatting (bidi, zero width), and surrogate characters, which make shown text differ from real text."""
    return char not in "\n\t" and unicodedata.category(char) in ("Cc", "Cf", "Cs")


def plain(text):
    """Owner text for a report: no live links, no characters that hide or reorder it."""
    return "".join(" " if invisible(c) else c for c in str(text)).replace("](", "] (")


def remote(path, depth=0):
    """A network path, or a link to one, found without following it: looking alone makes Windows contact the host."""
    if os.name != "nt":
        return False
    path = str(path).replace("/", "\\")
    if path.startswith("\\\\?\\") and path[5:6] == ":":
        path = path[4:]
    if path.startswith("\\\\"):
        return True
    if depth > 16:
        return True
    drive, rest = os.path.splitdrive(os.path.abspath(path))
    at = drive + "\\"
    parts = [p for p in rest.split("\\") if p]
    for n, part in enumerate(parts):
        at = os.path.join(at, part)
        try:
            os.lstat(at)
            target = os.readlink(at)
        except FileNotFoundError:
            return False
        except (OSError, ValueError):  # not a link
            continue
        if not os.path.isabs(target) and not target.startswith("\\\\"):
            target = os.path.join(os.path.dirname(at), target)
        return remote("\\".join([target] + parts[n + 1:]), depth + 1)
    return False


def secret(path):
    if remote(path):
        raise Invalid("network paths are never followed")
    return any(fnmatch.fnmatch(os.path.basename(p).lower(), s) for p in (path, os.path.realpath(path)) for s in SECRET)


def inside(path, folder):
    if remote(path) or remote(folder):
        return False
    real, base = os.path.normcase(os.path.realpath(path)), os.path.normcase(os.path.realpath(folder))
    return real == base or real.startswith(base.rstrip("\\/") + os.sep)


def read(path):
    if secret(path):
        raise Invalid("secret-like files are never opened")
    if os.path.getsize(path) > MAX_BYTES:
        raise Invalid("file too large to check")
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        return f.read().replace("\r\n", "\n")


def cell(text):
    text = text.strip()
    if len(text) > 1 and text[0] == text[-1] == "`" and "`" not in text[1:-1]:
        text = text[1:-1]
    return text.replace("\\|", "|")


def section(text, heading):
    """The section under a ## or ### heading, with its heading line, or None."""
    lines, start, level, fenced = text.split("\n"), None, 0, False
    for n, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            fenced = not fenced
        m = None if fenced else re.match(r"^(#{1,6}) (.*)$", line)
        if not m:
            continue
        if start is None and m.group(2).rstrip() == heading:
            start, level = n, len(m.group(1))
        elif start is not None and len(m.group(1)) <= level:
            return "\n".join(lines[start:n]).rstrip()
    return None if start is None else "\n".join(lines[start:]).rstrip()


def parse(path):
    if not inside(path, os.path.dirname(path)) or os.path.getsize(path) > MAX_AUDIT:
        raise Invalid("an audit file is a file of at most 64 KB in the tool's own folder")
    text, checks, errors = read(path), [], []
    table = section(text, "Checks")
    if table is None:
        return [], ["no Checks section"], text
    rows = [x for x in table.split("\n") if x.startswith("|")]
    if not rows or [c.lower() for c in map(cell, rows[0].strip("|").split("|"))] != COLUMNS:
        return [], ["the Checks table needs the columns " + ", ".join(COLUMNS)], text
    if len(rows) - 2 > MAX_CHECKS:
        errors.append("more than %d checks; only the first %d run" % (MAX_CHECKS, MAX_CHECKS))
    for row in rows[2:2 + MAX_CHECKS]:
        cells = [cell(c) for c in re.split(r"(?<!\\)\|", row.strip()[1:-1])]
        if len(cells) != len(COLUMNS):
            errors.append("a check row has %d cells: %s" % (len(cells), row[:80]))
            continue
        check = dict(zip(COLUMNS, cells))
        if check["kind"] not in KINDS or check["scope"] not in ("global", "workspace"):
            errors.append("%s: unknown kind or scope" % check["id"])
        else:
            checks.append(check)
    return checks, errors, text


class Runner:
    def __init__(self, audit, workspace, global_dir):
        self.text = ""
        self.roots = {"plugin": os.path.dirname(audit), "workspace": workspace, "global": global_dir}

    def split(self, spec):
        m = ROOT.match(spec)
        if not m:
            raise Invalid("a path starts with {plugin}, {workspace}, or {global}")
        rest, name = spec[m.end():], m.group(1)
        for part in re.split(r"[\\/]", rest) if rest else []:
            if not part or part in (".", "..") or "**" in part or ":" in part or part != part.rstrip(". ") or re.search(r"[\x00-\x1f]", part):
                raise Invalid("a path stays inside its root and uses plain names")
        if sum(rest.count(c) for c in "*?[") > MAX_WILDCARDS:
            raise Invalid("a path has at most %d wildcards" % MAX_WILDCARDS)
        parts = re.split(r"[\\/]", rest) if rest else []
        if any(c in part for part in parts[:-1] for c in "*?["):
            raise Invalid("wildcards stand only in a path's last part")
        if self.roots[name]:
            fixed = parts[:-1] if parts and any(c in parts[-1] for c in "*?[") else parts
            if remote(os.path.join(self.roots[name], *fixed)):
                raise Invalid("network paths are never followed")
        if not self.roots[name]:
            raise Invalid("needs a workspace")
        return name, rest

    def path(self, spec):
        name, rest = self.split(spec)
        base = glob.escape(self.roots[name])
        return os.path.join(base, rest) if rest else base

    def one(self, spec):
        name, rest = self.split(spec)
        return os.path.normpath(os.path.join(self.roots[name], rest)) if rest else self.roots[name]

    def many(self, spec):
        found = list(itertools.islice(glob.iglob(self.path(spec), recursive=True), MAX_FILES + 1))
        if len(found) > MAX_FILES:
            raise Invalid("the pattern matches too many files")
        if any(remote(p) for p in found):
            raise Invalid("network paths are never followed")
        return sorted(found)

    def open_text(self, spec, path=None):
        """The text of a file a check may read: the tool's own files, and Markdown elsewhere."""
        name, _ = self.split(spec)
        path = path or self.one(spec)
        if not inside(path, self.roots[name]):
            raise Invalid("the path leaves its root through a link")
        if name != "plugin":
            rel = os.path.relpath(os.path.realpath(path), os.path.realpath(self.roots[name])).replace(os.sep, "/")
            if rel not in (INSTRUCTION_FILES if name == "workspace" else ("CLAUDE.md",)):
                raise Invalid("outside the tool's own folder only the AGENTS.md and CLAUDE.md files are read")
        return read(path)

    def open_json(self, spec):
        name, _ = self.split(spec)
        path = self.one(spec)
        if not inside(path, self.roots[name]) or not os.path.realpath(path).lower().endswith(".json"):
            raise Invalid("a key check reads a JSON file inside its root")
        return json.loads(read(path))

    def install_target(self, spec):
        name, rest = self.split(spec)
        if name != "workspace" or rest.replace("\\", "/") not in INSTRUCTION_FILES:
            raise Invalid("text is installed only in the workspace's AGENTS.md or CLAUDE.md files")
        return self.one(spec)

    def value(self, m):
        spec, keys = m.group(1), m.group(2)
        if not re.fullmatch(r"\.howtoai/[a-z0-9-]+/settings\.json", spec):
            raise Invalid("a value is filled in only from .howtoai/<tool>/settings.json")
        try:
            node = self.open_json("{workspace}/" + spec)
            for key in keys.split("/"):
                node = node[key]
        except (OSError, ValueError, KeyError, TypeError):
            raise NotSetUp("%s in %s is not set" % (keys, spec))
        if not node:
            raise NotSetUp("%s in %s is empty" % (keys, spec))
        if not isinstance(node, list) or not all(isinstance(i, str) and re.fullmatch(r"[a-z][a-z0-9@.+#-]{0,23}", i) for i in node):
            raise Invalid("only a list of short lowercase names can be filled in")
        if len(node) < 3:
            return " and ".join(node)
        return ", ".join(node[:-1]) + ", and " + node[-1]

    def block(self, ref):
        """The text a check installs: a fenced block of the AUDIT.md, or a section of a file in the plugin."""
        if ref.startswith("#"):
            body = section(self.text, ref[1:])
            lines = (body or "").split("\n")
            marks = [n for n, line in enumerate(lines) if line.startswith("```")]
            if len(marks) < 2:
                raise Invalid("no text block %s" % ref)
            raw = self.sized("\n".join(lines[marks[0] + 1:marks[1]]).rstrip())
            return self.installable(self.sized(VALUE.sub(self.value, raw)))
        spec, _, heading = ref.partition("#")
        if not spec.startswith("{plugin}/") or not spec.endswith(".md"):
            raise Invalid("installed text comes from the plugin's own Markdown files")
        body = section(self.open_text(spec), heading)
        if body is None:
            raise Invalid("no section %s in %s" % (heading, spec))
        return self.installable(self.sized(body))

    def sized(self, text):
        """Before any pattern sees owner text."""
        if len(text.encode("utf-8", "replace")) > MAX_BLOCK:
            raise Invalid("text to install is at most %d bytes" % MAX_BLOCK)
        return text

    def installable(self, text):
        if any(invisible(c) for c in text):
            raise Invalid("text to install has hidden characters")
        for n, char in enumerate(text):  # no exceptions, code spans included
            if char == "@" and (n == 0 or not (text[n - 1].isascii() and text[n - 1].isalnum())):
                raise Invalid("text to install has no word that starts with @, because @ imports a file")
        if re.search(r"\]\([^)]*[\"'<>]", text):
            raise Invalid("a link in text to install has unsafe characters")
        return text

    def applies(self, rules):
        return all(not self.holds(r[4:]) if r.startswith("not ") else self.holds(r) for r in rules.split(" && "))

    def holds(self, rule):
        if rule == "always":
            return True
        kind, _, rest = rule.partition(" ")
        if kind == "exists":
            return os.path.exists(self.one(rest))
        if kind == "contains":
            spec, _, words = rest.partition(" :: ")
            path = self.one(spec)
            if not words:
                raise Invalid("contains needs text")
            return os.path.isfile(path) and words in self.open_text(spec)
        raise Invalid("Applies is always, exists <path>, or contains <path> :: <text>")

    def run(self, check):
        kind, target, expect = check["kind"], check["target"], check["expect"]
        if kind == "review":
            found = [p for p in self.many(target) if os.path.isfile(p)][:20]
            for p in found:
                self.open_text(target, p)
            return "review", "judge read-only, from these files alone", {"files": [p.replace(os.sep, "/") for p in found], "question": plain(expect)}
        if kind == "command":
            shown = target
            for name, value in self.roots.items():
                if "{%s}" % name in shown:
                    if not value or re.search(r"[^\w :/\\.,+@=~()&'-]", value):
                        raise Invalid("{%s} cannot be put into a command safely" % name)
                    if re.search(r"[()&']", value):  # harmless inside double quotes only
                        if "'" in value and "'" in target:
                            raise Invalid("{%s} has ' and the command quotes with ' too" % name)
                        pieces = target.split("{%s}" % name)
                        if any("".join(pieces[:n]).count('"') % 2 == 0 for n in range(1, len(pieces))):
                            raise Invalid("{%s} has ( ) & or ' and stands outside double quotes in the command" % name)
                    shown = shown.replace("{%s}" % name, value.replace("\\", "/"))
            if any(invisible(c) for c in shown) or "\n" in shown:
                raise Invalid("a command with hidden characters is never shown for approval")
            return "needs-approval", "not run", {"command": shown, "pass_when": plain(expect)}
        if kind == "exists":
            found = self.many(target)
            return ("pass", "", None) if found else ("fail", "missing: %s" % target, None)
        if kind in ("section", "line"):
            path = self.install_target(target)
            try:
                wanted = self.block(expect)
            except NotSetUp as e:
                return "fail", "not set up: %s" % e, None
            if not os.path.isfile(path):
                return "fail", "missing file: %s" % target, wanted
            have = self.open_text(target)
            if kind == "line":
                for x in [w.strip() for w in wanted.split("\n") if w.strip()]:
                    named = re.match(r"- `[^`]+`", x)
                    area = (section(have, "Skills and agents") or "") if named else have
                    lines = [y.strip() for y in area.split("\n")]
                    entries = [y for y in lines if y.startswith(named.group(0))] if named else [x] if x in lines else []
                    if entries != [x]:
                        if len(entries) > 1:
                            return "fail", "%d entries of that name; keep one, with this text" % len(entries), wanted
                        return "fail", "line different; show the old one" if entries else "line missing", wanted
                return "pass", "", None
            heading = wanted.split("\n", 1)[0].lstrip("#").strip()
            mine = section(have, heading)
            if mine == wanted:
                return "pass", "", None
            return "fail", "section %s is %s" % (heading, "missing" if mine is None else "different"), wanted
        if kind == "import":
            if target != "{workspace}" or expect != "@AGENTS.md":
                raise Invalid("import checks the workspace's CLAUDE.md for @AGENTS.md, and nothing else")
            folder = self.one(target)
            names = [n for n in INSTRUCTION_FILES[1:] if remote(os.path.join(folder, n)) or os.path.isfile(os.path.join(folder, n))]
            beside = [os.path.join(folder, n) for n in names]
            if any(remote(p) for p in beside):
                raise Invalid("network paths are never followed")
            if not beside or any(expect in self.open_text("{workspace}/" + n) for n in names):
                return "pass", "", None
            return "fail", "%s exists without %s" % (os.path.basename(beside[0]), expect), expect
        if kind in ("contains", "absent"):
            found = [p for p in self.many(target) if os.path.isfile(p)]
            if not found and kind == "contains":
                return "fail", "no file matches %s" % target, None
            bad = [os.path.basename(p) for p in found if (expect in self.open_text(target, p)) != (kind == "contains")]
            return ("fail", "not so in: %s" % ", ".join(bad[:15]), None) if bad else ("pass", "", None)
        if kind == "json":
            gone, keys = expect.startswith("!"), expect.lstrip("!")
            path = self.one(target)
            there = os.path.isfile(path)
            if there:
                try:
                    node = self.open_json(target)
                except ValueError:
                    return "fail", "not valid JSON: %s" % target, None
                for key in keys.split("/"):
                    if isinstance(node, dict) and key in node:
                        node = node[key]
                    else:
                        there = False
                        break
            if there != gone:
                return "pass", "", None
            return "fail", "%s is %s" % (keys, "present" if gone else "absent"), None
        if kind == "hook":
            parts = expect.split(None, 2)
            if target != "{global}/settings.json" or len(parts) != 3 or not re.fullmatch(r"[\w-]+\.(py|sh|js|ts|ps1)", parts[1]):
                raise Invalid("hook takes {global}/settings.json and: <event> <script file> <matcher>")
            event, script, matcher = parts
            try:
                entries = self.open_json(target).get("hooks", {}).get(event, [])
            except (OSError, ValueError, AttributeError):
                entries = []
            named = re.compile(r"[/\\\"' ]%s([\"' ;]|$)" % re.escape(script))
            for entry in entries:
                if isinstance(entry, dict) and entry.get("matcher") == matcher:
                    if any(named.search(str(h.get("command", ""))) for h in entry.get("hooks", []) if isinstance(h, dict)):
                        return "pass", "", None
            return "fail", "no %s hook runs %s with that matcher" % (event, script), None
        if kind == "allow":
            rules = expect.split(" or ")
            if target != "{global}/settings.json" or not all(re.fullmatch(r"Skill\([a-z0-9:-]{1,80}\)", r) for r in rules):
                raise Invalid("allow takes {global}/settings.json and Skill(<name>) rules joined by ' or '")
            try:
                allowed = self.open_json(target)["permissions"]["allow"]
                found = any(r in allowed for r in rules)
            except (OSError, ValueError, KeyError, TypeError):
                found = False
            return ("pass", "", None) if found else ("fail", "no allow rule %s" % expect, None)
        # link: each match of the target is the same file or folder as the entry of that name in Expect
        sources, dest, bad = self.many(target), self.one(expect), []
        for src in sources:
            if remote(os.path.join(dest, os.path.basename(src))):
                bad.append(os.path.basename(src))
                continue
            try:
                ok = os.path.samefile(src, os.path.join(dest, os.path.basename(src)))
            except OSError:
                ok = False
            if not ok:
                bad.append(os.path.basename(src))
        if not sources or bad:
            return "fail", "not linked: %s" % (", ".join(bad[:30]) or target), None
        return "pass", "", None


def plugin_root(path):
    folder = path if os.path.isdir(path) else os.path.dirname(path)
    for _ in range(5):
        manifest = os.path.join(folder, ".claude-plugin", "plugin.json")
        if not remote(manifest) and os.path.isfile(manifest):
            return folder
        folder = os.path.dirname(folder)
    return None


def markdown_below(folder):
    found, depth = [], folder.count(os.sep)
    if remote(folder):
        return found
    for base, dirs, names in os.walk(folder, followlinks=False):
        dirs[:] = [d for d in dirs if base.count(os.sep) - depth < MAX_DEPTH
                   and not remote(os.path.join(base, d)) and os.path.normcase(os.path.realpath(os.path.join(base, d))) == os.path.normcase(os.path.join(os.path.realpath(base), d))]
        found += [os.path.join(base, n) for n in names if n.lower().endswith(".md")]
        if len(found) > MAX_FILES:
            break
    return found


def discover(global_dir, workspace):
    folders, agents, commands = set(), set(), set()

    def tool(path):
        if remote(path):
            return
        real = os.path.realpath(path)
        if os.path.isdir(real):
            folders.add(real)
        root = plugin_root(real)
        if root:
            folders.add(root)

    def single(path, kind, top):
        """An agent's audit is beside it. A command's is in audits/ beside the commands folder, at the same subpath."""
        if path.lower().endswith(".audit.md") or remote(path) or not os.path.isfile(path):
            return
        real = os.path.realpath(path)
        tool(real)
        folder, name = os.path.split(real)
        if kind == "agents":
            agents.add(os.path.join(folder, name[:-3] + ".AUDIT.md"))
            return
        real_top = os.path.realpath(top)
        if inside(real, real_top):
            parts = [p for p in os.path.relpath(folder, real_top).split(os.sep) if p != "."]
            base = os.path.dirname(real_top)
        else:  # a linked command: beside the outermost commands folder of its target, else beside the target's folder
            names = folder.split(os.sep)
            if "commands" in names:
                at = names.index("commands")
                parts, base = names[at + 1:], os.sep.join(names[:at])
            else:
                parts, base = [], os.path.dirname(folder)
        commands.add(os.path.join(base, "audits", *parts, name[:-3] + ".AUDIT.md"))

    try:
        installed = dict(json.loads(read(os.path.join(global_dir, "plugins", "installed_plugins.json")))["plugins"])
    except Exception:  # absent or not the expected shape: no installed plugins
        installed = {}
    for entries in installed.values():
        for entry in entries if isinstance(entries, list) else []:
            try:
                where, project = entry.get("installPath"), entry.get("projectPath")
                if project and (not workspace or os.path.normcase(os.path.abspath(project)) != os.path.normcase(workspace)):
                    continue
                if where and not remote(where) and os.path.isdir(where):
                    folders.add(os.path.realpath(where))
            except Exception:  # one bad entry never ends the discovery
                continue
    bases = [global_dir] + ([os.path.join(workspace, ".claude")] if workspace else [])
    for base in bases:
        for kind in ("skills", "agents", "commands", "mods", "tools"):
            if remote(os.path.join(base, kind)):
                continue
            for path in itertools.islice(glob.iglob(os.path.join(glob.escape(base), kind, "*")), MAX_FILES):
                if os.path.basename(path) != "synced":
                    tool(path)
        for kind in ("agents", "commands"):
            top = os.path.join(base, kind)
            for path in markdown_below(top):
                single(path, kind, top)
    for root in [f for f in folders if plugin_root(f) == f]:
        for kind in ("skills", "mods", "tools"):
            if remote(os.path.join(root, kind)):
                continue
            for path in itertools.islice(glob.iglob(os.path.join(glob.escape(root), kind, "*")), MAX_FILES):
                if inside(path, root) and os.path.isdir(path):
                    folders.add(os.path.realpath(path))
        for kind in ("agents", "commands"):
            top = os.path.join(root, kind)
            for path in markdown_below(top):
                if inside(path, root):
                    single(path, kind, top)

    beside = {os.path.join(f, "AUDIT.md") for f in folders}
    return sorted(p for p in beside | agents | commands if not remote(p) and os.path.isfile(p))


def owner(audit):
    base = os.path.basename(audit)
    if base != "AUDIT.md":
        return base[:-len(".AUDIT.md")]
    folder = os.path.dirname(audit)
    try:
        manifest = os.path.join(folder, ".claude-plugin", "plugin.json")
        if not inside(manifest, folder):
            return os.path.basename(folder)
        return json.loads(read(manifest))["name"]
    except (OSError, ValueError, KeyError, Invalid):
        return os.path.basename(folder)


def check_file(audit, workspace, global_dir, own):
    runner = Runner(audit, workspace, global_dir)
    try:
        name = plain(owner(audit))[:60]
    except Exception:
        name = "unnamed"
    try:
        checks, errors, runner.text = parse(audit)
    except Exception as e:
        checks, errors = [], ["unreadable: %s" % type(e).__name__]
    base = {"tool": name, "file": plain(audit.replace(os.sep, "/"))}
    results = [dict(base, id="format", status="invalid", evidence=plain(e)[:300], fix="") for e in errors[:MAX_CHECKS]]
    for check in checks:
        if check["scope"] not in own:
            continue
        extra = None
        try:
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9-]{0,19}", check["id"]):
                raise Invalid("an ID is letters, digits, and hyphens")
            if runner.applies(check["applies"]):
                status, evidence, extra = runner.run(check)
            else:
                status, evidence = "not-applicable", "not true here: %s" % check["applies"][:300]
        except Invalid as e:
            status, evidence = "invalid", str(e)
        except Exception as e:  # one bad check never ends the others
            status, evidence = "invalid", "could not run: %s" % type(e).__name__
        row = dict(base, id=plain(check["id"])[:20], status=status, evidence=plain(evidence)[:2000],
                   fix=plain(check["fix"])[:1000] if status not in ("pass", "not-applicable") else "")
        if isinstance(extra, dict):
            row.update({k: [plain(x) for x in v] if isinstance(v, list) else v if k == "command" else plain(v) for k, v in extra.items()})
        elif status == "fail" and extra:
            row["text"] = extra
        results.append(row)
    skipped = [plain(c["id"])[:20] for c in checks if c["scope"] not in own]
    return {"seen": dict(base, skipped_other_scope=skipped), "results": results}


def child(audit, workspace, global_dir, own):
    """One audit file. The watchdog runs in a C thread, so it also ends a pattern match that holds the interpreter."""
    with open(os.devnull, "w") as nowhere:
        faulthandler.dump_traceback_later(SECONDS, exit=True, file=nowhere)
        text = json.dumps(check_file(audit, workspace, global_dir, own))
        faulthandler.cancel_dump_traceback_later()
    sys.stdout.write(text)
    return 0


def not_run(audit, why):
    name = os.path.basename(os.path.dirname(audit)) if os.path.basename(audit) == "AUDIT.md" else os.path.basename(audit)[:-9]
    base = {"tool": plain(name)[:60], "file": plain(audit.replace(os.sep, "/"))}
    return {"seen": dict(base, skipped_other_scope=[]),
            "results": [dict(base, id="format", status="invalid", evidence=why, fix="")]}


def isolated(audit, workspace, global_dir, own):
    command = [sys.executable, "-I", "-B", os.path.abspath(__file__), "--child", audit, "--scopes", ",".join(own),
               "--global-dir", global_dir] + (["--workspace", workspace] if workspace else [])
    try:
        done = subprocess.run(command, capture_output=True, stdin=subprocess.DEVNULL, timeout=SECONDS + 3)
        if done.returncode == 0:
            return json.loads(done.stdout.decode("utf-8"))
        why = "stopped: over %d seconds, or it crashed" % SECONDS
    except subprocess.TimeoutExpired:
        why = "stopped: over %d seconds" % SECONDS
    except Exception as e:
        why = "could not be checked: %s" % type(e).__name__
    return not_run(audit, why)


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace")
    ap.add_argument("--global-dir", default=os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join("~", ".claude"))
    ap.add_argument("--audit")
    ap.add_argument("--child", help=argparse.SUPPRESS)
    ap.add_argument("--scopes", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    global_dir = os.path.abspath(os.path.expanduser(a.global_dir))
    workspace = os.path.abspath(a.workspace) if a.workspace else None
    if a.child:
        return child(a.child, workspace, global_dir, tuple((a.scopes or "").split(",")))
    if workspace and not os.path.isdir(workspace):
        print(json.dumps({"ok": False, "error": "no such workspace: %s" % workspace}))
        return 1
    if a.audit and not os.path.isfile(a.audit):
        print(json.dumps({"ok": False, "error": "no such file: %s" % a.audit}))
        return 1
    for label, folder in (("workspace", workspace), ("global", global_dir)):
        if folder and remote(folder):
            row = {"tool": label, "file": plain(folder.replace(os.sep, "/")), "id": "format", "status": "invalid",
                   "evidence": "not run: a network path, which the audit never follows", "fix": ""}
            print(json.dumps({"ok": True, "audits": [], "counts": {"invalid": 1}, "results": [row]}, indent=1))
            return 0
    everywhere = set()
    if a.audit:
        audits, scopes = [os.path.abspath(a.audit)], ("global", "workspace") if workspace else ("global",)
    else:
        audits, scopes = discover(global_dir, workspace), ("workspace",) if workspace else ("global",)
        everywhere = set(discover(global_dir, None)) if workspace else set(audits)

    seen, results = [], []
    files, queue = {}, []
    for audit in audits:
        # a standalone agent or command is its own tool
        who = plugin_root(audit) or (os.path.dirname(audit) if os.path.basename(audit) == "AUDIT.md" else audit)
        files[who] = files.get(who, 0) + 1
        queue.append((files[who], who, audit))
    spent, started = {}, time.monotonic()
    for nth, who, audit in sorted(queue, key=lambda q: q[0]):
        # a tool only this workspace has gets its global checks here, because no other run finds it
        own = scopes if a.audit or audit in everywhere else ("global", "workspace")
        began = time.monotonic()
        if nth > OWNER_FILES or spent.get(who, 0) >= OWNER_SECONDS:
            one = not_run(audit, "not run: this tool used up its %d files or %d seconds" % (OWNER_FILES, OWNER_SECONDS))
        elif began - started >= RUN_SECONDS:
            one = not_run(audit, "not run: the audit's %d seconds were used up" % RUN_SECONDS)
        else:
            one = isolated(audit, workspace, global_dir, own)
            spent[who] = spent.get(who, 0) + time.monotonic() - began
        seen.append(one["seen"])
        results += one["results"]
    counts = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print(json.dumps({"ok": True, "audits": seen, "counts": counts, "results": results}, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
