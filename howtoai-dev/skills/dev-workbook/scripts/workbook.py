"""workbook - parse, merge, and maintain howtoai-dev technology workbooks.

Python 3, standard library only. Every command prints one JSON object (resolve can print Markdown).
Format: references/format.md in this skill. Layers: base (this skill's workbooks/), user
(~/.claude/howtoai/workbooks/), project (<workspace>/AGENTS/workbooks/); project wins over user, user
over base. Every command takes --base-dir and --user-dir to replace the default folders (tests use them).

  open      [--workspace W]
            What the skill prints when it loads, with no arguments from the caller: every MUST and MUST
            NOT of the workspace's workbooks, the tags, and how to search the rest. Writes the search
            file <workspace>/AGENTS/state/cache/workbook-search.md, one tagged line per statement. The
            workspace is the nearest folder at or above the current one with dev settings. Exits 0 also
            when it cannot load, and says so, because a failing load would hide the skill.
  resolve   --workspace W [--paths P ...] [--technologies T ...] [--tags T ...] [--topics S ...]
            [--stage NAME] [--markdown [--part N] | --versions]
            Finds the technologies a step touches (from --technologies, the project's dev settings
            workbooks.technologies, and the Load when globs of every workbook matched against --paths),
            merges their layers, and returns a tailored subset: every MUST and MUST NOT of every
            workbook found, plus the other statements of the touched ones (those matched by --paths or
            named in --technologies), narrowed to --tags when given (a tag or a section slug). With no
            paths, technologies, or tags it returns everything. --topics shows only some sections, MUST
            rules included, for a user who asks to see part of a workbook; a dev step never passes it. --markdown ends with the receipt; a result too
            large to print exact comes in parts (--part N), the MUST rules first, and says how many. --versions leaves the
            statements out. Also returns the overrides, the conflicts, the technologies seen in the paths that have no
            workbook (missing), and a receipt ready for dev-core's state append.receipts. Each path is
            placed in its code project (the deepest Codebase versions line of the project workbook whose
            folder holds it) and gets that line's workbook: a version workbook such as dotnet@8, or the
            general one. Results are keyed by workbook, each with its code_projects (version, support
            date, support_ended) and unrecorded_paths. [--today YYYY-MM-DD] replaces the system date.
  validate  FILE [--overlay]
            Checks a workbook against the format. --overlay allows a user or project file that holds
            only some sections. Infers the layer from the Header when not given.
  propose   --workspace W --tech T --section SLUG --text TEXT --source SOURCE [--level MUST|SHOULD|MUST NOT] [--tags T ...]
            [--layer project|user] [--replaces ID] [--write] [--allow-process-wording] [--date YYYY-MM-DD]
            Previews a new statement (or a replacement for ID) in a project or user workbook: the next
            ID, likely duplicates, process wording, and secret-like text. --write saves it; a write is
            refused while process wording is flagged unless --allow-process-wording is given.
  skeleton  --tech T --title TITLE --layer base|user|project --out FILE [--date YYYY-MM-DD]
            [--version-key K [--copy-base]]
            Writes an empty workbook with every section set to "none yet" (Create, make route). Refuses
            to overwrite an existing file. --version-key makes a version workbook T@K.md; --copy-base
            starts it as a copy of the base T.md (same IDs, Versions reset, Supported until dropped).
  record-version --workspace W --tech T --path FOLDER --version TEXT --source FILE [--workbook T@K]
            [--supported-until YYYY-MM-DD] [--write] [--date YYYY-MM-DD]
            Previews a Codebase versions line for one code project in the project workbook T.md (it
            replaces the line for the same folder); --write saves it.
  audit     --workspace W [--today YYYY-MM-DD] [--max-age DAYS] [--support-warn-days DAYS] [--run-version-commands]
            Lists format errors, sources checked more than --max-age days ago (default 180), overrides
            of IDs that no longer exist in the base, workbooks whose Supported until date has passed
            (support_ended) or falls within --support-warn-days (default 180, support_ending), and,
            only with --run-version-commands, each workbook's installed version from its read-only
            Version command. A base or user date that passed means the workbook is out of date; a
            project date that passed means the codebase's version is out of support, an upgrade to
            plan, not a fault.
  check-skills SKILLS_DIR
            For every dev-* skill except dev-core and dev-workbook, checks that each stage file (or
            SKILL.md when there are no stages) calls workbook.py resolve.

Exit code 0 on success, 1 with {"ok": false, "error": ...} on a usage or file error. validate and
check-skills exit 0 and report "ok": false when they find problems.
"""

import argparse
import datetime
import glob as globmod
import json
import os
import re
import shlex
import subprocess
import sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEGACY_SECTION = "Skills and agents"  # no longer written or required; accepted last in older files
SECTIONS = [("Overview", "overview"), ("Setup and configuration", "setup"), ("Idioms and patterns", "patterns"),
            ("Pitfalls", "pitfalls"), ("Commands", "commands"), ("Testing", "testing"), ("Security", "security"),
            ("Performance", "performance"), ("Deployment and operations", "deploy"), ("Our situation", "situation")]
HEADING_TO_SLUG = {h.lower(): s for h, s in SECTIONS}
SLUGS = [s for _, s in SECTIONS]
LAYERS = ["base", "user", "project"]
LAYER_PREFIX = {"base": "", "user": "u", "project": "p"}
SEP = " · "
TAGS = ("access", "async", "build", "caching", "cli", "config", "data", "dependencies", "di", "errors", "formatting",
        "health", "http", "image", "lifecycle", "linting", "logging", "modules", "nullability", "performance", "secrets",
        "state", "strings", "style", "tests", "versions")
SETTINGS_FILE = "settings.json"  # the workspace's shared AGENTS/settings.json, one top-level key per tool
SETTINGS_KEY = "howtoai-dev"     # this plugin's key in it
STATE_FOLDER = "state"           # AGENTS/state/: run records, left out of Git


def agents_dir(ws):
    """The workspace's AGENTS/ folder in the case it exists in (Agents/ counts), else <ws>/AGENTS."""
    try:
        for name in os.listdir(ws):
            if name.lower() == "agents" and os.path.isdir(os.path.join(ws, name)):
                return os.path.join(ws, name)
    except OSError:
        pass
    return os.path.join(ws, "AGENTS")


def agents_file(ws, *parts):
    """A file the user reviews, at the AGENTS/ root (settings.json, workbooks/, deploy-targets.json, ...)."""
    return os.path.join(agents_dir(ws), *parts)


def state_dir(ws, *parts):
    """<workspace>/AGENTS/state/<parts>: run records (deploy approvals, deploy log, cache), left out of Git."""
    return os.path.join(agents_dir(ws), STATE_FOLDER, *parts)


def project_settings(ws):
    """The "howtoai-dev" part of the workspace's shared AGENTS/settings.json, or None when missing."""
    p = agents_file(ws, SETTINGS_FILE)
    with open(p, encoding="utf-8-sig") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("not an object")
    return data.get(SETTINGS_KEY)


PAGE = 20000  # characters of statements in one part
PRINT_MAX = 28000  # characters; the Bash tool saves longer output to a file and shows only a preview
STMT = re.compile(r"^- \*\*(?P<id>[a-z0-9-]+\.[a-z]+\.[up]?\d{3})\*\*"
                  r"(?: · (?P<level>MUST NOT|MUST|SHOULD))?"
                  r" · (?P<text>.+?)(?: · tags: (?P<tags>[a-z-]+(?:, [a-z-]+)*))?"
                  r" · source: (?P<source>.+?) · confirmed: (?P<confirmed>.+)$")
SOURCE_LINE = re.compile(r"^- \[(?P<name>[^\]]+)\]\((?P<url>[^)]+)\) · checked (?P<checked>\d{4}-\d{2}-\d{2})(?P<rest>.*)$")
KNOWN = {  # technologies the dev process may meet, for reporting missing workbooks
    "csharp": ["**/*.cs", "**/*.csx"], "dotnet": ["**/*.csproj", "**/*.sln", "**/*.slnx", "**/global.json"],
    "docker": ["**/Dockerfile", "**/Dockerfile.*", "**/*.dockerfile", "**/compose.yaml", "**/compose.yml",
               "**/docker-compose*.yml", "**/docker-compose*.yaml"],
    "terraform": ["**/*.tf", "**/*.tfvars", "**/*.tftest.hcl"], "python": ["**/*.py", "**/pyproject.toml"],
    "typescript": ["**/*.ts", "**/*.tsx", "**/tsconfig.json"], "javascript": ["**/*.js", "**/*.jsx", "**/*.mjs"],
    "go": ["**/*.go", "**/go.mod"], "java": ["**/*.java", "**/pom.xml", "**/build.gradle*"], "rust": ["**/*.rs", "**/Cargo.toml"],
    "sql": ["**/*.sql"], "github-actions": ["**/.github/workflows/*.yml", "**/.github/workflows/*.yaml"],
    "kubernetes": ["**/k8s/**/*.yaml", "**/*.helm.yaml", "**/Chart.yaml"], "powershell": ["**/*.ps1", "**/*.psm1"],
}
PROCESS_WORDS = [r"(?<!auto-)\bapprov", r"\bask (the )?user", r"\breview round", r"\bdev stage",r"\bbefore (you|the agent|building|merging)",
                 r"\bdev-(plan|test|build|review|deploy|learn)\b", r"\bthe agent (must|should)", r"\bin this process\b",
                 r"\bwork item", r"\bplan (doc|page)", r"\bgoldfish\b"]
SECRET_PATTERNS = [r"-----BEGIN [A-Z ]*PRIVATE KEY", r"\bghp_[A-Za-z0-9]{20,}", r"\bgithub_pat_", r"\bxox[abprs]-",
                   r"\bAKIA[0-9A-Z]{16}\b", r"\bsk-[A-Za-z0-9_-]{20,}", r"://[^/\s:@]+:[^/\s@]+@"]


class Fail(Exception):
    pass


def out(obj, code=0):
    sys.stdout.write(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")
    sys.exit(code)


def today(arg=None):
    if arg:
        datetime.date.fromisoformat(arg)
        return arg
    return datetime.date.today().isoformat()


def iso_date(text):
    """The date for a YYYY-MM-DD string, or None when it is not one."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text or ""):
        return None
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        return None


UPGRADE = "keep following the codebase's version; an upgrade is due at some point, as a change of its own"
SUPPORT_MEANING = {
    "base": "the workbook's versions are out of support: refresh its Versions, Supported until, and version-specific statements (base workbooks change through skill-builder)",
    "user": "the user workbook's versions are out of support: refresh its Versions and Supported until",
    "project": "the version this project workbook was made for is out of support: " + UPGRADE,
    "version": "this version is out of support; its workbook stays for the code projects that use it: " + UPGRADE,
    "codebase": "this code project's version is out of support: " + UPGRADE,
}
VERSION_STEM = re.compile(r"^(?P<tech>[a-z0-9-]+)@(?P<key>[a-z0-9.-]+)$")
CODEBASE_LINE = re.compile(r"^- `(?P<path>[^`]+)` · (?P<version>.+?) · workbook: `(?P<workbook>[a-z0-9-]+(?:@[a-z0-9.-]+)?)`"
                           r" · supported until (?P<until>\d{4}-\d{2}-\d{2}|unknown) · source: (?P<source>.+?)"
                           r" · checked (?P<checked>\d{4}-\d{2}-\d{2})$")


def tech_of_stem(stem):
    """`dotnet@8` -> `dotnet`; a plain technology name stays as it is."""
    return stem.split("@", 1)[0]


def norm_prefix(path):
    """A code project's folder as a path prefix: '' for the whole repository, else 'src/Api/'."""
    p = (path or "").replace("\\", "/").strip()
    while p.startswith("./"):
        p = p[2:]
    return "" if p in ("", ".") else p.rstrip("/") + "/"


def norm_path(path):
    p = path.replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p


# parsing ----------------------------------------------------------------------------------

def parse(path):
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    wb = {"path": path, "title_line": lines[0] if lines else "", "header": {}, "sources": [], "globs": [],
          "sections": {}, "order": [], "statements": [], "errors": [], "other_headings": [], "codebase": []}
    current, block = None, None
    for n, line in enumerate(lines, 1):
        if line.startswith("## "):
            name = line[3:].strip()
            current = name
            wb["order"].append(name)
            continue
        if current == "Header":
            if line.strip() in ("Sources:", "Codebase versions:"):
                block = line.strip()
                continue
            if block == "Codebase versions:" and line.startswith("- ") and line.strip() != "- none yet":
                c = CODEBASE_LINE.match(line)
                if c:
                    wb["codebase"].append(dict(c.groupdict(), prefix=norm_prefix(c.group("path")), line=n, raw=line))
                else:
                    wb["errors"].append(f"line {n}: codebase version line does not match the format")
                continue
            m = re.match(r"^\| (?P<k>[^|]+?) \| (?P<v>.*?) \|$", line)
            if m and m.group("k") not in ("Key", "---"):
                wb["header"][m.group("k").strip()] = m.group("v").strip().strip("`")
            s = SOURCE_LINE.match(line)
            if s:
                wb["sources"].append({"name": s.group("name"), "url": s.group("url"), "checked": s.group("checked"),
                                      "note": s.group("rest").lstrip(" ·").strip(), "line": n})
        elif current == "Load when":
            m = re.match(r"^\| `(?P<g>[^`]+)` \|$", line)
            if m:
                wb["globs"].append(m.group("g"))
        elif current and current.lower() in HEADING_TO_SLUG:
            slug = HEADING_TO_SLUG[current.lower()]
            wb["sections"].setdefault(slug, [])
            if line.startswith("- "):
                if line.strip() == "- none yet":
                    continue
                m = STMT.match(line)
                if not m:
                    wb["errors"].append(f"line {n}: statement does not match the format")
                    continue
                st = {k: m.group(k) for k in ("id", "level", "text", "source", "confirmed")}
                st["line"] = n
                st["section"] = slug
                st["tags"] = m.group("tags").split(", ") if m.group("tags") else []
                wb["sections"][slug].append(st)
                wb["statements"].append(st)
    return wb


def technology_of(wb, path):
    return wb["header"].get("Technology") or os.path.splitext(os.path.basename(path))[0]


def validate_wb(path, overlay=None):
    wb = parse(path)
    errors, warnings = list(wb["errors"]), []
    tech = technology_of(wb, path)
    layer = wb["header"].get("Layer", "")
    stem = os.path.splitext(os.path.basename(path))[0]
    key = wb["header"].get("Version key", "")
    is_version = bool(key) or "@" in stem
    if overlay is None:
        overlay = layer in ("user", "project") and not is_version
    if layer not in LAYERS:
        errors.append(f"Header Layer must be one of {LAYERS}, got {layer!r}")
    if is_version and not re.fullmatch(r"[a-z0-9.-]+", key):
        errors.append("a version workbook needs a Header Version key of lowercase letters, digits, dots, and hyphens")
    want = f"{tech}@{key}" if is_version else tech
    if stem != want:
        errors.append(f"file name must be {want}.md to match Technology" + (" and Version key" if is_version else ""))
    if is_version and layer == "user":
        errors.append("a version workbook lives in the base or project layer, not the user layer")
    prefixes = {}
    for c in wb["codebase"]:
        if layer != "project" or is_version:
            errors.append(f"line {c['line']}: Codebase versions belong only in the project workbook {tech}.md")
        if tech_of_stem(c["workbook"]) != tech:
            errors.append(f"line {c['line']}: workbook `{c['workbook']}` is not a {tech} workbook")
        if c["until"] != "unknown" and iso_date(c["until"]) is None or iso_date(c["checked"]) is None:
            errors.append(f"line {c['line']}: dates must be real, YYYY-MM-DD")
        if c["prefix"] in prefixes:
            errors.append(f"line {c['line']}: code project {c['path']} is listed twice (first on line {prefixes[c['prefix']]})")
        prefixes[c["prefix"]] = c["line"]
        if SEP in c["version"]:
            errors.append(f"line {c['line']}: version text contains the separator ' · '")
    if not re.fullmatch(r"[a-z0-9-]+", tech or ""):
        errors.append("Technology must be lowercase letters, digits, and hyphens")
    if not re.match(r"^# .+ workbook", wb["title_line"]):
        errors.append("first line must be '# <Title> workbook'")
    required = ["Technology", "Layer", "Updated"] + ([] if overlay else ["Title", "Versions"])
    for k in required:
        if not wb["header"].get(k):
            errors.append(f"Header is missing {k}")
    upd = wb["header"].get("Updated", "")
    if upd and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", upd):
        errors.append("Header Updated must be YYYY-MM-DD")
    sup = wb["header"].get("Supported until", "")
    if sup and iso_date(sup) is None:
        errors.append("Header Supported until must be a real date, YYYY-MM-DD")
    expected = ["Contents", "Header", "Load when"] + [h for h, _ in SECTIONS]
    order = wb["order"][:-1] if wb["order"][-1:] == [LEGACY_SECTION] else wb["order"]  # a file written before 2026-11-25
    if overlay:
        present = [h for h in order]
        filtered = [h for h in expected if h in present]
        if [h for h in present if h in expected] != filtered:
            errors.append("sections are out of order")
        for h in ("Contents", "Header"):
            if h not in present:
                errors.append(f"missing section {h}")
    else:
        if order != expected:
            missing = [h for h in expected if h not in order]
            extra = [h for h in order if h not in expected]
            errors.append(f"sections must be exactly {expected}; missing {missing}, unexpected {extra}")
        if not wb["globs"]:
            errors.append("Load when has no globs")
    prefix = LAYER_PREFIX.get(layer, "")
    seen = {}
    cited = {s["url"] for s in wb["sources"]}
    for st in wb["statements"]:
        parts = st["id"].split(".")
        if parts[0] != tech:
            errors.append(f"line {st['line']}: ID {st['id']} must start with {tech}.")
        if parts[1] != st["section"]:
            errors.append(f"line {st['line']}: ID {st['id']} is in section {st['section']}")
        num = parts[2]
        if layer == "base" and not num.isdigit():
            errors.append(f"line {st['line']}: base IDs use plain numbers, got {num}")
        if layer in ("user", "project") and not (num.startswith(prefix) or num.isdigit()):
            errors.append(f"line {st['line']}: {layer} IDs use {prefix}NNN (or repeat a lower ID to replace it)")
        if st["id"] in seen:
            errors.append(f"line {st['line']}: duplicate ID {st['id']} (first on line {seen[st['id']]})")
        seen[st["id"]] = st["line"]
        if SEP in st["text"]:
            errors.append(f"line {st['line']}: text contains the separator ' · '")
        for tag in st["tags"]:
            if tag not in TAGS:
                errors.append(f"line {st['line']}: unknown tag {tag}; use {', '.join(TAGS)}")
        if not st["tags"] and not st["text"].lower().startswith("withdrawn:"):
            if layer == "base":
                errors.append(f"line {st['line']}: {st['id']} has no tags")
            else:
                warnings.append(f"line {st['line']}: {st['id']} has no tags")
        for url in re.findall(r"\]\((https?://[^)]+)\)", st["source"]):
            if url not in cited:
                errors.append(f"line {st['line']}: source {url} is not in the Header Sources")
        if re.search("|".join(PROCESS_WORDS), st["text"], re.I):
            warnings.append(f"line {st['line']}: {st['id']} may be a process instruction")
    if not overlay:
        for slug in SLUGS:
            if slug not in wb["sections"]:
                continue
    counts = {s: len(wb["sections"].get(s, [])) for s in SLUGS}
    return {"ok": not errors, "file": path, "technology": tech, "layer": layer, "statements": len(wb["statements"]),
            "counts": counts, "errors": errors, "warnings": warnings}


# layers -----------------------------------------------------------------------------------

def layer_dirs(ws, base_dir, user_dir):
    return {"base": base_dir or os.path.join(SKILL_DIR, "workbooks"),
            "user": user_dir or os.path.join(os.path.expanduser("~"), ".claude", "howtoai", "workbooks"),
            "project": agents_file(ws, "workbooks") if ws else None}


def available(dirs):
    techs = set()
    for d in dirs.values():
        if d and os.path.isdir(d):
            techs.update(os.path.splitext(f)[0] for f in os.listdir(d) if f.endswith(".md"))
    return sorted(techs)


def load_layers(tech, dirs):
    layers = []
    for layer in LAYERS:
        d = dirs[layer]
        p = os.path.join(d, f"{tech}.md") if d else None
        if p and os.path.isfile(p):
            layers.append((layer, parse(p)))
    return layers


def version_files(stem, dirs):
    """A version workbook's files, in the base and project folders, as (layer, workbook)."""
    found = []
    for layer in ("base", "project"):
        p = os.path.join(dirs[layer], f"{stem}.md") if dirs[layer] else None
        if p and os.path.isfile(p):
            found.append((layer, parse(p)))
    return found


def load_for(stem, dirs):
    """The layers for one workbook: a plain technology loads its three layers. A version workbook
    (`dotnet@8`) takes the base role, labelled 'version' (the base copy wins over a project copy), with the
    technology's user and project overlays on top, so the user's and project's choices apply to every version."""
    if "@" not in stem:
        return load_layers(stem, dirs)
    files = version_files(stem, dirs)
    if not files:
        return []
    overlays = [(l, wb) for l, wb in load_layers(tech_of_stem(stem), dirs)
                if l != "base" and "Load when" not in wb["order"]]
    return [("version", files[0][1])] + overlays


def project_wb(tech, dirs):
    p = os.path.join(dirs["project"], f"{tech}.md") if dirs["project"] else None
    return parse(p) if p and os.path.isfile(p) else None


def merge(layers):
    merged, origin, overrides, conflicts = {}, {}, [], []
    for layer, wb in layers:
        for st in wb["statements"]:
            sid = st["id"]
            entry = dict(st, layer=layer)
            if sid in merged:
                prev = merged[sid]
                entry["tags"] = st["tags"] or prev["tags"]  # a replacement keeps the tags and level it does not restate
                entry["level"] = st["level"] or prev["level"]
                if prev["text"] != st["text"]:
                    rec = {"id": sid, "from": prev["layer"], "to": layer, "old": prev["text"], "new": st["text"]}
                    if prev["layer"] in ("user", "project") and layer in ("user", "project"):
                        conflicts.append(rec)
                    else:
                        overrides.append(rec)
            merged[sid] = entry
            origin[sid] = layer
    statements = [s for s in merged.values() if not s["text"].lower().startswith("withdrawn:")]
    return statements, overrides, conflicts


def glob_re(pattern):
    out_ = ""
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out_ += "(?:.*/)?"
            i += 3
        elif pattern.startswith("**", i):
            out_ += ".*"
            i += 2
        elif pattern[i] == "*":
            out_ += "[^/]*"
            i += 1
        elif pattern[i] == "?":
            out_ += "[^/]"
            i += 1
        else:
            out_ += re.escape(pattern[i])
            i += 1
    return re.compile("^" + out_ + "$")


def matches(path, globs):
    p = path.replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return any(glob_re(g).match(p) for g in globs)


def project_technologies(ws):
    if not ws:
        return []
    p = agents_file(ws, SETTINGS_FILE)
    try:
        return list(((project_settings(ws) or {}).get("workbooks") or {}).get("technologies") or [])
    except FileNotFoundError:
        return []
    except (ValueError, AttributeError, TypeError) as e:
        raise Fail(f"{p} cannot be read ({type(e).__name__}); fix it, because the workbook rules come from it")


# commands ---------------------------------------------------------------------------------

def find_workspace(start):
    folder = os.path.abspath(start)
    while True:
        if os.path.isfile(agents_file(folder, SETTINGS_FILE)):
            return folder
        parent = os.path.dirname(folder)
        if parent == folder:
            return None
        folder = parent


def is_must(st):
    return (st.get("level") or "").startswith("MUST")


def statement_line(st):
    return f"- {st['id']}{' ' + st['level'] if st.get('level') else ''}: {st['text']}"


def write_if_changed(path, text):
    try:
        with open(path, encoding="utf-8") as f:
            if f.read() == text:
                return
    except OSError:
        pass
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    try:
        os.replace(tmp, path)
    except OSError:  # another reviewer is writing or reading the same file
        os.remove(tmp)
        with open(path, encoding="utf-8") as f:
            if f.read() != text:
                raise


def open_text(a):
    ws = find_workspace(a.workspace or os.getcwd())
    if not ws and not a.workspace and os.environ.get("CLAUDE_PROJECT_DIR"):
        ws = find_workspace(os.environ["CLAUDE_PROJECT_DIR"])
    if not ws:
        return ("No dev workspace here (no AGENTS/settings.json in this folder or above it), so no workbook "
                "rules are loaded. If the work is in a dev workspace elsewhere, say that its rules are not loaded. The routes below still work for a workspace you name; howtoai-dev's INSTALL.md "
                "sets a workspace up.")
    if not project_technologies(ws):
        return "The dev settings list no workbooks (workbooks.technologies), so there are no workbook rules to load."
    found = resolve(argparse.Namespace(workspace=ws, base_dir=a.base_dir, user_dir=a.user_dir, paths=None,
                                       technologies=None, topics=None, tags=None, stage=None, today=None,
                                       general=True))
    dirs = layer_dirs(ws, a.base_dir, a.user_dir)
    rows, must, tools, sources, broken = [], [], [], [], []
    for stem, secs in found["sections"].items():
        info = found["technologies"][stem]
        for _, wb in load_for(stem, dirs):
            broken += [f"{wb['path'].replace(os.sep, '/')} {e}" for e in wb["errors"]]
        globs = []
        for _, wb in load_layers(info["technology"], dirs):
            globs += [g for g in wb["globs"] if g not in globs]
        versions = "".join(f"; code project {c['path']} on {c['version']}" for c in info["code_projects"])
        tools.append(f"- #{stem} {info['title']} ({info['versions']}): {' '.join(globs)}{versions}")
        for slug, sts in secs.items():
            for st in sts:
                tags = " ".join("#" + x for x in [stem, slug] + [x for x in st["tags"] if x != slug])
                rows.append(f"- {tags} {statement_line(st)[2:]}")
                sources.append(f"- {stem} {st['id']}: {st['source']}")
                if is_must(st):
                    must.append(statement_line(st) + (f" [{stem}]" if "@" in stem else ""))
    cache = state_dir(ws, "cache")
    write_if_changed(os.path.join(cache, ".gitignore"), "*\n")
    search = os.path.join(cache, "workbook-search.md")
    write_if_changed(search, "\n".join(rows) + "\n")
    cited = os.path.join(cache, "workbook-sources.md")
    write_if_changed(cited, "\n".join(sources) + "\n")
    used = sorted({x for secs in found["sections"].values() for sts in secs.values() for st in sts for x in st["tags"]})
    lines = [f"Every MUST and MUST NOT of this workspace's workbooks ({len(must)} of {len(rows)} statements):", ""]
    lines += must + ["", f"Search file for all {len(rows)} statements, one tagged line each: {search.replace(os.sep, '/')}", "",
                     f"Each statement's source, by ID: {cited.replace(os.sep, '/')}", "",
                     "Workbooks, their tag, and their files:"] + tools
    lines += ["", "Section tags: " + " ".join("#" + s for s in SLUGS), "Subject tags: " + " ".join("#" + s for s in used)]
    if broken:
        lines.append("Statements NOT loaded because their line is malformed (one may be a MUST; say so in what you report): "
                     + "; ".join(broken))
    if found["missing"]:
        lines.append("No workbook yet: " + ", ".join(found["missing"]) + ". Say so; never fill it in from memory.")
    if found["conflicts"]:
        lines.append("Conflicts between the user's and the project's layer: " + ", ".join(c["id"] for c in found["conflicts"]))
    return "\n".join(lines)


def cmd_open(a):
    try:
        text = open_text(a)
    except Exception as e:  # the load must not fail: that would hide the skill and the reason
        text = (f"The workbooks could not be loaded ({type(e).__name__}: {e}). Never go on from memory: a stage stops "
                "and says so, and a subagent returns only the line `Blocked: rules not read in full: workbooks`.")
    sys.stdout.write(text + "\n")


def resolve(a):
    ws = os.path.abspath(a.workspace) if a.workspace else None
    dirs = layer_dirs(ws, a.base_dir, a.user_dir)
    have = [t for t in available(dirs) if "@" not in t]
    paths = [os.path.relpath(os.path.abspath(p), ws) if ws and os.path.isabs(p) else p for p in (a.paths or [])]
    wanted = {}
    for t in (a.technologies or []) + project_technologies(ws):
        wanted.setdefault(tech_of_stem(t), []).append("settings" if t in project_technologies(ws) else "requested")
    for t in have:
        globs = []
        for _, wb in load_layers(t, dirs):
            globs += wb["globs"]
        for p in paths:
            if matches(p, globs):
                wanted.setdefault(t, []).append(p)
    missing = sorted(t for t in wanted if t not in have)
    for t, globs in KNOWN.items():
        if t not in have and any(matches(p, globs) for p in paths) and t not in missing:
            missing.append(t)
    topics = None
    if a.topics:
        topics = []
        for tp in a.topics:
            slug = HEADING_TO_SLUG.get(tp.lower(), tp.lower())
            if slug not in SLUGS:
                raise Fail(f"unknown topic {tp!r}; use one of {SLUGS} or their headings")
            topics.append(slug)
    tags = [x.lstrip("#").lower() for x in (a.tags or [])]
    for x in tags:
        if x not in TAGS and x not in SLUGS:
            raise Fail(f"unknown tag {x!r}; use a section {SLUGS} or one of {list(TAGS)}")
    tailored = bool(a.paths or a.technologies or tags)
    aimed = bool(a.paths or a.technologies)
    named = {tech_of_stem(x) for x in (a.technologies or [])}  # named by the caller, also when the settings list it
    result = {"ok": True, "workspace": ws, "technologies": {}, "sections": {}, "overrides": [], "conflicts": [],
              "missing": sorted(missing)}
    receipt = {"stage": a.stage or "", "statements": [], "workbooks": {}}
    now = datetime.date.fromisoformat(today(a.today))
    for t in sorted(x for x in wanted if x in have):
        own = project_wb(t, dirs)
        lines = own["codebase"] if own else []
        labels = [w for w in wanted[t] if w in ("settings", "requested")]
        tpaths = [w for w in wanted[t] if w not in ("settings", "requested")]
        groups = {}  # workbook stem -> {"paths": [...], "lines": {prefix: line}, "unrecorded": [...]}
        for p in tpaths:
            np_ = norm_path(p)
            hit = max((c for c in lines if np_.startswith(c["prefix"])), key=lambda c: len(c["prefix"]), default=None)
            g = groups.setdefault(hit["workbook"] if hit else t, {"paths": [], "lines": {}, "unrecorded": []})
            g["paths"].append(p)
            if hit:
                g["lines"][hit["prefix"]] = hit
            else:
                g["unrecorded"].append(p)
        if not tpaths:  # no paths: every recorded code project's workbook, or the general one
            for c in lines:
                groups.setdefault(c["workbook"], {"paths": [], "lines": {}, "unrecorded": []})["lines"][c["prefix"]] = c
            if not lines or getattr(a, "general", False):  # unrecorded paths get the general workbook
                groups.setdefault(t, {"paths": [], "lines": {}, "unrecorded": []})
        for stem in sorted(groups):
            g = groups[stem]
            layers = load_for(stem, dirs)
            if not layers:
                if stem not in result["missing"]:
                    result["missing"].append(stem)
                continue
            statements, overrides, conflicts = merge(layers)
            base = layers[0][1]
            sup = base["header"].get("Supported until", "")
            sup_date = iso_date(sup)
            code_projects = []
            for c in g["lines"].values():
                until = iso_date(c["until"])
                code_projects.append({"path": c["path"], "version": c["version"], "supported_until": c["until"],
                                      "support_ended": bool(until and until < now), "source": c["source"],
                                      "checked": c["checked"]})
            result["technologies"][stem] = {"technology": t, "title": base["header"].get("Title", t),
                                            "versions": base["header"].get("Versions", ""), "supported_until": sup,
                                            "support_ended": bool(sup_date and sup_date < now),
                                            "code_projects": code_projects, "unrecorded_paths": g["unrecorded"],
                                            "matched_by": sorted(set(labels + g["paths"])), "layers": [l for l, _ in layers]}
            secs = {}
            touched = bool(tpaths) or t in named or not aimed
            for st in statements:
                if topics and st["section"] not in topics:
                    continue
                if tailored and not is_must(st):
                    if not touched or (tags and not set(tags) & {st["section"], *st["tags"]}):
                        continue
                secs.setdefault(st["section"], []).append({k: st[k] for k in ("id", "level", "text", "tags", "source", "layer")})
                receipt["statements"].append(st["id"] if stem == t else f"{stem}:{st['id']}")
            result["sections"][stem] = {s: secs[s] for s in SLUGS if s in secs}
            result["overrides"] += overrides
            result["conflicts"] += conflicts
            receipt["workbooks"][stem] = " + ".join(f"{l} {wb['header'].get('Updated', '?')}" for l, wb in layers)
    result["missing"] = sorted(result["missing"])
    result["receipt"] = receipt
    return result


def markdown_of(result, part=None):
    def body():
        """Rows of (text, workbook heading, section heading, receipt ID, is a MUST)."""
        rows = []
        for stem, info in result["technologies"].items():
            ended = f", support ended {info['supported_until']}" if info["support_ended"] else ""
            named = f" [{stem}]" if "@" in stem else ""
            top = f"## {info['title']} ({info['versions']}{ended}){named}"
            rows.append((top, top, None, None, True))
            for c in info["code_projects"]:
                note = f", support ended {c['supported_until']}" if c["support_ended"] else ""
                rows.append((f"Code project `{c['path']}`: {c['version']}{note}", top, None, None, True))
            if info["unrecorded_paths"]:
                rows.append(("No recorded version for: " + ", ".join(info["unrecorded_paths"]), top, None, None, True))
            for slug, sts in result["sections"][stem].items():
                sub = f"### {dict((s, h) for h, s in SECTIONS)[slug]}"
                rows.append((sub, top, sub, None, None))
                for s in sts:
                    sid = s["id"] if stem == info["technology"] else f"{stem}:{s['id']}"
                    rows.append((statement_line(s), top, sub, sid, is_must(s)))
        if result["missing"]:
            rows.append(("Missing workbooks: " + ", ".join(result["missing"]), None, None, None, True))
        if result["conflicts"]:
            rows.append(("Conflicts to ask the user about:", None, None, None, True))
            rows += [(f"- {c['id']}: {c['from']} says {c['old']!r}; {c['to']} says {c['new']!r}", None, None, None, True)
                     for c in result["conflicts"]]
        return rows

    def with_receipt(lines, receipt):
        return "\n".join(lines + ["", "Receipt: " + json.dumps(receipt, ensure_ascii=False, separators=(",", ":"))]) + "\n"

    def paged(rows):
        """Pages that each repeat the workbook and section heading their statements belong to."""
        pages, lines, ids, top, sub, size = [], [], [], None, None, 0
        for text, t, s, sid, _ in rows:
            if text in (t, s):
                continue  # headings are written with the row that needs them
            need = len(text) + len(t or "") + len(s or "") + 3
            if lines and size + need > PAGE:
                pages.append((lines, ids))
                lines, ids, top, sub, size = [], [], None, None, 0
            for head, changed in ((t, t != top), (s, s != sub or t != top)):
                if head and changed:
                    lines.append(head)
                    size += len(head) + 1
            top, sub = t, s
            lines.append(text)
            size += len(text) + 1
            if sid:
                ids.append(sid)
        return pages + ([(lines, ids)] if lines else [])

    rows = body()
    whole = with_receipt([r[0] for r in rows], result["receipt"])
    if len(whole) <= PRINT_MAX:
        if part not in (None, 1):
            raise Fail("this result has one part")
        return whole
    # too long to arrive exact at once: parts of the same resolve, the MUST rules first, each with its own receipt
    pages = paged([r for r in rows if r[4] is True]) + paged([r for r in rows if r[4] is False])
    n = part or 1
    if not 1 <= n <= len(pages):
        raise Fail(f"--part is 1 to {len(pages)}")
    head = [f"PART {n} of {len(pages)} of this step's statements" +
            (": they are too many to print exact at once. Before you go on, run the same command with "
             + ", ".join(f"--part {i}" for i in range(2, len(pages) + 1)) + " added, and record every part's receipt."
             if n == 1 else "."), ""]
    lines, ids = pages[n - 1]
    return with_receipt(head + lines, dict(result["receipt"], statements=ids, part=f"{n}/{len(pages)}"))


def cmd_resolve(a):
    result = resolve(a)
    if a.versions:
        out({k: result[k] for k in ("ok", "workspace", "technologies", "missing", "overrides", "conflicts")})
    if a.markdown:
        sys.stdout.write(markdown_of(result, a.part))
        sys.exit(0)
    out(result)


def render_overlay(tech, title, layer, updated, sources, sections, codebase=None):
    present = [(h, s) for h, s in SECTIONS if sections.get(s)]
    contents = ["- [Header](#header)"] + [f"- [{h}](#{h.lower().replace(' ', '-')})" for h, _ in present]
    lines = [f"# {title} workbook ({layer})", "", "## Contents", ""] + contents + ["", "## Header", "",
             "| Key | Value |", "| --- | --- |", f"| Technology | `{tech}` |", f"| Title | {title} |",
             f"| Layer | {layer} |", f"| Updated | {updated} |", "", "Sources:", ""]
    lines += [f"- [{s['name']}]({s['url']}) · checked {s['checked']}" + (f" · {s['note']}" if s.get("note") else "")
              for s in sources] or ["- none yet"]
    if codebase:
        lines += ["", "Codebase versions:", ""] + list(codebase)
    for h, s in present:
        lines += ["", f"## {h}", ""]
        for st in sections[s]:
            lvl = f" · {st['level']}" if st.get("level") else ""
            tagged = f" · tags: {', '.join(st['tags'])}" if st.get("tags") else ""
            lines.append(f"- **{st['id']}**{lvl} · {st['text']}{tagged} · source: {st['source']} · confirmed: {st['confirmed']}")
    return "\n".join(lines) + "\n"


def section_span(lines, heading):
    """(start, end) line indexes of a '## heading' section's body, or None."""
    try:
        h = lines.index(f"## {heading}")
    except ValueError:
        return None
    end = next((i for i in range(h + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return h + 1, end


def put_in_list(lines, start, end, marker, new_line, same):
    """Puts new_line in the bullet list that follows `marker` (or the list right after `start` when marker is
    None) between start and end: it replaces the first line for which same(line) is true, else it is appended,
    and a '- none yet' bullet is dropped. Without the marker, the marker and list are added at the end."""
    i = start
    if marker is not None:
        i = next((k for k in range(start, end) if lines[k].strip() == marker), None)
        if i is None:
            at = end
            while at > start and lines[at - 1].strip() == "":
                at -= 1
            lines[at:at] = ["", marker, "", new_line]
            return lines
        i += 1
    while i < end and lines[i].strip() == "":
        i += 1
    j = i
    while j < end and lines[j].startswith("- "):
        j += 1
    block = [l for l in lines[i:j] if l.strip() != "- none yet"]
    for k, l in enumerate(block):
        if same(l):
            block[k] = new_line
            break
    else:
        block.append(new_line)
    if i == j:  # no list yet
        lines[i:i] = block + ([""] if i < end and lines[i].strip() else [])
    else:
        lines[i:j] = block
    return lines


def write_lines(path, lines):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines).rstrip("\n") + "\n")


def tokens(text):
    return set(re.findall(r"[a-z0-9]+", text.lower())) - {"the", "a", "an", "to", "of", "and", "or", "in", "for", "use", "is"}


def cmd_propose(a):
    ws = os.path.abspath(a.workspace)
    dirs = layer_dirs(ws, a.base_dir, a.user_dir)
    stem, slug, layer = a.tech, a.section, a.layer
    tech = tech_of_stem(stem)
    if slug not in SLUGS:
        raise Fail(f"section must be one of {SLUGS}")
    if SEP in a.text or SEP in a.source:
        raise Fail("text and source must not contain ' · '")
    date = today(a.date)
    unknown = [x for x in (a.tags or []) if x not in TAGS]
    if unknown:
        raise Fail(f"unknown tags {unknown}; use {list(TAGS)}")
    target = os.path.join(dirs[layer], f"{stem}.md")
    if "@" in stem and (layer != "project" or not os.path.isfile(target)):
        raise Fail(f"no project workbook {stem}.md: a version workbook is changed only in the project layer once "
                   f"Create has made it; for a choice that holds for every version, propose to {tech}")
    layers = load_for(stem, dirs)
    statements, _, _ = merge(layers)
    own = parse(target) if os.path.isfile(target) else None
    if a.replaces:
        if not any(s["id"] == a.replaces for s in statements):
            raise Fail(f"{a.replaces} is not in any layer of {stem}")
        sid = a.replaces
    else:
        nums = [int(s["id"].split(".")[2][1:]) for s in (own["statements"] if own else [])
                if s["id"].split(".")[2].startswith(LAYER_PREFIX[layer])]
        sid = f"{tech}.{slug}.{LAYER_PREFIX[layer]}{max(nums, default=0) + 1:03d}"
    new_t = tokens(a.text)
    dupes = [s["id"] for s in statements if s["id"] != sid and new_t and
             len(new_t & tokens(s["text"])) / max(1, len(new_t | tokens(s["text"]))) >= 0.6]
    process = [w for w in PROCESS_WORDS if re.search(w, a.text, re.I)]
    secrets = [p for p in SECRET_PATTERNS if re.search(p, a.text + " " + a.source)]
    level = a.level or next((s["level"] for s in statements if s["id"] == sid), None)
    lvl = f" · {level}" if level else ""
    given = list(a.tags or next((s["tags"] for s in statements if s["id"] == sid), []))
    tagged = f" · tags: {', '.join(given)}" if given else ""
    line = f"- **{sid}**{lvl} · {a.text}{tagged} · source: {a.source} · confirmed: {layer}, {date}"
    preview = {"ok": True, "written": False, "file": target, "id": sid, "line": line, "duplicates": dupes,
               "process_wording": process, "secret_like": bool(secrets)}
    if secrets:
        raise Fail("the statement looks like it holds a secret; workbooks never store secrets")
    if not a.write:
        out(preview)
    if process and not a.allow_process_wording:
        raise Fail("process wording flagged: " + ", ".join(process) + "; send process instructions to dev-learn, "
                   "or pass --allow-process-wording when the statement is a technology fact")
    new_sources = [(name, url) for name, url in re.findall(r"\[([^\]]+)\]\((https?://[^)]+)\)", a.source)
                   if not any(s["url"] == url for s in (own["sources"] if own else []))]
    if own and "Load when" in own["order"]:  # a full workbook (a version workbook, or one Create made): edit in place
        with open(target, encoding="utf-8") as f:
            lines = f.read().splitlines()
        heading = dict((s, h) for h, s in SECTIONS)[slug]
        span = section_span(lines, heading)
        if not span:
            raise Fail(f"{target} has no section {heading}")
        put_in_list(lines, span[0], span[1], None, line, lambda l: l.startswith(f"- **{sid}**"))
        for name, url in new_sources:
            hs, he = section_span(lines, "Header")
            put_in_list(lines, hs, he, "Sources:", f"- [{name}]({url}) · checked {date}", lambda l: f"]({url})" in l)
        lines = [f"| Updated | {date} |" if l.startswith("| Updated |") else l for l in lines]
        write_lines(target, lines)
        check = validate_wb(target)
        preview.update(written=True, validate=check)
        out(preview)
    base_title = next((wb["header"].get("Title") for l, wb in layers if wb["header"].get("Title")), tech)
    sections = {s: [] for s in SLUGS}
    sources = []
    if own:
        for st in own["statements"]:
            sections[st["section"]].append(st)
        sources = own["sources"]
    entry = {"id": sid, "level": level, "text": a.text, "tags": given, "source": a.source, "confirmed": f"{layer}, {date}"}
    for s in SLUGS:
        sections[s] = [x for x in sections[s] if x["id"] != sid]
    sections[slug].append(entry)
    sources += [{"name": name, "url": url, "checked": date, "note": ""} for name, url in new_sources]
    os.makedirs(dirs[layer], exist_ok=True)
    with open(target, "w", encoding="utf-8", newline="\n") as f:
        f.write(render_overlay(tech, base_title, layer, date, sources, sections,
                               codebase=[c["raw"] for c in own["codebase"]] if own else None))
    check = validate_wb(target, overlay=True)
    preview.update(written=True, validate=check)
    out(preview)


def cmd_skeleton(a):
    if os.path.exists(a.out):
        raise Fail(f"{a.out} exists; skeleton never overwrites")
    if not re.fullmatch(r"[a-z0-9-]+", a.tech):
        raise Fail("technology must be lowercase letters, digits, and hyphens")
    date = today(a.date)
    key = a.version_key or ""
    if key and not re.fullmatch(r"[a-z0-9.-]+", key):
        raise Fail("version key must be lowercase letters, digits, dots, and hyphens")
    want = f"{a.tech}@{key}.md" if key else f"{a.tech}.md"
    if os.path.basename(a.out) != want:
        raise Fail(f"the file must be named {want}")
    if a.copy_base:
        if not key:
            raise Fail("--copy-base needs --version-key: it starts a version workbook from the general one")
        src = os.path.join(a.base_dir or os.path.join(SKILL_DIR, "workbooks"), f"{a.tech}.md")
        if not os.path.isfile(src):
            raise Fail(f"no base workbook {a.tech}.md to copy")
        with open(src, encoding="utf-8") as f:
            lines = f.read().splitlines()
        if f"## {LEGACY_SECTION}" in lines:  # a base written before 2026-11-25
            lines = [l for l in lines[:lines.index(f"## {LEGACY_SECTION}")] if l != "- [Skills and agents](#skills-and-agents)"]
            while lines and not lines[-1].strip():
                lines.pop()
        rows = {"Title": a.title, "Versions": "none yet", "Layer": a.layer, "Updated": date}
        copied = []
        for l in lines:
            m = re.match(r"^\| (?P<k>[^|]+?) \| (?P<v>.*?) \|$", l)
            k = m.group("k").strip() if m else None
            if k == "Supported until":
                continue
            if k in rows:
                l = f"| {k} | {rows[k]} |"
            copied.append(l)
            if k == "Technology":
                copied.append(f"| Version key | {key} |")
        copied[0] = f"# {a.title} workbook"
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        write_lines(a.out, copied)
        out({"ok": True, "file": a.out, "copied_from": src, "statements": len(parse(a.out)["statements"]),
             "next": "check every statement against the official docs for this version, then set Versions and Supported until"})
    contents =["- [Header](#header)", "- [Load when](#load-when)"] + \
               [f"- [{h}](#{h.lower().replace(' ', '-')})" for h, _ in SECTIONS]
    lines = [f"# {a.title} workbook", "", "## Contents", ""] + contents + ["", "## Header", "", "| Key | Value |",
             "| --- | --- |", f"| Technology | `{a.tech}` |"] + ([f"| Version key | {key} |"] if key else []) + \
            [f"| Title | {a.title} |", "| Versions | none yet |",
             f"| Layer | {a.layer} |", f"| Updated | {date} |", "", "Sources:", "", "- none yet", "", "## Load when", "",
             "| Glob |", "| --- |"]
    lines += [f"| `{g}` |" for g in KNOWN.get(a.tech, [])]
    for h, _ in SECTIONS:
        lines += ["", f"## {h}", "", "- none yet"]
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    out({"ok": True, "file": a.out, "globs": KNOWN.get(a.tech, [])})


def cmd_record_version(a):
    ws = os.path.abspath(a.workspace)
    dirs = layer_dirs(ws, a.base_dir, a.user_dir)
    tech = a.tech
    if "@" in tech or not re.fullmatch(r"[a-z0-9-]+", tech):
        raise Fail("--tech takes the technology (dotnet); name the version workbook with --workbook (dotnet@8)")
    stem = a.workbook or tech
    if stem != tech and not (VERSION_STEM.match(stem) and tech_of_stem(stem) == tech):
        raise Fail(f"--workbook must be {tech} or {tech}@<version>")
    until = a.supported_until or "unknown"
    if until != "unknown" and iso_date(until) is None:
        raise Fail("--supported-until must be YYYY-MM-DD or unknown")
    if SEP in a.version or SEP in a.source or "`" in a.path:
        raise Fail("version, source, and path must not contain ' · ' or backticks")
    if any(re.search(p, a.version + " " + a.source) for p in SECRET_PATTERNS):
        raise Fail("the line looks like it holds a secret; workbooks never store secrets")
    date = today(a.date)
    prefix = norm_prefix(a.path)
    line = (f"- `{prefix or './'}` · {a.version} · workbook: `{stem}` · supported until {until} · "
            f"source: {a.source} · checked {date}")
    target = os.path.join(dirs["project"], f"{tech}.md")
    own = parse(target) if os.path.isfile(target) else None
    old = next((c["raw"] for c in (own["codebase"] if own else []) if c["prefix"] == prefix), None)
    exists = stem in available(dirs)
    preview = {"ok": True, "written": False, "file": target, "line": line, "replaces": old, "workbook_exists": exists,
               "note": "" if exists else f"no {stem} workbook yet: Create makes it (skeleton --version-key --copy-base)"}
    if not a.write:
        out(preview)
    if own:
        with open(target, encoding="utf-8") as f:
            lines = f.read().splitlines()
        span = section_span(lines, "Header")
        if not span:
            raise Fail(f"{target} has no Header section")
        put_in_list(lines, span[0], span[1], "Codebase versions:", line,
                    lambda l: bool(CODEBASE_LINE.match(l)) and norm_prefix(CODEBASE_LINE.match(l).group("path")) == prefix)
        lines = [f"| Updated | {date} |" if l.startswith("| Updated |") else l for l in lines]
        write_lines(target, lines)
    else:
        base = load_layers(tech, dirs)
        title = next((wb["header"].get("Title") for _, wb in base if wb["header"].get("Title")), tech)
        os.makedirs(dirs["project"], exist_ok=True)
        with open(target, "w", encoding="utf-8", newline="\n") as f:
            f.write(render_overlay(tech, title, "project", date, [], {}, codebase=[line]))
    preview.update(written=True, validate=validate_wb(target))
    out(preview)


def cmd_audit(a):
    ws = os.path.abspath(a.workspace) if a.workspace else None
    dirs = layer_dirs(ws, a.base_dir, a.user_dir)
    now = datetime.date.fromisoformat(today(a.today))
    report = {"ok": True, "checked": [], "format_errors": [], "old_sources": [], "orphan_overrides": [],
              "support_ended": [], "support_ending": [], "missing_version_workbooks": [], "versions": [],
              "version_commands": "run" if a.run_version_commands else "not run (needs the user's go-ahead)",
              "checks_run": ["format", f"source age over {a.max_age} days", "orphan overrides",
                             f"support dates (ended, or ending within {a.support_warn_days} days)"] +
                            (["installed versions"] if a.run_version_commands else []),
              "checks_skipped": ([] if a.run_version_commands else
                                 [{"check": "installed versions", "reason": "needs --run-version-commands after the user's go-ahead"}]) +
                                [{"check": "sources still say the same", "reason": "not checked online; reopen the pages to confirm"}]}
    every = available(dirs)

    def support(entry, until, meaning):
        days = (until - now).days
        if days < 0:
            report["support_ended"].append({**entry, "days_past": -days, "meaning": meaning})
        elif days <= a.support_warn_days:
            report["support_ending"].append({**entry, "days_left": days})

    for t in every:
        is_version = "@" in t
        layers = version_files(t, dirs) if is_version else load_layers(t, dirs)
        base_ids = {s["id"] for l, wb in layers if l == "base" for s in wb["statements"]}
        for l, wb in layers:
            name = f"{l}/{t}.md"
            report["checked"].append(name)
            v = validate_wb(wb["path"], overlay=(l != "base" and not is_version))
            report["format_errors"] += [f"{name}: {e}" for e in v["errors"]]
            report.setdefault("untagged", []).extend(  # a replacement inherits the base statement's tags
                f"{name}: {w}" for w in v.get("warnings", [])
                if w.endswith("has no tags") and (l == "base" or w.split(": ")[1].split()[0] not in base_ids))
            for s in wb["sources"]:
                age = (now - datetime.date.fromisoformat(s["checked"])).days
                if age > a.max_age:
                    report["old_sources"].append({"workbook": name, "source": s["url"], "checked": s["checked"], "days": age})
            if l != "base" and not is_version:
                for s in wb["statements"]:
                    if s["id"].split(".")[2].isdigit() and s["id"] not in base_ids:
                        report["orphan_overrides"].append({"workbook": name, "id": s["id"]})
            sup = iso_date(wb["header"].get("Supported until", ""))
            if sup:
                support({"workbook": name, "layer": l, "versions": wb["header"].get("Versions", ""),
                         "supported_until": sup.isoformat()}, sup, SUPPORT_MEANING["version" if is_version else l])
            elif l == "base" or is_version:
                report["checks_skipped"].append({"check": "support dates", "workbook": name,
                                                 "reason": "no Supported until date in its Header"})
            for c in wb["codebase"]:
                entry = {"workbook": name, "layer": l, "code_project": c["path"], "versions": c["version"],
                         "supported_until": c["until"]}
                until = iso_date(c["until"])
                if until:
                    support(entry, until, SUPPORT_MEANING["codebase"])
                checked = iso_date(c["checked"])
                if checked and (now - checked).days > a.max_age:
                    report["old_sources"].append({"workbook": name, "code_project": c["path"], "source": c["source"],
                                                  "checked": c["checked"], "days": (now - checked).days})
                if c["workbook"] not in every:
                    report["missing_version_workbooks"].append({"workbook": name, "code_project": c["path"],
                                                                "needs": c["workbook"]})
        cmd = next((wb["header"].get("Version command") for _, wb in layers if wb["header"].get("Version command")), "")
        if cmd and a.run_version_commands:
            try:
                p = subprocess.run(shlex.split(cmd), capture_output=True, text=True, timeout=20)
                installed = (p.stdout or p.stderr).strip().splitlines()[0] if (p.stdout or p.stderr).strip() else ""
            except (OSError, subprocess.TimeoutExpired) as e:
                installed = f"not available ({e.__class__.__name__})"
            versions = next((wb["header"].get("Versions") for _, wb in layers if wb["header"].get("Versions")), "")
            report["versions"].append({"technology": t, "command": cmd, "installed": installed, "workbook_covers": versions})
    out(report)


CONSULT_FILES = {  # the files whose stage records a workbook receipt
    "dev-plan": ("stages/scope.md",),
    "dev-test": ("routes/write.md", "routes/run.md"),
    "dev-build": ("routes/build.md",),
    "dev-review": ("routes/review.md",),
    "dev-learn": ("routes/learn.md",),
    "dev-deploy": ("routes/deploy.md",),
}


def cmd_check_skills(a):
    results = []
    for d in sorted(globmod.glob(os.path.join(a.skills_dir, "dev-*"))):
        name = os.path.basename(d)
        if name in ("dev-core", "dev-workbook") or not os.path.isdir(d):
            continue
        named = [os.path.join(d, *rel.split("/")) for rel in CONSULT_FILES.get(name, ())]
        if named and any(os.path.isfile(f) for f in named):
            stage_files = named
        else:
            stage_files = sorted(globmod.glob(os.path.join(d, "stages", "*.md")) + globmod.glob(os.path.join(d, "routes", "*.md"))) \
                or [os.path.join(d, "SKILL.md")]
        for f in stage_files:
            try:
                text = open(f, encoding="utf-8").read()
            except FileNotFoundError:
                results.append({"file": f, "ok": False, "reason": "missing"})
                continue
            ok = "WORKBOOK resolve" in text or ("workbook.py" in text and "resolve" in text)
            results.append({"file": os.path.relpath(f, a.skills_dir), "ok": ok,
                            "reason": "" if ok else "no Consult step calling workbook.py resolve"})
    passed = all(r["ok"] for r in results)
    out({"ok": passed, "files": results, "note": "" if results else "no dev stage skills found yet"}, 0 if passed else 1)


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(prog="workbook")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--base-dir")
        p.add_argument("--user-dir")
        return p
    p = common(sub.add_parser("open"))
    p.add_argument("--workspace")
    p = common(sub.add_parser("resolve"))
    p.add_argument("--tags", nargs="*"); p.add_argument("--versions", action="store_true"); p.add_argument("--part", type=int)
    p.add_argument("--workspace"); p.add_argument("--paths", nargs="*"); p.add_argument("--technologies", nargs="*")
    p.add_argument("--topics", nargs="*"); p.add_argument("--stage"); p.add_argument("--markdown", action="store_true")
    p.add_argument("--today")
    p = common(sub.add_parser("validate")); p.add_argument("file"); p.add_argument("--overlay", action="store_true", default=None)
    p = common(sub.add_parser("propose"))
    p.add_argument("--workspace", required=True); p.add_argument("--tech", required=True); p.add_argument("--section", required=True)
    p.add_argument("--text", required=True); p.add_argument("--source", required=True)
    p.add_argument("--level", choices=["MUST", "SHOULD", "MUST NOT"]); p.add_argument("--layer", choices=["project", "user"], default="project")
    p.add_argument("--tags", nargs="*")
    p.add_argument("--replaces"); p.add_argument("--write", action="store_true"); p.add_argument("--allow-process-wording", action="store_true")
    p.add_argument("--date")
    p = common(sub.add_parser("skeleton"))
    p.add_argument("--tech", required=True); p.add_argument("--title", required=True)
    p.add_argument("--layer", choices=LAYERS, required=True); p.add_argument("--out", required=True); p.add_argument("--date")
    p.add_argument("--version-key"); p.add_argument("--copy-base", action="store_true")
    p = common(sub.add_parser("record-version"))
    p.add_argument("--workspace", required=True); p.add_argument("--tech", required=True); p.add_argument("--path", required=True)
    p.add_argument("--version", required=True); p.add_argument("--source", required=True); p.add_argument("--workbook")
    p.add_argument("--supported-until"); p.add_argument("--date"); p.add_argument("--write", action="store_true")
    p = common(sub.add_parser("audit"))
    p.add_argument("--workspace"); p.add_argument("--today"); p.add_argument("--max-age", type=int, default=180)
    p.add_argument("--support-warn-days", type=int, default=180)
    p.add_argument("--run-version-commands", action="store_true")
    p = common(sub.add_parser("check-skills")); p.add_argument("skills_dir")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "open":
            cmd_open(a)
        elif a.cmd == "resolve":
            cmd_resolve(a)
        elif a.cmd == "validate":
            if not os.path.isfile(a.file):
                raise Fail(f"no such file {a.file}")
            out(validate_wb(a.file, a.overlay))
        elif a.cmd == "propose":
            cmd_propose(a)
        elif a.cmd == "skeleton":
            cmd_skeleton(a)
        elif a.cmd == "record-version":
            cmd_record_version(a)
        elif a.cmd == "audit":
            cmd_audit(a)
        elif a.cmd == "check-skills":
            cmd_check_skills(a)
    except Fail as e:
        out({"ok": False, "error": str(e)}, 1)
    except ValueError as e:
        out({"ok": False, "error": f"bad value: {e}"}, 1)


if __name__ == "__main__":
    main()
