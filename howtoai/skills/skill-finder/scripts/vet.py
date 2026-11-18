"""skill-finder vetting helpers: isolate a candidate, scan it, and compare an install.

Standard library only; run with `py -3 -I` (or `python3 -I`). Never runs, imports,
or installs anything from the candidate: every file is read as data.

Commands:

  vet.py isolate <source folder or file> [--into DIR] [--commit SHA]
      Copies a local candidate (a skill folder, a plugin folder, an agent or
      command file, a hook or MCP config, or a workflow folder) into a new, empty
      folder outside every discovery path, as <new folder>/<candidate name>, and
      writes a manifest of every file's SHA-256 beside it (not inside the copy).
      Everything is copied, including node_modules/ and __pycache__/, except
      symbolic links and junctions (not followed) and .git/ (its commit is
      recorded); each of those is listed under "left_out".
      A remote candidate is cloned instead (`git clone --depth 1 <url> <new folder>/<name>`),
      then recorded with `vet.py manifest`.

  vet.py manifest <folder> --out <manifest.json> [--commit SHA] [--subdir PATH]
      Writes the manifest of a folder that is already isolated (for example, a
      fresh git clone). The commit is read from .git when not given. For one
      plugin of a multi-plugin marketplace clone, --subdir names the plugin's
      own folder (relative to the clone), so the manifest holds only the files
      that install; the commit is still the clone's.

  vet.py scan <folder>
      Lists what the candidate holds (skills, agents, commands, hooks, MCP servers,
      plugin and marketplace manifests, settings files, scripts, binaries,
      symbolic links) and every line that needs a reviewer's eye: network calls,
      process launches, shell piping, credential and environment reads, writes
      to Claude configuration, unpinned runtime downloads, literal secrets,
      instructions aimed at the agent, hidden text (HTML comments, zero-width and
      bidirectional characters, long encoded blobs), plus compiled or binary code
      that cannot be reviewed (.pyc, .exe, .dll, ..., or any file whose first
      bytes show bytecode, an executable, or a zip archive), which is "high", and
      bundled dependency folders (node_modules/). "high" hits fail the
      candidate unless the reviewer finds them harmless in context and says why.
      The scan narrows the review; it never replaces reading every file.

  vet.py compare <manifest.json> (--dir <installed folder> | --plugin <name@marketplace>) [--subdir PATH]
      Compares an installed copy with the reviewed manifest: added, removed, and
      changed files, and, for a plugin, the installed gitCommitSha against the
      reviewed commit. Every file in the installed copy counts, including .git/,
      node_modules/, and __pycache__/, and every link or junction in it is
      reported as added; only Claude Code's own bookkeeping (.in_use/,
      .mcpb-cache/) is ignored. Exit code 0 when they match, 1 when they differ.

Output is JSON on stdout, UTF-8.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REVIEW_SKIP = (".git",)  # git metadata of a clone: recorded as the commit, never installed
INSTALL_BOOKKEEPING = {".in_use", ".mcpb-cache"}  # written by Claude Code into an installed plugin's folder
TEXT_LIMIT = 2 * 1024 * 1024  # bytes read per file for the scan
BINARY_EXT = re.compile(r"\.(exe|dll|so|dylib|bin|pyc|pyo|class|jar|wasm|node|msi|dmg|app|scr|com)$", re.I)
SCRIPT_EXT = re.compile(r"\.(py|sh|bash|zsh|js|mjs|cjs|ts|tsx|ps1|psm1|rb|pl|php|cmd|bat|go|rs|lua)$", re.I)

# (category, severity, pattern). "high" = fails the candidate unless explained in context.
RULES = [
    ("pipe-to-shell", "high", r"(curl|wget|iwr|Invoke-WebRequest|irm|Invoke-RestMethod)\b[^\n|]*\|\s*(ba|z)?sh\b|\|\s*(iex|Invoke-Expression)\b"),
    ("remote-code", "high", r"\b(eval|exec)\s*\(\s*(requests\.get|urllib|fetch|await\s+fetch|http)|\bnew\s+Function\s*\(|DownloadString\s*\("),
    ("credential-file", "high", r"(~|\$HOME|%USERPROFILE%|\$env:USERPROFILE|\bos\.path\.expanduser\(|Path\.home\(\)|\bhomedir\(\)|getenv\(\s*['\"](HOME|USERPROFILE)['\"])[^\n]{0,60}\.(ssh|aws|gnupg|kube|docker|netrc|npmrc|pypirc|git-credentials)\b"
                                r"|['\"/\\]\.(ssh|aws|gnupg|kube)([/\\'\"]|$)|authorized_keys|id_rsa|id_ed25519|\.claude\.json\b|\.credentials\.json\b"),
    ("encoded-exec", "high", r"\bbase64\s+(-d|-D|--decode)\b[^\n]*\|\s*(ba|z|da)?sh\b|\b(exec|eval)\s*\([^\n]{0,40}(b64decode|base64|atob\s*\(|fromCharCode|unhexlify|zlib\.decompress|marshal\.loads)"
                             r"|\bnew\s+Function\s*\([^\n]{0,20}atob|FromBase64String[^\n]{0,120}(iex|Invoke-Expression)|(iex|Invoke-Expression)[^\n]{0,120}FromBase64String|-(EncodedCommand|enc|e)\s+[A-Za-z0-9+/=]{20,}"
                             r"|\bcertutil(\.exe)?\s+[^\n]*-decode(hex)?\b|\bxxd\s+(-\w+\s+)*-r\b"
                             r"|\b(printf|echo\s+-e)\s+[^\n|]*\\x[0-9a-fA-F]{2}[^\n|]*\|\s*(ba|z|da|k)?sh\b"),
    ("literal-secret", "high", r"\b(sk-(ant-)?[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,}|github_pat_\w{20,}|xox[abp]-[\w-]{10,}|AKIA[0-9A-Z]{16})\b|-----BEGIN [A-Z ]*PRIVATE KEY-----|Bearer\s+(?![$<{])[A-Za-z0-9._~+/-]{8,}"),
    ("agent-instruction", "high", r"(ignore|disregard|forget)\s+(all\s+|any\s+)?(the\s+)?(previous|prior|above|earlier|system)\s+(instructions|prompts?|rules)"
                                  r"|do\s+not\s+(tell|inform|show|mention\s+(this\s+)?to)\s+the\s+user|without\s+(asking|telling)\s+the\s+user"
                                  r"|skip\s+(any\s+|all\s+|the\s+)?(approval|confirmation|permission)s?|bypassPermissions|--dangerously-skip-permissions"
                                  r"|dangerouslyDisableSandbox|you\s+are\s+now\s+(in\s+)?(developer|admin|unrestricted|jailbreak)"),
    ("claude-config-write", "high", r"(\.claude[/\\](settings(\.local)?\.json|CLAUDE\.md|agents|skills|commands|hooks)|claude_desktop_config\.json|known_marketplaces\.json)[^\n]{0,60}(write|>>?|open\([^)]*['\"][wa]|Set-Content|Add-Content|Out-File|copy|cp\s|mv\s)"
                                    r"|(write|>>?|Set-Content|Add-Content|Out-File)[^\n]{0,60}\.claude[/\\](settings|CLAUDE\.md)"),
    ("network", "review", r"\b(curl|wget|Invoke-WebRequest|Invoke-RestMethod|iwr|irm|nc|ncat|telnet|scp|rsync|ftp)\b|\brequests\.(get|post|put|delete|patch|request)\b|urllib\.request|\bhttpx\.|\baiohttp\b|\bsocket\.|\bfetch\s*\(|\baxios\b|XMLHttpRequest|WebSocket\s*\(|\bhttps?\.request\s*\("),
    ("url", "review", r"\b(https?|wss?|ftp)://[^\s\"'<>)\]]+"),
    ("process", "review", r"\bsubprocess\.|\bos\.(system|popen|exec\w*|spawn\w*)\b|child_process|\bexecSync\b|\bspawn\s*\(|Start-Process|\bShell\.Application\b|Runtime\.getRuntime\(\)\.exec|\bpty\.spawn"),
    ("env-read", "review", r"\bos\.environ\b|\bos\.getenv\b|process\.env\b|\$env:|\bgetenv\s*\(|\$\{?[A-Z][A-Z0-9_]*(TOKEN|KEY|SECRET|PASSWORD|PASS)\}?|\b[A-Z][A-Z0-9]*_(API_KEY|TOKEN|SECRET|PASSWORD)\b"),
    ("file-write-outside", "review", r"(~|\$HOME|%USERPROFILE%|%APPDATA%|/etc/|C:\\\\Windows|/usr/)[^\n]{0,80}(write|>>?|Set-Content|Out-File|chmod|chown|rm\s+-rf|Remove-Item)"),
    ("unpinned-download", "review", r"\b(npx|bunx|pnpx)\s+(-y\s+|--yes\s+)?(?!-)[@\w./-]+(?<!@latest)(?=\s|\"|'|$)(?![^\n]*@\d)|\buvx\s+(?!-)[\w.-]+(?![^\n]*==)|\bpip3?\s+install\s+(?![^\n]*==)[\w.-]+|\bdocker\s+(run|pull)\s+[^\s:]+(:latest)?(\s|$)|@latest\b"),
    ("encoded-blob", "review", r"[A-Za-z0-9+/]{120,}={0,2}|\\x[0-9a-fA-F]{2}(\\x[0-9a-fA-F]{2}){30,}|\bbase64\s+(-d|--decode)\b|\batob\s*\(|b64decode"),
    ("persistence", "review", r"\b(crontab|schtasks|launchctl|systemctl\s+enable|New-ScheduledTask|Register-ScheduledTask|reg\s+add|HKCU\\\\|HKLM\\\\|\.bashrc|\.zshrc|\.profile|Startup\\\\)"),
]
COMPILED = [(c, s, re.compile(p, re.I)) for c, s, p in RULES]
# A file that decodes something anywhere, and runs a variable or unmarshals code, runs a hidden payload
DECODES = re.compile(r"b64decode|base64|unhexlify|fromhex|\bhex_codec|codecs\.decode|zlib\.decompress|lzma\.decompress|bz2\.decompress"
                     r"|gzip\.decompress|marshal\.loads|\batob\s*\(|FromBase64String|Buffer\.from\([^)]*['\"](base64|hex)['\"]", re.I)
RUNS_VARIABLE = re.compile(r"\bmarshal\.loads\s*\(|(?<![\w.])(exec|eval)\s*\(\s*[A-Za-z_][\w.]*\s*[,)]")
# First bytes of compiled code and archives, whatever the file is named
MAGIC = [(b"MZ", "Windows executable (MZ)"), (b"\x7fELF", "ELF executable"), (b"\xfe\xed\xfa\xce", "Mach-O executable"),
         (b"\xfe\xed\xfa\xcf", "Mach-O executable"), (b"\xce\xfa\xed\xfe", "Mach-O executable"),
         (b"\xcf\xfa\xed\xfe", "Mach-O executable"), (b"\xca\xfe\xba\xbe", "Mach-O universal binary or Java class"),
         (b"PK\x03\x04", "zip archive (zip, whl, jar)"), (b"\x00asm", "WebAssembly module")]


def magic_kind(raw):
    """What compiled code or archive the first bytes show, else None."""
    word = int.from_bytes(raw[:2], "little")
    if len(raw) >= 8 and raw[2:4] == b"\r\n" and (2900 <= word < 4000 or word == 62211):
        return "Python bytecode (.pyc)"
    for sig, kind in MAGIC:
        if raw.startswith(sig):
            if sig == b"MZ" and b"\x00" not in raw[:64]:
                continue  # text that happens to start with MZ
            return kind
    return None


HIDDEN_CHARS = re.compile("[\u200b\u200c\u200d\u2060\ufeff\u202a-\u202e\u2066-\u2069\u00ad]")
HTML_COMMENT = re.compile(r"<!--(.*?)-->", re.S)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def is_link(path):
    """A symbolic link, or on Windows a directory junction, which os.walk would otherwise follow."""
    return os.path.islink(path) or (hasattr(os.path, "isjunction") and os.path.isjunction(path))


def eol_hash(path):
    """SHA-256 with CRLF read as LF, so a checkout's line endings alone never count as a change."""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()


def walk(root, skip=REVIEW_SKIP):
    """Every file under root, without following links, as (relative path, full path, is_link).
    Folders named in skip are left out at any depth."""
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        keep = []
        for d in sorted(dirnames):
            full = os.path.join(dirpath, d)
            if is_link(full):
                yield os.path.relpath(full, root).replace(os.sep, "/"), full, True
            elif d not in skip:
                keep.append(d)
        dirnames[:] = keep
        for f in sorted(filenames):
            full = os.path.join(dirpath, f)
            yield os.path.relpath(full, root).replace(os.sep, "/"), full, is_link(full)


def git_commit(root):
    head = os.path.join(root, ".git", "HEAD")
    try:
        ref = open(head, encoding="utf-8").read().strip()
    except OSError:
        return None
    if ref.startswith("ref: "):
        path = os.path.join(root, ".git", *ref[5:].split("/"))
        try:
            return open(path, encoding="utf-8").read().strip()
        except OSError:
            packed = os.path.join(root, ".git", "packed-refs")
            try:
                for line in open(packed, encoding="utf-8"):
                    if line.strip().endswith(ref[5:]):
                        return line.split()[0]
            except OSError:
                return None
            return None
    return ref


def build_manifest(root, commit=None, source=None, skip=REVIEW_SKIP):
    files, eol, links = {}, {}, []
    for rel, full, linked in walk(root, skip):
        if linked:
            links.append({"path": rel, "target": os.readlink(full)})
        else:
            files[rel] = sha256(full)
            eol[rel] = eol_hash(full)
    return {"made": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "source": source, "copy": os.path.abspath(root).replace(os.sep, "/"),
            "commit": commit or git_commit(root), "files": files, "files_eol": eol, "symlinks": links}


def cmd_isolate(args):
    src = os.path.abspath(os.path.expanduser(args.source))
    if not os.path.exists(src):
        sys.exit(json.dumps({"error": "source not found: %s" % args.source}))
    parent = args.into or None
    if parent:
        os.makedirs(parent, exist_ok=True)
    box = tempfile.mkdtemp(prefix="skill-finder-vet-", dir=parent)
    name = os.path.basename(src.rstrip("/\\")) or "candidate"
    dest = os.path.join(box, name)
    left_out = []
    if os.path.isdir(src):
        def ignore(d, names):
            out = set()
            for n in names:
                full = os.path.join(d, n)
                rel = os.path.relpath(full, src).replace(os.sep, "/")
                if is_link(full):
                    left_out.append({"path": rel, "reason": "link or junction, not followed", "target": os.readlink(full)})
                    out.add(n)
                elif n == ".git" and os.path.isdir(full):
                    left_out.append({"path": rel, "reason": "git metadata; its commit is recorded"})
                    out.add(n)
            return out
        shutil.copytree(src, dest, symlinks=False, ignore=ignore)
    else:
        os.makedirs(dest)
        shutil.copy2(src, os.path.join(dest, os.path.basename(src)), follow_symlinks=False)
    manifest = build_manifest(dest, args.commit or git_commit(src), src.replace(os.sep, "/"))
    manifest["left_out"] = left_out
    out = os.path.join(box, "manifest.json")
    # The manifest sits next to the copy, not in it, so the audit never reads it as the candidate's file.
    with open(out, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    print(json.dumps({"ok": True, "copy": dest.replace(os.sep, "/"), "manifest": out.replace(os.sep, "/"),
                      "files": len(manifest["files"]), "commit": manifest["commit"],
                      "left_out": left_out}, indent=1))


def sub_folder(root, subdir):
    """root/subdir for one plugin of a multi-plugin repository; it must stay inside root."""
    if not subdir:
        return root
    root = os.path.abspath(root)
    full = os.path.abspath(os.path.join(root, *re.split(r"[/\\]+", subdir.strip("/\\"))))
    if not full.startswith(root + os.sep) or not os.path.isdir(full):
        sys.exit(json.dumps({"error": "subfolder not found inside %s: %s" % (root, subdir)}))
    return full


def cmd_manifest(args):
    root = os.path.abspath(args.folder)
    if not os.path.isdir(root):
        sys.exit(json.dumps({"error": "folder not found: %s" % args.folder}))
    # The commit is the clone's; the files are the plugin's own subfolder when --subdir names one
    manifest = build_manifest(sub_folder(root, args.subdir), args.commit or git_commit(root))
    manifest["subdir"] = args.subdir
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    print(json.dumps({"ok": True, "manifest": args.out, "files": len(manifest["files"]), "commit": manifest["commit"],
                      "symlinks": manifest["symlinks"]}, indent=1))


def kind_of(rel):
    low = rel.lower()
    name = low.rsplit("/", 1)[-1]
    if name == "skill.md":
        return "skill"
    if re.search(r"(^|/)agents/[^/]+\.md$", low):
        return "agent"
    if re.search(r"(^|/)commands/.+\.md$", low):
        return "command"
    if low.endswith(".claude-plugin/plugin.json"):
        return "plugin manifest"
    if low.endswith(".claude-plugin/marketplace.json"):
        return "marketplace manifest"
    if re.search(r"(^|/)hooks/hooks\.json$", low):
        return "hooks"
    if name in (".mcp.json", "mcp.json") or name.endswith(".mcpb") or name.endswith(".dxt"):
        return "mcp servers"
    if name in ("settings.json", "settings.local.json"):
        return "settings"
    if re.search(r"(^|/)\.github/workflows/.+\.ya?ml$", low) or re.search(r"(^|/)workflows/.+\.(js|ya?ml)$", low):
        return "workflow"
    if name in ("package.json", "requirements.txt", "pyproject.toml", "setup.py", "package-lock.json", "uv.lock"):
        return "dependencies"
    if BINARY_EXT.search(name):
        return "binary"
    if SCRIPT_EXT.search(name) or re.search(r"(^|/)bin/[^/]+$", low):
        return "script"
    return None


def cmd_scan(args):
    root = os.path.abspath(args.folder)
    inventory, hits, links, unread = {}, [], [], []
    count = 0
    deps = set()
    for rel, full, linked in walk(root):
        if linked:
            links.append({"path": rel, "target": os.readlink(full)})
            hits.append({"category": "link", "severity": "high", "file": rel, "line": None,
                         "match": "link or junction", "text": "points to %s" % os.readlink(full)})
            continue
        count += 1
        k = kind_of(rel)
        if k:
            inventory.setdefault(k, []).append(rel)
        parts = rel.split("/")
        if "node_modules" in parts:
            dep = "/".join(parts[:parts.index("node_modules") + 1])
            if dep not in deps:
                deps.add(dep)
                inventory.setdefault("bundled dependencies", []).append(dep)
                hits.append({"category": "bundled-dependencies", "severity": "review", "file": dep, "line": None,
                             "match": "node_modules", "text": "third-party packages ship inside the candidate; review them or fail it"})
        if BINARY_EXT.search(rel):
            hits.append({"category": "compiled-code", "severity": "high", "file": rel, "line": None,
                         "match": rel.rsplit(".", 1)[-1], "text": "compiled or binary code cannot be reviewed; it fails the candidate"})
            unread.append({"path": rel, "reason": "compiled or binary code"})
            continue
        try:
            with open(full, "rb") as f:
                raw = f.read(TEXT_LIMIT + 1)
        except OSError as e:
            unread.append({"path": rel, "reason": str(e)})
            continue
        magic = magic_kind(raw)
        if magic:
            if k != "binary":
                inventory.setdefault("binary", []).append(rel)
            hits.append({"category": "compiled-code", "severity": "high", "file": rel, "line": None, "match": magic,
                         "text": "the file's first bytes show %s, whatever its name; it cannot be reviewed and fails the candidate" % magic})
            unread.append({"path": rel, "reason": "compiled or binary code (%s)" % magic})
            continue
        if b"\x00" in raw[:4096]:
            if k != "binary":
                inventory.setdefault("binary", []).append(rel)
            unread.append({"path": rel, "reason": "binary file; open it with a tool that shows its type"})
            continue
        if len(raw) > TEXT_LIMIT:
            unread.append({"path": rel, "reason": "over 2 MB; read it in parts"})
        text = raw[:TEXT_LIMIT].decode("utf-8", errors="replace")
        lines = text.splitlines()
        decodes = bool(DECODES.search(text))
        for i, line in enumerate(lines, 1):
            if decodes:
                m = RUNS_VARIABLE.search(line)
                if m:
                    hits.append({"category": "encoded-exec", "severity": "high", "file": rel, "line": i,
                                 "match": m.group(0)[:120], "text": "runs a variable or unmarshals code in a file that also "
                                 "decodes data: %s" % line.strip()[:160]})
            for cat, sev, rx in COMPILED:
                m = rx.search(line)
                if m:
                    hits.append({"category": cat, "severity": sev, "file": rel, "line": i,
                                 "match": m.group(0)[:120], "text": line.strip()[:200]})
            if HIDDEN_CHARS.search(line):
                hits.append({"category": "hidden-text", "severity": "high", "file": rel, "line": i,
                             "match": ", ".join("U+%04X" % ord(c) for c in sorted(set(HIDDEN_CHARS.findall(line)))),
                             "text": HIDDEN_CHARS.sub("<?>", line.strip())[:200]})
        if rel.lower().endswith((".md", ".markdown", ".html", ".htm")):
            for m in HTML_COMMENT.finditer(text):
                body = m.group(1).strip()
                if body:
                    hits.append({"category": "hidden-text", "severity": "review", "file": rel,
                                 "line": text.count("\n", 0, m.start()) + 1, "match": "HTML comment",
                                 "text": re.sub(r"\s+", " ", body)[:200]})
    by_sev = {"high": sum(1 for h in hits if h["severity"] == "high"),
              "review": sum(1 for h in hits if h["severity"] == "review")}
    by_cat = {}
    for h in hits:
        by_cat[h["category"]] = by_cat.get(h["category"], 0) + 1
    if os.path.isdir(os.path.join(root, ".git")):
        inventory["git metadata"] = [".git"]  # not scanned, never installed
    print(json.dumps({"folder": root.replace(os.sep, "/"), "files": count, "inventory": inventory,
                      "symlinks": links, "unread": unread, "counts": by_sev, "by_category": by_cat,
                      "hits": hits}, ensure_ascii=False, indent=1))


def cmd_compare(args):
    try:
        with open(args.manifest, encoding="utf-8") as f:
            reviewed = json.load(f)
    except (OSError, ValueError) as e:
        sys.exit(json.dumps({"error": "cannot read the reviewed manifest: %s" % e}))
    commit_installed = None
    if args.plugin:
        ip = os.path.join(os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude"), "plugins", "installed_plugins.json")
        try:
            with open(ip, encoding="utf-8") as f:
                rows = json.load(f).get("plugins", {}).get(args.plugin) or []
        except (OSError, ValueError) as e:
            sys.exit(json.dumps({"error": "cannot read installed_plugins.json: %s" % e}))
        if not rows:
            sys.exit(json.dumps({"error": "%s is not installed" % args.plugin}))
        row = sorted(rows, key=lambda r: r.get("lastUpdated", ""))[-1]
        folder, commit_installed = row.get("installPath"), row.get("gitCommitSha")
    else:
        folder = args.dir
    if not folder or not os.path.isdir(folder):
        sys.exit(json.dumps({"error": "installed folder not found: %s" % folder}))
    folder = sub_folder(folder, args.subdir)
    # Every file of the installed copy counts; only Claude Code's own bookkeeping in a plugin's install folder is not content
    installed = build_manifest(folder, skip=())
    now = {p: h for p, h in installed["files"].items() if p.split("/", 1)[0] not in INSTALL_BOOKKEEPING}
    before = reviewed["files"]
    linked = sorted(l["path"] + " (link to %s)" % l["target"] for l in installed["symlinks"]
                    if l["path"].split("/", 1)[0] not in INSTALL_BOOKKEEPING)
    added = sorted(set(now) - set(before)) + linked
    removed = sorted(set(before) - set(now))
    differ = sorted(p for p in set(now) & set(before) if now[p] != before[p])
    # A file that differs only in CRLF versus LF line endings is the same content
    eol_before, eol_now = reviewed.get("files_eol", {}), installed["files_eol"]
    eol_only = [p for p in differ if p in eol_before and eol_before[p] == eol_now.get(p)]
    changed = [p for p in differ if p not in eol_only]
    commit_match = None
    if commit_installed and reviewed.get("commit"):
        commit_match = commit_installed.lower() == reviewed["commit"].lower()
    same = not (added or removed or changed) and commit_match is not False
    print(json.dumps({"match": same, "installed": str(folder).replace(os.sep, "/"),
                      "reviewed_commit": reviewed.get("commit"), "installed_commit": commit_installed,
                      "commit_match": commit_match, "added": added, "removed": removed, "changed": changed,
                      "line_endings_only": eol_only}, indent=1))
    sys.exit(0 if same else 1)


def main():
    ap = argparse.ArgumentParser(description="skill-finder vetting helpers")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("isolate")
    p.add_argument("source")
    p.add_argument("--into", help="parent folder for the new isolated folder (default: the system temp folder)")
    p.add_argument("--commit")
    p = sub.add_parser("manifest")
    p.add_argument("folder")
    p.add_argument("--out", required=True)
    p.add_argument("--commit")
    p.add_argument("--subdir", help="one plugin's folder inside a multi-plugin marketplace clone, relative to the clone")
    p = sub.add_parser("scan")
    p.add_argument("folder")
    p = sub.add_parser("compare")
    p.add_argument("manifest")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--dir")
    g.add_argument("--plugin")
    p.add_argument("--subdir", help="compare only this subfolder of the installed folder (for example, one plugin "
                   "of a marketplace clone given with --dir)")
    args = ap.parse_args()
    {"isolate": cmd_isolate, "manifest": cmd_manifest, "scan": cmd_scan, "compare": cmd_compare}[args.cmd](args)


if __name__ == "__main__":
    main()
