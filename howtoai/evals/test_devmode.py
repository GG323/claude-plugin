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
- [Skills and agents](#skills-and-agents)

## Project

A test.

## Workspace layout

- [AGENTS](AGENTS/) - source folder.

## Skills and agents

None apply.
"""


DEFAULT_ON = (
    "Dev mode is on: the installed and created skills, agents, and tools are kept in this workspace's files, under "
    "version control, and the global folders `~/.claude/skills/` and `~/.claude/agents/` hold only links to them (a "
    "directory junction or symbolic link per skill, a symbolic link per agent). Git version control should be enabled."
)
DEFAULT_OFF = (
    "Dev mode is off: the installed skills, agents, and tools come from normal plugin installs, and created ones are "
    "saved in the usual `.claude` folders. Git version control should be enabled."
)


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

    def write_agents(self, text=AGENTS_MD, newline="\n"):
        with open(os.path.join(self.ws, "AGENTS.md"), "w", encoding="utf-8", newline=newline) as f:
            f.write(text)

    def read_agents(self):
        with open(os.path.join(self.ws, "AGENTS.md"), encoding="utf-8") as f:
            return f.read()

    def write_entry(self, *labelled):
        text = AGENTS_MD.replace("## Skills and agents",
                                 "## Dev mode\n\n%s\n\n## Skills and agents" % "\n".join(labelled))
        self.write_agents(text)
        return text

    def set_on(self, *extra):
        if not os.path.exists(os.path.join(self.ws, "AGENTS.md")):
            self.write_agents()
        return self.run_cmd("set", "--dev-mode", "on", "--workspace", self.ws, "--as-of", "2026-11-21",
                            "--git-version-control", "on", "--write", *extra)

    # ---- status and set --------------------------------------------------------------

    def test_status_without_pointer(self):
        r = self.run_cmd("status", code=1)
        self.assertFalse(r["ok"])
        self.assertIsNone(r["setting"])
        self.assertIsNone(r["dev_mode"], "unknown is never reported as off")
        self.assertEqual([x["setting"] for x in r["needs_setting"]], ["Git version control", "Dev mode"])
        self.assertIsNone(r["paths"])
        self.assertEqual(r["links"], [])

    def test_set_needs_agents_md(self):
        r = self.run_cmd("set", "--dev-mode", "on", "--workspace", self.ws, "--write", code=1)
        self.assertIn("AGENTS.md", r["error"])

    def test_set_preview_writes_nothing(self):
        self.write_agents()
        r = self.run_cmd("set", "--dev-mode", "on", "--git-version-control", "on", "--workspace", self.ws)
        self.assertEqual(r["entry_action"], "insert")
        self.assertIn("+- **Dev mode:** on", r["diff"])
        self.assertFalse(r["written"])
        self.assertEqual(self.read_agents(), AGENTS_MD)
        self.assertFalse(os.path.exists(os.path.join(self.claude, "howtoai", "install.json")))

    def test_set_writes_entry_and_pointer(self):
        r = self.set_on()
        self.assertTrue(r["written"])
        text = self.read_agents()
        self.assertIn("## Dev mode\n\n%s\n\n- **Git version control:** on\n- **Dev mode:** on\n" % DEFAULT_ON, text)
        self.assertIn("- **Dev mode:** on\n- **Source folder:** [AGENTS/](AGENTS/)\n- **Plugins folder:** [AGENTS/plugins/](AGENTS/plugins/)", text)
        order = [text.index(h) for h in ("## Workspace layout", "## Dev mode", "## Skills and agents")]
        self.assertEqual(order, sorted(order))
        self.assertIn("- [Workspace layout](#workspace-layout)\n- [Dev mode](#dev-mode)\n- [Skills and agents]", text)
        with open(os.path.join(self.claude, "howtoai", "install.json"), encoding="utf-8") as f:
            pointer = json.load(f)
        self.assertEqual(set(pointer), {"workspace", "howtoai_root", "updated"})
        s = self.run_cmd("status")
        self.assertTrue(s["dev_mode"])
        self.assertEqual(s["setting"]["source_folder"], "AGENTS")
        self.assertEqual(s["setting"]["plugins_folder"], "AGENTS/plugins")
        self.assertEqual(s["paths"]["skills"], os.path.join(os.path.abspath(self.ws), "AGENTS", "skills"))
        again = self.set_on()
        self.assertFalse(again["changed"])
        self.assertFalse(again["pointer_changed"])
        self.assertFalse(again["written"])

    def test_status_reads_named_workspace_without_pointer(self):
        self.write_agents(AGENTS_MD.replace("## Skills and agents",
                                            "## Dev mode\n\nText.\n\n- **Git version control:** on\n- **Dev mode:** on\n- **Source folder:** `My tools/`\n\n## Skills and agents"))
        s = self.run_cmd("status", "--workspace", self.ws)
        self.assertIsNone(s["pointer"])
        self.assertEqual(s["setting"]["source_folder"], "My tools")
        self.assertEqual(s["setting"]["plugins_folder"], "My tools/plugins")

    def test_status_parses_link_with_spaces(self):
        self.set_on("--source-folder", "My tools", "--plugins-folder", "PLUGIN/claude-plugin")
        self.assertIn("- **Source folder:** [My tools/](<My tools/>)", self.read_agents())
        s = self.run_cmd("status")["setting"]
        self.assertEqual((s["source_folder"], s["plugins_folder"]), ("My tools", "PLUGIN/claude-plugin"))

    def test_malformed_entry_refused(self):
        self.write_agents(AGENTS_MD.replace("## Skills and agents", "## Dev mode\n\nOn, I think.\n\n## Skills and agents"))
        r = self.run_cmd("status", "--workspace", self.ws, code=1)
        self.assertIn("on or off", r["error"])
        self.assertEqual([x["setting"] for x in r["needs_setting"]], ["Git version control", "Dev mode"])
        r = self.run_cmd("set", "--dev-mode", "on", "--git-version-control", "on", "--workspace", self.ws, "--write")
        self.assertEqual(r["entry_action"], "replace")
        self.assertNotIn("On, I think.", self.read_agents())
        self.assertTrue(self.run_cmd("status", "--workspace", self.ws)["dev_mode"])

    def test_set_keeps_folders_and_switches_off(self):
        self.set_on("--source-folder", "Agents", "--plugins-folder", "PLUGIN/claude-plugin")
        r = self.run_cmd("set", "--dev-mode", "on", "--workspace", self.ws)
        self.assertEqual(r["setting"]["plugins_folder"], "PLUGIN/claude-plugin")
        self.assertFalse(r["changed"])
        r = self.run_cmd("set", "--dev-mode", "off", "--workspace", self.ws, "--write")
        self.assertEqual(r["entry_action"], "replace")
        text = self.read_agents()
        self.assertIn("## Dev mode\n\n%s\n\n- **Git version control:** on\n- **Dev mode:** off\n" % DEFAULT_OFF, text)
        self.assertNotIn("- **Dev mode:** on", text)
        self.assertEqual(text.count("## Dev mode"), 1)
        self.assertEqual(text.count("- [Dev mode](#dev-mode)"), 1)
        self.assertFalse(self.run_cmd("status")["dev_mode"])

    def test_set_rejects_bad_folders(self):
        self.write_agents()
        self.run_cmd("set", "--dev-mode", "on", "--workspace", self.ws, "--source-folder", "../out", code=2)
        self.run_cmd("set", "--dev-mode", "on", "--workspace", self.ws, "--source-folder", self.tmp, code=2)
        self.run_cmd("set", "--dev-mode", "on", code=2)
        self.run_cmd("set", "--dev-mode", "on", "--workspace", os.path.join(self.tmp, "missing"), code=2)

    def test_set_keeps_crlf(self):
        self.write_agents(newline="\r\n")
        self.set_on()
        with open(os.path.join(self.ws, "AGENTS.md"), "rb") as f:
            raw = f.read()
        self.assertNotIn(b"\r\r", raw)
        self.assertEqual(raw.count(b"\n"), raw.count(b"\r\n"))

    # ---- Git version control ---------------------------------------------------------

    def test_git_setting_off_is_kept_with_dev_mode_off(self):
        self.write_agents()
        args = ("set", "--dev-mode", "off", "--workspace", self.ws, "--write")
        self.run_cmd(*args, "--git-version-control", "off")
        text = self.read_agents()
        self.assertIn("- **Git version control:** off\n- **Dev mode:** off\n", text)
        self.assertNotIn("should be enabled", text)
        s = self.run_cmd("status")
        self.assertIs(s["setting"]["git_version_control"], False)
        self.assertIs(s["dev_mode"], False)
        self.assertIsNone(s["git"])
        self.assertFalse(self.run_cmd(*args)["changed"], "a rerun without the option keeps off")

    def test_dev_mode_refuses_git_off(self):
        self.write_agents()
        r = self.run_cmd("set", "--dev-mode", "on", "--git-version-control", "off", "--workspace", self.ws, "--write", code=1)
        self.assertIn("Dev mode needs Git version control on", r["error"])
        self.assertEqual(self.read_agents(), AGENTS_MD)

    def test_dev_mode_never_switches_git_on_silently(self):
        self.write_agents()
        self.run_cmd("set", "--dev-mode", "off", "--git-version-control", "off", "--workspace", self.ws, "--write")
        before = self.read_agents()
        r = self.run_cmd("set", "--dev-mode", "on", "--workspace", self.ws, "--write", code=1)
        self.assertIn("Dev mode needs Git version control on", r["error"])
        self.assertEqual(self.read_agents(), before)
        self.set_on()
        self.assertIn(DEFAULT_ON, self.read_agents())

    def test_hand_edited_dev_on_git_off_is_an_error(self):
        self.write_entry("- **Git version control:** off", "- **Dev mode:** on")
        r = self.run_cmd("status", "--workspace", self.ws, code=1)
        self.assertIn("Dev mode needs Git version control on", r["error"])
        self.assertIsNone(r["setting"])
        self.assertIsNone(r["paths"])

    def test_missing_git_line_is_an_error(self):
        for dev in ("on", "off"):
            text = self.write_entry("- **Dev mode:** %s" % dev)
            r = self.run_cmd("status", "--workspace", self.ws, code=1)
            self.assertEqual([x["setting"] for x in r["needs_setting"]], ["Git version control"])
            self.assertIn("on or off", r["error"])
            r = self.run_cmd("set", "--dev-mode", dev, "--workspace", self.ws, "--write", code=1)
            self.assertIn("--git-version-control", r["error"])
            self.assertEqual(self.read_agents(), text, "set must not guess")

    def test_missing_dev_mode_line_is_an_error_and_repairable(self):
        self.write_entry("- **Git version control:** on", "- **Source folder:** `My tools/`")
        r = self.run_cmd("status", "--workspace", self.ws, code=1)
        self.assertEqual([x["setting"] for x in r["needs_setting"]], ["Dev mode"])
        self.assertIsNone(r["dev_mode"])
        r = self.run_cmd("set", "--dev-mode", "on", "--workspace", self.ws, "--write")
        self.assertEqual(r["setting"]["source_folder"], "My tools", "a repair keeps the folders")

    def test_bad_dev_mode_value_is_an_error(self):
        self.write_entry("- **Git version control:** on", "- **Dev mode:** yes")
        r = self.run_cmd("status", "--workspace", self.ws, code=1)
        self.assertIn("'yes'", r["error"])

    def test_no_section_is_an_error(self):
        self.write_agents()
        r = self.run_cmd("status", "--workspace", self.ws, code=1)
        self.assertEqual([x["setting"] for x in r["needs_setting"]], ["Git version control", "Dev mode"])
        self.assertIsNone(r["dev_mode"])
        self.run_cmd("set", "--dev-mode", "off", "--workspace", self.ws, "--write", code=1)
        self.assertEqual(self.read_agents(), AGENTS_MD)

    def test_link_needs_a_valid_setting(self):
        src = self.skill("demo")
        r = self.run_cmd("link", "--source", src, "--write", code=1)
        self.assertIn("needs_setting", r)
        self.assertFalse(os.path.lexists(os.path.join(self.claude, "skills", "demo")))

    def test_status_still_lists_links_on_error(self):
        self.set_on()
        self.run_cmd("link", "--source", self.skill("demo"), "--write")
        self.write_agents()
        r = self.run_cmd("status", code=1)
        self.assertEqual([x["name"] for x in r["links"]], ["demo"], "unlink must stay possible")

    def test_git_setting_bad_value_refused_by_status_and_set(self):
        text = AGENTS_MD.replace("## Skills and agents", "## Dev mode\n\n- **Git version control:** maybe\n- **Dev mode:** on\n"
                                 "- **Source folder:** `My tools/`\n\n## Skills and agents")
        self.write_agents(text)
        self.assertIn("Git version control", self.run_cmd("status", "--workspace", self.ws, code=1)["error"])
        self.run_cmd("set", "--dev-mode", "on", "--workspace", self.ws, "--write", code=1)
        self.assertEqual(self.read_agents(), text, "a bad value must not reset the folders")
        r = self.run_cmd("set", "--dev-mode", "on", "--git-version-control", "on", "--workspace", self.ws, "--write")
        self.assertEqual(r["setting"]["source_folder"], "My tools", "an explicit repair keeps the folders")

    def test_git_health_without_repository(self):
        self.set_on()
        g = self.run_cmd("status")["git"]
        self.assertFalse(g["ok"])
        self.assertIn("not in a Git repository", " ".join(g["problems"]))
        self.assertFalse(os.path.exists(os.path.join(self.ws, ".git")), "the script never runs git init")

    @unittest.skipUnless(shutil.which("git"), "needs git")
    def test_git_health_repository_ignored_and_nested(self):
        self.set_on()
        subprocess.run(["git", "init", "-q", self.ws], check=True)
        self.assertEqual(self.run_cmd("status")["git"]["problems"], [])
        with open(os.path.join(self.ws, ".gitignore"), "w", encoding="utf-8") as f:
            f.write("AGENTS/plugins/\n")
        g = self.run_cmd("status")["git"]
        self.assertFalse(g["ok"])
        self.assertIn("ignored", " ".join(g["problems"]))
        plugins = os.path.join(self.ws, "AGENTS", "plugins")
        os.makedirs(plugins)
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
        order = [text.index(h) for h in ("## Workspace layout", "## Markdown conventions", "### Instruction flow", "## Skills and agents")]
        self.assertEqual(order, sorted(order))
        self.assertIn("- [Markdown conventions](#markdown-conventions)\n  - [Markdown structure](#markdown-structure)", text)
        r = self.run_cmd("agents-md", "--workspace", self.ws, "--write")
        self.assertFalse(r["changed"])
        self.assertEqual(r["blocks"][0]["action"], "none")

    def test_agents_md_after_set_keeps_order(self):
        self.set_on()
        self.run_cmd("agents-md", "--workspace", self.ws, "--write")
        text = self.read_agents()
        order = [text.index(h) for h in ("## Workspace layout", "## Dev mode", "## Markdown conventions", "## Skills and agents")]
        self.assertEqual(order, sorted(order))
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
        with open(os.path.join(other, "AGENTS.md"), "w", encoding="utf-8") as f:
            f.write(AGENTS_MD)
        return other

    def set_other(self, other, dev_mode):
        return self.run_cmd("set", "--dev-mode", dev_mode, "--git-version-control", "on", "--workspace", other,
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
        os.remove(os.path.join(self.ws, "AGENTS.md"))
        other = self.other_workspace()
        self.assertEqual(self.set_other(other, "off")["pointer"]["workspace"], os.path.abspath(other))

    def test_dev_mode_off_takes_over_a_pointer_without_a_valid_setting(self):
        for number, text in enumerate((AGENTS_MD, AGENTS_MD.replace(
                "## Skills and agents", "## Dev mode\n\n- **Dev mode:** on\n\n## Skills and agents"))):
            with self.subTest(number=number):
                self.set_on()
                self.write_agents(text)
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


if __name__ == "__main__":
    unittest.main()
