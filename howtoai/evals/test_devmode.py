"""Tests for scripts/devmode.py. Every test works in its own temporary folder.

Run: py -3 -I -B -m unittest discover -s "<howtoai>/evals" -v
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "devmode.py")

AGENTS_MD = """# Test workspace

## Contents

- [Project](#project)
- [Workspace layout](#workspace-layout)
- [Installed skills](#installed-skills)

## Project

A test.

## Workspace layout

- [AGENTS](AGENTS/) - source folder.

## Installed skills

None apply.
"""


class DevModeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="devmode-test-")
        self.claude = os.path.join(self.tmp, "claude")
        self.ws = os.path.join(self.tmp, "workspace")
        os.makedirs(self.claude)
        os.makedirs(self.ws)

    def tearDown(self):
        # Remove links first so rmtree never follows a junction into a target.
        for folder in ("skills", "agents"):
            d = os.path.join(self.claude, folder)
            if os.path.isdir(d):
                for n in os.listdir(d):
                    p = os.path.join(d, n)
                    if os.path.islink(p) or (hasattr(os.path, "isjunction") and os.path.isjunction(p)):
                        os.rmdir(p) if os.path.isdir(p) else os.unlink(p)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_cmd(self, *args, code=0):
        r = subprocess.run([sys.executable, "-I", "-B", SCRIPT, "--claude-dir", self.claude] + list(args),
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, code, r.stdout + r.stderr)
        return json.loads(r.stdout) if r.stdout.strip() else {}

    def skill(self, name, base=None):
        d = os.path.join(base or os.path.join(self.ws, "AGENTS", "skills"), name)
        os.makedirs(d)
        with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write("---\nname: %s\n---\n" % name)
        return d

    def write_agents(self, text=AGENTS_MD, newline="\n", ws=None):
        with open(os.path.join(ws or self.ws, "AGENTS.md"), "w", encoding="utf-8", newline=newline) as f:
            f.write(text)

    def read_agents(self):
        with open(os.path.join(self.ws, "AGENTS.md"), encoding="utf-8") as f:
            return f.read()

    def settings_file(self, ws=None):
        return os.path.join(ws or self.ws, "AGENTS", "settings.json")

    def write_settings(self, data, ws=None):
        path = self.settings_file(ws)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(data if isinstance(data, str) else json.dumps(data))
        return path

    def read_settings(self, ws=None):
        with open(self.settings_file(ws), encoding="utf-8") as f:
            return json.load(f)

    def set_on(self, *extra):
        return self.run_cmd("set", "--dev-mode", "on", "--workspace", self.ws, "--as-of", "2026-11-21", "--write", *extra)

    # ---- status and set --------------------------------------------------------------

    def test_status_without_pointer(self):
        r = self.run_cmd("status", code=1)
        self.assertFalse(r["ok"])
        self.assertIsNone(r["setting"])
        self.assertIsNone(r["dev_mode"], "unknown is never reported as off")
        self.assertEqual([x["setting"] for x in r["needs_setting"]], ["Dev mode"])
        self.assertIsNone(r["paths"])
        self.assertEqual(r["links"], [])

    def test_set_needs_no_agents_md(self):
        r = self.set_on()
        self.assertTrue(r["written"])
        self.assertFalse(os.path.exists(os.path.join(self.ws, "AGENTS.md")), "set never writes AGENTS.md")
        self.assertEqual(self.read_settings(), {"howtoai": {"dev_mode": True}})

    def test_set_preview_writes_nothing(self):
        r = self.run_cmd("set", "--dev-mode", "on", "--workspace", self.ws)
        self.assertIn('"dev_mode": true', r["diff"])
        self.assertIn("AGENTS/settings.json", r["diff"])
        self.assertFalse(r["written"])
        self.assertFalse(os.path.exists(self.settings_file()))
        self.assertFalse(os.path.exists(os.path.join(self.claude, "howtoai", "install.json")))

    def test_set_writes_the_key_and_pointer(self):
        r = self.set_on()
        self.assertTrue(r["written"])
        self.assertEqual((r["key"], r["setting"]), ("howtoai", {"dev_mode": True, "source_folder": "AGENTS",
                                                                 "plugins_folder": "AGENTS/plugins"}))
        self.assertEqual(self.read_settings(), {"howtoai": {"dev_mode": True}}, "defaults are not written")
        with open(os.path.join(self.claude, "howtoai", "install.json"), encoding="utf-8") as f:
            pointer = json.load(f)
        self.assertEqual(set(pointer), {"workspace", "howtoai_root", "updated"})
        s = self.run_cmd("status")
        self.assertTrue(s["dev_mode"])
        self.assertTrue(s["settings_file_exists"])
        self.assertEqual(s["setting"]["source_folder"], "AGENTS")
        self.assertEqual(s["setting"]["plugins_folder"], "AGENTS/plugins")
        self.assertEqual(s["paths"]["skills"], os.path.join(os.path.abspath(self.ws), "AGENTS", "skills"))
        again = self.set_on()
        self.assertFalse(again["changed"])
        self.assertFalse(again["pointer_changed"])
        self.assertFalse(again["written"])

    def test_set_keeps_other_tools_keys(self):
        other = {"howtoai-dev": {"tracker": {"kind": "markdown"}, "workbooks": {"technologies": ["python"]}}}
        self.write_settings(other)
        self.set_on()
        data = self.read_settings()
        self.assertEqual(data["howtoai-dev"], other["howtoai-dev"])
        self.assertEqual(data["howtoai"], {"dev_mode": True})
        self.run_cmd("set", "--dev-mode", "off", "--workspace", self.ws, "--write")
        self.assertEqual(self.read_settings(), {"howtoai-dev": other["howtoai-dev"], "howtoai": {"dev_mode": False}})

    def test_set_refuses_a_broken_settings_file(self):
        for text in ("{ broken", "[1, 2]"):
            with self.subTest(text=text):
                self.write_settings(text)
                self.run_cmd("set", "--dev-mode", "on", "--workspace", self.ws, "--write", code=1)
                self.run_cmd("status", "--workspace", self.ws, code=1)
                with open(self.settings_file(), encoding="utf-8") as f:
                    self.assertEqual(f.read(), text, "other tools' settings are never overwritten")

    def test_status_reads_named_workspace_without_pointer(self):
        self.write_settings({"howtoai": {"dev_mode": True, "source_folder": "My tools/"}})
        s = self.run_cmd("status", "--workspace", self.ws)
        self.assertIsNone(s["pointer"])
        self.assertEqual(s["setting"]["source_folder"], "My tools")
        self.assertEqual(s["setting"]["plugins_folder"], "My tools/plugins")

    def test_folders_are_written_only_when_not_default(self):
        self.set_on("--source-folder", "My tools", "--plugins-folder", "PLUGIN/claude-plugin")
        self.assertEqual(self.read_settings()["howtoai"],
                         {"dev_mode": True, "source_folder": "My tools", "plugins_folder": "PLUGIN/claude-plugin"})
        s = self.run_cmd("status")["setting"]
        self.assertEqual((s["source_folder"], s["plugins_folder"]), ("My tools", "PLUGIN/claude-plugin"))

    def test_set_keeps_folders_and_switches_off(self):
        self.set_on("--source-folder", "Agents", "--plugins-folder", "PLUGIN/claude-plugin")
        r = self.run_cmd("set", "--dev-mode", "on", "--workspace", self.ws)
        self.assertEqual(r["setting"]["plugins_folder"], "PLUGIN/claude-plugin")
        self.assertFalse(r["changed"])
        r = self.run_cmd("set", "--dev-mode", "off", "--workspace", self.ws, "--write")
        self.assertTrue(r["changed"])
        self.assertEqual(r["previous"]["dev_mode"], True)
        self.assertIs(self.read_settings()["howtoai"]["dev_mode"], False)
        self.assertFalse(self.run_cmd("status")["dev_mode"])

    def test_set_rejects_bad_folders(self):
        self.run_cmd("set", "--dev-mode", "on", "--workspace", self.ws, "--source-folder", "../out", code=2)
        self.run_cmd("set", "--dev-mode", "on", "--workspace", self.ws, "--source-folder", self.tmp, code=2)
        self.run_cmd("set", "--dev-mode", "on", code=2)
        self.run_cmd("set", "--dev-mode", "on", "--workspace", os.path.join(self.tmp, "missing"), code=2)
        self.run_cmd("set", "--dev-mode", "on", "--workspace", self.ws, "--git-version-control", "on", code=2)

    # ---- an invalid setting ----------------------------------------------------------

    def test_missing_key_is_an_error(self):
        self.write_settings({"howtoai-dev": {}})
        r = self.run_cmd("status", "--workspace", self.ws, code=1)
        self.assertEqual([x["setting"] for x in r["needs_setting"]], ["Dev mode"])
        self.assertIsNone(r["dev_mode"])
        self.assertIn("on or off", r["error"])

    def test_bad_dev_mode_value_is_an_error_and_repairable(self):
        self.write_settings({"howtoai": {"dev_mode": "yes", "source_folder": "My tools"}})
        r = self.run_cmd("status", "--workspace", self.ws, code=1)
        self.assertIn("'yes'", r["error"])
        self.assertIsNone(r["setting"])
        self.assertIsNone(r["paths"])
        r = self.run_cmd("set", "--dev-mode", "on", "--workspace", self.ws, "--write")
        self.assertEqual(r["setting"]["source_folder"], "My tools", "a repair keeps the folders")

    def test_a_key_that_is_not_an_object_is_an_error(self):
        self.write_settings({"howtoai": True})
        r = self.run_cmd("status", "--workspace", self.ws, code=1)
        self.assertIn("must be an object", r["error"])
        self.run_cmd("set", "--dev-mode", "off", "--workspace", self.ws, "--write")
        self.assertEqual(self.read_settings(), {"howtoai": {"dev_mode": False}})

    def test_link_needs_a_valid_setting(self):
        src = self.skill("demo")
        r = self.run_cmd("link", "--source", src, "--write", code=1)
        self.assertIn("needs_setting", r)
        self.assertFalse(os.path.lexists(os.path.join(self.claude, "skills", "demo")))

    def test_status_still_lists_links_on_error(self):
        self.set_on()
        self.run_cmd("link", "--source", self.skill("demo"), "--write")
        self.write_settings({})
        r = self.run_cmd("status", code=1)
        self.assertEqual([x["name"] for x in r["links"]], ["demo"], "unlink must stay possible")

    # ---- Git -------------------------------------------------------------------------

    def test_git_health_without_repository(self):
        self.set_on()
        g = self.run_cmd("status")["git"]
        self.assertFalse(g["ok"])
        self.assertTrue(g["required"])
        self.assertIn("not in a Git repository", " ".join(g["problems"]))
        self.assertFalse(os.path.exists(os.path.join(self.ws, ".git")), "the script never runs git init")

    def test_git_is_advice_only_with_dev_mode_off(self):
        self.run_cmd("set", "--dev-mode", "off", "--workspace", self.ws, "--write")
        g = self.run_cmd("status", "--workspace", self.ws)["git"]
        self.assertFalse(g["required"])
        self.assertEqual(list(g["repos"]), ["settings"], "with dev mode off only the settings file is checked")

    @unittest.skipUnless(shutil.which("git"), "needs git")
    def test_git_health_repository_ignored_and_nested(self):
        self.set_on()
        subprocess.run(["git", "init", "-q", self.ws], check=True)
        self.assertEqual(self.run_cmd("status")["git"]["problems"], [])
        with open(os.path.join(self.ws, ".gitignore"), "w", encoding="utf-8") as f:
            f.write("AGENTS/plugins/\n")
        g = self.run_cmd("status")["git"]
        self.assertTrue(g["ok"], "an ignored plugins folder that is not cloned yet is only a note")
        plugins = os.path.join(self.ws, "AGENTS", "plugins")
        os.makedirs(plugins)
        g = self.run_cmd("status")["git"]
        self.assertFalse(g["ok"])
        self.assertIn("ignored", " ".join(g["problems"]))
        subprocess.run(["git", "init", "-q", plugins], check=True)
        self.assertTrue(self.run_cmd("status")["git"]["ok"], "a folder with its own repository is versioned there")

    # ---- link and unlink -------------------------------------------------------------

    def test_link_preview_then_write(self):
        self.set_on()
        src = self.skill("demo")
        dest = os.path.join(self.claude, "skills", "demo")
        r = self.run_cmd("link", "--source", src)
        self.assertEqual(r["action"], "create")
        self.assertTrue(r["in_source"])
        self.assertFalse(os.path.lexists(dest))
        r = self.run_cmd("link", "--source", src, "--write")
        self.assertEqual(r["state"], "link-ok")
        self.assertTrue(os.path.isfile(os.path.join(dest, "SKILL.md")))
        r = self.run_cmd("link", "--source", src, "--write")
        self.assertEqual(r["action"], "none")
        links = self.run_cmd("status")["links"]
        self.assertEqual([(x["name"], x["state"], x["in_workspace"]) for x in links], [("demo", "link-ok", True)])

    def test_link_never_replaces_real_folder(self):
        self.set_on()
        src = self.skill("demo")
        real = self.skill("demo", base=os.path.join(self.claude, "skills"))
        r = self.run_cmd("link", "--source", src, "--write", "--replace-link", code=1)
        self.assertIn("never replaced", r["error"])
        self.assertTrue(os.path.isfile(os.path.join(real, "SKILL.md")))
        self.assertEqual(self.run_cmd("status")["links"][0]["state"], "real")

    def test_link_replace_only_with_flag(self):
        self.set_on()
        old = self.skill("demo", base=os.path.join(self.tmp, "old"))
        new = self.skill("demo")
        self.run_cmd("link", "--source", old, "--write")
        r = self.run_cmd("link", "--source", new, "--write", code=1)
        self.assertIn("--replace-link", r["error"])
        r = self.run_cmd("link", "--source", new, "--write", "--replace-link")
        self.assertEqual(r["action"], "replace")
        self.assertEqual(r["state"], "link-ok")
        self.assertTrue(os.path.isfile(os.path.join(old, "SKILL.md")), "old target must stay")

    def test_broken_link_reported(self):
        self.set_on()
        gone = self.skill("demo", base=os.path.join(self.tmp, "gone"))
        self.run_cmd("link", "--source", gone, "--write")
        shutil.rmtree(gone)
        self.assertEqual(self.run_cmd("status")["links"][0]["state"], "link-broken")

    def test_unlink_removes_only_links(self):
        self.set_on()
        src = self.skill("demo")
        dest = os.path.join(self.claude, "skills", "demo")
        self.run_cmd("link", "--source", src, "--write")
        r = self.run_cmd("unlink", "--dest", dest)
        self.assertEqual(r["action"], "remove")
        self.assertTrue(os.path.lexists(dest), "preview must not remove")
        self.run_cmd("unlink", "--dest", dest, "--write")
        self.assertFalse(os.path.lexists(dest))
        self.assertTrue(os.path.isfile(os.path.join(src, "SKILL.md")), "target must stay")
        real = self.skill("other", base=os.path.join(self.claude, "skills"))
        self.run_cmd("unlink", "--dest", real, "--write", code=1)
        self.assertTrue(os.path.isdir(real))
        self.run_cmd("unlink", "--dest", src, "--write", code=1)

    def test_link_rejects_non_skill(self):
        self.set_on()
        d = os.path.join(self.ws, "notaskill")
        os.makedirs(d)
        self.run_cmd("link", "--source", d, code=1)
        self.run_cmd("link", "--source", os.path.join(self.ws, "missing.md"), code=1)

    def test_link_agent_file(self):
        self.set_on()
        agents = os.path.join(self.ws, "AGENTS", "agents")
        os.makedirs(agents)
        src = os.path.join(agents, "helper.md")
        with open(src, "w", encoding="utf-8") as f:
            f.write("---\nname: helper\n---\n")
        r = subprocess.run([sys.executable, "-I", "-B", SCRIPT, "--claude-dir", self.claude, "link", "--source", src, "--write"],
                           capture_output=True, text=True, encoding="utf-8")
        res = json.loads(r.stdout)
        if r.returncode == 1 and "Developer Mode" in res.get("error", ""):
            self.skipTest("file links need Developer Mode on this computer")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual((res["kind"], res["link"]), ("agent", "symlink"))
        self.assertTrue(os.path.islink(os.path.join(self.claude, "agents", "helper.md")))

    # ---- check-deps ------------------------------------------------------------------

    def test_check_deps_shape(self):
        names = {i["name"]: i for i in self.run_cmd("check-deps")["items"]}
        self.assertEqual(names["python"]["status"], "ok")
        for s in ("skill-builder", "skill-finder", "skill-audit", "skill-design", "brain-dump", "grilling", "handover"):
            self.assertEqual(names[s]["status"], "ok", s)
        self.assertEqual(names["update-config"]["status"], "unknown")

    # ---- agents-md -------------------------------------------------------------------

    def test_agents_md_needs_file(self):
        self.run_cmd("agents-md", "--workspace", self.ws, code=1)

    def test_agents_md_insert_and_rerun(self):
        self.write_agents()
        r = self.run_cmd("agents-md", "--workspace", self.ws)
        self.assertTrue(r["changed"])
        self.assertEqual(self.read_agents(), AGENTS_MD, "preview must not write")
        r = self.run_cmd("agents-md", "--workspace", self.ws, "--write")
        self.assertEqual((r["blocks"][0]["action"], r["blocks"][0]["state"]), ("insert", "missing"))
        text = self.read_agents()
        order = [text.index(h) for h in ("## Workspace layout", "## Markdown conventions", "### Instruction flow", "## Installed skills")]
        self.assertEqual(order, sorted(order))
        self.assertIn("- [Markdown conventions](#markdown-conventions)\n  - [Markdown structure](#markdown-structure)", text)
        r = self.run_cmd("agents-md", "--workspace", self.ws, "--write")
        self.assertFalse(r["changed"])
        self.assertEqual(r["blocks"][0]["action"], "none")

    def test_agents_md_after_set_keeps_the_setting(self):
        self.write_agents()
        self.set_on()
        self.assertEqual(self.read_agents(), AGENTS_MD, "set never touches AGENTS.md")
        self.run_cmd("agents-md", "--workspace", self.ws, "--write")
        self.assertNotIn("Dev mode", self.read_agents())
        self.assertTrue(self.run_cmd("status")["dev_mode"])

    def test_agents_md_differing_baseline_kept(self):
        self.write_agents()
        self.run_cmd("agents-md", "--workspace", self.ws, "--write")
        self.write_agents(self.read_agents().replace("### Instruction flow\n", "### Instruction flow\n\nA local rule.\n"))
        r = self.run_cmd("agents-md", "--workspace", self.ws, "--write")
        base = r["blocks"][0]
        self.assertEqual((base["action"], base["state"]), ("kept", "differs"))
        self.assertIn("A local rule.", base["diff"])
        self.assertIn("A local rule.", self.read_agents())
        r = self.run_cmd("agents-md", "--workspace", self.ws, "--write", "--replace-baseline")
        self.assertEqual(r["blocks"][0]["action"], "replace")
        self.assertNotIn("A local rule.", self.read_agents())

    def other_workspace(self):
        other = os.path.join(os.path.dirname(self.ws), "other-" + os.path.basename(self.ws))
        os.makedirs(other)
        self.addCleanup(__import__("shutil").rmtree, other, True)
        return other

    def set_other(self, other, dev_mode):
        return self.run_cmd("set", "--dev-mode", dev_mode, "--workspace", other,
                            "--as-of", "2026-11-22", "--write")

    def test_dev_mode_off_keeps_the_pointers_workspace(self):
        self.set_on()
        other = self.other_workspace()
        r = self.set_other(other, "off")
        self.assertTrue(r["written"])
        self.assertFalse(r["pointer_changed"])
        self.assertEqual(r["pointer"]["workspace"], os.path.abspath(self.ws))
        self.assertTrue(self.run_cmd("status")["dev_mode"])
        self.assertFalse(self.run_cmd("status", "--workspace", other)["dev_mode"])

    def test_dev_mode_on_moves_the_pointer(self):
        self.set_on()
        other = self.other_workspace()
        self.assertEqual(self.set_other(other, "on")["pointer"]["workspace"], os.path.abspath(other))

    def test_dev_mode_off_takes_over_a_dead_pointer(self):
        self.set_on()
        os.remove(self.settings_file())
        other = self.other_workspace()
        self.assertEqual(self.set_other(other, "off")["pointer"]["workspace"], os.path.abspath(other))

    def test_dev_mode_off_takes_over_a_pointer_without_a_valid_setting(self):
        for number, data in enumerate(({}, {"howtoai": {"source_folder": "AGENTS"}})):
            with self.subTest(number=number):
                self.set_on()
                self.write_settings(data)
                other = self.other_workspace()
                r = self.set_other(other, "off")
                self.assertEqual(r["pointer"]["workspace"], os.path.abspath(other))
                self.assertFalse(self.run_cmd("status")["dev_mode"])
                __import__("shutil").rmtree(other)

    def test_dev_mode_off_repairs_a_malformed_pointer(self):
        self.set_on()
        for value in (5, "relative"):
            with open(os.path.join(self.claude, "howtoai", "install.json"), "w", encoding="utf-8") as f:
                json.dump({"workspace": value}, f)
            other = self.other_workspace()
            self.assertEqual(self.set_other(other, "off")["pointer"]["workspace"], os.path.abspath(other))
            __import__("shutil").rmtree(other)

    def test_dev_mode_off_writes_the_first_pointer(self):
        other = self.other_workspace()
        self.assertEqual(self.set_other(other, "off")["pointer"]["workspace"], os.path.abspath(other))

    # ---- multi-repo workspaces, shared clones, workspace links -------------------

    def fake_clone(self, base):
        os.makedirs(os.path.join(base, ".claude-plugin"))
        os.makedirs(os.path.join(base, "howtoai"))
        os.makedirs(os.path.join(base, ".git"))
        with open(os.path.join(base, ".claude-plugin", "marketplace.json"), "w", encoding="utf-8") as f:
            f.write("{}")
        return base

    def test_multi_repo_root_is_a_note_not_a_problem(self):
        for name in ("app", "infra"):
            os.makedirs(os.path.join(self.ws, name, ".git"))
        self.run_cmd("set", "--dev-mode", "off", "--workspace", self.ws, "--write")
        g = self.run_cmd("status", "--workspace", self.ws)["git"]
        self.assertTrue(g["ok"], g)
        self.assertEqual(g["layout"], "multi-repo")
        self.assertEqual([os.path.basename(p) for p in g["nested_repos"]], ["app", "infra"])
        self.assertIn("stays local", " ".join(g["notes"]))
        self.assertFalse(os.path.exists(os.path.join(self.ws, ".git")), "the script never runs git init")

    def test_plain_folder_without_repositories_is_still_a_problem(self):
        os.makedirs(os.path.join(self.ws, "notes"))
        self.set_on()
        g = self.run_cmd("status")["git"]
        self.assertFalse(g["ok"])
        self.assertEqual(g["layout"], "single-repo")
        self.assertIn("not in a Git repository", " ".join(g["problems"]))

    def test_shared_clone_keeps_the_owners_pointer(self):
        clone = self.fake_clone(os.path.join(self.ws, "AGENTS", "plugins"))
        self.set_on()
        other = self.other_workspace()
        os.makedirs(os.path.join(other, "repo", ".git"))
        r = self.run_cmd("set", "--dev-mode", "on", "--workspace", other,
                         "--plugins-folder", clone, "--as-of", "2026-11-25", "--write")
        self.assertEqual(r["pointer"]["workspace"], os.path.abspath(self.ws), "the clone's owner keeps the pointer")
        self.assertFalse(r["pointer_changed"])
        self.assertTrue(r["paths"]["plugins_shared"])
        self.assertEqual(r["setting"]["source_folder"], "AGENTS")
        self.assertEqual(self.read_settings(other)["howtoai"]["plugins_folder"], clone.replace("\\", "/"),
                         "an absolute shared clone is written as it is")
        st = self.run_cmd("status", "--workspace", other)
        self.assertTrue(st["dev_mode"])
        self.assertEqual(os.path.normcase(os.path.normpath(st["paths"]["plugins"])),
                         os.path.normcase(os.path.normpath(clone)))
        self.assertEqual(st["git"]["problems"], [], st["git"])

    def test_absolute_plugins_folder_must_be_a_clone(self):
        plain = os.path.join(self.tmp, "not-a-clone")
        os.makedirs(plain)
        r = self.run_cmd("set", "--dev-mode", "on", "--workspace", self.ws,
                         "--plugins-folder", plain, code=2)
        self.assertIn("howtoai-mods", r["error"])

    def test_a_harness_folder_is_never_a_link_source(self):
        self.set_on()
        src = self.skill("local-tool", os.path.join(self.ws, ".claude", "skills"))
        r = self.run_cmd("link", "--source", src, "--write", code=1)
        self.assertTrue(r["in_harness_folder"])
        self.assertIn("AGENTS/", r["error"])
        self.assertFalse(os.path.lexists(os.path.join(self.claude, "skills", "local-tool")))

    def test_workspace_link_for_a_workspace_only_skill(self):
        self.set_on()
        src = self.skill("uvp-only")
        r = self.run_cmd("link", "--source", src, "--into", "workspace", "--workspace", self.ws, "--write")
        dest = os.path.join(self.ws, ".claude", "skills", "uvp-only")
        self.assertEqual((r["action"], r["into"], os.path.normcase(r["dest"])), ("create", "workspace", os.path.normcase(dest)))
        self.assertTrue(r["in_source"])
        self.assertTrue(os.path.isfile(os.path.join(dest, "SKILL.md")), "the workspace link resolves")
        self.assertFalse(os.path.lexists(os.path.join(self.claude, "skills", "uvp-only")), "nothing global")
        self.assertEqual(self.run_cmd("link", "--source", src, "--into", "workspace", "--workspace", self.ws)["action"], "none")
        r = self.run_cmd("unlink", "--dest", dest, "--write")
        self.assertTrue(r["written"])
        self.assertFalse(os.path.lexists(dest))
        self.assertTrue(os.path.isfile(os.path.join(src, "SKILL.md")), "unlink never touches the target")

    def test_workspace_link_needs_a_workspace_and_other_harnesses(self):
        self.set_on()
        src = self.skill("tool-x")
        self.run_cmd("link", "--source", src, "--into", "workspace", code=2)
        r = self.run_cmd("link", "--source", src, "--into", "workspace", "--workspace", self.ws, "--harness", "copilot")
        self.assertEqual(os.path.normcase(r["dest"]), os.path.normcase(os.path.join(self.ws, ".copilot", "skills", "tool-x")))
        r = self.run_cmd("link", "--source", src, "--harness", "agents")
        self.assertEqual(os.path.normcase(r["dest"]),
                         os.path.normcase(os.path.join(os.path.dirname(self.claude), ".agents", "skills", "tool-x")))

    def test_workspace_link_needs_no_entry_in_that_workspace(self):
        self.set_on()
        other = self.other_workspace()
        src = self.skill("local-only", os.path.join(other, "AGENTS", "skills"))
        r = self.run_cmd("link", "--source", src, "--into", "workspace", "--workspace", other)
        self.assertEqual(r["action"], "create")
        self.assertTrue(r["in_source"])

    def test_ignored_plugins_folder_not_cloned_yet_is_a_note(self):
        os.makedirs(os.path.join(self.ws, "AGENTS", ".git"))
        with open(os.path.join(self.ws, "AGENTS", ".gitignore"), "w", encoding="utf-8") as f:
            f.write("plugins/\nstate/\n")
        os.makedirs(os.path.join(self.ws, "app", ".git"))
        self.run_cmd("set", "--dev-mode", "on", "--workspace", self.ws, "--write")
        g = self.run_cmd("status", "--workspace", self.ws)["git"]
        self.assertNotIn("plugins", " ".join(g["problems"]))
        self.assertIn("not cloned yet", " ".join(g["notes"]))

    def test_unlink_refuses_a_link_outside_harness_folders(self):
        r = self.run_cmd("unlink", "--dest", os.path.join(self.ws, "AGENTS", "skills", "x"), code=1)
        self.assertIn("harness folder", r["error"])


if __name__ == "__main__":
    unittest.main()
