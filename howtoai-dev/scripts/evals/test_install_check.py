"""Tests for install_check.py. Run: py -3 -I -B <this file>.

Every test uses a temporary home folder (--home) and an empty or temporary PATH (--path), so no
real settings, skills, or tools are read, and --no-probe, so no external command runs.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "install_check.py")
PLUGIN = os.path.dirname(os.path.dirname(HERE))


def run(*args):
    p = subprocess.run([sys.executable, "-I", "-B", SCRIPT, *args], capture_output=True, text=True, encoding="utf-8")
    return p.returncode, json.loads(p.stdout)


def write(path, text=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def link_dir(src, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.name == "nt":
        import _winapi
        _winapi.CreateJunction(src, dest)
    else:
        os.symlink(src, dest, target_is_directory=True)


class InstallCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="install-check-")
        self.home = os.path.join(self.tmp.name, "home")
        self.bin = os.path.join(self.tmp.name, "bin")
        os.makedirs(self.home)
        os.makedirs(self.bin)

    def tearDown(self):
        self.tmp.cleanup()

    def deps(self):
        return run("--home", self.home, "deps", "--no-probe", "--path", self.bin)

    def by_name(self, out):
        return {i["name"]: i for i in out["items"]}

    def fake_tool(self, name):
        path = os.path.join(self.bin, name + (".exe" if os.name == "nt" else ""))
        write(path)
        os.chmod(path, 0o755)

    def test_empty_home_misses_required_items(self):
        code, out = self.deps()
        items = self.by_name(out)
        self.assertEqual((code, out["deps_ok"]), (1, False))
        for name in ("git", "grilling", "skill-builder"):
            self.assertEqual(items[name]["status"], "missing", name)
            self.assertTrue(items[name]["fix"], name)
        self.assertEqual(items["devmode.py"]["for_choice"], "dev mode on")
        self.assertEqual(items["Atlassian MCP server"]["status"], "unknown")
        self.assertTrue(all(l["state"] == "missing" for l in out["dev_links"]))

    def test_required_items_present(self):
        self.fake_tool("git")
        self.fake_tool("gh")
        for name in ("grilling", "skill-builder"):
            write(os.path.join(self.home, ".claude", "skills", name, "SKILL.md"), "---\nname: x\n---\n")
        code, out = self.deps()
        items = self.by_name(out)
        self.assertEqual((code, out["deps_ok"]), (0, True), out)
        self.assertEqual((items["gh"]["status"], items["az"]["status"]), ("ok", "missing"))
        self.assertIn("not probed", items["gh"]["detail"])

    def test_skill_found_in_plugin_cache_and_pointer(self):
        write(os.path.join(self.home, ".claude", "plugins", "cache", "howtoai-mods", "howtoai", "1.0.0",
                           "skills", "grilling", "SKILL.md"))
        root = os.path.join(self.tmp.name, "howtoai")
        write(os.path.join(root, "scripts", "devmode.py"))
        write(os.path.join(self.home, ".claude", "howtoai", "install.json"),
              json.dumps({"workspace": self.tmp.name, "howtoai_root": root, "updated": "2026-11-21"}))
        _, out = self.deps()
        items = self.by_name(out)
        self.assertEqual(items["grilling"]["status"], "ok")
        self.assertEqual(items["devmode.py"]["status"], "ok")
        self.assertEqual(out["pointer_workspace"], self.tmp.name)

    def test_dev_links_states_and_hooks(self):
        skills = os.path.join(self.home, ".claude", "skills")
        link_dir(os.path.join(PLUGIN, "skills", "dev-plan"), os.path.join(skills, "dev-plan"))
        os.makedirs(os.path.join(skills, "dev-test"))
        other = os.path.join(self.tmp.name, "other-dev-build")
        os.makedirs(other)
        link_dir(other, os.path.join(skills, "dev-build"))
        write(os.path.join(self.home, ".claude", "settings.json"),
              json.dumps({"hooks": {"PreToolUse": [{"hooks": [{"command": "x/hooks/dev_test_first.py"},
                                                              {"command": "x/hooks/dev_safe_target.py"}]}]}}))
        _, out = self.deps()
        states = {l["name"]: l["state"] for l in out["dev_links"]}
        self.assertEqual((states["dev-plan"], states["dev-test"], states["dev-build"], states["goldfish-spec.md"]),
                         ("ok", "real", "elsewhere", "missing"))
        hooks = self.by_name(out)["dev hooks"]
        self.assertEqual((hooks["status"], hooks["in_settings"], hooks["plugin_installed"], hooks["fix"]), ("ok", True, False, ""))
        write(os.path.join(self.home, ".claude", "plugins", "installed_plugins.json"),
              json.dumps({"plugins": {"howtoai-dev@howtoai-mods": [{}]}}))
        _, out = self.deps()
        hooks = self.by_name(out)["dev hooks"]
        self.assertTrue(hooks["plugin_installed"] and hooks["in_settings"])
        self.assertIn("twice", hooks["fix"])
        self.assertEqual(len(out["checks_skipped"]), 4)

    def test_index_of_the_plugin_is_clean(self):
        code, out = run("index")
        self.assertEqual(code, 0, out["problems"] if "problems" in out else out)
        self.assertGreater(out["links_checked"], 20)
        self.assertGreater(out["keys_checked"], 5)

    def test_index_reports_drift(self):
        root = os.path.join(self.tmp.name, "plugin")
        shutil.copytree(os.path.join(PLUGIN, "skills", "dev-core", "assets"), os.path.join(root, "skills", "dev-core", "assets"))
        write(os.path.join(root, "skills", "dev-plan", "stages", "split.md"), "# Split\n\n## Send to the tracker\n")
        write(os.path.join(root, "docs", "install-index.md"),
              "# Index\n\n- [ok](../skills/dev-plan/stages/split.md#send-to-the-tracker)\n"
              "- [gone](../skills/dev-plan/stages/split.md#write-the-work-items)\n"
              "- [missing](../skills/dev-plan/stages/none.md)\n"
              "- keys `tracker.kind`, `tracker.gitlab_repo`, `plan.publish`, `os.path`, file `plan.md`\n- [self](#index)\n")
        code, out = run("--plugin-root", root, "index")
        self.assertEqual(code, 1)
        self.assertEqual(out["problems"], [
            "link to a missing file: ../skills/dev-plan/stages/none.md",
            "missing heading #write-the-work-items in " + os.path.join("skills", "dev-plan", "stages", "split.md"),
            "setting key not in the schema: tracker.gitlab_repo"])
        self.assertEqual(out["keys_checked"], 3)
        self.assertEqual(out["names_skipped"], ["os.path: its first part is not a top-level setting", "plan.md: a file name"])


def git_bash():
    for p in (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files (x86)\Git\bin\bash.exe"):
        if os.path.isfile(p):
            return p
    return shutil.which("bash") if os.name != "nt" else None


class HookCommandTests(unittest.TestCase):
    def test_install_hook_commands_run_and_fail_open(self):
        """The dev-mode hook command lines in INSTALL.md run as written (lesson L-131)."""
        bash = git_bash()
        if not bash:
            self.skipTest("no Git Bash or bash found")
        import re
        with open(os.path.join(PLUGIN, "INSTALL.md"), encoding="utf-8") as f:
            text = f.read()
        cmd = re.search(r'command `(F="<plugins folder>/howtoai-dev/hooks/dev_test_first\.py";[^`]+)`', text)
        self.assertTrue(cmd, "hook command not found in INSTALL.md")
        plugins = os.path.dirname(PLUGIN).replace("\\", "/")
        for hook in ("dev_test_first.py", "dev_safe_target.py"):
            line = cmd.group(1).replace("<plugins folder>", plugins).replace("dev_test_first.py", hook)
            with tempfile.TemporaryDirectory(prefix="hook-cmd-") as cwd:
                p = subprocess.run([bash, "-c", line], input=json.dumps({"tool_name": "Edit", "cwd": cwd,
                                   "tool_input": {"file_path": os.path.join(cwd, "x.txt")}}),
                                   capture_output=True, text=True, encoding="utf-8", cwd=cwd, timeout=60)
            self.assertEqual(p.returncode, 0, (hook, p.stderr))


if __name__ == "__main__":
    unittest.main()
