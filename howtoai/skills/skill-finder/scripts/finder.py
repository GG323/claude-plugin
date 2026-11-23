"""skill-finder index and search.

Commands (run with the Python that has chromadb, see SKILL.md):

  finder.py index  [--budget N] [--skip-expand] [--sources PATH] [--index DIR]
      Rebuild the shipped index (index/catalog.jsonl.gz, index/vectors.npy, index/meta.json)
      from the remote sources in sources.json. Entries whose text did not change keep their
      vectors; plugin internals (skills, agents, commands, hooks, MCP servers) are read from
      each plugin's repository tarball, streamed in memory and never written to disk or run,
      up to N repositories per run (default 300), cached by commit in the catalog.

  finder.py search "<need>" ["<another phrasing>" ...] [--top N] [--cwd DIR] [--no-local]
      Hybrid search: vector (Chroma, all-MiniLM-L6-v2) and keyword (BM25) over the shipped
      index plus local sources scanned live, fused by reciprocal rank across all phrasings.
      Prints a Markdown shortlist with full descriptions and inner components.

  finder.py expand <id> [<id> ...]
      Read the internals of the given entries now (for entries not yet expanded) and print
      them. Writes nothing.

  finder.py dump --shard K/N
      Print every shipped entry compactly, one per line, for thorough-mode subagents.

  finder.py stats
      Print index age, counts per source, and expansion coverage.

Output is UTF-8. Network: GitHub raw and codeload, agenticskills.io. No credentials used.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import gzip
import hashlib
import html
import io
import json
import math
import os
import re
import sys
import tarfile
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SKILL_DIR = Path(__file__).resolve().parent.parent
UA = "skill-finder/1.0 (+https://github.com/GG323/claude-plugin)"
EMBED_CHARS = 1200
MAX_TAR_BYTES = 60 * 1024 * 1024
MAX_MEMBER_BYTES = 256 * 1024


# --- Small helpers ------------------------------------------------------------------------


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def fetch(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def text_hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:16]


def clean(s: object, limit: int = 4000) -> str:
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return s[:limit]


def frontmatter(text: str) -> dict:
    """Minimal YAML frontmatter reader: name, description (plain, quoted, or block scalar)."""
    m = re.match(r"﻿?---\s*\r?\n(.*?)\r?\n---", text, re.S)
    if not m:
        return {}
    out, lines, i = {}, m.group(1).splitlines(), 0
    while i < len(lines):
        km = re.match(r"^([A-Za-z_-]+):\s*(.*)$", lines[i])
        i += 1
        if not km:
            continue
        key, val = km.group(1), km.group(2).strip()
        if val in ("|", ">", "|-", ">-", "|+", ">+") or val == "":
            block = []
            while i < len(lines) and (lines[i].startswith((" ", "\t")) or not lines[i].strip()):
                block.append(lines[i].strip())
                i += 1
            val = " ".join(b for b in block if b)
        else:
            while i < len(lines) and lines[i].startswith((" ", "\t")):
                val += " " + lines[i].strip()
                i += 1
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        out[key] = val
    return out


def first_text_line(text: str) -> str:
    body = re.sub(r"﻿?---.*?---", "", text, count=1, flags=re.S)
    for line in body.splitlines():
        line = line.strip().lstrip("#").strip()
        if line:
            return line
    return ""


def github_parts(url: str) -> tuple[str, str] | None:
    m = re.match(r"https?://github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?/?$", url or "")
    return (m.group(1), m.group(2)) if m else None


# --- Reading plugin internals ---------------------------------------------------------------


class Capped(io.RawIOBase):
    def __init__(self, raw, cap):
        self.raw, self.cap, self.n = raw, cap, 0

    def readable(self):
        return True

    def readinto(self, b):
        data = self.raw.read(len(b))
        self.n += len(data)
        if self.n > self.cap:
            raise IOError("tarball over size cap")
        b[: len(data)] = data
        return len(data)


def components_from_files(files: dict[str, str]) -> tuple[list[dict], dict]:
    """files: relative path -> text. Returns (components, plugin.json dict)."""
    comps, manifest = [], {}
    for rel, text in sorted(files.items()):
        low = rel.lower()
        name = rel.rsplit("/", 1)[-1]
        if low.endswith(".claude-plugin/plugin.json") and low.count("/") == 1:
            try:
                manifest = json.loads(text)
            except ValueError:
                pass
        elif name == "SKILL.md":
            fm = frontmatter(text)
            comps.append({"kind": "skill", "name": fm.get("name") or (rel.split("/")[-2] if "/" in rel else "skill"),
                          "description": clean(fm.get("description") or first_text_line(text), 1200)})
        elif re.search(r"(^|/)agents/[^/]+\.md$", low):
            fm = frontmatter(text)
            comps.append({"kind": "agent", "name": fm.get("name") or name[:-3],
                          "description": clean(fm.get("description") or first_text_line(text), 800)})
        elif re.search(r"(^|/)commands/.+\.md$", low):
            fm = frontmatter(text)
            comps.append({"kind": "command", "name": "/" + name[:-3],
                          "description": clean(fm.get("description") or first_text_line(text), 500)})
        elif re.search(r"(^|/)hooks/hooks\.json$", low):
            try:
                hj = json.loads(text)
                ev = sorted((hj.get("hooks") or {}).keys())
                modules = [str(x).rsplit("/", 1)[-1] for x in hj.get("modules") or []]
            except (ValueError, AttributeError):
                ev, modules = [], []
            if modules:  # a mod: hooks.json names its hooks modules
                comps.append({"kind": "mod", "name": "hooks", "description": "Mod hooks modules: " + ", ".join(modules)})
            else:
                comps.append({"kind": "hook", "name": "hooks", "description": "Hook events: " + (", ".join(ev) or "unknown")})
        elif re.search(r"(^|/)hooks/[^/]+\.(tsx|ts)$", low):
            comps.append({"kind": "mod", "name": name, "description": "Mod module (UI or behaviour change of Claude Code)"})
        elif low == ".mcp.json":
            try:
                servers = sorted((json.loads(text).get("mcpServers") or json.loads(text)).keys())
            except (ValueError, AttributeError):
                servers = []
            comps.append({"kind": "mcp", "name": "mcp", "description": "MCP servers: " + (", ".join(servers) or "unknown")})
    # Keep it bounded: big packs list many skills; the names still help search
    return comps[:120], manifest


WANTED = re.compile(r"(SKILL\.md$|/agents/[^/]+\.md$|/commands/.+\.md$|/hooks/hooks\.json$|/hooks/[^/]+\.tsx?$|\.mcp\.json$|\.claude-plugin/plugin\.json$)", re.I)


def read_tarball(owner: str, repo: str, ref: str) -> dict[str, str]:
    """Stream a GitHub tarball and return wanted text files (path without the top folder)."""
    url = f"https://codeload.github.com/{owner}/{repo}/tar.gz/{ref}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    files: dict[str, str] = {}
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = io.BufferedReader(Capped(r, MAX_TAR_BYTES), 1 << 16)
        with tarfile.open(fileobj=raw, mode="r|gz") as tf:
            for m in tf:
                if not m.isfile() or m.size > MAX_MEMBER_BYTES:
                    continue
                rel = m.name.split("/", 1)[1] if "/" in m.name else m.name
                if not WANTED.search("/" + rel):
                    continue
                f = tf.extractfile(m)
                if f:
                    files[rel] = f.read().decode("utf-8", errors="replace")
    return files


def subtree(files: dict[str, str], prefix: str | None) -> dict[str, str]:
    prefix = (prefix or "").strip("./").strip("/")
    if not prefix:
        return dict(files)
    p = prefix + "/"
    return {k[len(p):]: v for k, v in files.items() if k.startswith(p)}


# --- Remote sources -------------------------------------------------------------------------


def entry(source: str, name: str, description: str, **kw) -> dict:
    e = {"source": source, "name": name, "description": clean(description, 3000)}
    e.update({k: v for k, v in kw.items() if v not in (None, "", [], {})})
    e["id"] = f"{source}/{name}"
    return e


def load_marketplace(src: dict) -> list[dict]:
    repo = src["repo"]
    data = json.loads(fetch(f"https://raw.githubusercontent.com/{repo}/HEAD/.claude-plugin/marketplace.json"))
    mname = data.get("name") or src["id"]
    owner_repo = repo
    out = []
    for p in data.get("plugins", []):
        s = p.get("source")
        author = p.get("author", {}).get("name") if isinstance(p.get("author"), dict) else p.get("author")
        if isinstance(s, str):
            loc = {"repo": f"https://github.com/{owner_repo}", "path": s, "ref": "HEAD", "in_marketplace": True}
            skills = p.get("skills")
        elif isinstance(s, dict):
            loc = {"repo": s.get("url") or (f"https://github.com/{s['repo']}" if s.get("repo") else ""),
                   "path": s.get("path", ""), "ref": s.get("sha") or s.get("ref") or "HEAD"}
            skills = None
        else:
            continue
        repo_owner = (github_parts(loc["repo"]) or ("", ""))[0]
        # Anthropic wrote it: its author is Anthropic, or it lives in an anthropics repository
        # (the community marketplace repo is Anthropic's, but its plugins are not)
        community_local = loc.get("in_marketplace") and src["id"] == "claude-community"
        anthropic = (author or "").strip().lower() == "anthropic" or (repo_owner == "anthropics" and not community_local)
        mark = "anthropic" if anthropic else src.get("mark", "unaudited")
        e = entry(src["id"], p["name"], p.get("description", ""), kind="plugin", mark=mark,
                  author=author, category=p.get("category"), homepage=p.get("homepage"),
                  install=f"claude plugin install {p['name']}@{mname}",
                  marketplace_add=repo, loc=loc)
        if skills:
            e["skill_paths"] = skills
        out.append(e)
    return out


def load_directory(src: dict) -> list[dict]:
    path = Path(os.path.expanduser(src["path"]))
    if not path.exists():
        raise FileNotFoundError(f"{path} not found (Claude Code writes it when the plugin directory is opened)")
    data = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for l in data.get("listings", []):
        repo = (l.get("source") or {}).get("repository") or {}
        review = (((l.get("checks") or {}).get("review") or {}).get("state")) or "none"
        by = (((l.get("checks") or {}).get("review") or {}).get("by") or {}).get("type")
        mark = "reviewed" if review == "done" else "unaudited"
        if github_parts(repo.get("url", "")) and github_parts(repo["url"])[0] == "anthropics":
            mark = "anthropic"
        out.append(entry(src["id"], l["name"], l.get("summary", ""), kind="plugin", mark=mark,
                         review=f"{review}{'/' + by if by else ''}", surfaces=l.get("surfaces"),
                         version=(l.get("release") or {}).get("version"),
                         install="Install from the Claude plugin directory (Claude Code `/plugin` > Discover, or claude.ai > Plugins)",
                         loc={"repo": repo.get("url", ""), "path": repo.get("path", ""), "ref": repo.get("reviewed_commit") or "HEAD"}))
    return out


def load_agenticskills(src: dict) -> list[dict]:
    base = src["url"].rstrip("/")
    page = fetch(base + "/site-map").decode("utf-8", errors="replace")
    links = sorted(set(re.findall(r'href="(/(?:skills|mcp)/[\w.-]+)"', page)))
    log(f"  agenticskills: {len(links)} pages")

    def one(link):
        try:
            t = fetch(base + link).decode("utf-8", errors="replace")
        except Exception as ex:  # noqa: BLE001 - a failed page is skipped, counted below
            return None, f"{link}: {ex}"
        title = html.unescape((re.search(r"<title>(.*?)</title>", t, re.S) or [None, link])[1])
        desc = html.unescape((re.search(r'<meta name="description" content="(.*?)"', t, re.S) or [None, ""])[1])
        name = re.sub(r"\s+[—-]\s+.*$", "", title).strip()
        by = re.search(r"by (.+?) \|", title)
        # A page also lists related skills' commands; take the one for this page's own skill
        slug = link.split("/")[-1].lower()
        cmds = list(dict.fromkeys(re.findall(r"npx skills add ([\w.-]+/[\w.-]+@[\w.:-]+)", t)))
        key = re.sub(r"[^a-z0-9]", "", name.lower())
        own = [c for c in cmds if c.split("@", 1)[1].lower() == slug or re.sub(r"[^a-z0-9]", "", c.split("@", 1)[1].lower()) == key]
        npx = re.match(r"(.*)", own[0]) if own else (re.match(r"(.*)", cmds[0]) if len(cmds) == 1 else None)
        gh = re.findall(r"https://github\.com/([\w.-]+/[\w.-]+)", t)
        kind = "mcp" if link.startswith("/mcp/") else "skill"
        loc = None
        if npx:
            owner_repo, skill = npx.group(1).split("@", 1)
            loc = {"repo": f"https://github.com/{owner_repo}", "path": "", "ref": "HEAD", "skill": skill}
        elif gh:
            loc = {"repo": f"https://github.com/{gh[0]}", "path": "", "ref": "HEAD"}
        e = entry(src["id"], link.split("/")[-1], f"{name}: {desc}", kind=kind, mark="curated",
                  author=by.group(1) if by else None, homepage=base + link,
                  install=(f"npx skills add {npx.group(1)} (sends telemetry unless DISABLE_TELEMETRY=1), or copy its SKILL.md folder into ~/.claude/skills/" if npx else "See the page for setup"),
                  loc=loc)
        return e, None

    out, errors = [], []
    with cf.ThreadPoolExecutor(6) as ex:
        for e, err in ex.map(one, links):
            if e:
                out.append(e)
            if err:
                errors.append(err)
    if errors:
        log(f"  agenticskills: {len(errors)} pages failed, first: {errors[0]}")
    return out


LOADERS = {"marketplace": load_marketplace, "directory": load_directory, "agenticskills": load_agenticskills}


# --- Expansion ------------------------------------------------------------------------------


def expand_group(repo_url: str, ref: str, entries: list[dict]) -> str | None:
    gp = github_parts(repo_url)
    if not gp:
        return "not a GitHub repository"
    files = None
    for attempt in range(3):
        try:
            files = read_tarball(gp[0], gp[1], ref)
            break
        except urllib.error.HTTPError as ex:
            return f"HTTPError {ex.code}"  # missing repo or commit: retrying will not help
        except Exception as ex:  # noqa: BLE001 - network hiccups (DNS, resets) are retried
            err = f"{type(ex).__name__}: {ex}"
            time.sleep(2 + 4 * attempt)
    if files is None:
        return err
    for e in entries:
        loc = e["loc"]
        sub = subtree(files, loc.get("path", ""))
        if e.get("skill_paths"):
            sub = {k: v for k, v in files.items() if any(k.startswith(sp.strip("./").strip("/") + "/") for sp in e["skill_paths"])}
        if loc.get("skill"):
            sk = {k: v for k, v in files.items() if k.endswith("SKILL.md") and (f"/{loc['skill']}/" in "/" + k)}
            sub = sk or sub
        comps, manifest = components_from_files(sub)
        e["components"] = comps
        if manifest.get("description") and len(manifest["description"]) > len(e["description"]):
            e["description"] = clean(manifest["description"], 3000)
        if manifest.get("types") or any(c["kind"] == "mod" for c in comps):
            e["is_mod"] = True
        e["expanded"] = f"{repo_url}@{ref}"
        e["expanded_at"] = int(time.time())
    return None


def expand(entries: list[dict], budget: int) -> dict:
    groups: dict[tuple[str, str], list[dict]] = {}
    for e in entries:
        loc = e.get("loc")
        if not loc or not loc.get("repo"):
            continue
        if e.get("expanded") == f"{loc['repo']}@{loc['ref']}":
            # A pinned commit never changes; a branch head is read again after 28 days
            if loc["ref"] != "HEAD" or time.time() - e.get("expanded_at", 0) < 28 * 86400:
                continue
        groups.setdefault((loc["repo"], loc["ref"]), []).append(e)
    order = sorted(groups.items(), key=lambda kv: (min(x.get("priority", 9) for x in kv[1]), kv[0]))
    # Whole-marketplace repos hold many plugins: always take them, they count once
    todo = order[:budget]
    stats = {"repos_total": len(groups), "repos_done": 0, "repos_failed": 0, "left": max(0, len(groups) - budget)}
    # Four at a time: more parallel downloads made Windows DNS lookups fail in bulk
    with cf.ThreadPoolExecutor(4) as ex:
        futs = {ex.submit(expand_group, r, ref, es): (r, es) for (r, ref), es in todo}
        for i, f in enumerate(cf.as_completed(futs), 1):
            try:
                err = f.result()
            except Exception as exc:  # noqa: BLE001 - one odd repository never stops the run
                err = f"{type(exc).__name__} while reading: {exc}"
            r, es = futs[f]
            if err:
                stats["repos_failed"] += 1
                for e in es:
                    e["expand_error"] = err[:200]
            else:
                stats["repos_done"] += 1
                for e in es:
                    e.pop("expand_error", None)
            if i % 50 == 0:
                log(f"  expanded {i}/{len(todo)} repositories")
    return stats


# --- Embedding text and vectors ---------------------------------------------------------------


def embed_text(e: dict) -> str:
    parts = [f"{e['name']}: {e['description']}"]
    for c in e.get("components", [])[:40]:
        parts.append(f"{c['kind']} {c['name']}: {c['description'][:160]}")
    return " | ".join(parts)[:EMBED_CHARS]


def component_records(e: dict) -> list[dict]:
    """Each skill and agent inside a plugin is searchable on its own, pointing to its parent."""
    out = []
    for c in e.get("components", []):
        if c["kind"] in ("skill", "agent", "command") and len(c["description"]) > 30:
            out.append({"id": f"{e['id']}#{c['kind']}:{c['name']}", "parent": e["id"],
                        "text": f"{c['name']}: {c['description']}"[:EMBED_CHARS]})
    return out


def embedder():
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
    return DefaultEmbeddingFunction()


def embed(ef, texts: list[str]) -> "list":
    import numpy as np
    out = []
    for i in range(0, len(texts), 256):
        out.extend(ef(texts[i : i + 256]))
        if len(texts) > 512 and (i // 256) % 8 == 0:
            log(f"  embedded {min(i + 256, len(texts))}/{len(texts)}")
    return np.asarray(out, dtype="float32")


# --- Index ----------------------------------------------------------------------------------


def index_dir(args) -> Path:
    return Path(args.index) if args.index else SKILL_DIR / "index"


def read_catalog(d: Path) -> list[dict]:
    p = d / "catalog.jsonl.gz"
    if not p.exists():
        return []
    with gzip.open(p, "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def cmd_index(args) -> None:
    import numpy as np

    d = index_dir(args)
    d.mkdir(parents=True, exist_ok=True)
    if not os.access(d, os.W_OK):
        sys.exit(f"Index folder {d} is not writable (plugin install?). Run the index from the skill's source folder.")
    sources = json.loads(Path(args.sources or SKILL_DIR / "sources.json").read_text(encoding="utf-8"))
    old = {e["id"]: e for e in read_catalog(d)}
    entries, status = [], {}
    for src in sources["remote"]:
        t = time.time()
        try:
            got = LOADERS[src["type"]](src)
            for e in got:
                e["priority"] = src.get("priority", 9)
                prev = old.get(e["id"])
                # Keep earlier expansion when the plugin's location did not change
                if prev and prev.get("loc") == e.get("loc") and prev.get("components") is not None:
                    e["components"] = prev["components"]
                    e["expanded"] = prev.get("expanded")
                    e["expanded_at"] = prev.get("expanded_at", 0)
                    if prev.get("is_mod"):
                        e["is_mod"] = True
                    if prev.get("description") and len(prev["description"]) > len(e["description"]):
                        e["description"] = prev["description"]
            entries.extend(got)
            status[src["id"]] = {"ok": True, "entries": len(got), "seconds": round(time.time() - t)}
            log(f"{src['id']}: {len(got)} entries")
        except Exception as ex:  # noqa: BLE001 - keep the previous entries of a failed source
            kept = [e for e in old.values() if e["source"] == src["id"]]
            entries.extend(kept)
            status[src["id"]] = {"ok": False, "error": f"{type(ex).__name__}: {ex}"[:300], "kept_previous": len(kept)}
            log(f"{src['id']}: FAILED ({ex}); kept {len(kept)} previous entries")
    exp = {"skipped": True}
    if not args.skip_expand:
        log(f"Expanding plugin internals (budget {args.budget} repositories)")
        exp = expand(entries, args.budget)
    # Duplicates across sources (same repo and path) stay separate entries but are linked
    seen: dict[str, str] = {}
    for e in entries:
        loc = e.get("loc") or {}
        key = f"{loc.get('repo', '').lower().removesuffix('.git')}|{loc.get('path', '').strip('./')}|{loc.get('skill', '')}"
        if loc.get("repo"):
            if key in seen and seen[key] != e["id"]:
                e["same_as"] = seen[key]
            else:
                seen[key] = e["id"]
    # Vectors: one row per entry and per inner skill/agent/command; reuse unchanged rows
    rows = []
    for e in entries:
        rows.append({"id": e["id"], "parent": e["id"], "text": embed_text(e)})
        rows.extend(component_records(e))
    old_vecs = {}
    if (d / "vectors.npy").exists() and (d / "rows.json").exists():
        ov = np.load(d / "vectors.npy")
        for r, v in zip(json.loads((d / "rows.json").read_text(encoding="utf-8")), ov):
            old_vecs[(r["id"], r["h"])] = v
    for r in rows:
        r["h"] = text_hash(r["text"])
    need = [r for r in rows if (r["id"], r["h"]) not in old_vecs]
    log(f"Embedding {len(need)} new or changed rows of {len(rows)}")
    new = {}
    if need:
        vecs = embed(embedder(), [r["text"] for r in need])
        new = {(r["id"], r["h"]): v for r, v in zip(need, vecs)}
    mat = np.stack([new.get((r["id"], r["h"]), old_vecs.get((r["id"], r["h"]))) for r in rows]).astype("float16")
    np.save(d / "vectors.npy", mat)
    (d / "rows.json").write_text(json.dumps([{"id": r["id"], "parent": r["parent"], "h": r["h"]} for r in rows]), encoding="utf-8")
    with gzip.open(d / "catalog.jsonl.gz", "wt", encoding="utf-8") as f:
        for e in sorted(entries, key=lambda x: x["id"]):
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    expanded = sum(1 for e in entries if e.get("components") is not None)
    meta = {"built": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "model": "chromadb DefaultEmbeddingFunction (all-MiniLM-L6-v2, ONNX)",
            "entries": len(entries), "rows": len(rows), "expanded_entries": expanded,
            "sources": status, "expansion": exp}
    (d / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))


# --- Local sources (scanned live) -------------------------------------------------------------


def read_plugin_dir(root: Path) -> dict[str, str]:
    """The wanted text files of a plugin folder on disk, by path relative to it."""
    files = {}
    for p in root.rglob("*"):
        if not p.is_file() or any(part in ("node_modules", ".git") for part in p.parts):
            continue
        rel = p.relative_to(root).as_posix()
        if WANTED.search("/" + rel) and p.stat().st_size <= MAX_MEMBER_BYTES:
            files[rel] = p.read_text(encoding="utf-8", errors="replace")
    return files


def scan_claude_marketplaces(src: dict, shipped_repos: set[str]) -> list[dict]:
    """Plugins of every marketplace the user added to Claude Code, read from its local clone.
    Marketplaces the shipped index already holds are skipped."""
    known = Path(os.path.expanduser(src["path"]))
    if not known.exists():
        return []
    try:
        markets = json.loads(known.read_text(encoding="utf-8"))
    except ValueError:
        return []
    out = []
    for mname, m in markets.items():
        msrc = m.get("source") or {}
        repo = (msrc.get("repo") or "").lower() or "/".join(github_parts(msrc.get("url", "")) or ()).lower()
        if repo and repo in shipped_repos:
            continue
        root = Path(m.get("installLocation", ""))
        mf = root / ".claude-plugin" / "marketplace.json"
        if not mf.exists():
            continue
        try:
            data = json.loads(mf.read_text(encoding="utf-8"))
        except ValueError:
            continue
        owner = repo.split("/")[0] if repo else ""
        for p in data.get("plugins", []):
            s = p.get("source")
            comps = []
            if isinstance(s, str) and (root / s).is_dir():
                comps, manifest = components_from_files(read_plugin_dir((root / s).resolve()))
            author = p.get("author", {}).get("name") if isinstance(p.get("author"), dict) else p.get("author")
            mark = "anthropic" if owner == "anthropics" or (author or "").strip().lower() == "anthropic" else "unaudited"
            out.append(entry(f"{src['id']}:{mname}", p["name"], p.get("description", ""), kind="plugin", mark=mark,
                             author=author, install=f"claude plugin install {p['name']}@{mname}",
                             path=(root / s).as_posix() if isinstance(s, str) else None, origin="third-party",
                             components=comps, is_mod=any(c["kind"] == "mod" for c in comps) or None))
    return out


# Who a local entry belongs to, which decides whether skill-finder vets it before reuse
ORIGIN_NOTE = {
    "user-folder": "vet before reuse unless the user wrote it or skill-builder's registry lists it; ask when unsure",
    "third-party": "vet before reuse or install; a third-party copy on this computer is not the user's own work",
    "synced": "synced by the Claude app (Anthropic); vet before adapting or copying it",
}


def plugin_root_of(path: Path, stop: Path) -> Path | None:
    """The nearest folder at or above path that holds .claude-plugin/plugin.json, inside stop."""
    for d in [path, *path.parents]:
        if (d / ".claude-plugin" / "plugin.json").is_file():
            return d
        if d == stop:
            break
    return None


def scan_local(sources: dict, cwd: Path) -> list[dict]:
    out, seen_real = [], set()
    shipped_repos = {s["repo"].lower() for s in sources.get("remote", []) if s.get("repo")}
    for src in sources.get("local", []):
        if src["type"] == "claude-marketplaces":
            out.extend(scan_claude_marketplaces(src, shipped_repos))
            continue
        root = Path(os.path.expanduser(src["path"]))
        if not root.is_absolute():
            root = cwd / root
        if not root.exists():
            continue
        origin = "user-folder" if src["type"] == "skills-folder" else "third-party"
        if src["type"] == "plugins-folder":
            # Whole plugins too, so a pack's hooks, MCP servers, and agents are searchable and vetted with it
            for mf in root.rglob(".claude-plugin/plugin.json"):
                proot = mf.parent.parent
                if any(part in ("node_modules", ".git") for part in proot.parts) or str(proot.resolve()).lower() in seen_real:
                    continue
                seen_real.add(str(proot.resolve()).lower())
                try:
                    comps, manifest = components_from_files(read_plugin_dir(proot))
                except OSError:
                    continue
                name = manifest.get("name") or proot.name
                out.append({"id": f"{src['id']}/{name}@{proot.as_posix()}", "source": src["id"], "name": name,
                            "description": clean(manifest.get("description") or "", 3000), "kind": "plugin",
                            "mark": "local", "path": proot.as_posix(), "origin": origin, "components": comps,
                            "is_mod": any(c["kind"] == "mod" for c in comps) or None})
        for p in root.rglob("SKILL.md"):
            if any(part in ("node_modules", ".git", "evals", "_sandbox") for part in p.parts):
                continue
            real = str(p.resolve()).lower()
            if real in seen_real:
                continue
            seen_real.add(real)
            try:
                t = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            fm = frontmatter(t)
            name = fm.get("name") or p.parent.name
            proot = plugin_root_of(p.parent, root)
            out.append({"id": f"{src['id']}/{name}@{p.parent.as_posix()}", "source": src["id"], "name": name,
                        "description": clean(fm.get("description") or first_text_line(t), 3000),
                        "kind": "skill", "mark": "local", "path": p.parent.as_posix(), "components": [],
                        "origin": "synced" if "/skills/synced/" in p.as_posix() else origin,
                        "plugin": proot.as_posix() if proot else None})
    return out


# --- Search ---------------------------------------------------------------------------------


TOKEN = re.compile(r"[a-z0-9]+")
STOP = set("a an the and or of to for in on with by from is are be that this it as at use when you your can".split())


def tokens(s: str) -> list[str]:
    return [t for t in TOKEN.findall(s.lower()) if t not in STOP]


class BM25:
    def __init__(self, docs: list[list[str]], k1=1.4, b=0.75):
        self.k1, self.b, self.docs = k1, b, docs
        self.avg = sum(map(len, docs)) / max(1, len(docs))
        df: dict[str, int] = {}
        for d in docs:
            for t in set(d):
                df[t] = df.get(t, 0) + 1
        n = len(docs)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
        self.tf = [{} for _ in docs]
        for i, d in enumerate(docs):
            for t in d:
                self.tf[i][t] = self.tf[i].get(t, 0) + 1

    def top(self, q: list[str], k: int) -> list[int]:
        scores = []
        for i, tf in enumerate(self.tf):
            s, L = 0.0, len(self.docs[i])
            for t in q:
                if t in tf:
                    f = tf[t]
                    s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * L / self.avg))
            if s:
                scores.append((s, i))
        return [i for _, i in sorted(scores, reverse=True)[:k]]


def load_index(args) -> tuple[list[dict], list[dict], "object", dict]:
    import numpy as np

    d = index_dir(args)
    if not (d / "meta.json").exists():
        sys.exit(f"No index in {d}. Run 'finder.py index' first (skill-audit does this weekly).")
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    entries = read_catalog(d)
    rows = json.loads((d / "rows.json").read_text(encoding="utf-8"))
    vecs = np.load(d / "vectors.npy").astype("float32")
    return entries, rows, vecs, meta


def cmd_search(args) -> None:
    import numpy as np
    import chromadb

    entries, rows, vecs, meta = load_index(args)
    sources = json.loads(Path(args.sources or SKILL_DIR / "sources.json").read_text(encoding="utf-8"))
    by_id = {e["id"]: e for e in entries}
    ef = embedder()
    if not args.no_local:
        local = scan_local(sources, Path(args.cwd or os.getcwd()))
        if local:
            lv = embed(ef, [embed_text(e) for e in local])
            entries += local
            for e in local:
                by_id[e["id"]] = e
            rows = rows + [{"id": e["id"], "parent": e["id"]} for e in local]
            vecs = np.vstack([vecs, lv])
    client = chromadb.EphemeralClient()
    col = client.create_collection("skills", metadata={"hnsw:space": "cosine"}, embedding_function=None)
    for i in range(0, len(rows), 5000):
        col.add(ids=[f"{k}" for k in range(i, min(i + 5000, len(rows)))], embeddings=vecs[i : i + 5000].tolist())
    texts = []
    for r in rows:
        e = by_id[r["parent"]]
        if r["id"] == r["parent"]:
            texts.append(tokens(embed_text(e)))
        else:
            cname = r["id"].split("#", 1)[1].split(":", 1)[1]
            c = next((c for c in e.get("components", []) if c["name"] == cname), None)
            texts.append(tokens(f"{cname} {c['description'] if c else ''}"))
    bm = BM25(texts)
    k = 60
    fused: dict[str, float] = {}
    hits: dict[str, set] = {}
    best_comp: dict[str, set] = {}
    for q in args.queries:
        qv = ef([q])
        res = col.query(query_embeddings=[list(map(float, qv[0]))], n_results=min(k, len(rows)))
        vec_rank = [int(x) for x in res["ids"][0]]
        kw_rank = bm.top(tokens(q), k)
        for method, ranking in (("vector", vec_rank), ("keyword", kw_rank)):
            # A plugin counts once per query and method, at its best-ranked row, so a pack
            # with many inner skills does not outrank a precise single skill by volume
            counted = set()
            for rank, ri in enumerate(ranking):
                r = rows[ri]
                pid = r["parent"]
                if r["id"] != pid:
                    best_comp.setdefault(pid, set()).add(r["id"].split("#", 1)[1])
                if pid in counted:
                    continue
                counted.add(pid)
                fused[pid] = fused.get(pid, 0) + 1 / (60 + rank)
                hits.setdefault(pid, set()).add(method)
    # Collapse duplicates of the same plugin across sources onto the first-seen id
    order = sorted(fused, key=lambda x: -fused[x])
    shown, out = set(), []
    for pid in order:
        e = by_id[pid]
        canon = e.get("same_as") or pid
        if canon in shown:
            continue
        shown.add(canon)
        out.append(pid)
        if len(out) >= args.top:
            break
    age = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(meta["built"])).days
    print(f"# Shortlist ({len(out)} of {len(entries)} entries; index built {meta['built'][:10]}, {age} days old; "
          f"queries: {len(args.queries)})\n")
    failed = [s for s, v in meta["sources"].items() if not v.get("ok")]
    if failed:
        print(f"Sources that failed at index time: {', '.join(failed)}\n")
    for n, pid in enumerate(out, 1):
        e = by_id[pid]
        dup = [x["id"] for x in entries if x.get("same_as") == pid] + ([e["same_as"]] if e.get("same_as") else [])
        print(f"## {n}. {e['name']}  [{e.get('kind', '?')}{', mod' if e.get('is_mod') else ''}] mark: {e.get('mark', '?')}")
        print(f"- id: `{pid}`; found by: {', '.join(sorted(hits[pid]))}; score {fused[pid]:.3f}")
        if dup:
            print(f"- also listed as: {', '.join('`' + x + '`' for x in dup)}")
        for key in ("author", "review", "homepage", "path", "install"):
            if e.get(key):
                print(f"- {key}: {e[key]}")
        if e.get("plugin"):
            print(f"- part of plugin: {e['plugin']} (installing the plugin installs all of it, so vet the whole plugin)")
        if e.get("origin"):
            print(f"- vetting: {ORIGIN_NOTE[e['origin']]}")
        if e.get("loc") and e["loc"].get("repo"):
            print(f"- source: {e['loc']['repo']} {e['loc'].get('path', '')} @ {e['loc'].get('ref', '')}")
        print(f"- description: {e['description']}")
        comps = e.get("components")
        if comps is None:
            print("- internals: not read yet (run `finder.py expand " + pid + "`)" if e.get("loc") else "- internals: none")
        elif comps:
            matched = best_comp.get(pid, set())
            # A pack can list the same component more than once (copies in several folders); show each once
            comps = list({(c["kind"], c["name"], c["description"]): c for c in comps}.values())
            ordered = sorted(comps, key=lambda c: (f"{c['kind']}:{c['name']}" not in matched, c["kind"]))
            print(f"- internals ({len(comps)}):")
            for c in ordered[:12]:
                star = " (matched)" if f"{c['kind']}:{c['name']}" in matched else ""
                print(f"  - {c['kind']} `{c['name']}`{star}: {c['description'][:300]}")
            if len(comps) > 12:
                print(f"  - ... {len(comps) - 12} more")
        if e.get("expand_error"):
            print(f"- internals could not be read: {e['expand_error']}")
        print()


def cmd_expand(args) -> None:
    entries, *_ = load_index(args)
    by_id = {e["id"]: e for e in entries}
    picked = [by_id[i] for i in args.ids if i in by_id]
    for i in args.ids:
        if i not in by_id:
            print(f"unknown id: {i}")
    for e in picked:
        e.pop("expanded", None)
    expand(picked, budget=len(picked))
    for e in picked:
        print(f"## {e['name']} (`{e['id']}`)")
        if e.get("expand_error"):
            print(f"- could not read: {e['expand_error']}")
        for c in e.get("components", []):
            print(f"- {c['kind']} `{c['name']}`: {c['description']}")
        print()


def cmd_dump(args) -> None:
    entries, *_ = load_index(args)
    k, n = map(int, args.shard.split("/"))
    for i, e in enumerate(sorted(entries, key=lambda x: x["id"])):
        if i % n != k - 1:
            continue
        comps = "; ".join(f"{c['kind']} {c['name']}: {c['description'][:120]}" for c in e.get("components", [])[:15])
        print(f"{e['id']} [{e.get('mark')}] :: {e['description'][:500]}" + (f" || {comps}" if comps else ""))


def cmd_stats(args) -> None:
    entries, rows, _, meta = load_index(args)
    age = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(meta["built"])).days
    print(json.dumps({"built": meta["built"], "age_days": age, "entries": len(entries), "rows": len(rows),
                      "expanded": sum(1 for e in entries if e.get("components") is not None),
                      "sources": meta["sources"], "expansion": meta.get("expansion")}, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser(description="skill-finder index and search")
    ap.add_argument("--index", help="index folder (default: the skill's index/)")
    ap.add_argument("--sources", help="sources.json (default: the skill's own)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("index")
    p.add_argument("--budget", type=int, default=300)
    p.add_argument("--skip-expand", action="store_true")
    p = sub.add_parser("search")
    p.add_argument("queries", nargs="+")
    p.add_argument("--top", type=int, default=60)
    p.add_argument("--cwd")
    p.add_argument("--no-local", action="store_true")
    p = sub.add_parser("expand")
    p.add_argument("ids", nargs="+")
    p = sub.add_parser("dump")
    p.add_argument("--shard", default="1/1")
    sub.add_parser("stats")
    args = ap.parse_args()
    {"index": cmd_index, "search": cmd_search, "expand": cmd_expand, "dump": cmd_dump, "stats": cmd_stats}[args.cmd](args)


if __name__ == "__main__":
    main()
