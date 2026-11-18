"""Unit tests for scripts/design_studio.py (standard library unittest).

  py -3 evals/test_design_studio.py            (from the skill folder)

Every test works on a temporary database and, for apply-house, a temporary copy of the skill folder; the
real ~/.claude/howtoai/designs.db and the shipped house files are never touched. Set STUDIO_TEST_TMP to
choose where the temporary folders are made.
"""
from __future__ import annotations

import copy
import http.client
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL / "scripts"))
import design_studio as DS  # noqa: E402
import tokens as T  # noqa: E402

TMP = os.environ.get("STUDIO_TEST_TMP") or None


class StoreCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=TMP)
        self.store = DS.Store(Path(self.tmp.name) / "designs.db", SKILL).init()

    def tearDown(self):
        self.tmp.cleanup()

    def house(self):
        return self.store.get(DS.HOUSE_SLUG)

    def client(self, name="Acme"):
        return self.store.create({"from": DS.HOUSE_SLUG, "name": name, "kind": "client", "client": name})


class TestStore(StoreCase):
    def test_seed(self):
        rows = self.store.list()
        self.assertEqual(len(rows), 1)
        h = self.house()
        self.assertEqual((h["name"], h["kind"], h["is_default"], h["version"]), ("HowToAI house", "house", True, 1))
        self.assertEqual(h["spec"], json.loads((SKILL / "assets" / "design-tokens.json").read_text(encoding="utf-8")))
        self.assertEqual(h["tagline"], "warm workshop with coral sparks")
        self.assertTrue(h["guidelines"]["do"] and h["guidelines"]["dont"])
        self.assertEqual(set(h["palette_meta"]), set(T.COLORS))
        self.assertEqual(h["source_url"], DS.REFERO_URL)
        self.assertEqual(len(rows[0]["swatches"]), 5)
        self.store.init()  # a second init does not seed again
        self.assertEqual(self.store.count(), 1)

    def test_create_duplicate_update_and_history(self):
        a = self.client()
        self.assertEqual((a["slug"], a["kind"], a["version"], a["is_default"]), ("acme", "client", 1, False))
        b = self.store.create({"from": "acme"})
        self.assertEqual(b["name"], "Acme copy")
        c = self.store.create({"from": "acme"})
        self.assertEqual(c["name"], "Acme copy 2")
        with self.assertRaises(DS.StudioError) as e:
            self.store.create({"from": "acme", "name": "acme"})
        self.assertEqual(e.exception.status, 409)
        # a full-body create
        full = self.store.create({"name": "Northwind", "kind": "reference", "spec": a["spec"]})
        self.assertEqual(full["slug"], "northwind")
        # a details-only change keeps the version
        u = self.store.update("acme", {"tagline": "green and calm"})
        self.assertEqual((u["tagline"], u["version"]), ("green and calm", 1))
        self.assertEqual(len(self.store.versions("acme")), 1)
        # a spec change bumps the version and keeps the old one
        spec = copy.deepcopy(u["spec"])
        spec["choices"]["shape"] = "crisp"
        u2 = self.store.update("acme", {"spec": spec})
        self.assertEqual(u2["version"], 2)
        self.assertEqual(u2["spec"]["tokens"]["radius"]["r-2"], "10px")
        self.assertEqual(u2["spec"]["version"], 2)
        vs = self.store.versions("acme")
        self.assertEqual([v["version"] for v in vs], [2, 1])
        # a guidelines change bumps it too
        u3 = self.store.update("acme", {"guidelines": {"do": ["Use green"], "dont": []}})
        self.assertEqual(u3["version"], 3)
        # resending the same spec is not a change
        u4 = self.store.update("acme", {"spec": u3["spec"]})
        self.assertEqual(u4["version"], 3)

    def test_restore_version(self):
        a = self.client()
        spec = copy.deepcopy(a["spec"])
        spec["choices"]["palette"] = "signal"
        self.store.update("acme", {"spec": spec})
        r = self.store.restore("acme", 1)
        self.assertEqual(r["version"], 3)
        self.assertEqual(r["spec"]["choices"]["palette"], "ember")
        self.assertEqual([v["version"] for v in self.store.versions("acme")], [3, 2, 1])
        with self.assertRaises(DS.StudioError):
            self.store.restore("acme", 9)

    def test_one_default(self):
        self.client()
        self.store.set_default("acme")
        defaults = [d["slug"] for d in self.store.list() if d["is_default"]]
        self.assertEqual(defaults, ["acme"])
        self.store.set_default(DS.HOUSE_SLUG)
        self.assertEqual([d["slug"] for d in self.store.list() if d["is_default"]], [DS.HOUSE_SLUG])
        with self.store.connect() as c:  # the database itself refuses a second default
            with self.assertRaises(Exception):
                c.execute("UPDATE designs SET is_default = 1 WHERE slug = 'acme'")

    def test_delete_default_refused_and_confirm_needed(self):
        self.client()
        with self.assertRaises(DS.StudioError) as e:
            self.store.delete(DS.HOUSE_SLUG, DS.HOUSE_SLUG)
        self.assertEqual(e.exception.status, 409)
        for bad in (None, "", "acm", "howtoai-house"):
            with self.assertRaises(DS.StudioError) as e:
                self.store.delete("acme", bad)
            self.assertEqual(e.exception.status, 400)
        self.assertEqual(self.store.delete("acme", "acme"), {"deleted": "acme"})
        self.assertEqual(self.store.count(), 1)

    def test_contrast_failing_save_refused(self):
        a = self.client()
        spec = copy.deepcopy(a["spec"])
        spec["options"]["palette"][0]["light"]["muted"] = "#bbbbbb"  # the chosen palette, ember
        with self.assertRaises(DS.StudioError) as e:
            self.store.update("acme", {"spec": spec})
        self.assertEqual(e.exception.status, 422)
        self.assertIn("muted on bg", e.exception.message)
        self.assertEqual(self.store.get("acme")["version"], 1)
        with self.assertRaises(DS.StudioError):
            self.store.create({"name": "Bad", "spec": spec})
        # a schema problem is refused too
        spec2 = copy.deepcopy(a["spec"])
        spec2["options"]["density"][0]["text-xs"] = "0.6rem"
        with self.assertRaises(DS.StudioError):
            self.store.update("acme", {"spec": spec2})

    def test_exports(self):
        h = self.house()
        md, name, _ = DS.export(h, "design-md", False, SKILL)
        self.assertEqual(name, "DESIGN.md")
        self.assertTrue(md.startswith("# HowToAI house"))
        self.assertIn("## Contents", md)
        self.assertIn("## Skills and agents", md)
        self.assertGreater(len(DS.export(h, "design-md", True, SKILL)[0]), len(md))
        tw = DS.export(h, "tailwind", True, SKILL)[0]
        self.assertIn("@theme {", tw)
        self.assertIn("--color-accent: #c43000;", tw)
        self.assertIn("--color-accent: #ff6a33;", tw)
        css_ext = DS.export(h, "css", True, SKILL)[0]
        self.assertIn("--accent: #c43000;", css_ext)
        self.assertIn(':root[data-theme="dark"]', css_ext)
        self.assertIn("--dur-1", css_ext)
        self.assertNotIn("--dur-1", DS.export(h, "css", False, SKILL)[0])
        self.assertEqual(json.loads(DS.export(h, "tokens", True, SKILL)[0]), h["spec"])
        self.assertEqual(json.loads(DS.export(h, "tokens", False, SKILL)[0]), h["spec"]["tokens"])
        prof = DS.export(h, "profile", False, SKILL)[0]
        self.assertIn("# Design profile:", prof)
        self.assertIn("no overrides", prof)
        with self.assertRaises(DS.StudioError):
            DS.export(h, "pdf", False, SKILL)
        # a client profile lists only what differs
        a = self.client()
        spec = copy.deepcopy(a["spec"])
        spec["choices"]["palette"] = "signal"
        self.store.update("acme", {"spec": spec})
        prof = DS.export(self.store.get("acme"), "profile", False, SKILL)[0]
        self.assertIn("--accent: #0a5cc2;", prof)
        self.assertNotIn("--bg:", prof)

    def test_css_import(self):
        css = ('@import url("https://fonts.googleapis.com/css2?family=Lato:wght@400;700&display=swap");\n'
               ':root { --accent: #0b6e4f; --font-body: "Lato", sans-serif; --r-2: 12px }\n'
               '@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --accent: #5fd3a8; } }\n')
        d = self.store.import_text(css, "Acme", "client", "Acme Ltd")
        self.assertEqual((d["slug"], d["kind"], d["client"]), ("acme", "client", "Acme Ltd"))
        t = d["spec"]["tokens"]
        self.assertEqual(t["light"]["accent"], "#0b6e4f")
        self.assertEqual(t["dark"]["accent"], "#5fd3a8")
        self.assertEqual(t["radius"]["r-2"], "12px")
        self.assertEqual(t["font"]["font-body"], '"Lato", sans-serif')
        self.assertIn("family=Lato", t["fonts_url"])
        self.assertFalse(T.failures(T.validate(d["spec"])))
        # a tokens JSON round trip
        j = self.store.import_text(DS.export(d, "tokens", True, SKILL)[0], "Acme again", "reference")
        self.assertEqual(j["spec"]["tokens"], d["spec"]["tokens"])
        # an import that fails contrast is refused
        with self.assertRaises(DS.StudioError) as e:
            self.store.import_text(":root { --muted: #dddddd; }", "Pale")
        self.assertEqual(e.exception.status, 422)
        with self.assertRaises(DS.StudioError):
            self.store.import_text("body { color: red; }", "Nothing")


class TestReference(StoreCase):
    def test_seed_reference_from_house_meta(self):
        ref = self.house()["reference"]
        self.assertEqual(len(ref["principles"]), 6)
        self.assertEqual(ref["principles"][0]["title"], "A calm stage, one spark")
        self.assertIn("`--bg`", ref["principles"][0]["text"])
        self.assertTrue(ref["voice"]["text"] and ref["voice"]["write"] and ref["voice"]["avoid"])
        self.assertEqual(set(ref["components"]), set(DS.COMPONENT_KEYS))
        self.assertEqual([s["title"] for s in ref["surfaces"]][:2], ["Web page", "Artifact or report"])
        self.assertEqual(set(ref["type_scale"]), set(T.SIZES))
        self.assertEqual(ref["type_scale"]["text-display"]["tracking"], "-0.045em")
        with self.store.connect() as c:
            self.assertEqual(c.execute("PRAGMA user_version").fetchone()[0], DS.SCHEMA_VERSION)

    def test_reference_round_trip_and_history(self):
        a = self.client()
        self.assertEqual(a["reference"], self.house()["reference"])  # a duplicate starts from its source's content
        ref = copy.deepcopy(a["reference"])
        ref["principles"].insert(0, {"title": "Green and calm", "text": "Use `--accent` sparingly."})
        ref["principles"].pop()  # remove one
        ref["principles"][1], ref["principles"][2] = ref["principles"][2], ref["principles"][1]  # reorder
        ref["voice"]["text"] = "Plain and warm."
        ref["components"]["button"] = "Rounded, one primary per view."
        ref["surfaces"].append({"title": "Email", "items": ["Plain text first.", "  ", "One link."]})
        ref["type_scale"]["text-xl"] = {"leading": "1.25", "tracking": "-0.01em", "weight": "600"}
        u = self.store.update("acme", {"reference": ref})
        self.assertEqual(u["version"], 2)  # reference content is versioned
        self.assertEqual(u["spec"]["version"], 2)
        got = self.store.get("acme")["reference"]
        self.assertEqual(got["principles"][0], {"title": "Green and calm", "text": "Use `--accent` sparingly."})
        self.assertEqual(len(got["principles"]), 6)
        self.assertEqual(got["surfaces"][-1], {"title": "Email", "items": ["Plain text first.", "One link."]})
        self.assertEqual(got["type_scale"]["text-xl"]["weight"], "600")
        self.assertEqual(self.store.get(DS.HOUSE_SLUG)["reference"]["voice"]["text"], self.house()["reference"]["voice"]["text"])  # house untouched
        # resending the same content is no change; the palette labels and hidden swatches are versioned too
        self.assertEqual(self.store.update("acme", {"reference": got})["version"], 2)
        pm = copy.deepcopy(u["palette_meta"])
        pm["shade"]["hidden"] = True
        pm["brand"]["label"] = "Leaf mark"
        u3 = self.store.update("acme", {"palette_meta": pm})
        self.assertEqual((u3["version"], u3["palette_meta"]["shade"].get("hidden")), (3, True))
        # history keeps the old reference and labels; restore brings them back as a new version
        old = self.store.version_detail("acme", 1)
        self.assertEqual(old["reference"]["voice"]["text"], a["reference"]["voice"]["text"])
        r = self.store.restore("acme", 1)
        self.assertEqual(r["version"], 4)
        self.assertEqual(r["reference"], a["reference"])
        self.assertNotIn("hidden", r["palette_meta"].get("shade", {}))
        self.assertEqual(self.store.restore("acme", 3)["palette_meta"]["brand"]["label"], "Leaf mark")

    def test_reference_validation(self):
        self.client()
        bad = [{"principles": "x"}, {"principles": [{"title": "a" * 200, "text": ""}]}, {"voice": {"text": "bad\x01"}},
               {"components": {"widget": "x"}}, {"surfaces": [{"title": "S", "items": [3]}]},
               {"type_scale": {"text-huge": {}}}, {"type_scale": {"text-md": {"weight": "bold"}}},
               {"type_scale": {"text-md": {"leading": "1;}"}}}, "not an object"]
        for b in bad:
            with self.assertRaises(DS.StudioError, msg=repr(b)) as e:
                self.store.update("acme", {"reference": b})
            self.assertEqual(e.exception.status, 400)
        self.assertEqual(self.store.get("acme")["version"], 1)

    def test_design_md_has_reference_and_preview_export(self):
        h = self.house()
        md = DS.export(h, "design-md", True, SKILL)[0]
        for part in ("## Principles and voice", "**A calm stage, one spark.**", "Voice: Friendly workshop", "## Components",
                     "**Button.**", "## Guidance per surface", "### Web page", "### Surface notes", "| Line height |"):
            self.assertIn(part, md)
        self.assertIn("- [Principles and voice](#principles-and-voice)", md)
        # an unsaved edit exports without being saved
        spec = copy.deepcopy(h["spec"])
        spec["choices"]["palette"] = "signal"
        ref = copy.deepcopy(h["reference"])
        ref["principles"][0]["title"] = "Unsaved title"
        d = self.store.preview({"slug": DS.HOUSE_SLUG, "name": "HowToAI house", "spec": spec, "reference": ref})
        self.assertIn("Unsaved title", DS.export(d, "design-md", False, SKILL)[0])
        self.assertIn("--accent: #0a5cc2;", DS.export(d, "css", False, SKILL)[0])
        self.assertEqual(self.house()["version"], 1)
        new = self.store.preview({"name": "", "spec": spec})
        self.assertEqual(new["slug"], "new-design")
        with self.assertRaises(DS.StudioError):
            self.store.preview({"spec": {"choices": {}}})


def build_v1_db(path: Path, root: Path = SKILL):
    """A database as version 1 of design_studio.py wrote it: the v1 schema, the seeded house row, a client
    row, and one saved version, with no reference column."""
    import sqlite3
    c = sqlite3.connect(str(path))
    c.executescript(DS.SCHEMA_V1)
    c.execute("PRAGMA user_version = 1")
    doc = DS.house_doc(root)
    meta = DS.house_meta(root)
    ins = ("INSERT INTO designs (slug, name, tagline, description, kind, client, project_path, source_url, is_default,"
           " version, spec, guidelines, palette_meta, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, '', ?, ?, ?, ?, ?, ?, ?, ?)")
    c.execute(ins, (DS.HOUSE_SLUG, DS.HOUSE_NAME, meta["tagline"], meta["description"], "house", "", DS.REFERO_URL, 1, 1,
                    DS.canon(doc), DS.canon(meta["guidelines"]), DS.canon(meta["palette_meta"]), "2026-11-09T10:00:00+02:00", "2026-11-09T10:00:00+02:00"))
    spec2 = copy.deepcopy(doc)
    spec2["version"], spec2["choices"]["palette"] = 2, "signal"
    spec2["tokens"] = T.resolve(spec2)
    c.execute(ins, ("acme", "Acme", "green", "", "client", "Acme Ltd", "", 0, 2, DS.canon(spec2),
                    DS.canon({"do": ["Use green"], "dont": []}), DS.canon(meta["palette_meta"]), "2026-11-09T11:00:00+02:00", "2026-11-09T12:00:00+02:00"))
    acme_id = c.execute("SELECT id FROM designs WHERE slug = 'acme'").fetchone()[0]
    c.execute("INSERT INTO design_versions (design_id, version, spec, guidelines, saved_at) VALUES (?, 1, ?, ?, ?)",
              (acme_id, DS.canon(doc), DS.canon({"do": [], "dont": []}), "2026-11-09T11:00:00+02:00"))
    c.commit()
    c.close()


class TestMigration(unittest.TestCase):
    def test_v1_database_upgrades_in_place(self):
        import sqlite3
        with tempfile.TemporaryDirectory(dir=TMP) as tmp:
            db = Path(tmp) / "designs.db"
            build_v1_db(db)
            before = sqlite3.connect(str(db))
            rows_before = before.execute("SELECT slug, name, version, spec, guidelines, palette_meta, updated_at FROM designs ORDER BY id").fetchall()
            versions_before = before.execute("SELECT design_id, version, spec, guidelines, saved_at FROM design_versions").fetchall()
            before.close()
            store = DS.Store(db, SKILL).init()
            c = sqlite3.connect(str(db))
            self.assertEqual(c.execute("PRAGMA user_version").fetchone()[0], 2)
            self.assertEqual(c.execute("SELECT slug, name, version, spec, guidelines, palette_meta, updated_at FROM designs ORDER BY id").fetchall(), rows_before)
            self.assertEqual(c.execute("SELECT design_id, version, spec, guidelines, saved_at FROM design_versions").fetchall(), versions_before)
            self.assertEqual(c.execute("SELECT reference, palette_meta FROM design_versions").fetchall(), [(None, None)])
            c.close()
            self.assertEqual(store.count(), 2)  # no second seed
            house_ref = DS.house_reference(SKILL)
            self.assertEqual(store.get(DS.HOUSE_SLUG)["reference"], house_ref)
            self.assertEqual(store.get("acme")["reference"], house_ref)
            self.assertEqual(store.get("acme")["spec"]["choices"]["palette"], "signal")
            # a second init is a no-op; restoring a pre-v2 version keeps the current reference
            store.init()
            ref = copy.deepcopy(house_ref)
            ref["voice"]["text"] = "Acme voice."
            store.update("acme", {"reference": ref})
            r = store.restore("acme", 1)
            self.assertEqual(r["spec"]["choices"]["palette"], "ember")
            self.assertEqual(r["reference"]["voice"]["text"], "Acme voice.")
            self.assertEqual([v["version"] for v in store.versions("acme")], [4, 3, 2, 1])

    def test_migration_rolls_back_on_error(self):
        import sqlite3
        with tempfile.TemporaryDirectory(dir=TMP) as tmp:
            db = Path(tmp) / "designs.db"
            build_v1_db(db)
            orig = DS.MIGRATION_V2
            DS.MIGRATION_V2 = orig[:1] + ["ALTER TABLE no_such_table ADD COLUMN x TEXT"]
            try:
                with self.assertRaises(sqlite3.OperationalError):
                    DS.Store(db, SKILL).init()
            finally:
                DS.MIGRATION_V2 = orig
            c = sqlite3.connect(str(db))
            self.assertEqual(c.execute("PRAGMA user_version").fetchone()[0], 1)
            self.assertNotIn("reference", {r[1] for r in c.execute("PRAGMA table_info(designs)")})
            c.close()
            self.assertEqual(DS.Store(db, SKILL).init().count(), 2)  # and a later run migrates cleanly


class TestServer(StoreCase):
    def setUp(self):
        super().setUp()
        self.httpd = DS.make_server(self.store, 0, "test-token")
        self.port = self.httpd.port
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        super().tearDown()

    def req(self, method, path, body=None, headers=None, host=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        h = {"Host": host or f"127.0.0.1:{self.port}"}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            h["Content-Type"] = "application/json"
        h.update(headers or {})
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        raw = r.read()
        c.close()
        ct = r.getheader("Content-Type", "")
        return r.status, (json.loads(raw) if ct.startswith("application/json") else raw.decode()), r

    def test_bound_to_loopback(self):
        self.assertEqual(self.httpd.server_address[0], "127.0.0.1")

    def test_host_and_origin_guard(self):
        self.assertEqual(self.req("GET", "/api/health")[0], 200)
        self.assertEqual(self.req("GET", "/api/health", host=f"localhost:{self.port}")[0], 200)
        self.assertEqual(self.req("GET", "/api/health", host="evil.example:80")[0], 403)
        self.assertEqual(self.req("GET", "/", host=f"127.0.0.1.evil.test:{self.port}")[0], 403)
        st, body, _ = self.req("POST", "/api/designs", {"from": DS.HOUSE_SLUG, "name": "X"}, {"Origin": "http://evil.example"})
        self.assertEqual(st, 403)
        self.assertEqual(self.store.count(), 1)
        st, _, _ = self.req("POST", "/api/designs", {"from": DS.HOUSE_SLUG, "name": "X"}, {"Origin": f"http://127.0.0.1:{self.port}"})
        self.assertEqual(st, 201)
        # a JSON body needs the JSON content type (no simple cross-site form posts)
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        c.request("POST", "/api/designs", body=b'{"from":"howtoai-house","name":"Y"}',
                  headers={"Host": f"127.0.0.1:{self.port}", "Content-Type": "text/plain"})
        self.assertEqual(c.getresponse().status, 415)
        c.close()
        # shutdown needs the token
        self.assertEqual(self.req("POST", "/api/shutdown")[0], 403)

    def test_only_the_page_is_served(self):
        st, body, r = self.req("GET", "/")
        self.assertEqual(st, 200)
        self.assertIn('id="design-tokens"', body)
        self.assertIn("default-src 'none'", r.getheader("Content-Security-Policy"))
        for p in ("/../assets/house.css", "/references/design-reference.html", "/%2e%2e/scripts/tokens.py", "/index.html", "//etc/passwd"):
            self.assertEqual(self.req("GET", p)[0], 404, p)
        self.assertEqual(self.req("GET", "/api/designs/..%2fx")[0], 404)

    def test_api_round_trip(self):
        st, h, _ = self.req("GET", "/api/health")
        self.assertEqual((h["ok"], h["app"], h["designs"]), (True, "howtoai-design-studio", 1))
        st, d, _ = self.req("POST", "/api/designs", {"from": DS.HOUSE_SLUG, "name": "Acme", "kind": "client"})
        self.assertEqual((st, d["slug"]), (201, "acme"))
        spec = d["spec"]
        spec["options"]["palette"][0]["light"]["muted"] = "#cccccc"
        st, err, _ = self.req("PUT", "/api/designs/acme", {"spec": spec})
        self.assertEqual(st, 422)
        self.assertIn("error", err)
        self.assertTrue(err["problems"])
        self.assertEqual(self.req("DELETE", "/api/designs/acme")[0], 400)
        self.assertEqual(self.req("DELETE", "/api/designs/howtoai-house?confirm=howtoai-house")[0], 409)
        self.assertEqual(self.req("POST", "/api/designs/acme/default")[0], 200)
        self.assertEqual(self.req("POST", "/api/designs/howtoai-house/default")[0], 200)
        st, text, r = self.req("GET", "/api/designs/acme/export?format=tailwind&view=compact")
        self.assertEqual((st, r.getheader("X-Filename")), (200, "acme.tailwind.css"))
        self.assertIn("@theme", text)
        st, d2, _ = self.req("POST", "/api/import", {"name": "Imp", "kind": "reference", "text": ":root{--r-2:8px}"})
        self.assertEqual((st, d2["spec"]["tokens"]["radius"]["r-2"]), (201, "8px"))
        self.assertEqual(self.req("POST", "/api/designs/acme/apply-house", {"confirm": "acme"})[0], 409)
        self.assertEqual(self.req("POST", "/api/designs/howtoai-house/apply-house", {})[0], 400)
        self.assertEqual(self.req("DELETE", "/api/designs/acme?confirm=acme")[0], 200)
        self.assertEqual(self.req("GET", "/api/designs/acme")[0], 404)

    def test_api_reference_preview_and_versions(self):
        st, h, _ = self.req("GET", "/api/designs/howtoai-house")
        ref = h["reference"]
        ref["components"]["badge"] = "Edited badge note."
        st, u, _ = self.req("PUT", "/api/designs/howtoai-house", {"reference": ref})
        self.assertEqual((st, u["version"], u["reference"]["components"]["badge"]), (200, 2, "Edited badge note."))
        st, v1, _ = self.req("GET", "/api/designs/howtoai-house/versions/1")
        self.assertEqual(st, 200)
        self.assertNotEqual(v1["reference"]["components"]["badge"], "Edited badge note.")
        self.assertEqual(self.req("GET", "/api/designs/howtoai-house/versions/9")[0], 404)
        st, md, r = self.req("POST", "/api/export-preview?format=design-md&view=compact",
                             {"slug": "howtoai-house", "name": "Draft name", "reference": {**ref, "surfaces_intro": "Draft intro."}})
        self.assertEqual((st, r.getheader("X-Filename")), (200, "DESIGN.md"))
        self.assertIn("# Draft name", md)
        self.assertIn("Draft intro.", md)
        self.assertEqual(self.req("GET", "/api/designs/howtoai-house")[1]["name"], "HowToAI house")  # nothing saved
        self.assertEqual(self.req("POST", "/api/export-preview?format=css", {"reference": {"voice": 3}})[0], 400)
        self.assertEqual(self.req("POST", "/api/export-preview", {"x": 1}, {"Origin": "http://evil.example"})[0], 403)


class TestApplyHouse(unittest.TestCase):
    """apply-house on a scratch copy of the skill folder only."""

    def test_apply_house_on_copy(self):
        with tempfile.TemporaryDirectory(dir=TMP) as tmp:
            root = Path(tmp) / "skill-design"
            for sub in ("assets", "references", "scripts"):
                shutil.copytree(SKILL / sub, root / sub, ignore=shutil.ignore_patterns("__pycache__"))
            store = DS.Store(Path(tmp) / "designs.db", root).init()
            d = store.get(DS.HOUSE_SLUG)
            spec = copy.deepcopy(d["spec"])
            spec["choices"]["palette"] = "signal"
            store.update(DS.HOUSE_SLUG, {"spec": spec})
            code, out = DS.apply_house(store, DS.HOUSE_SLUG)
            self.assertEqual(code, 0, out)
            new = json.loads((root / "assets" / "design-tokens.json").read_text(encoding="utf-8"))
            self.assertEqual(new["choices"]["palette"], "signal")
            self.assertEqual(new["version"], d["spec"]["version"] + 1)
            self.assertIn("--accent: #0a5cc2;", (root / "assets" / "house.css").read_text(encoding="utf-8"))
            self.assertEqual(T.cmd_check(root), 0)
            # the shipped files are untouched
            self.assertEqual(json.loads((SKILL / "assets" / "design-tokens.json").read_text(encoding="utf-8"))["choices"]["palette"], "ember")


if __name__ == "__main__":
    unittest.main(verbosity=2)
