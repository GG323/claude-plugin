"""Tests for workbook.py. Run: py -3 -I <this file>.

Every test uses temporary base, user, and project folders, so no real workbook is read or written,
except test_shipped_workbooks_validate, which only reads the shipped base workbooks.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(SKILL, "scripts", "workbook.py")

BASE = """# Demo workbook

## Contents

- [Header](#header)

## Header

| Key | Value |
| --- | --- |
| Technology | `demo` |
| Title | Demo |
| Versions | 1.x |
| Version command | `py -3 --version` |
| Layer | base |
| Updated | 2026-01-01 |

Sources:

- [Demo docs](https://example.org/demo) · checked 2025-01-01

## Load when

| Glob |
| --- |
| `**/*.demo` |

## Overview

- **demo.overview.001** · Demo is a sample. · tags: style · source: [Demo docs](https://example.org/demo) · confirmed: base, 2026-01-01

## Setup and configuration

- none yet

## Idioms and patterns

- **demo.patterns.001** · MUST · Pin the demo version. · tags: versions · source: [Demo docs](https://example.org/demo) · confirmed: base, 2026-01-01
- **demo.patterns.002** · SHOULD · Keep demo files small. · tags: style · source: [Demo docs](https://example.org/demo) · confirmed: base, 2026-01-01

## Pitfalls

- none yet

## Commands

- **demo.commands.001** · Run `demo check`. · tags: cli · source: [Demo docs](https://example.org/demo) · confirmed: base, 2026-01-01

## Testing

- none yet

## Security

- none yet

## Performance

- none yet

## Deployment and operations

- none yet

## Our situation

- none yet

## Skills and agents

- `dev-workbook` - keeps this workbook; the dev skills read it through `workbook.py resolve`.
"""


def overlay(layer, lines, header=""):
    return (f"# Demo workbook ({layer})\n\n## Contents\n\n- [Header](#header)\n\n## Header\n\n| Key | Value |\n| --- | --- |\n"
            f"| Technology | `demo` |\n{header}| Layer | {layer} |\n| Updated | 2026-02-01 |\n\nSources:\n\n- none yet\n\n"
            "## Idioms and patterns\n\n" + "\n".join(lines) + "\n\n## Skills and agents\n\n- `dev-workbook` - keeps this layer.\n")


def run(*args):
    p = subprocess.run([sys.executable, "-I", SCRIPT, *args], capture_output=True, text=True, encoding="utf-8")
    try:
        return p.returncode, json.loads(p.stdout)
    except json.JSONDecodeError:
        return p.returncode, p.stdout


class WorkbookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="workbook-test-")
        t = self.tmp.name
        self.base, self.user, self.ws = os.path.join(t, "base"), os.path.join(t, "user"), os.path.join(t, "ws")
        for d in (self.base, self.user, os.path.join(self.ws, ".howtoai", "workbooks")):
            os.makedirs(d)
        with open(os.path.join(self.base, "demo.md"), "w", encoding="utf-8") as f:
            f.write(BASE)
        self.dirs = ["--base-dir", self.base, "--user-dir", self.user]

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, layer, lines, header=""):
        d = self.user if layer == "user" else os.path.join(self.ws, ".howtoai", "workbooks")
        with open(os.path.join(d, "demo.md"), "w", encoding="utf-8") as f:
            f.write(overlay(layer, lines, header))

    def write_base(self, text):
        with open(os.path.join(self.base, "demo.md"), "w", encoding="utf-8") as f:
            f.write(text)

    def test_validate_base_ok_and_errors(self):
        code, out = run("validate", os.path.join(self.base, "demo.md"))
        self.assertTrue(out["ok"], out["errors"])
        bad = BASE.replace("demo.patterns.002", "demo.pitfalls.002").replace(
            "Demo is a sample. · tags: style · source: [Demo docs](https://example.org/demo)", "Demo is a sample. · tags: style · source: [Other](https://other.example)")
        p = os.path.join(self.base, "demo.md")
        with open(p, "w", encoding="utf-8") as f:
            f.write(bad)
        code, out = run("validate", p)
        self.assertFalse(out["ok"])
        self.assertTrue(any("is in section patterns" in e for e in out["errors"]))
        self.assertTrue(any("not in the Header Sources" in e for e in out["errors"]))

    def test_resolve_by_paths_and_topics_with_receipt(self):
        code, out = run("resolve", "--workspace", self.ws, "--paths", "src/a.demo", "src/b.py", "--topics", "patterns",
                        "--stage", "build", *self.dirs)
        self.assertEqual(code, 0)
        self.assertEqual(list(out["sections"]["demo"]), ["patterns"])
        self.assertEqual(out["receipt"]["statements"], ["demo.patterns.001", "demo.patterns.002"])
        self.assertEqual(out["receipt"]["stage"], "build")
        self.assertIn("python", out["missing"])
        self.assertEqual(out["technologies"]["demo"]["matched_by"], ["src/a.demo"])

    def test_resolve_layers_override_withdraw_conflict(self):
        self.write("user", ["- **demo.patterns.001** · MUST · Pin demo to 1.4. · source: user, 2026-02-01 · confirmed: user, 2026-02-01",
                            "- **demo.patterns.u001** · Prefer tabs. · source: user, 2026-02-01 · confirmed: user, 2026-02-01"])
        self.write("project", ["- **demo.patterns.001** · MUST · Pin demo to 1.5. · source: `demo.lock` · confirmed: project, 2026-02-01",
                               "- **demo.patterns.002** · withdrawn: files are generated here · source: `README.md` · confirmed: project, 2026-02-01"])
        code, out = run("resolve", "--workspace", self.ws, "--technologies", "demo", *self.dirs)
        pats = {s["id"]: s for s in out["sections"]["demo"]["patterns"]}
        self.assertEqual(pats["demo.patterns.001"]["text"], "Pin demo to 1.5.")
        self.assertEqual(pats["demo.patterns.001"]["layer"], "project")
        self.assertNotIn("demo.patterns.002", pats)
        self.assertIn("demo.patterns.u001", pats)
        self.assertEqual([c["id"] for c in out["conflicts"]], ["demo.patterns.001"])
        self.assertEqual(out["technologies"]["demo"]["layers"], ["base", "user", "project"])

    def test_resolve_markdown(self):
        p = subprocess.run([sys.executable, "-I", SCRIPT, "resolve", "--workspace", self.ws, "--technologies", "demo",
                            "--topics", "Commands", "--markdown", *self.dirs], capture_output=True, text=True, encoding="utf-8")
        self.assertIn("### Commands", p.stdout)
        self.assertIn("demo.commands.001", p.stdout)

    def test_propose_preview_write_and_ids(self):
        args = ["propose", "--workspace", self.ws, "--tech", "demo", "--section", "situation", "--text",
                "Our demo files live in `cfg/`.", "--source", "`cfg/app.demo`", "--date", "2026-03-01", *self.dirs]
        code, out = run(*args)
        self.assertEqual((code, out["written"], out["id"]), (0, False, "demo.situation.p001"))
        self.assertFalse(os.path.exists(out["file"]))
        code, out = run(*args, "--write")
        self.assertTrue(out["written"] and out["validate"]["ok"], out)
        code, out = run(*args[:-6], "--text", "Our demo builds run on Linux.", "--source", "`ci.yml`", "--date", "2026-03-01", *self.dirs, "--write")
        self.assertEqual(out["id"], "demo.situation.p002")
        code, res = run("resolve", "--workspace", self.ws, "--technologies", "demo", "--topics", "situation", *self.dirs)
        self.assertEqual([s["id"] for s in res["sections"]["demo"]["situation"]], ["demo.situation.p001", "demo.situation.p002"])

    def test_propose_flags_duplicates_process_and_secrets(self):
        code, out = run("propose", "--workspace", self.ws, "--tech", "demo", "--section", "patterns", "--text",
                        "Pin the demo version always.", "--source", "x", *self.dirs)
        self.assertIn("demo.patterns.001", out["duplicates"])
        code, out = run("propose", "--workspace", self.ws, "--tech", "demo", "--section", "patterns", "--text",
                        "Ask the user for approval before you change demo files.", "--source", "x", "--write", *self.dirs)
        self.assertEqual(code, 1)
        self.assertIn("process wording", out["error"])
        code, out = run("propose", "--workspace", self.ws, "--tech", "demo", "--section", "patterns", "--text",
                        "Use `terraform apply -auto-approve` only with a saved plan.", "--source", "x", *self.dirs)
        self.assertEqual(out["process_wording"], [])
        code, out = run("propose", "--workspace", self.ws, "--tech", "demo", "--section", "situation", "--text",
                        "Connect with postgres://admin:hunter2@db/app.", "--source", "x", *self.dirs)
        self.assertEqual(code, 1)
        self.assertIn("secret", out["error"])

    def test_propose_replaces_existing_id(self):
        code, out = run("propose", "--workspace", self.ws, "--tech", "demo", "--section", "patterns", "--replaces",
                        "demo.patterns.001", "--level", "MUST", "--text", "Pin demo to 1.6.", "--source", "`demo.lock`", "--write", *self.dirs)
        self.assertEqual(out["id"], "demo.patterns.001")
        code, res = run("resolve", "--workspace", self.ws, "--technologies", "demo", "--topics", "patterns", *self.dirs)
        self.assertEqual(res["sections"]["demo"]["patterns"][0]["text"], "Pin demo to 1.6.")
        self.assertEqual(res["overrides"][0]["id"], "demo.patterns.001")

    def test_skeleton_and_no_overwrite(self):
        out_path = os.path.join(self.ws, ".howtoai", "workbooks", "python.md")
        code, out = run("skeleton", "--tech", "python", "--title", "Python", "--layer", "project", "--out", out_path, "--date", "2026-03-01")
        self.assertEqual(code, 0)
        code, v = run("validate", out_path)
        self.assertTrue(v["ok"], v["errors"])
        code, out = run("skeleton", "--tech", "python", "--title", "Python", "--layer", "project", "--out", out_path)
        self.assertEqual(code, 1)

    def test_audit_old_sources_and_orphans(self):
        self.write("project", ["- **demo.patterns.009** · Old override. · source: `x` · confirmed: project, 2026-02-01"])
        code, out = run("audit", "--workspace", self.ws, "--today", "2026-03-01", *self.dirs)
        self.assertEqual(out["old_sources"][0]["source"], "https://example.org/demo")
        self.assertEqual(out["orphan_overrides"][0]["id"], "demo.patterns.009")
        self.assertTrue(out["version_commands"].startswith("not run"))
        self.assertEqual(out["versions"], [])

    def test_audit_support_dates_by_layer(self):
        self.write_base(BASE.replace("| Versions | 1.x |\n", "| Versions | 1.x |\n| Supported until | 2026-02-01 |\n"))
        self.write("user", [], header="| Supported until | 2026-05-01 |\n")
        self.record("src/old/", "0.9", "demo@0", "2026-01-15", date="2025-06-01")
        code, out = run("audit", "--workspace", self.ws, "--today", "2026-03-01", *self.dirs)
        ended = {e["layer"]: e for e in out["support_ended"]}
        self.assertEqual(sorted(ended), ["base", "project"])
        self.assertEqual(ended["base"]["days_past"], 28)
        self.assertIn("workbook's versions are out of support", ended["base"]["meaning"])
        self.assertEqual((ended["project"]["code_project"], ended["project"]["versions"]), ("src/old/", "0.9"))
        self.assertIn("keep following the codebase's version", ended["project"]["meaning"])
        self.assertEqual([(e["layer"], e["days_left"]) for e in out["support_ending"]], [("user", 61)])
        self.assertFalse(any(s["check"] == "support dates" for s in out["checks_skipped"]))
        self.assertEqual(out["missing_version_workbooks"], [{"workbook": "project/demo.md", "code_project": "src/old/", "needs": "demo@0"}])
        self.assertTrue(any(s.get("code_project") == "src/old/" for s in out["old_sources"]))

    def record(self, path, version, workbook, until, date="2026-02-01", write=True):
        args = ["record-version", "--workspace", self.ws, "--tech", "demo", "--path", path, "--version", version,
                "--workbook", workbook, "--supported-until", until, "--source", "`src/demo.lock`", "--date", date]
        return run(*args, *(["--write"] if write else []), *self.dirs)

    def make_version(self, key):
        out_path = os.path.join(self.ws, ".howtoai", "workbooks", f"demo@{key}.md")
        return run("skeleton", "--tech", "demo", "--title", f"Demo {key}", "--layer", "project", "--out", out_path,
                   "--version-key", key, "--copy-base", "--date", "2026-02-01", *self.dirs), out_path

    def test_record_version_preview_write_replace(self):
        code, out = self.record("src/old", "0.9", "demo@0", "2026-01-15", write=False)
        self.assertFalse(out["written"])
        self.assertFalse(out["workbook_exists"])
        self.assertIn("Create makes it", out["note"])
        self.assertFalse(os.path.exists(out["file"]))
        self.record("src/old", "0.9", "demo@0", "2026-01-15")
        self.record("./", "1.2", "demo", "unknown")
        code, out = self.record("src/old/", "0.10", "demo@0", "2026-06-01")
        self.assertTrue(out["validate"]["ok"], out["validate"]["errors"])
        self.assertTrue(out["replaces"].startswith("- `src/old/` · 0.9"))
        with open(out["file"], encoding="utf-8") as f:
            text = f.read()
        self.assertEqual(text.count("workbook: `demo@0`"), 1)
        self.assertIn("- `./` · 1.2 · workbook: `demo` · supported until unknown", text)
        code, out = run("record-version", "--workspace", self.ws, "--tech", "demo", "--path", "x", "--version", "1",
                        "--workbook", "other@1", "--source", "`x`", *self.dirs)
        self.assertEqual(code, 1)

    def test_version_workbook_copy_propose_and_resolve(self):
        (code, out), vpath = self.make_version("0")
        self.assertTrue(out["ok"], out)
        self.assertTrue(run("validate", vpath)[1]["ok"], run("validate", vpath)[1]["errors"])
        self.record("src/old/", "0.9", "demo@0", "2026-01-15")
        self.record("src/", "1.2", "demo", "2027-01-01")
        code, out = run("propose", "--workspace", self.ws, "--tech", "demo@0", "--section", "patterns",
                        "--text", "Version 0 has no async API.", "--source", "`src/demo.lock`", "--write", *self.dirs)
        self.assertEqual(out["id"], "demo.patterns.p001")
        self.assertTrue(out["validate"]["ok"], out["validate"]["errors"])
        code, out = run("resolve", "--workspace", self.ws, "--paths", "src/old/a.demo", "src/new/b.demo", "other/c.demo",
                        "--today", "2026-03-01", *self.dirs)
        self.assertEqual(sorted(out["technologies"]), ["demo", "demo@0"])
        old = out["technologies"]["demo@0"]
        self.assertEqual(old["layers"], ["version", "project"])
        self.assertEqual([(c["path"], c["version"], c["support_ended"]) for c in old["code_projects"]], [("src/old/", "0.9", True)])
        self.assertIn("demo.patterns.p001", [s["id"] for s in out["sections"]["demo@0"]["patterns"]])
        self.assertNotIn("demo.patterns.p001", [s["id"] for s in out["sections"]["demo"]["patterns"]])
        new = out["technologies"]["demo"]
        self.assertEqual([c["path"] for c in new["code_projects"]], ["src/"])
        self.assertEqual(new["unrecorded_paths"], ["other/c.demo"])
        self.assertIn("demo@0:demo.patterns.p001", out["receipt"]["statements"])
        p = subprocess.run([sys.executable, "-I", SCRIPT, "resolve", "--workspace", self.ws, "--paths", "src/old/a.demo",
                            "--today", "2026-03-01", "--markdown", *self.dirs], capture_output=True, text=True, encoding="utf-8")
        self.assertIn("Code project `src/old/`: 0.9, support ended 2026-01-15", p.stdout)
        code, out = run("audit", "--workspace", self.ws, "--today", "2026-03-01", *self.dirs)
        self.assertIn("project/demo@0.md", out["checked"])
        self.assertEqual(out["format_errors"], [])
        self.assertEqual(out["orphan_overrides"], [])
        self.assertEqual(out["missing_version_workbooks"], [])

    def test_propose_to_missing_version_workbook_refused(self):
        code, out = run("propose", "--workspace", self.ws, "--tech", "demo@3", "--section", "patterns",
                        "--text", "x", "--source", "`x`", *self.dirs)
        self.assertEqual(code, 1)
        self.assertIn("Create has made it", out["error"])

    def test_validate_codebase_lines_only_in_project(self):
        line = "- `src/` · 1.2 · workbook: `demo` · supported until unknown · source: `x` · checked 2026-02-01"
        self.write_base(BASE.replace("- [Demo docs](https://example.org/demo) · checked 2025-01-01\n",
                                     "- [Demo docs](https://example.org/demo) · checked 2025-01-01\n\nCodebase versions:\n\n" + line + "\n"))
        code, out = run("validate", os.path.join(self.base, "demo.md"))
        self.assertTrue(any("belong only in the project workbook" in e for e in out["errors"]))

    def test_audit_skips_base_without_support_date(self):
        code, out = run("audit", "--workspace", self.ws, "--today", "2026-03-01", *self.dirs)
        self.assertEqual(out["support_ended"], [])
        self.assertIn({"check": "support dates", "workbook": "base/demo.md", "reason": "no Supported until date in its Header"},
                      out["checks_skipped"])

    def test_validate_rejects_bad_support_date(self):
        self.write_base(BASE.replace("| Versions | 1.x |\n", "| Versions | 1.x |\n| Supported until | 2026-02-30 |\n"))
        code, out = run("validate", os.path.join(self.base, "demo.md"))
        self.assertFalse(out["ok"])
        self.assertTrue(any("Supported until" in e for e in out["errors"]))

    def test_resolve_reports_workbook_support(self):
        self.write_base(BASE.replace("| Versions | 1.x |\n", "| Versions | 1.x |\n| Supported until | 2026-01-01 |\n"))
        code, out = run("resolve", "--workspace", self.ws, "--technologies", "demo", "--today", "2026-03-01", *self.dirs)
        info = out["technologies"]["demo"]
        self.assertEqual((info["versions"], info["supported_until"], info["support_ended"], info["code_projects"]),
                         ("1.x", "2026-01-01", True, []))

    def test_check_skills(self):
        skills = os.path.join(self.tmp.name, "skills")
        os.makedirs(os.path.join(skills, "dev-build", "stages"))
        os.makedirs(os.path.join(skills, "dev-core"))
        with open(os.path.join(skills, "dev-build", "stages", "build.md"), "w", encoding="utf-8") as f:
            f.write("1. Consult: run workbook.py resolve with the paths.\n")
        with open(os.path.join(skills, "dev-build", "stages", "gate.md"), "w", encoding="utf-8") as f:
            f.write("1. Run the tests.\n")
        code, out = run("check-skills", skills)
        self.assertFalse(out["ok"])
        self.assertEqual([r["ok"] for r in out["files"]], [True, False])

    def test_shipped_workbooks_validate(self):
        wbdir = os.path.join(SKILL, "workbooks")
        for name in sorted(os.listdir(wbdir)):
            code, out = run("validate", os.path.join(wbdir, name))
            self.assertTrue(out["ok"], f"{name}: {out['errors']}")


    def test_github_actions_found_in_a_repository_in_a_subfolder(self):
        for rel in ("shop/.github/workflows/ci.yml", ".github/workflows/ci.yml", "shop/docs/workflows.yml"):
            path = os.path.join(self.ws, *rel.split("/"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write("on: push\n")
        for rel, found in (("shop/.github/workflows/ci.yml", True), (".github/workflows/ci.yml", True),
                           ("shop/docs/workflows.yml", False)):
            code, out = run("resolve", "--workspace", self.ws, "--stage", "build", "--paths", rel, *self.dirs)
            self.assertEqual(code, 0, out)
            self.assertEqual("github-actions" in out["missing"], found, rel)


if __name__ == "__main__":
    unittest.main()
