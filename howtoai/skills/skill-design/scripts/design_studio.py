"""skill-design design studio: a local web app and SQLite store for named designs.

  py -3 design_studio.py serve [--port N] [--open] [--db PATH]
  py -3 design_studio.py url | stop
  py -3 design_studio.py list | show <slug>
  py -3 design_studio.py export <slug> --format design-md|tailwind|css|tokens|profile [--extended] [--out FILE]
  py -3 design_studio.py set-default <slug>
  py -3 design_studio.py import <file> [--name NAME] [--kind client|reference] [--client NAME]
  py -3 design_studio.py delete <slug> --confirm <slug>
  py -3 design_studio.py apply-house <slug>

Every command also takes `--db PATH` (default `~/.claude/howtoai/designs.db`, or env HOWTOAI_DESIGN_DB),
`--runtime PATH` (default `~/.claude/howtoai/design-studio.json`, or env HOWTOAI_DESIGN_RUNTIME), and
`--root PATH` (the skill folder; default this skill, used for the page, the seed, and `apply-house`).

`serve` binds 127.0.0.1 only (port 47615, or a free port when that one is taken or reserved), serves the one
page `references/design-reference.html` at `/` and a JSON API under `/api/`, and refuses requests whose Host
is not 127.0.0.1:<port> or localhost:<port>, and non-GET requests from another Origin. Every saved design spec
passes the same schema and contrast checks as `tokens.py apply` (imported from tokens.py). `apply-house`
writes a design to the shipped house files through `tokens.py apply`: only on the user's explicit request.

The database is at schema version 2 (`PRAGMA user_version`): version 2 adds each design's reference content
(`designs.reference`) and keeps reference and palette labels in `design_versions`. An older database is
upgraded in place, in one transaction, the first time any command opens it.

Standard library only.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import html as htmllib
import http.client
import json
import os
import re
import secrets
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tokens as T  # noqa: E402  (the skill's own tokens tool: validation, contrast, resolve)

SKILL = HERE.parent
APP = "howtoai-design-studio"
DEFAULT_PORT = 47615
HOME_DIR = Path.home() / ".claude" / "howtoai"
DEFAULT_DB = HOME_DIR / "designs.db"
DEFAULT_RUNTIME = HOME_DIR / "design-studio.json"
REFERO_URL = "https://styles.refero.design/style/c556ab50-a242-4854-9395-450c0004bac5"
HOUSE_SLUG = "howtoai-house"
HOUSE_NAME = "HowToAI house"
KINDS = ("house", "client", "reference")
FORMATS = ("design-md", "tailwind", "css", "tokens", "profile")
SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,78}[a-z0-9])?$")
MAX_BODY = 1_000_000
KEY_SWATCHES = ["bg", "fg", "accent", "feature-bg", "link"]
GROUP_KEYS = {"palette": None, "type": ["fonts_url"] + T.FONTS + T.TYPE_EXTRA,
              "shape": T.RADIUS + T.BORDER + ["shadow"], "density": T.SPACE + T.SIZES}
HOUSE_META_RE = re.compile(r'<script type="application/json" id="house-meta">(.*?)</script>', re.S)

# Version 1, the first schema: kept as it was, so an older database is upgraded step by step in place.
SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS designs (
  id INTEGER PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL UNIQUE,
  tagline TEXT NOT NULL DEFAULT '',
  description TEXT NOT NULL DEFAULT '',
  kind TEXT NOT NULL CHECK (kind IN ('house','client','reference')),
  client TEXT NOT NULL DEFAULT '',
  project_path TEXT NOT NULL DEFAULT '',
  source_url TEXT NOT NULL DEFAULT '',
  is_default INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0,1)),
  version INTEGER NOT NULL DEFAULT 1,
  spec TEXT NOT NULL,
  guidelines TEXT NOT NULL DEFAULT '{"do":[],"dont":[]}',
  palette_meta TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS one_default ON designs(is_default) WHERE is_default = 1;
CREATE TABLE IF NOT EXISTS design_versions (
  design_id INTEGER NOT NULL REFERENCES designs(id) ON DELETE CASCADE,
  version INTEGER NOT NULL,
  spec TEXT NOT NULL,
  guidelines TEXT NOT NULL,
  saved_at TEXT NOT NULL,
  PRIMARY KEY (design_id, version)
);
"""
# Version 2: per-design reference content (principles, voice, component notes, guidance per surface, and the
# type scale's line height, tracking, and weight) in designs.reference; design_versions keeps reference and
# palette_meta too. Rows saved before version 2 hold NULL there: restoring one keeps the current value.
MIGRATION_V2 = [
    "ALTER TABLE designs ADD COLUMN reference TEXT NOT NULL DEFAULT '{}'",
    "ALTER TABLE design_versions ADD COLUMN reference TEXT",
    "ALTER TABLE design_versions ADD COLUMN palette_meta TEXT",
]
SCHEMA_VERSION = 2
REF_TEXT_MAX = 2000
COMPONENT_KEYS = ["button", "card", "table", "badge", "form", "chart", "callout"]
STEP_FIELDS = ("leading", "tracking", "weight")


class StudioError(Exception):
    def __init__(self, status: int, message: str, problems=None):
        super().__init__(message)
        self.status, self.message, self.problems = status, message, list(problems or [])


def now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60].strip("-")
    return s or "design"


def paths_for(root: Path) -> dict:
    return T.paths_for(root)


def house_doc(root: Path) -> dict:
    return json.loads(paths_for(root)["json"].read_text(encoding="utf-8"))


def house_meta(root: Path) -> dict:
    """Tagline, description, guidelines, and palette labels of the house design, from the page's house-meta JSON."""
    try:
        m = HOUSE_META_RE.search(paths_for(root)["ref"].read_text(encoding="utf-8"))
        meta = json.loads(m.group(1)) if m else {}
    except (OSError, ValueError):
        meta = {}
    return {"tagline": meta.get("tagline", "warm workshop with orange sparks"),
            "description": meta.get("description", ""),
            "guidelines": meta.get("guidelines", {"do": [], "dont": []}),
            "palette_meta": meta.get("palette_meta", {}),
            "reference": meta.get("reference", {})}


def house_reference(root: Path) -> dict:
    """The house design's reference content (the text of the former fixed reference view), cleaned."""
    try:
        return clean_reference(house_meta(root)["reference"])
    except StudioError:
        return clean_reference({})


# ---------------------------------------------------------------- validation

def clean_text(data: dict, key: str, limit: int, default: str = "") -> str:
    v = data.get(key, default)
    if v is None:
        v = ""
    if not isinstance(v, str):
        raise StudioError(400, f"{key} must be text")
    v = v.strip()
    if len(v) > limit:
        raise StudioError(400, f"{key} is longer than {limit} characters")
    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", v):
        raise StudioError(400, f"{key} contains control characters")
    return v


def clean_guidelines(g) -> dict:
    if g is None:
        return {"do": [], "dont": []}
    if not isinstance(g, dict):
        raise StudioError(400, "guidelines must be an object with do and dont lists")
    out = {}
    for k in ("do", "dont"):
        lst = g.get(k, [])
        if not isinstance(lst, list) or len(lst) > 40 or not all(isinstance(x, str) and len(x) <= 400 for x in lst):
            raise StudioError(400, f"guidelines.{k} must be a list of at most 40 lines of up to 400 characters")
        out[k] = [x.strip() for x in lst if x.strip()]
    return out


def clean_palette_meta(pm) -> dict:
    if pm is None:
        return {}
    if not isinstance(pm, dict):
        raise StudioError(400, "palette_meta must be an object")
    out = {}
    for k, v in pm.items():
        if k not in T.COLORS or not isinstance(v, dict):
            raise StudioError(400, f"palette_meta: unknown color token {k!r}")
        item = {f: clean_text(v, f, 120) for f in ("label", "role")}
        if v.get("hidden"):  # the swatch is left out of the palette; every token keeps its value
            item["hidden"] = True
        if item["label"] or item["role"] or item.get("hidden"):
            out[k] = item
    return out


def _ref_text(obj, key, where, limit=REF_TEXT_MAX):
    try:
        return clean_text(obj, key, limit)
    except StudioError as e:
        raise StudioError(400, f"reference.{where}: {e.message}")


def _ref_list(v, where, limit=20):
    if v is None:
        return []
    if not isinstance(v, list) or len(v) > limit:
        raise StudioError(400, f"reference.{where} must be a list of at most {limit} items")
    return v


STEP_RE = {"leading": re.compile(r"^(normal|\d*\.?\d+(px|rem|em|%)?)$"),
           "tracking": re.compile(r"^(normal|0|-?\d*\.?\d+(em|px|rem))$"),
           "weight": re.compile(r"^[1-9]00$")}


def clean_reference(r) -> dict:
    """Per-design reference content: principles, voice, component notes, guidance per surface, type scale details.
    Text is plain (a `backtick` span is shown as code); every field is checked for type, length, and control characters."""
    if r is None:
        r = {}
    if not isinstance(r, dict):
        raise StudioError(400, "reference must be an object")
    out = {"principles": [], "voice": {}, "components": {}, "surfaces_intro": "", "surfaces": [], "type_scale": {}}
    for i, p in enumerate(_ref_list(r.get("principles"), "principles")):
        if not isinstance(p, dict):
            raise StudioError(400, "reference.principles items must be objects with title and text")
        item = {"title": _ref_text(p, "title", f"principles[{i}].title", 120), "text": _ref_text(p, "text", f"principles[{i}].text")}
        if item["title"] or item["text"]:
            out["principles"].append(item)
    v = r.get("voice") or {}
    if not isinstance(v, dict):
        raise StudioError(400, "reference.voice must be an object with text, write, and avoid")
    out["voice"] = {k: _ref_text(v, k, f"voice.{k}") for k in ("text", "write", "avoid")}
    c = r.get("components") or {}
    if not isinstance(c, dict) or any(k not in COMPONENT_KEYS for k in c):
        raise StudioError(400, "reference.components must map " + ", ".join(COMPONENT_KEYS) + " to text")
    out["components"] = {k: _ref_text(c, k, f"components.{k}") for k in COMPONENT_KEYS}
    out["surfaces_intro"] = _ref_text(r, "surfaces_intro", "surfaces_intro")
    for i, s in enumerate(_ref_list(r.get("surfaces"), "surfaces")):
        if not isinstance(s, dict):
            raise StudioError(400, "reference.surfaces items must be objects with title and items")
        items = [_ref_text({"x": x}, "x", f"surfaces[{i}].items", 600) if isinstance(x, str) else None
                 for x in _ref_list(s.get("items"), f"surfaces[{i}].items")]
        if None in items:
            raise StudioError(400, f"reference.surfaces[{i}].items must be text")
        item = {"title": _ref_text(s, "title", f"surfaces[{i}].title", 120), "items": [x for x in items if x]}
        if item["title"] or item["items"]:
            out["surfaces"].append(item)
    ts = r.get("type_scale") or {}
    if not isinstance(ts, dict) or any(k not in T.SIZES for k in ts):
        raise StudioError(400, "reference.type_scale must map text-* size tokens to leading, tracking, and weight")
    for k in T.SIZES:  # every step is present, so an untouched step never reads as a change
        step = ts.get(k) or {}
        if not isinstance(step, dict):
            raise StudioError(400, f"reference.type_scale.{k} must be an object")
        o = {}
        for f in STEP_FIELDS:
            val = _ref_text(step, f, f"type_scale.{k}.{f}", 20)
            if val and not STEP_RE[f].match(val):
                raise StudioError(400, f"reference.type_scale.{k}.{f}: {val!r} is not a valid "
                                  + {"leading": "line height (1.2, 24px)", "tracking": "letter spacing (-0.02em, 0)",
                                     "weight": "font weight (100 to 900)"}[f])
            if val:
                o[f] = val
        out["type_scale"][k] = o
    return out


def normalize_spec(spec, version: int) -> dict:
    """Set version and date, re-resolve tokens from the choices, and run tokens.py's checks. Raises on FAIL."""
    if not isinstance(spec, dict):
        raise StudioError(400, "spec must be a JSON object in the design-tokens.json schema")
    spec = json.loads(json.dumps(spec))
    spec["version"] = int(version)
    spec["date"] = dt.date.today().isoformat()
    try:
        spec["tokens"] = T.resolve(spec)
    except (KeyError, TypeError, AttributeError):
        pass  # validate() reports what is missing
    rep = T.validate(spec)
    fails = T.failures(rep)
    if fails:
        contrast = [f for f in fails if f.startswith("contrast")]
        raise StudioError(422, ("Contrast check failed: " if contrast else "The design does not pass the tokens checks: ")
                          + (contrast or fails)[0], fails)
    return spec


def spec_core(spec) -> str:
    """A spec without its version and date and with tokens re-resolved: equal cores mean no real change."""
    if not isinstance(spec, dict):
        return canon(spec)
    s = {k: v for k, v in spec.items() if k not in ("version", "date")}
    try:
        s["tokens"] = T.resolve(spec)
    except (KeyError, TypeError, AttributeError):
        pass
    return canon(s)


# ---------------------------------------------------------------- store

class Store:
    def __init__(self, db: Path, root: Path = SKILL):
        self.db, self.root = Path(db), Path(root)
        self.lock = threading.RLock()

    @contextlib.contextmanager
    def connect(self):
        """One connection per operation: commits on success, rolls back on error, always closes."""
        c = sqlite3.connect(str(self.db), timeout=10)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        try:
            yield c
            c.commit()
        except BaseException:
            c.rollback()
            raise
        finally:
            c.close()

    def init(self):
        self.db.parent.mkdir(parents=True, exist_ok=True)
        with self.lock, self.connect() as c:
            c.execute("PRAGMA journal_mode = WAL")
            self._migrate(c)
            if c.execute("SELECT COUNT(*) FROM designs").fetchone()[0] == 0:
                self._seed(c)
        return self

    def _migrate(self, c):
        """Bring the database up to SCHEMA_VERSION in place, one step per version, each step in one transaction."""
        if c.execute("PRAGMA user_version").fetchone()[0] < 1:
            c.executescript(SCHEMA_V1)
            c.execute("PRAGMA user_version = 1")
            c.commit()
        if c.execute("PRAGMA user_version").fetchone()[0] < 2:
            c.execute("BEGIN IMMEDIATE")
            try:
                if c.execute("PRAGMA user_version").fetchone()[0] < 2:  # another process may have migrated meanwhile
                    cols = {r[1] for r in c.execute("PRAGMA table_info(designs)")}
                    vcols = {r[1] for r in c.execute("PRAGMA table_info(design_versions)")}
                    for sql in MIGRATION_V2:
                        col, table = sql.split(" ADD COLUMN ")[1].split()[0], sql.split()[2]
                        if col not in (cols if table == "designs" else vcols):
                            c.execute(sql)
                    # Every existing design starts from the house reference content, its own copy to edit.
                    c.execute("UPDATE designs SET reference = ? WHERE reference = '{}' OR reference = ''",
                              (canon(house_reference(self.root)),))
                    c.execute("PRAGMA user_version = 2")
                c.commit()
            except BaseException:
                c.rollback()
                raise

    def _seed(self, c):
        doc = house_doc(self.root)
        meta = house_meta(self.root)
        t = now()
        c.execute("INSERT INTO designs (slug, name, tagline, description, kind, client, project_path, source_url, is_default,"
                  " version, spec, guidelines, palette_meta, reference, created_at, updated_at)"
                  " VALUES (?, ?, ?, ?, 'house', '', '', ?, 1, 1, ?, ?, ?, ?, ?, ?)",
                  (HOUSE_SLUG, HOUSE_NAME, meta["tagline"], meta["description"], REFERO_URL,
                   canon(doc), canon(clean_guidelines(meta["guidelines"])), canon(clean_palette_meta(meta["palette_meta"])),
                   canon(house_reference(self.root)), t, t))

    # -- reads

    @staticmethod
    def _row(r, full=True) -> dict:
        d = dict(r)
        spec = json.loads(d.pop("spec"))
        d["is_default"] = bool(d["is_default"])
        if full:
            d["spec"] = spec
            d["guidelines"] = json.loads(d["guidelines"])
            d["palette_meta"] = json.loads(d["palette_meta"])
            d["reference"] = clean_reference(json.loads(d.get("reference") or "{}"))
        else:
            for k in ("guidelines", "palette_meta", "reference", "description", "project_path", "source_url", "created_at"):
                d.pop(k, None)
            tok = spec.get("tokens", {})
            d["swatches"] = [{"token": k, "light": tok.get("light", {}).get(k), "dark": tok.get("dark", {}).get(k)}
                             for k in KEY_SWATCHES]
        d.pop("id", None)
        return d

    def _get(self, c, slug):
        r = c.execute("SELECT * FROM designs WHERE slug = ?", (slug,)).fetchone()
        if r is None:
            raise StudioError(404, f"No design with the slug {slug!r}")
        return r

    def count(self) -> int:
        with self.connect() as c:
            return c.execute("SELECT COUNT(*) FROM designs").fetchone()[0]

    def list(self) -> list:
        with self.connect() as c:
            rows = c.execute("SELECT * FROM designs ORDER BY is_default DESC, kind = 'house' DESC, name COLLATE NOCASE").fetchall()
            return [self._row(r, full=False) for r in rows]

    def get(self, slug) -> dict:
        with self.connect() as c:
            return self._row(self._get(c, slug))

    def default(self) -> dict:
        with self.connect() as c:
            return self._row(c.execute("SELECT * FROM designs WHERE is_default = 1").fetchone())

    def versions(self, slug) -> list:
        with self.connect() as c:
            r = self._get(c, slug)
            old = c.execute("SELECT version, saved_at FROM design_versions WHERE design_id = ? ORDER BY version DESC",
                            (r["id"],)).fetchall()
            return [{"version": r["version"], "saved_at": r["updated_at"], "current": True}] + \
                   [{"version": o["version"], "saved_at": o["saved_at"], "current": False} for o in old]

    # -- writes

    def _fields(self, data: dict, base: dict) -> dict:
        f = {}
        f["name"] = clean_text(data, "name", 80, base.get("name", ""))
        if not f["name"]:
            raise StudioError(400, "Give the design a name")
        f["tagline"] = clean_text(data, "tagline", 200, base.get("tagline", ""))
        f["description"] = clean_text(data, "description", 4000, base.get("description", ""))
        f["kind"] = clean_text(data, "kind", 20, base.get("kind", "client"))
        if f["kind"] not in KINDS:
            raise StudioError(400, "kind must be house, client, or reference")
        f["client"] = clean_text(data, "client", 120, base.get("client", ""))
        if f["kind"] == "client" and not f["client"]:
            f["client"] = f["name"]
        f["project_path"] = clean_text(data, "project_path", 500, base.get("project_path", ""))
        f["source_url"] = clean_text(data, "source_url", 500, base.get("source_url", ""))
        if f["source_url"] and not re.match(r"https?://[^\s<>\"']+$", f["source_url"]):
            raise StudioError(400, "source_url must be an http or https link")
        f["guidelines"] = clean_guidelines(data.get("guidelines", base.get("guidelines")))
        f["palette_meta"] = clean_palette_meta(data.get("palette_meta", base.get("palette_meta")))
        f["reference"] = clean_reference(data.get("reference", base.get("reference")))
        return f

    def _unique_slug(self, c, name):
        base = slugify(name)
        slug, n = base, 2
        while c.execute("SELECT 1 FROM designs WHERE slug = ?", (slug,)).fetchone():
            slug, n = f"{base}-{n}", n + 1
        return slug

    def _check_name(self, c, name, slug=None):
        r = c.execute("SELECT slug FROM designs WHERE name = ? COLLATE NOCASE", (name,)).fetchone()
        if r and r["slug"] != slug:
            raise StudioError(409, f"A design named {name!r} already exists")

    def create(self, data: dict) -> dict:
        if not isinstance(data, dict):
            raise StudioError(400, "Send a JSON object")
        with self.lock, self.connect() as c:
            if data.get("from"):
                src = self._row(self._get(c, str(data["from"])))
                base = {**src, "kind": "reference" if src["kind"] == "house" else src["kind"]}
                merged = {**base, **{k: v for k, v in data.items() if k not in ("from", "spec")}}
                if not str(data.get("name") or "").strip():
                    name, n = f"{src['name']} copy", 2
                    while c.execute("SELECT 1 FROM designs WHERE name = ? COLLATE NOCASE", (name,)).fetchone():
                        name, n = f"{src['name']} copy {n}", n + 1
                    merged["name"] = name
                spec = data.get("spec", src["spec"])
                f = self._fields(merged, base)
            else:
                default = self._row(c.execute("SELECT * FROM designs WHERE is_default = 1").fetchone())
                f = self._fields(data, {"kind": "client", "reference": default["reference"]})
                spec = data.get("spec")
                if spec is None:
                    spec = default["spec"]
            if f["kind"] == "house":
                raise StudioError(400, "There is only one house design; choose client or reference")
            self._check_name(c, f["name"])
            spec = normalize_spec(spec, 1)
            slug = self._unique_slug(c, f["name"])
            t = now()
            c.execute("INSERT INTO designs (slug, name, tagline, description, kind, client, project_path, source_url, is_default,"
                      " version, spec, guidelines, palette_meta, reference, created_at, updated_at)"
                      " VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 1, ?, ?, ?, ?, ?, ?)",
                      (slug, f["name"], f["tagline"], f["description"], f["kind"], f["client"], f["project_path"],
                       f["source_url"], canon(spec), canon(f["guidelines"]), canon(f["palette_meta"]), canon(f["reference"]), t, t))
            return self._row(self._get(c, slug))

    def update(self, slug: str, data: dict, _restore_from=None) -> dict:
        if not isinstance(data, dict):
            raise StudioError(400, "Send a JSON object")
        with self.lock, self.connect() as c:
            r = self._get(c, slug)
            cur = self._row(r)
            f = self._fields(data, cur)
            if cur["kind"] == "house":
                f["kind"] = "house"
            elif f["kind"] == "house":
                raise StudioError(400, "There is only one house design; choose client or reference")
            self._check_name(c, f["name"], slug)
            spec_in = data.get("spec", cur["spec"])
            spec_changed = spec_core(spec_in) != spec_core(cur["spec"])
            changed = (spec_changed or canon(f["guidelines"]) != canon(cur["guidelines"])
                       or canon(f["reference"]) != canon(cur["reference"]) or canon(f["palette_meta"]) != canon(cur["palette_meta"]))
            version = cur["version"] + 1 if changed else cur["version"]
            if spec_changed:
                spec = normalize_spec(spec_in, version)
            elif changed:  # same tokens, new version number: stamp it on the spec too
                spec = {**cur["spec"], "version": version, "date": dt.date.today().isoformat()}
            else:
                spec = cur["spec"]
            t = now()
            if changed:
                c.execute("INSERT OR REPLACE INTO design_versions (design_id, version, spec, guidelines, reference, palette_meta, saved_at)"
                          " VALUES (?, ?, ?, ?, ?, ?, ?)",
                          (r["id"], cur["version"], canon(cur["spec"]), canon(cur["guidelines"]), canon(cur["reference"]),
                           canon(cur["palette_meta"]), cur["updated_at"]))
            c.execute("UPDATE designs SET name = ?, tagline = ?, description = ?, kind = ?, client = ?, project_path = ?,"
                      " source_url = ?, version = ?, spec = ?, guidelines = ?, palette_meta = ?, reference = ?, updated_at = ? WHERE id = ?",
                      (f["name"], f["tagline"], f["description"], f["kind"], f["client"], f["project_path"], f["source_url"],
                       version, canon(spec), canon(f["guidelines"]), canon(f["palette_meta"]), canon(f["reference"]), t, r["id"]))
            return self._row(self._get(c, slug))

    def restore(self, slug: str, version: int) -> dict:
        with self.lock:
            with self.connect() as c:
                r = self._get(c, slug)
                old = c.execute("SELECT spec, guidelines, reference, palette_meta FROM design_versions WHERE design_id = ? AND version = ?",
                                (r["id"], int(version))).fetchone()
                if old is None:
                    raise StudioError(404, f"{slug} has no saved version {version}")
            data = {"spec": json.loads(old["spec"]), "guidelines": json.loads(old["guidelines"])}
            for k in ("reference", "palette_meta"):  # NULL: saved before schema version 2, so keep the current value
                if old[k] is not None:
                    data[k] = json.loads(old[k])
            return self.update(slug, data)

    def version_detail(self, slug: str, version: int) -> dict:
        """One saved version's spec, guidelines, reference, and palette labels (None where not recorded)."""
        with self.connect() as c:
            r = self._get(c, slug)
            if int(version) == r["version"]:
                d = self._row(r)
                return {"version": d["version"], "spec": d["spec"], "guidelines": d["guidelines"],
                        "reference": d["reference"], "palette_meta": d["palette_meta"], "current": True}
            old = c.execute("SELECT * FROM design_versions WHERE design_id = ? AND version = ?", (r["id"], int(version))).fetchone()
            if old is None:
                raise StudioError(404, f"{slug} has no saved version {version}")
            return {"version": old["version"], "spec": json.loads(old["spec"]), "guidelines": json.loads(old["guidelines"]),
                    "reference": json.loads(old["reference"]) if old["reference"] is not None else None,
                    "palette_meta": json.loads(old["palette_meta"]) if old["palette_meta"] is not None else None, "current": False}

    def preview(self, data: dict) -> dict:
        """An unsaved design for the live code tabs: the saved row (or the default for a new design) with the
        edited fields over it and tokens resolved from the choices. Nothing is checked for contrast or written."""
        if not isinstance(data, dict):
            raise StudioError(400, "Send a JSON object")
        slug = str(data.get("slug") or "")
        try:
            base = self.get(slug) if slug else None
        except StudioError:
            base = None
        if base is None:
            base = {**self.default(), "slug": slugify(str(data.get("name") or "")) if data.get("name") else "new-design",
                    "version": 1, "is_default": False, "kind": "client"}
        f = self._fields({**data, "name": str(data.get("name") or "").strip() or base["name"] or "Untitled design"}, base)
        spec = data.get("spec", base["spec"])
        try:
            spec = json.loads(json.dumps(spec))
            spec["tokens"] = T.resolve(spec)
            for g in T.TOKEN_GROUPS:
                for k in T.TOKEN_GROUPS[g]:
                    spec["tokens"][g][k]  # noqa: B018  (every token must be there for the exporters)
        except (KeyError, TypeError, AttributeError, ValueError):
            raise StudioError(422, "The design is incomplete: a preset or token is missing")
        return {**base, **f, "spec": spec}

    def set_default(self, slug: str) -> dict:
        with self.lock, self.connect() as c:
            r = self._get(c, slug)
            c.execute("UPDATE designs SET is_default = 0 WHERE is_default = 1 AND id != ?", (r["id"],))
            c.execute("UPDATE designs SET is_default = 1 WHERE id = ?", (r["id"],))
            return self._row(self._get(c, slug))

    def delete(self, slug: str, confirm) -> dict:
        with self.lock, self.connect() as c:
            r = self._get(c, slug)
            if confirm != slug:
                raise StudioError(400, f"Deleting needs confirm={slug}")
            if r["is_default"]:
                raise StudioError(409, "The default design cannot be deleted; set another design as default first")
            c.execute("DELETE FROM designs WHERE id = ?", (r["id"],))
            return {"deleted": slug}

    def import_text(self, text: str, name: str = "", kind: str = "", client: str = "", source_url: str = "") -> dict:
        if not isinstance(text, str) or not text.strip():
            raise StudioError(400, "Paste a design-tokens JSON file or CSS with custom properties")
        if len(text) > MAX_BODY:
            raise StudioError(413, "The file is too large")
        base = self.default()
        spec = spec_from_text(text, base["spec"], name or "import")
        kind = kind or ("client" if client else "reference")
        return self.create({"name": name or "Imported design", "kind": kind, "client": client, "spec": spec,
                            "source_url": source_url, "palette_meta": base["palette_meta"],
                            "tagline": "imported design", "description": ""})


# ---------------------------------------------------------------- import

TOKEN_NAMES = set(T.COLORS + T.FONTS + T.SIZES + T.TYPE_EXTRA + T.SPACE + T.RADIUS + T.BORDER + ["shadow"] + T.MOTION + T.LAYOUT)
PREFIXES = [("color-", ""), ("radius-", "r-"), ("spacing-", "")]


def token_name(raw: str):
    n = raw.strip().lstrip("-").lower()
    if n in TOKEN_NAMES:
        return n
    for pre, rep in PREFIXES:
        if n.startswith(pre):
            m = rep + n[len(pre):]
            if m in TOKEN_NAMES:
                return m
    return None


def css_decls(css: str) -> dict:
    """Custom properties per theme: {'light': {...}, 'dark': {...}} from :root, html, @theme, and dark blocks."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out = {"light": {}, "dark": {}}
    ctx, start = [], 0

    def take(decl):
        m = re.match(r"\s*(--[\w-]+)\s*:\s*(.+?)\s*$", decl, re.S)
        if not m:
            return
        where = " ".join(ctx).lower().replace(':not([data-theme="light"])', "").replace(":not([data-theme='light'])", "")
        theme = "dark" if "dark" in where and "light" not in where else "light"
        name = token_name(m.group(1))
        val = re.sub(r"\s+", " ", m.group(2)).replace("!important", "").strip()
        if name and val and "var(" not in val:
            out[theme][name] = val

    for i, ch in enumerate(css):
        if ch == "{":
            ctx.append(css[start:i].strip())
            start = i + 1
        elif ch == "}":
            if ctx:
                take(css[start:i])  # the last declaration may have no semicolon
                ctx.pop()
            start = i + 1
        elif ch == ";":
            if ctx:
                take(css[start:i])
            start = i + 1
    return out


def fonts_url_for(fonts: dict, css: str, fallback: str) -> str:
    """The Google Fonts link in the CSS (else the base option's link), with every missing first face added."""
    m = re.search(r"https://fonts\.googleapis\.com/css2\?[^\"')\s]+", css)
    url = htmllib.unescape(m.group(0)) if m else fallback
    system = {"system-ui", "-apple-system", "segoe ui", "arial", "helvetica", "consolas", "courier new", "sans-serif",
              "serif", "monospace", "georgia", "calibri", "verdana", "tahoma"}
    for k in T.FONTS:
        first = fonts[k].split(",")[0].strip().strip("\"'")
        if first.lower() not in system and first.replace(" ", "+") not in url:
            url += "&family=" + first.replace(" ", "+")
    return url


def put_option(spec: dict, group: str, values: dict, oid: str, label: str):
    lst = spec["options"][group]
    existing = next((o for o in lst if o.get("id") == oid), None)
    if existing is None:
        if len(lst) >= 4:
            drop = next(o for o in reversed(lst) if o.get("id") != spec["choices"][group])
            lst.remove(drop)
        existing = {"id": oid}
        lst.append(existing)
    existing.clear()
    existing.update({"id": oid, "label": label, **values})
    spec["choices"][group] = oid


def spec_from_text(text: str, base_spec: dict, name: str) -> dict:
    """A full spec from a design-tokens JSON file, a bare tokens object, or CSS custom properties."""
    try:
        data = json.loads(text)
    except ValueError:
        data = None
    if isinstance(data, dict) and {"options", "choices", "tokens"} <= set(data):
        return data
    if isinstance(data, dict):
        tok = data.get("tokens", data)
        decls = {"light": {}, "dark": {}}
        for g, grp in tok.items():
            if g in ("light", "dark") and isinstance(grp, dict):
                decls[g].update({k: v for k, v in grp.items() if k in T.COLORS and isinstance(v, str)})
            elif isinstance(grp, dict):
                decls["light"].update({k: v for k, v in grp.items() if k in TOKEN_NAMES and isinstance(v, str)})
        css = tok.get("fonts_url", "") if isinstance(tok.get("fonts_url"), str) else ""
    elif data is None:
        decls, css = css_decls(text), text
    else:
        raise StudioError(400, "The JSON is not a tokens object")
    light, dark = decls["light"], decls["dark"]
    if not any(k in TOKEN_NAMES for k in list(light) + list(dark)):
        raise StudioError(422, "No known design tokens found (custom properties such as --bg, --accent, --font-body, --r-2)")
    spec = json.loads(json.dumps(base_spec))
    label = f"Imported: from {name}"[:120]
    cur = {g: T.find(spec["options"], g, spec["choices"][g]) for g in GROUP_KEYS}
    if any(k in T.COLORS for k in list(light) + list(dark)):
        pal = {"light": {**cur["palette"]["light"], **{k: v for k, v in light.items() if k in T.COLORS}},
               "dark": {**cur["palette"]["dark"], **{k: v for k, v in dark.items() if k in T.COLORS}}}
        put_option(spec, "palette", pal, "imported", label)
    for g in ("type", "shape", "density"):
        keys = GROUP_KEYS[g]
        found = {k: light[k] for k in keys if k in light}
        if not found:
            continue
        vals = {k: cur[g][k] for k in keys}
        vals.update(found)
        if g == "type":
            for k in T.FONTS:
                if not re.search(r"(sans-serif|serif|monospace)\s*$", vals[k]):
                    vals[k] = vals[k].rstrip(", ") + (", monospace" if k == "font-mono" else ", sans-serif")
            if any(k in found for k in T.FONTS):
                vals["fonts_url"] = fonts_url_for(vals, css, cur[g]["fonts_url"])
        put_option(spec, g, vals, "imported", label)
    for g, keys in (("motion", T.MOTION), ("layout", T.LAYOUT)):
        for k in keys:
            if k in light:
                spec["tokens"][g][k] = light[k]
    spec["tokens"] = T.resolve(spec)
    return spec


# ---------------------------------------------------------------- exports

def _face(v: str) -> str:
    return v.split(",")[0].strip().strip("\"'")


def _label(d, k):
    return d["palette_meta"].get(k, {}).get("label", "")


def _role(d, k):
    return d["palette_meta"].get(k, {}).get("role", "")


def export_design_md(d: dict, extended: bool) -> str:
    t, s = d["spec"]["tokens"], d["spec"]
    colors = T.COLORS if extended else ["bg", "surface", "fg", "muted", "line", "accent", "accent-fg", "feature-bg", "brand", "link"]
    L = [f"# {d['name']}", ""]
    if d["tagline"]:
        L += [f"*{d['tagline']}*", ""]
    ref = d.get("reference") or clean_reference({})
    has_principles = bool(ref["principles"] or any(ref["voice"].values()))
    has_components = any(ref["components"].values())
    has_surfaces = bool(ref["surfaces"] or ref["surfaces_intro"] or s.get("surfaces"))
    L += ["## Contents", "", "- [Overview](#overview)"]
    L += ["- [Principles and voice](#principles-and-voice)"] if has_principles else []
    L += ["- [Colors](#colors)", "- [Typography](#typography)", "- [Spacing and shape](#spacing-and-shape)"]
    L += ["- [Components](#components)"] if has_components else []
    L += ["- [Guidance per surface](#guidance-per-surface)"] if has_surfaces else []
    L += ["- [Guidelines](#guidelines)", "- [Skills and agents](#skills-and-agents)", "", "## Overview", ""]
    if d["description"]:
        L += [d["description"], ""]
    who = {"house": "The HowToAI house design.", "client": f"Client design for {d['client'] or d['name']}.",
           "reference": "A reference design."}[d["kind"]]
    L += [f"- {who}", f"- Design studio slug `{d['slug']}`, version {d['version']} ({s['date']}).",
          "- Every page ships light and dark themes; use the tokens, never raw values."]
    if d["source_url"]:
        L.append(f"- Source: <{d['source_url']}>")
    if has_principles:
        L += ["", "## Principles and voice", ""]
        for p in ref["principles"]:
            L += [f"- **{p['title'] or 'Principle'}.** {p['text']}".rstrip()]
        v = ref["voice"]
        if v["text"]:
            L += ["", f"Voice: {v['text']}"]
        if v["write"]:
            L += [f"- Write: {v['write']}"]
        if v["avoid"]:
            L += [f"- Avoid: {v['avoid']}"]
    L += ["", "## Colors", "", "| Token | Light | Dark | Name | Role |", "| --- | --- | --- | --- | --- |"]
    for k in colors:
        L.append(f"| `--{k}` | `{t['light'][k]}` | `{t['dark'][k]}` | {_label(d, k)} | {_role(d, k)} |")
    L += ["", "## Typography", "", f"- Display: {_face(t['font']['font-display'])} (`--font-display`)",
          f"- Body: {_face(t['font']['font-body'])} (`--font-body`)", f"- Mono: {_face(t['font']['font-mono'])} (`--font-mono`)",
          f"- Fonts: <{t['fonts_url']}>"]
    if extended:
        ts = ref["type_scale"]
        L += ["", "| Token | Size | Line height | Tracking | Weight |", "| --- | --- | --- | --- | --- |"]
        L += [f"| `--{k}` | `{t['type'][k]}` | {ts.get(k, {}).get('leading', '')} | {ts.get(k, {}).get('tracking', '')} | "
              f"{ts.get(k, {}).get('weight', '')} |" for k in T.SIZES]
        L += ["", "| Token | Value |", "| --- | --- |"] + [f"| `--{k}` | `{t['type'][k]}` |" for k in T.TYPE_EXTRA]
        L += ["", "Full stacks:", ""] + [f"- `--{k}: {t['font'][k]}`" for k in T.FONTS]
    else:
        L.append(f"- Body size {t['type']['text-md']}, line height {t['type']['leading-body']}; smallest text {t['type']['text-xs']}.")
    L += ["", "## Spacing and shape", "",
          f"- Base unit {t['space']['s-1']}; element gap {t['space']['s-3']}; card padding {t['space']['s-6']}; section gap {t['space']['s-9']}.",
          f"- Page max width {t['layout']['page-max']}; text measure {t['layout']['measure']}.",
          f"- Radius: controls {t['radius']['r-1']}, cards {t['radius']['r-2']}, feature cards {t['radius']['r-3']}, buttons {t['radius']['r-pill']}.",
          f"- Borders {t['border']['border-w']} and {t['border']['border-w-strong']}; shadow {t['shadow']['shadow']}."]
    if extended:
        L += ["", "| Token | Value |", "| --- | --- |"]
        L += [f"| `--{k}` | `{t['space'][k]}` |" for k in T.SPACE]
        L += [f"| `--{k}` | `{t['motion'][k]}` |" for k in T.MOTION]
    if has_components:
        names = {"button": "Button", "card": "Card and feature card", "table": "Table", "badge": "Badge", "form": "Form field",
                 "chart": "Chart colors", "callout": "Callout"}
        L += ["", "## Components", ""] + [f"- **{names[k]}.** {ref['components'][k]}" for k in COMPONENT_KEYS if ref["components"][k]]
    if has_surfaces:
        L += ["", "## Guidance per surface", ""]
        if ref["surfaces_intro"]:
            L += [ref["surfaces_intro"], ""]
        for sf in ref["surfaces"]:
            L += [f"### {sf['title'] or 'Surface'}", ""] + [f"- {x}" for x in sf["items"]] + [""]
        if s.get("surfaces"):
            L += ["### Surface notes", ""] + [f"- `{k}`: {v}" for k, v in s["surfaces"].items()] + [""]
        if L[-1] == "":
            L.pop()
    L += ["", "## Guidelines", "", "### Do", ""] + ([f"- {x}" for x in d["guidelines"]["do"]] or ["- Not recorded."])
    L += ["", "### Don't", ""] + ([f"- {x}" for x in d["guidelines"]["dont"]] or ["- Not recorded."])
    L += ["", "## Skills and agents", "",
          f"- `skill-design` - builds and reviews outputs in this design: `design_studio.py show {d['slug']}` prints its tokens.", ""]
    return "\n".join(L)


def _theme_blocks(lines_dark: list, indent="  ") -> list:
    return (["@media (prefers-color-scheme: dark) {", '  :root:not([data-theme="light"]) {']
            + [f"    {x}" for x in lines_dark] + ["  }", "}", ':root[data-theme="dark"] {'] + [f"{indent}{x}" for x in lines_dark] + ["}"])


def export_tailwind(d: dict, extended: bool) -> str:
    t = d["spec"]["tokens"]
    L = [f"/* {d['name']}: Tailwind CSS v4 theme from the HowToAI design studio ({d['slug']} v{d['version']}). */",
         f'@import url("{t["fonts_url"]}");', '@import "tailwindcss";', "", "@theme {"]
    L += [f"  --color-{k}: {t['light'][k]};" for k in T.COLORS]
    L += [f"  --{k}: {t['font'][k]};" for k in T.FONTS]
    L += [f"  --font-sans: {t['font']['font-body']};"]
    L += [f"  --radius-{k[2:] if k.startswith('r-') else k}: {t['radius'][k]};" for k in T.RADIUS]
    if extended:
        L += [f"  --{k}: {t['type'][k]};" for k in T.SIZES]
        L += [f"  --{k}: {t['type'][k]};" for k in T.TYPE_EXTRA]
        L += [f"  --spacing: {t['space']['s-1']};"] + [f"  --spacing-{k}: {t['space'][k]};" for k in T.SPACE]
        L += [f"  --{k}: {t['border'][k]};" for k in T.BORDER] + [f"  --shadow-card: {t['shadow']['shadow']};"]
        L += [f"  --ease-house: {t['motion']['ease']};", f"  --container-page: {t['layout']['page-max']};"]
    L += ["}", ""]
    L += _theme_blocks([f"--color-{k}: {t['dark'][k]};" for k in T.COLORS])
    return "\n".join(L) + "\n"


def export_css(d: dict, extended: bool) -> str:
    t = d["spec"]["tokens"]
    head = f"/* {d['name']}: design tokens from the HowToAI design studio ({d['slug']} v{d['version']}, {d['spec']['date']}). */"
    if extended:
        block = T.css_block(d["spec"]).splitlines()
        block = [x for x in block if x not in (T.START, T.END) and not x.startswith("/* Generated by tokens.py")]
        return "\n".join([head, f'@import url("{t["fonts_url"]}");'] + block) + "\n"
    L = [head, ":root {"] + [f"  --{k}: {t['light'][k]};" for k in T.COLORS] + [f"  --{k}: {t['font'][k]};" for k in T.FONTS]
    L += [f"  --{k}: {t['radius'][k]};" for k in T.RADIUS] + ["  color-scheme: light;", "}"]
    L += _theme_blocks([f"--{k}: {t['dark'][k]};" for k in T.COLORS] + ["color-scheme: dark;"])
    return "\n".join(L) + "\n"


def export_tokens(d: dict, extended: bool) -> str:
    return json.dumps(d["spec"] if extended else d["spec"]["tokens"], indent=2, ensure_ascii=False) + "\n"


def export_profile(d: dict, root: Path) -> str:
    t = d["spec"]["tokens"]
    try:
        h = house_doc(root)["tokens"]
    except (OSError, ValueError, KeyError):
        h = {}
    light = [f"  --{k}: {t['light'][k]};" for k in T.COLORS if h.get("light", {}).get(k) != t["light"][k]]
    dark = [f"--{k}: {t['dark'][k]};" for k in T.COLORS if h.get("dark", {}).get(k) != t["dark"][k]]
    for g in ("font", "type", "space", "radius", "border", "shadow", "motion", "layout"):
        light += [f"  --{k}: {v};" for k, v in t[g].items() if h.get(g, {}).get(k) != v]
    fonts_changed = t["fonts_url"] != h.get("fonts_url")
    who = d["client"] or d["name"]
    choices = d["spec"]["choices"]
    L = [f"# Design profile: {who}", "",
         "Written by `skill-design` with the user's approval. It records only where this client departs from the HowToAI house design; "
         "everything not listed here follows the house design. Exported from the HowToAI design studio "
         f"(design `{d['slug']}`, version {d['version']}); edit the design there and export again.", "",
         "## Contents", "", "- [Decisions](#decisions)"]
    if fonts_changed:
        L.append("- [Font links](#font-links)")
    L += ["- [Token overrides](#token-overrides)", "- [Skills and agents](#skills-and-agents)", "",
          f"- **Source of truth:** client design in the HowToAI design studio (`{d['slug']}`, v{d['version']})"
          + (f", from {d['source_url']}" if d["source_url"] else ""),
          f"- **Updated:** {d['spec']['date']}", "- **Themes:** light and dark",
          f"- **Fonts:** {_face(t['font']['font-display'])}, {_face(t['font']['font-body'])}, {_face(t['font']['font-mono'])}; web fonts allowed: yes",
          "- **Logo:** Not recorded", "- **Voice:** house: plain words", "", "## Decisions", ""]
    for g in ("palette", "type", "shape", "density"):
        o = T.find(d["spec"]["options"], g, choices[g]) or {}
        L.append(f"- {g.capitalize()}: {o.get('label', choices[g])}")
    L += [f"- Do: {x}" for x in d["guidelines"]["do"]] + [f"- Don't: {x}" for x in d["guidelines"]["dont"]]
    if fonts_changed:
        L += ["", "## Font links", "", "`page.py new --profile` puts these tags in place of the house font link.", "", "```html",
              '<link rel="preconnect" href="https://fonts.googleapis.com">',
              '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
              f'<link rel="stylesheet" href="{htmllib.escape(t["fonts_url"])}">', "```"]
    L += ["", "## Token overrides", "", "Only tokens that change. `page.py new --profile` appends this block after the house tokens.", "", "```css", ":root {"]
    L += light or ["  /* no overrides: the same tokens as the house design */"]
    L += ["}"]
    if dark:
        L += _theme_blocks(dark)
    L += ["```", "", "## Skills and agents", "",
          "- `skill-design` - writes and reads this profile; Build and Review use it in place of the house design reference.", ""]
    return "\n".join(L)


def export(d: dict, fmt: str, extended: bool, root: Path):
    """(text, filename, content type) of one export."""
    if fmt == "design-md":
        return export_design_md(d, extended), "DESIGN.md", "text/markdown; charset=utf-8"
    if fmt == "tailwind":
        return export_tailwind(d, extended), f"{d['slug']}.tailwind.css", "text/css; charset=utf-8"
    if fmt == "css":
        return export_css(d, extended), f"{d['slug']}.tokens.css", "text/css; charset=utf-8"
    if fmt == "tokens":
        return export_tokens(d, extended), (f"{d['slug']}.design-tokens.json" if extended else f"{d['slug']}.tokens.json"), "application/json; charset=utf-8"
    if fmt == "profile":
        return export_profile(d, root), "client-profile.md", "text/markdown; charset=utf-8"
    raise StudioError(400, "format must be one of: " + ", ".join(FORMATS))


# ---------------------------------------------------------------- apply to the house files

def apply_house(store: Store, slug: str):
    """Write the design's spec to a temp file and run tokens.py apply on the house files. (exit code, output)."""
    d = store.get(slug)
    fd, tmp = tempfile.mkstemp(prefix="design-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(d["spec"], f, indent=2, ensure_ascii=False)
        p = subprocess.run([sys.executable, str(HERE / "tokens.py"), "--root", str(store.root), "apply", tmp],
                           capture_output=True, text=True, encoding="utf-8", timeout=120)
        return p.returncode, (p.stdout + p.stderr).strip()
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


# ---------------------------------------------------------------- HTTP

CSP = ("default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline' https://fonts.googleapis.com; "
       "font-src https://fonts.gstatic.com; img-src 'self' data: blob:; connect-src 'self'; base-uri 'none'; "
       "form-action 'none'; frame-ancestors 'none'")


class StudioServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = os.name != "nt"  # on Windows SO_REUSEADDR lets a second server share the port

    def __init__(self, addr, store: Store, token: str):
        self.store, self.token = store, token
        super().__init__(addr, Handler)

    def server_bind(self):
        if os.name == "nt" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

    @property
    def port(self) -> int:
        return self.server_address[1]


ROUTES = [
    ("GET", r"/api/health", "health"),
    ("GET", r"/api/designs", "list"),
    ("POST", r"/api/designs", "create"),
    ("POST", r"/api/import", "import_"),
    ("POST", r"/api/export-preview", "export_preview"),
    ("POST", r"/api/shutdown", "shutdown"),
    ("GET", r"/api/designs/(?P<slug>[a-z0-9-]{1,80})", "get"),
    ("PUT", r"/api/designs/(?P<slug>[a-z0-9-]{1,80})", "update"),
    ("DELETE", r"/api/designs/(?P<slug>[a-z0-9-]{1,80})", "delete"),
    ("POST", r"/api/designs/(?P<slug>[a-z0-9-]{1,80})/default", "default"),
    ("GET", r"/api/designs/(?P<slug>[a-z0-9-]{1,80})/versions", "versions"),
    ("GET", r"/api/designs/(?P<slug>[a-z0-9-]{1,80})/versions/(?P<version>\d{1,6})", "version_detail"),
    ("POST", r"/api/designs/(?P<slug>[a-z0-9-]{1,80})/restore/(?P<version>\d{1,6})", "restore"),
    ("GET", r"/api/designs/(?P<slug>[a-z0-9-]{1,80})/export", "export"),
    ("POST", r"/api/designs/(?P<slug>[a-z0-9-]{1,80})/apply-house", "apply_house"),
]


class Handler(BaseHTTPRequestHandler):
    server_version = "HowToAIDesignStudio/1"
    sys_version = ""

    def log_request(self, code="-", size="-"):  # quiet: log refused and failed requests only
        if str(code)[:1] in ("4", "5"):
            sys.stderr.write(f"{self.command} {self.path.split('?')[0]} -> {code}\n")

    def log_message(self, fmt, *args):
        sys.stderr.write((fmt % args) + "\n")

    # -- responses

    def _send(self, status: int, body: bytes, ctype: str, extra=None):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", CSP)
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status: int, obj):
        self._send(status, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _error(self, status: int, msg: str, problems=None):
        body = {"error": msg}
        if problems:
            body["problems"] = problems
        self._json(status, body)

    # -- guards

    def _allowed_hosts(self):
        p = self.server.port
        return {f"127.0.0.1:{p}", f"localhost:{p}"}

    def _guard(self) -> bool:
        host = (self.headers.get("Host") or "").strip().lower()
        if host not in self._allowed_hosts():
            self._error(403, "Host not allowed: open the studio at http://127.0.0.1:%d/" % self.server.port)
            return False
        if self.command not in ("GET", "HEAD"):
            origin = self.headers.get("Origin")
            if origin is not None and origin.strip().lower() not in {f"http://{h}" for h in self._allowed_hosts()}:
                self._error(403, "Cross-origin requests are not allowed")
                return False
            if (self.headers.get("Sec-Fetch-Site") or "").lower() == "cross-site":
                self._error(403, "Cross-site requests are not allowed")
                return False
        return True

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_BODY:
            raise StudioError(413, "Request body too large")
        if n == 0:
            return {}
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ctype != "application/json":
            raise StudioError(415, "Send JSON with Content-Type: application/json")
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise StudioError(400, "The body is not valid JSON")

    # -- dispatch

    def do_GET(self):
        self._dispatch()

    def do_HEAD(self):
        self._dispatch()

    def do_POST(self):
        self._dispatch()

    def do_PUT(self):
        self._dispatch()

    def do_DELETE(self):
        self._dispatch()

    def _dispatch(self):
        if not self._guard():
            return
        u = urllib.parse.urlsplit(self.path)
        self.query = urllib.parse.parse_qs(u.query)
        method = "GET" if self.command == "HEAD" else self.command
        try:
            if u.path == "/":
                if method != "GET":
                    raise StudioError(405, "Method not allowed")
                return self._page()
            for m, pat, name in ROUTES:
                mt = re.fullmatch(pat, u.path)
                if mt:
                    if m != method:
                        continue
                    return getattr(self, "api_" + name)(**mt.groupdict())
            if any(re.fullmatch(pat, u.path) for _, pat, _ in ROUTES):
                raise StudioError(405, "Method not allowed")
            raise StudioError(404, "Not found")
        except StudioError as e:
            self._error(e.status, e.message, e.problems)
        except Exception as e:  # never leak a traceback to the page
            sys.stderr.write(f"error: {type(e).__name__}: {e}\n")
            self._error(500, "The studio hit an internal error; see the terminal that runs it")

    def _page(self):
        try:
            body = paths_for(self.server.store.root)["ref"].read_bytes()
        except OSError:
            raise StudioError(500, "references/design-reference.html is missing")
        self._send(200, body, "text/html; charset=utf-8")

    @property
    def store(self) -> Store:
        return self.server.store

    def api_health(self):
        self._json(200, {"ok": True, "app": APP, "db": str(self.store.db), "designs": self.store.count()})

    def api_list(self):
        self._json(200, self.store.list())

    def api_get(self, slug):
        self._json(200, self.store.get(slug))

    def api_create(self):
        self._json(201, self.store.create(self._body()))

    def api_update(self, slug):
        self._json(200, self.store.update(slug, self._body()))

    def api_delete(self, slug):
        self._json(200, self.store.delete(slug, (self.query.get("confirm") or [None])[0]))

    def api_default(self, slug):
        self._json(200, self.store.set_default(slug))

    def api_versions(self, slug):
        self._json(200, self.store.versions(slug))

    def api_restore(self, slug, version):
        self._json(200, self.store.restore(slug, int(version)))

    def api_version_detail(self, slug, version):
        self._json(200, self.store.version_detail(slug, int(version)))

    def _send_export(self, d):
        fmt = (self.query.get("format") or ["design-md"])[0]
        ext = (self.query.get("view") or ["extended"])[0] != "compact"
        try:
            text, fname, ctype = export(d, fmt, ext, self.store.root)
        except (KeyError, TypeError, AttributeError) as e:
            raise StudioError(422, f"The design cannot be exported yet: {type(e).__name__} {e}")
        self._send(200, text.encode("utf-8"), ctype, {"Content-Disposition": f'attachment; filename="{fname}"',
                                                       "X-Filename": fname})

    def api_export(self, slug):
        self._send_export(self.store.get(slug))

    def api_export_preview(self):
        """The code tabs while editing: an export of the unsaved design in the body. Nothing is saved."""
        self._send_export(self.store.preview(self._body()))

    def api_import_(self):
        b = self._body()
        if not isinstance(b, dict):
            raise StudioError(400, "Send a JSON object")
        self._json(201, self.store.import_text(b.get("text", ""), str(b.get("name") or ""), str(b.get("kind") or ""),
                                               str(b.get("client") or ""), str(b.get("source_url") or "")))

    def api_apply_house(self, slug):
        b = self._body()
        if not isinstance(b, dict) or b.get("confirm") != slug:
            raise StudioError(400, f"Applying to the house files needs the typed confirmation {slug!r}")
        if not self.store.get(slug)["is_default"]:
            raise StudioError(409, "Only the default design can be applied to the house files")
        code, out = apply_house(self.store, slug)
        if code != 0:
            raise StudioError(422, "tokens.py apply refused the design; nothing was written", out.splitlines()[-12:])
        self._json(200, {"applied": slug, "output": out})

    def api_shutdown(self):
        if not secrets.compare_digest(self.headers.get("X-Studio-Token") or "", self.server.token):
            raise StudioError(403, "Wrong or missing studio token")
        self._json(200, {"stopping": True})
        threading.Thread(target=self.server.shutdown, daemon=True).start()


def make_server(store: Store, port: int, token: str = "") -> StudioServer:
    """Bind 127.0.0.1 on `port`, falling back to a free port when it is taken or reserved (WinError 10013)."""
    try:
        return StudioServer(("127.0.0.1", port), store, token or secrets.token_urlsafe(24))
    except OSError:
        if port == 0:
            raise
        return StudioServer(("127.0.0.1", 0), store, token or secrets.token_urlsafe(24))


# ---------------------------------------------------------------- runtime file

def read_runtime(rt: Path):
    try:
        return json.loads(rt.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def healthy(info) -> bool:
    if not isinstance(info, dict) or not isinstance(info.get("port"), int):
        return False
    try:
        c = http.client.HTTPConnection("127.0.0.1", info["port"], timeout=2)
        c.request("GET", "/api/health", headers={"Host": f"127.0.0.1:{info['port']}"})
        r = c.getresponse()
        data = json.loads(r.read().decode("utf-8"))
        c.close()
        return r.status == 200 and data.get("app") == APP
    except (OSError, ValueError, http.client.HTTPException):
        return False


# ---------------------------------------------------------------- commands

def cmd_serve(a, store: Store, rt: Path) -> int:
    info = read_runtime(rt)
    if healthy(info):
        print(f"The design studio is already running at {info['url']}")
        if a.open:
            webbrowser.open(info["url"])
        return 0
    store.init()
    httpd = make_server(store, a.port if a.port is not None else DEFAULT_PORT)
    url = f"http://127.0.0.1:{httpd.port}/"
    rt.parent.mkdir(parents=True, exist_ok=True)
    rt.write_text(json.dumps({"url": url, "port": httpd.port, "pid": os.getpid(), "started": now(),
                              "db": str(store.db), "token": httpd.token}, indent=2), encoding="utf-8")
    print(f"Design studio running at {url}\nDatabase {store.db}\nStop it with: py -3 \"{HERE / 'design_studio.py'}\" stop", flush=True)
    if a.open:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        cur = read_runtime(rt)
        if cur and cur.get("pid") == os.getpid():
            try:
                rt.unlink()
            except OSError:
                pass
        print("Design studio stopped.", flush=True)
    return 0


def cmd_url(rt: Path) -> int:
    info = read_runtime(rt)
    if healthy(info):
        print(info["url"])
        return 0
    print("The design studio is not running. Start it with: py -3 design_studio.py serve", file=sys.stderr)
    return 1


def cmd_stop(rt: Path) -> int:
    info = read_runtime(rt)
    if not info:
        print("The design studio is not running.")
        return 0
    stopped = False
    if healthy(info):
        try:
            c = http.client.HTTPConnection("127.0.0.1", info["port"], timeout=3)
            c.request("POST", "/api/shutdown", body=b"", headers={"Host": f"127.0.0.1:{info['port']}",
                                                                  "X-Studio-Token": str(info.get("token", ""))})
            stopped = c.getresponse().status == 200
            c.close()
        except (OSError, http.client.HTTPException):
            stopped = False
    if not stopped and isinstance(info.get("pid"), int) and healthy(info):
        try:
            os.kill(info["pid"], 15)
            stopped = True
        except OSError:
            pass
    try:
        rt.unlink()
    except OSError:
        pass
    print("Design studio stopped." if stopped else "The design studio was not running; removed its stale runtime file.")
    return 0


def cmd_list(store: Store) -> int:
    rows = store.list()
    print(f"{'slug':<28} {'name':<28} {'kind':<10} {'default':<8} {'version':<8} updated")
    for r in rows:
        print(f"{r['slug']:<28} {r['name'][:28]:<28} {r['kind']:<10} {'yes' if r['is_default'] else '':<8} {r['version']:<8} {r['updated_at']}")
    return 0


def main(argv=None) -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", default=argparse.SUPPRESS, help="SQLite database (default ~/.claude/howtoai/designs.db)")
    common.add_argument("--runtime", default=argparse.SUPPRESS, help="runtime file (default ~/.claude/howtoai/design-studio.json)")
    common.add_argument("--root", default=argparse.SUPPRESS, help="skill folder (default: this skill)")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, parents=[common])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve", parents=[common], help="start the studio on 127.0.0.1")
    s.add_argument("--port", type=int, default=None)
    s.add_argument("--open", action="store_true", help="open the studio in the default browser")
    sub.add_parser("url", parents=[common], help="print the running studio's URL; exit 1 if none")
    sub.add_parser("stop", parents=[common], help="stop the running studio")
    sub.add_parser("list", parents=[common], help="list designs")
    sh = sub.add_parser("show", parents=[common], help="print one design as JSON")
    sh.add_argument("slug")
    ex = sub.add_parser("export", parents=[common], help="export a design")
    ex.add_argument("slug")
    ex.add_argument("--format", required=True, choices=FORMATS)
    ex.add_argument("--compact", action="store_true", help="the compact view (default extended)")
    ex.add_argument("--extended", action="store_true", help="the extended view (the default)")
    ex.add_argument("--out", help="write to this file instead of printing")
    sd = sub.add_parser("set-default", parents=[common], help="make a design the default")
    sd.add_argument("slug")
    im = sub.add_parser("import", parents=[common], help="import a tokens JSON or CSS custom properties file")
    im.add_argument("file")
    im.add_argument("--name")
    im.add_argument("--kind", choices=("client", "reference"))
    im.add_argument("--client", default="")
    de = sub.add_parser("delete", parents=[common], help="delete a design (not the default)")
    de.add_argument("slug")
    de.add_argument("--confirm", required=True, help="repeat the slug")
    ah = sub.add_parser("apply-house", parents=[common], help="write a design to the shipped house files via tokens.py apply")
    ah.add_argument("slug")
    a = ap.parse_args(argv)

    db = Path(getattr(a, "db", None) or os.environ.get("HOWTOAI_DESIGN_DB") or DEFAULT_DB).expanduser().resolve()
    rt = Path(getattr(a, "runtime", None) or os.environ.get("HOWTOAI_DESIGN_RUNTIME") or DEFAULT_RUNTIME).expanduser().resolve()
    root = Path(getattr(a, "root", None) or SKILL).resolve()
    store = Store(db, root)
    if a.cmd == "serve":
        return cmd_serve(a, store, rt)
    if a.cmd == "url":
        return cmd_url(rt)
    if a.cmd == "stop":
        return cmd_stop(rt)
    try:
        store.init()
        if a.cmd == "list":
            return cmd_list(store)
        if a.cmd == "show":
            print(json.dumps(store.get(a.slug), indent=2, ensure_ascii=False))
        elif a.cmd == "export":
            text, fname, _ = export(store.get(a.slug), a.format, not a.compact, root)
            if a.out:
                Path(a.out).write_text(text, encoding="utf-8")
                print(f"Wrote {a.out} ({fname})")
            else:
                sys.stdout.write(text)
        elif a.cmd == "set-default":
            print(f"Default design: {store.set_default(a.slug)['name']}")
        elif a.cmd == "import":
            p = Path(a.file)
            d = store.import_text(p.read_text(encoding="utf-8"), a.name or p.stem, a.kind or "", a.client)
            print(f"Imported {d['name']} as {d['slug']} ({d['kind']})")
        elif a.cmd == "delete":
            store.delete(a.slug, a.confirm)
            print(f"Deleted {a.slug}")
        elif a.cmd == "apply-house":
            code, out = apply_house(store, a.slug)
            print(out)
            return code
        return 0
    except StudioError as e:
        print(f"Error: {e.message}", file=sys.stderr)
        for p in e.problems:
            print(f"  {p}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
