"""Regression tests for behaviour that crosses the dev skills' scripts and hooks.

Run: py -3 -I -B <this file>. Each test builds its own temporary workspace and reads no real settings
except where a script has no switch for them; nothing outside the temporary folder is written.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(PLUGIN, "skills")
PY = sys.executable.replace("\\", "/")
PASS_CMD = f'"{PY}" -c "print(1)"'


def script(skill, name, *args):
    path = os.path.join(SKILLS, skill, "scripts", name)
    p = subprocess.run([sys.executable, "-I", "-B", path, *map(str, args)], capture_output=True, text=True, encoding="utf-8")
    return p.returncode, json.loads(p.stdout)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def git(cwd, *args):
    return subprocess.run(["git", "-c", f"safe.directory={cwd.replace(os.sep, '/')}", *args], cwd=cwd,
                          capture_output=True, text=True, check=True).stdout


def repository(path, files, commit=True):
    os.makedirs(path, exist_ok=True)
    for rel, text in files.items():
        write(os.path.join(path, rel), text)
    git(path, "init", "-q")
    git(path, "config", "core.autocrlf", "false")
    if commit:
        git(path, "add", "-A")
        git(path, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false",
            "commit", "-q", "-m", "base")


class Workspace(unittest.TestCase):
    settings = {}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="dev-regressions-", ignore_cleanup_errors=True)
        self.ws = os.path.join(self.tmp.name, "ws")
        write(os.path.join(self.ws, "AGENTS.md"), "# Workspace\n")
        write(os.path.join(self.ws, "AGENTS", "settings", "dev", "settings.json"), json.dumps(self.settings))
        self.user = os.path.join(self.tmp.name, "user.json")
        write(self.user, "{}")

    def tearDown(self):
        self.tmp.cleanup()

    def new_change(self):
        code, out = script("dev-core", "devcore.py", "new-change", "--workspace", self.ws, "--title", "t",
                           "--slug", "t", "--user-file", self.user)
        self.assertEqual(code, 0, out)
        return out["change_dir"]

    def patch(self, change, patch):
        code, out = script("dev-core", "devcore.py", "state", change, "--patch", json.dumps(patch), "--user-file", self.user)
        self.assertEqual(code, 0, out)


class SeveralRepositories(Workspace):
    settings = {"build": {"gate": [{"name": "check", "command": PASS_CMD, "source": "ci"}]}}

    def new_change(self):
        change = super().new_change()
        self.patch(change, {"append": {"test_runs": {"n": 1, "route": "red-check", "wi": None, "result": "red",
                                                     "passed": 0, "failed": 1, "flaky": 0}}})
        return change

    def two_repositories(self):
        repository(os.path.join(self.ws, "shop"), {"src/a.py": "a = 1\n", "keep.txt": "keep\n"})
        repository(os.path.join(self.ws, "infra"), {"main.tf": "x = 1\n"})

    def build(self, *args):
        return script("dev-build", "build.py", *args, "--n", "1", "--user-file", self.user)

    def review(self, change, *args):
        return script("dev-review", "review.py", "diff", change, "--round", "1", "--user-file", self.user, *args)

    def test_build_lists_hunks_from_each_repository(self):
        self.two_repositories()
        change = self.new_change()
        code, out = self.build("start", change, "--wi", "whole")
        self.assertEqual(code, 0, out)
        write(os.path.join(self.ws, "shop", "src", "a.py"), "a = 2\n")
        write(os.path.join(self.ws, "infra", "main.tf"), "x = 2\n")
        code, out = self.build("hunks", change)
        self.assertEqual(code, 0, out)
        self.assertEqual(sorted(h["id"] for h in out["hunks"]), ["infra/main.tf:1-1", "shop/src/a.py:1-1"])

    def test_gate_tree_changes_when_any_repository_changes(self):
        self.two_repositories()
        change = self.new_change()
        self.build("start", change, "--wi", "whole")
        gate = ("gate", change, "--label", "after", "--name", "check", "--command", PASS_CMD)
        first = self.build(*gate)[1]
        write(os.path.join(self.ws, "infra", "main.tf"), "x = 3\n")
        second = self.build(*gate)[1]
        self.assertTrue(first.get("ok") and second.get("ok"), (first, second))
        self.assertNotEqual(first["tree"], second["tree"])

    def test_review_diff_has_workspace_relative_paths(self):
        self.two_repositories()
        change = self.new_change()
        write(os.path.join(self.ws, "shop", "src", "a.py"), "a = 2\n")
        write(os.path.join(self.ws, "infra", "new.tf"), "y = 1\n")
        code, out = self.review(change)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["files"], ["infra/new.tf", "shop/src/a.py"])
        patch = read(out["patch"])
        self.assertIn("+++ b/shop/src/a.py", patch)
        self.assertIn("+++ b/infra/new.tf", patch)

    def test_re_review_diffs_from_the_fix_build_in_each_repository(self):
        self.two_repositories()
        change = self.new_change()
        write(os.path.join(self.ws, "shop", "src", "a.py"), "a = 2\n")
        write(os.path.join(change, "review-1.md"), "# review\n")
        code, out = self.build("start", change, "--wi", "whole", "--route", "fix", "--review", "review-1.md")
        self.assertEqual(code, 0, out)
        write(os.path.join(self.ws, "infra", "main.tf"), "x = 2\n")
        code, out = self.review(change, "--since-build", "1")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["files"], ["infra/main.tf"])

    def test_repository_without_a_commit(self):
        repository(os.path.join(self.ws, "fresh"), {"a.txt": "a\n"}, commit=False)
        code, out = self.review(self.new_change())
        self.assertEqual(code, 0, out)
        self.assertEqual(out["files"], ["fresh/a.txt"])

    def test_repository_without_a_commit_ignores_the_callers_input(self):
        repository(os.path.join(self.ws, "fresh"), {"a.txt": "a\n"}, commit=False)
        change = self.new_change()
        path = os.path.join(SKILLS, "dev-review", "scripts", "review.py")
        p = subprocess.Popen([sys.executable, "-I", "-B", path, "diff", change, "--round", "1", "--user-file", self.user],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            p.wait(timeout=20)  # the caller's input stays open the whole time
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
            else:
                p.kill()
            p.wait()
            self.fail("review.py waits for the caller's input")
        finally:
            p.stdin.close()
            p.stdout.close()
        self.assertEqual(p.returncode, 0)

    def test_workspace_repository_with_a_repository_inside(self):
        repository(os.path.join(self.ws, "inner"), {"b.txt": "b\n"})
        repository(self.ws, {".gitignore": "inner/\n", "top.txt": "t\n"})
        write(os.path.join(self.ws, "inner", "b.txt"), "b2\n")
        write(os.path.join(self.ws, "top.txt"), "t2\n")
        code, out = self.review(self.new_change())
        self.assertEqual(code, 0, out)
        self.assertEqual(out["files"], ["inner/b.txt", "top.txt"])

    def test_unignored_repository_inside_is_not_read_as_a_link(self):
        repository(self.ws, {"top.txt": "t\n"})
        repository(os.path.join(self.ws, "inner"), {"b.txt": "b\n"})
        write(os.path.join(self.ws, "inner", "b.txt"), "b2\n")
        code, out = self.review(self.new_change())
        self.assertEqual(code, 0, out)
        self.assertEqual(out["files"], ["inner/b.txt"])

    def gate_out(self):
        return script("dev-deploy", "deploy.py", "gate", "--workspace", self.ws, "--target", "sandbox")[1]

    def test_deploy_gate_fails_on_uncommitted_work_in_a_repository(self):
        self.two_repositories()
        write(os.path.join(self.ws, "shop", "keep.txt"), "changed\n")
        out = self.gate_out()
        self.assertTrue(any("shop/keep.txt" in p for p in out["problems"]), out)

    def test_deploy_gate_fails_without_a_repository(self):
        out = self.gate_out()
        self.assertTrue(any("no git repository" in p for p in out["problems"]), out)

    def test_deploy_gate_accepts_clean_repositories(self):
        self.two_repositories()
        out = self.gate_out()
        self.assertIn("work committed", out["checks_run"])
        self.assertFalse(any("uncommitted" in p or "git repository" in p for p in out["problems"]), out)


class RepositoryEdges(Workspace):
    settings = {"build": {"gate": [{"name": "check", "command": PASS_CMD, "source": "ci"}]}}

    def diff(self, change, ws=None):
        return script("dev-review", "review.py", "diff", change, "--round", "1", "--user-file", self.user)

    def gate_out(self, ws=None):
        return script("dev-deploy", "deploy.py", "gate", "--workspace", ws or self.ws, "--target", "sandbox")[1]

    def uncommitted(self, out):
        return [p for p in out["problems"] if "target" not in p]

    def submodule(self):
        repository(os.path.join(self.ws, "sub"), {"s.txt": "1\n"})
        head = git(os.path.join(self.ws, "sub"), "rev-parse", "HEAD").strip()
        git(self.ws, "init", "-q")
        git(self.ws, "update-index", "--add", "--cacheinfo", f"160000,{head},sub")
        git(self.ws, "add", "AGENTS.md")
        git(self.ws, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "base")
        sub = os.path.join(self.ws, "sub")
        write(os.path.join(sub, "s.txt"), "2\n")
        git(sub, "add", "-A")
        git(sub, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "next")

    def test_submodule_pointer_change_fails_the_deploy_gate(self):
        self.submodule()
        self.assertTrue(any("sub" in p for p in self.uncommitted(self.gate_out())))

    def test_submodule_pointer_change_is_reviewed(self):
        self.submodule()
        code, out = self.diff(self.new_change())
        self.assertEqual((code, out.get("files")), (0, ["sub"]), out)

    def test_repository_deleted_after_the_snapshot_is_reported(self):
        repository(os.path.join(self.ws, "shop"), {"a.txt": "a\n"})
        repository(os.path.join(self.ws, "infra"), {"b.txt": "b\n"})
        change = self.new_change()
        code, out = script("dev-build", "build.py", "start", change, "--n", "1", "--wi", "whole", "--route", "fix",
                           "--review", "review-1.md", "--user-file", self.user)
        if code:
            write(os.path.join(change, "review-1.md"), "# review\n")
            code, out = script("dev-build", "build.py", "start", change, "--n", "1", "--wi", "whole", "--route", "fix",
                               "--review", "review-1.md", "--user-file", self.user)
        self.assertEqual(code, 0, out)
        os.rename(os.path.join(self.ws, "infra"), os.path.join(self.tmp.name, "gone"))
        code, out = script("dev-build", "build.py", "hunks", change, "--n", "1", "--user-file", self.user)
        self.assertEqual((code, [h["id"] for h in out.get("hunks", [])]), (0, ["infra:repository-removed"]), out)
        code, out = self.diff(change) if code else script("dev-review", "review.py", "diff", change, "--round", "2",
                                                         "--since-build", "1", "--user-file", self.user)
        self.assertEqual((code, out.get("files")), (0, ["infra"]), out)
        self.assertIn("infra", read(out["patch"]))

    def test_files_outside_every_repository_are_named(self):
        repository(os.path.join(self.ws, "shop"), {"a.txt": "a\n"})
        write(os.path.join(self.ws, "deploy.sh"), "echo\n")
        self.assertIn("deploy.sh", json.dumps(self.gate_out()["checks_skipped"]))

    def test_broken_repository_fails_the_gate(self):
        repository(os.path.join(self.ws, "shop"), {"a.txt": "a\n"})
        write(os.path.join(self.ws, "other", ".git", "HEAD"), "garbage\n")
        self.assertTrue(any("other" in p for p in self.uncommitted(self.gate_out())))

    def test_empty_git_folder_is_no_repository(self):
        repository(os.path.join(self.ws, "shop"), {"a.txt": "a\n"})
        os.makedirs(os.path.join(self.ws, "stray", ".git"))
        write(os.path.join(self.ws, "shop", "a.txt"), "b\n")
        code, out = self.diff(self.new_change())
        self.assertEqual((code, out.get("files")), (0, ["shop/a.txt"]), out)

    def test_repository_named_bin_is_checked(self):
        repository(os.path.join(self.ws, "shop"), {"a.txt": "a\n"})
        repository(os.path.join(self.ws, "bin"), {"tool.sh": "1\n"})
        write(os.path.join(self.ws, "bin", "tool.sh"), "2\n")
        self.assertTrue(any("bin/tool.sh" in p for p in self.uncommitted(self.gate_out())))

    def test_workspace_below_the_root_with_a_repository_inside(self):
        repository(os.path.join(self.ws, "my repo"), {"r.txt": "r\n"})
        repository(self.tmp.name, {".gitignore": "user.json\n"}, commit=False)
        git(self.tmp.name, "add", ".gitignore", "ws/AGENTS.md", "ws/AGENTS/settings")
        git(self.tmp.name, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "base")
        self.assertEqual(self.uncommitted(self.gate_out()), [])

    def test_patch_below_the_root_uses_workspace_paths(self):
        write(os.path.join(self.ws, "x.txt"), "1\n")
        repository(self.tmp.name, {".gitignore": "user.json\n"})
        write(os.path.join(self.ws, "x.txt"), "2\n")
        code, out = self.diff(self.new_change())
        self.assertEqual((code, out.get("files")), (0, ["x.txt"]), out)
        self.assertIn("+++ b/x.txt", read(out["patch"]))

    def test_repository_name_with_a_semicolon(self):
        repository(os.path.join(self.ws, "a;b"), {"a.txt": "a\n"})
        repository(os.path.join(self.ws, "c"), {"c.txt": "c\n"})
        write(os.path.join(self.ws, "a;b", "a.txt"), "z\n")
        code, out = self.diff(self.new_change())
        self.assertEqual((code, out.get("files")), (0, ["a;b/a.txt"]), out)

    def test_ignored_but_tracked_records_do_not_break_the_tree(self):
        change = self.new_change()
        repository(self.ws, {"a.txt": "a\n"})
        write(os.path.join(self.ws, ".gitignore"), "dev-plans/\nAGENTS/\n")
        code, first = self.diff(change)
        self.assertEqual(code, 0, first)
        tree = json.loads(read(first["changed"]))["tree"]
        write(os.path.join(change, "notes.md"), "n\n")
        code, second = self.diff(change)
        self.assertEqual(code, 0, second)
        self.assertEqual(json.loads(read(second["changed"]))["tree"], tree)


class RepositoryNesting(Workspace):
    def diff(self, change):
        return script("dev-review", "review.py", "diff", change, "--round", "1", "--user-file", self.user)

    def gate_out(self):
        return script("dev-deploy", "deploy.py", "gate", "--workspace", self.ws, "--target", "sandbox")[1]

    def link(self, outer, name):
        head = git(os.path.join(outer, name), "rev-parse", "HEAD").strip()
        git(outer, "update-index", "--add", "--cacheinfo", f"160000,{head},{name}")
        git(outer, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "link")

    def test_repository_inside_a_submodule(self):
        sub = os.path.join(self.ws, "sub")
        repository(sub, {"s.txt": "1\n"})
        repository(os.path.join(sub, "deep"), {"d.txt": "1\n"})
        self.link(sub, "deep")
        git(self.ws, "init", "-q")
        git(self.ws, "add", "AGENTS.md")
        self.link(self.ws, "sub")
        write(os.path.join(sub, "deep", "d.txt"), "2\n")
        code, out = self.diff(self.new_change())
        self.assertEqual((code, out.get("files")), (0, ["sub/deep/d.txt"]), out)

    def test_untracked_repository_inside_a_repository_inside(self):
        repository(self.ws, {"top.txt": "t\n"})
        repository(os.path.join(self.ws, "a"), {"a.txt": "1\n"})
        repository(os.path.join(self.ws, "a", "b"), {"b.txt": "1\n"})
        write(os.path.join(self.ws, "a", "b", "b.txt"), "2\n")
        code, out = self.diff(self.new_change())
        self.assertEqual((code, out.get("files")), (0, ["a/b/b.txt"]), out)

    def test_repository_added_during_a_build_is_one_hunk(self):
        repository(self.ws, {".gitignore": "cache/\n"})
        change = self.new_change()
        write(os.path.join(change, "review-1.md"), "# review\n")
        code, out = script("dev-build", "build.py", "start", change, "--n", "1", "--wi", "whole", "--route", "fix",
                           "--review", "review-1.md", "--user-file", self.user)
        self.assertEqual(code, 0, out)
        repository(os.path.join(self.ws, "cache", "clone"), {"one.txt": "1\n", "two.txt": "2\n"})
        code, out = script("dev-build", "build.py", "hunks", change, "--n", "1", "--user-file", self.user)
        self.assertEqual((code, [h["id"] for h in out.get("hunks", [])]), (0, ["cache/clone:repository-added"]), out)

    def test_broken_root_stops_the_review(self):
        write(os.path.join(self.ws, ".git", "HEAD"), "garbage\n")
        repository(os.path.join(self.ws, "shop"), {"a.txt": "a\n"})
        self.assertEqual(self.diff(self.new_change())[0], 1)

    def test_non_ascii_repository_name_passes_the_gate(self):
        repository(self.ws, {"top.txt": "t\n"})
        repository(os.path.join(self.ws, "Kund\u00e9"), {"k.txt": "k\n"})
        self.assertFalse(any("uncommitted" in p for p in self.gate_out()["problems"]))

    def test_workspace_ignored_by_the_repository_around_it(self):
        repository(self.tmp.name, {".gitignore": "ws/\nuser.json\n"})
        out = self.gate_out()
        self.assertTrue(any("no git repository" in p for p in out["problems"]), out)


class RedCheckPerItem(Workspace):
    def start(self, runs):
        repository(self.ws, {"a.txt": "a\n"})
        change = self.new_change()
        for n, (wi, result) in enumerate(runs, 1):
            self.patch(change, {"append": {"test_runs": {"n": n, "route": "red-check", "wi": wi, "result": result,
                                                         "passed": 0, "failed": 1, "flaky": 0}}})
        return script("dev-build", "build.py", "start", change, "--n", "1", "--wi", "whole", "--user-file", self.user)[0]

    def test_one_failed_item_stops_the_whole_plan(self):
        self.assertEqual(self.start([(1, "red-failed"), (2, "red")]), 1)

    def test_a_later_whole_plan_red_replaces_the_items(self):
        self.assertEqual(self.start([(1, "red-failed"), (None, "red")]), 0)


class RedCheck(Workspace):
    def start(self, *results):
        repository(os.path.join(self.ws, "shop"), {"a.txt": "a\n"})
        change = self.new_change()
        for n, result in enumerate(results, 1):
            self.patch(change, {"append": {"test_runs": {"n": n, "route": "red-check", "wi": None, "result": result,
                                                         "passed": 0, "failed": 1, "flaky": 0}}})
        return script("dev-build", "build.py", "start", change, "--n", "1", "--wi", "whole", "--user-file", self.user)

    def test_failed_red_check_stops_the_build(self):
        code, out = self.start("red-failed")
        self.assertEqual(code, 1, out)
        self.assertIn("red check", out["error"])

    def test_later_real_red_lets_the_build_start(self):
        code, out = self.start("red-failed", "red")
        self.assertEqual(code, 0, out)


class RedCheckMatching(Workspace):
    def start(self, runs, wi):
        repository(self.ws, {"a.txt": "a\n"})
        change = self.new_change()
        for n, (run_wi, result) in enumerate(runs, 1):
            self.patch(change, {"append": {"test_runs": {"n": n, "route": "red-check", "wi": run_wi, "result": result,
                                                         "passed": 0, "failed": 1, "flaky": 0}}})
        return script("dev-build", "build.py", "start", change, "--n", "1", "--wi", wi, "--user-file", self.user)

    def test_no_red_check_stops_the_build(self):
        self.assertEqual(self.start([], "whole")[0], 1)

    def test_failed_whole_plan_check_stops_a_work_item(self):
        self.assertEqual(self.start([(None, "red-failed")], "1")[0], 1)

    def test_failed_work_item_check_stops_the_whole_plan(self):
        self.assertEqual(self.start([(1, "red-failed")], "whole")[0], 1)

    def test_whole_plan_red_counts_for_a_work_item(self):
        self.assertEqual(self.start([(None, "red")], "1")[0], 0)

    def test_a_later_item_red_unlocks_that_item(self):
        self.assertEqual(self.start([(None, "red-failed"), (1, "red")], "1")[0], 0)

    def test_a_later_item_red_unlocks_that_item_after_whole(self):
        self.assertEqual(self.start([("whole", "red-failed"), (1, "red")], "1")[0], 0)

    def test_a_later_failed_item_check_still_stops_that_item(self):
        self.assertEqual(self.start([(None, "red"), (1, "red-failed")], "1")[0], 1)

    def test_a_later_failed_whole_check_still_stops_that_item(self):
        self.assertEqual(self.start([(1, "red"), (None, "red-failed")], "1")[0], 1)

    def test_another_items_red_does_not_unlock_this_item(self):
        self.assertEqual(self.start([(None, "red-failed"), (2, "red")], "1")[0], 1)

    def test_one_items_red_does_not_unlock_the_whole_plan(self):
        self.assertEqual(self.start([(None, "red-failed"), (1, "red")], "whole")[0], 1)


class Findings(Workspace):
    def tally(self, kind, reviewers, scores=(), verdicts=(), extra=None):
        level = "Severity" if kind == "plan" else "Impact"
        raw = os.path.join(self.tmp.name, "raw")
        for name, rows in reviewers.items():
            text = f"| ID | {level} | Area | Change | Location | Quote | Finding | Mark | Recommendation | Handling |\n" + "| --- " * 10 + "|\n"
            for fid, severity, area, change in rows:
                text += f"| {fid} | {severity} | {area} | {change} | src/{fid}.cs:1 | \"{fid}\" | {fid} is wrong | confirmed: read | fix | ASK |\n"
            write(os.path.join(raw, name + ".md"), text)
        for name, text in (extra or {}).items():
            write(os.path.join(raw, name), text)
        if scores:
            write(os.path.join(raw, "scores.md"), "| ID | Score | Reason |\n| --- | --- | --- |\n"
                  + "".join(f"| {i} | {s} | r |\n" for i, s in scores))
        if verdicts:
            write(os.path.join(raw, "verdicts.md"), "| ID | Verdict | Impact now | Evidence |\n| --- | --- | --- | --- |\n"
                  + "".join(f"| {i} | {v} | {n} | e |\n" for i, v, n in verdicts))
        code, out = script("dev-core", "findings.py", "collect", raw, "--kind", kind)
        if code:
            return out, ""
        path = os.path.join(self.tmp.name, "round.md")
        code, out = script("dev-core", "findings.py", "tally", raw, "--kind", kind, "--round", "1", "--out", path)
        return out, read(path) if code == 0 else ""

    def test_finding_that_stands_is_kept_under_the_threshold(self):
        out, _ = self.tally("plan", {"critic": [("P1-K1", "Major", "Readiness", "in")]},
                            [("P1-K1", 60)], [("P1-K1", "Stands", "Major")])
        self.assertEqual((out["kept"], out["clean"]), (1, False))

    def test_refuted_finding_stays_out(self):
        out, _ = self.tally("plan", {"critic": [("P1-K1", "Major", "Risk", "in")]},
                            [("P1-K1", 75)], [("P1-K1", "Refuted", "none")])
        self.assertEqual((out["kept"], out.get("possible")), (0, []))

    def test_likely_risk_is_shown_as_possible(self):
        out, text = self.tally("plan", {"critic": [("P1-K1", "Nit", "Risk", "in"), ("P1-K2", "Nit", "Clarity", "in"),
                                                   ("P1-K3", "Nit", "Risk", "in")]},
                               [("P1-K1", 70), ("P1-K2", 75), ("P1-K3", 69)])
        self.assertEqual((out["kept"], out.get("possible")), (0, ["P1-K1"]))
        self.assertIn("possible, not confirmed", text)

    def test_likely_bug_outside_the_change_is_shown_as_possible(self):
        out, _ = self.tally("code", {"correctness": [("R1-C1", "Minor", "Correctness", "outside")]}, [("R1-C1", 85)])
        self.assertEqual(out.get("possible"), ["R1-C1"])

    def test_bug_confirmed_by_inspection_needs_no_score(self):
        out, text = self.tally("code", {"confirmed": [("R1-I1", "Major", "Correctness", "in")]})
        self.assertEqual((out.get("ok"), out.get("kept"), out.get("clean")), (True, 1, False), out)
        self.assertIn("| 100 |", text)

    def test_blocked_reviewer_stops_collect(self):
        out, _ = self.tally("plan", {"critic": []},
                            extra={"compliance.md": "Blocked: rules not read in full: workbook-statements.md\n"})
        self.assertFalse(out["ok"])
        self.assertIn("compliance", out["error"])

    def test_check_not_run_is_reported(self):
        out, text = self.tally("plan", {"critic": []},
                               extra={"compliance.md": "Not run: freshness (no web access)\n\nNo findings\n"})
        self.assertEqual(out.get("not_run"), ["compliance: freshness (no web access)"])
        self.assertIn("freshness (no web access)", text)


class FindingEdges(Workspace):
    def collect(self, files):
        raw = os.path.join(self.tmp.name, "raw")
        for name, text in files.items():
            write(os.path.join(raw, name), text)
        return raw, script("dev-core", "findings.py", "collect", raw, "--kind", "code")

    def table(self, fid, impact):
        return ("| ID | Impact | Area | Location | Quote | Finding | Mark | Proposed fix | Handling |\n" + "| --- " * 9 + "|\n"
                + f"| {fid} | {impact} | Correctness | src/a.cs:5 | \"page * size\" | overflow | confirmed: read | fix | ASK |\n")

    def merged(self, reviewer_impact, verdict):
        raw, (code, out) = self.collect({"compliance.md": self.table("R1-W1", reviewer_impact),
                                         "confirmed.md": self.table("R1-I1", "Major")})
        self.assertEqual(code, 0, out)
        write(os.path.join(raw, "scores.md"), "| ID | Score | Reason |\n| --- | --- | --- |\n| R1-W1 | 40 | r |\n")
        write(os.path.join(raw, "verdicts.md"),
              f"| ID | Verdict | Impact now | Evidence |\n| --- | --- | --- | --- |\n| R1-W1 | {verdict} | none | e |\n")
        return script("dev-core", "findings.py", "tally", raw, "--kind", "code", "--round", "1",
                      "--out", os.path.join(self.tmp.name, "r.md"))[1]

    def test_proof_survives_a_merge(self):
        for impact, verdict in (("Minor", "Stands"), ("Major", "Refuted"), ("Critical", "Refuted")):
            out = self.merged(impact, verdict)
            self.assertEqual((out.get("kept"), out.get("clean")), (1, False), (impact, out))

    def test_blocked_is_seen_in_any_form(self):
        for line in ("- Blocked: rules not read", "blocked: rules not read", "> **Blocked:** rules not read"):
            self.assertEqual(self.collect({"compliance.md": line + "\n"})[1][0], 1, line)

    def test_reply_without_table_or_no_findings_is_refused(self):
        self.assertEqual(self.collect({"compliance.md": "I could not finish.\n"})[1][0], 1)

    def test_not_run_in_a_list_is_reported(self):
        raw, (code, out) = self.collect({"compliance.md": "- Not run: freshness\n\nNo findings\n"})
        self.assertEqual(json.loads(read(os.path.join(raw, "findings.json")))["not_run"], ["compliance: freshness"])


class ScoredDuplicates(Workspace):
    def tally(self, rows, at=None, area="Correctness"):
        raw = os.path.join(self.tmp.name, "raw")
        table = "| ID | Impact | Area | Change | Location | Quote | Finding | Mark | Proposed fix | Handling |\n" + "| --- " * 10 + "|\n"
        scores = "| ID | Score | Reason |\n| --- | --- | --- |\n"
        verdicts = "| ID | Verdict | Impact now | Evidence |\n| --- | --- | --- | --- |\n"
        for fid, change, score, reason, verdict in rows:
            where = (at or {}).get(fid, "src/a.cs:1")
            table += f"| {fid} | Major | {area} | {change} | {where} | \"{fid}\" | claim of {fid} | confirmed: read | fix | ASK |\n"
            scores += f"| {fid} | {score} | {reason} |\n"
            verdicts += f"| {fid} | {verdict} | {'none' if verdict == 'Refuted' else 'Major'} | e |\n"
        write(os.path.join(raw, "correctness.md"), table)
        write(os.path.join(raw, "scores.md"), scores)
        write(os.path.join(raw, "verdicts.md"), verdicts)
        code, out = script("dev-core", "findings.py", "collect", raw, "--kind", "code")
        self.assertEqual(code, 0, out)
        path = os.path.join(self.tmp.name, "r.md")
        code, out = script("dev-core", "findings.py", "tally", raw, "--kind", "code", "--round", "1", "--out", path)
        self.assertEqual(code, 0, out)
        return out, read(path)

    def test_duplicate_of_a_shown_finding_is_one_problem_with_it(self):
        out, text = self.tally([("R1-C1", "in", 92, "read", "Stands"),
                                ("R1-T2", "in", 15, "Duplicate of R1-C1.", "Stands")])
        self.assertEqual((out["kept"], out["clean"]), (2, False))
        self.assertEqual(self.groups(out), [["R1-C1", "R1-T2"]])
        self.assertNotIn("duplicate of R1-C1", text.split("## Appendix")[-1])

    def test_duplicate_outside_the_change_is_one_problem_with_it(self):
        out, _ = self.tally([("R1-W3", "outside", 75, "read", "Stands"),
                             ("R1-X1", "outside", 15, "Duplicate of R1-W3", "Stands")])
        self.assertEqual(sorted(out["outside_change"]), ["R1-W3", "R1-X1"])
        self.assertEqual(self.groups(out), [["R1-W3", "R1-X1"]])

    def test_duplicate_of_a_refuted_finding_stays(self):
        out, _ = self.tally([("R1-C1", "in", 92, "read", "Refuted"),
                             ("R1-T2", "in", 15, "Duplicate of R1-C1.", "Stands")])
        self.assertEqual(out["kept"], 1)

    def test_duplicate_in_the_change_is_not_hidden_behind_one_outside(self):
        out, _ = self.tally([("R1-W3", "outside", 90, "read", "Stands"),
                             ("R1-T2", "in", 15, "Duplicate of R1-W3.", "Stands")])
        self.assertEqual((out["kept"], out["clean"]), (1, False))
        self.assertEqual(self.groups(out), [["R1-W3", "R1-T2"]])

    def test_two_duplicates_of_each_other_both_stay(self):
        out, _ = self.tally([("R1-C1", "in", 15, "Duplicate of R1-T2.", "Stands"),
                             ("R1-T2", "in", 15, "Duplicate of R1-C1.", "Stands")])
        self.assertEqual(out["kept"], 2)

    def assert_both_shown(self, score, reason, at=None, area="Correctness"):
        out, _ = self.tally([("R1-C1", "in", 92, "read", "Stands"), ("R1-T2", "in", score, reason, "Stands")], at, area)
        self.assertEqual(out["kept"], 2)

    def test_a_duplicate_in_part_stays(self):
        self.assert_both_shown(55, "Duplicate of R1-C1 in part; the missing auth check is separate", area="Security")

    def test_a_denied_duplicate_stays(self):
        self.assert_both_shown(60, "Duplicate of R1-C1? No, a distinct bug, but the quote is cut")

    def test_a_perhaps_duplicate_stays(self):
        self.assert_both_shown(79, "Duplicate of R1-C1 perhaps; likely a second overflow")

    def test_a_low_score_with_more_than_the_wording_stays(self):
        self.assert_both_shown(15, "Duplicate of R1-C1 in part; the missing auth check is separate")

    def test_the_wording_above_20_stays(self):
        self.assert_both_shown(21, "Duplicate of R1-C1")
        out, _ = self.tally([("R1-C1", "in", 92, "read", "Stands"), ("R1-T2", "in", 21, "Duplicate of R1-C1", "Stands")])
        self.assertEqual(self.groups(out), [["R1-C1"], ["R1-T2"]])

    def test_the_same_pattern_in_another_file_stays(self):
        self.assert_both_shown(15, "Duplicate of R1-C1: same pattern in another file",
                               {"R1-C1": "src/a.py:5", "R1-T2": "src/auth.py:90"})

    def test_the_wording_for_another_file_stays(self):
        self.assert_both_shown(15, "Duplicate of R1-C1.", {"R1-C1": "src/a.py:5", "R1-T2": "src/auth.py:90"})

    def test_a_second_file_in_the_repeat_stays(self):
        self.assert_both_shown(15, "Duplicate of R1-C1.", {"R1-C1": "src/a.py:5", "R1-T2": "src/a.py:5; src/auth.py:90"})

    def test_the_same_file_name_in_another_folder_stays(self):
        self.assert_both_shown(15, "Duplicate of R1-C1.", {"R1-C1": "a.py:5", "R1-T2": "C:/ws/auth/a.py:5"})

    def test_outside_is_not_hidden_behind_one_in_the_change(self):
        out, _ = self.tally([("R1-C1", "in", 92, "read", "Stands"),
                             ("R1-X1", "outside", 15, "Duplicate of R1-C1.", "Stands")])
        self.assertEqual((out["kept"], out["outside_change"]), (1, ["R1-X1"]))

    def test_outside_in_other_code_keeps_its_follow_up(self):
        out, _ = self.tally([("R1-C1", "in", 92, "read", "Stands"),
                             ("R1-X1", "outside", 55, "Duplicate of R1-C1 in other code", "Stands")],
                            {"R1-C1": "src/a.py:5", "R1-X1": "src/auth.py:90"})
        self.assertEqual(out["outside_change"], ["R1-X1"])

    def groups(self, out):
        return [[problem["id"], *problem["repeats"]] for problem in out.get("problems", [])]

    def test_the_problem_names_the_repeat_its_location_and_its_claim(self):
        out, text = self.tally([("R1-C1", "in", 92, "read", "Stands"),
                                ("R1-T2", "in", 20, "Duplicate of R1-C1", "Stands")],
                               {"R1-C1": "src/a.cs:1", "R1-T2": "src/a.cs:9"})
        self.assertEqual(out["kept"], 2)
        listed = text.split("### Problems")[-1].split("\n## ")[0]
        lines = [line for line in listed.splitlines() if "same problem" in line]
        self.assertEqual(len(lines), 1, text)
        for part in ("R1-T2", "src/a.cs:9", "claim of R1-T2"):
            self.assertIn(part, lines[0])

    def test_a_repeat_written_at_another_location_is_one_problem(self):
        out, _ = self.tally([("R1-C4", "in", 88, "read", "Stands"),
                             ("R1-K3", "in", 10, "Duplicate of R1-C4", "Stands")],
                            {"R1-C4": "`wi/1.md` header", "R1-K3": "WI 1, header and End-to-end check"})
        self.assertEqual((out["kept"], self.groups(out)), (2, [["R1-C4", "R1-K3"]]))

    def test_a_repeat_on_the_other_side_is_one_problem_and_keeps_its_side(self):
        out, _ = self.tally([("R1-C1", "in", 85, "read", "Stands"),
                             ("R1-S2", "outside", 10, "Duplicate of R1-C1", "Stands")])
        self.assertEqual((out["kept"], out["outside_change"]), (1, ["R1-S2"]))
        self.assertEqual(self.groups(out), [["R1-C1", "R1-S2"]])

    def test_a_chain_of_repeats_is_one_problem(self):
        out, _ = self.tally([("R1-C1", "in", 90, "read", "Stands"),
                             ("R1-T2", "in", 10, "Duplicate of R1-C1", "Stands"),
                             ("R1-W3", "in", 10, "Duplicate of R1-T2", "Stands")])
        self.assertEqual(self.groups(out), [["R1-C1", "R1-T2", "R1-W3"]])

    def test_two_repeats_of_an_original_that_is_not_shown_are_one_problem(self):
        out, _ = self.tally([("R1-C1", "in", 90, "read", "Refuted"),
                             ("R1-T2", "in", 10, "Duplicate of R1-C1", "Stands"),
                             ("R1-W3", "in", 10, "Duplicate of R1-C1", "Stands")])
        self.assertEqual(self.groups(out), [["R1-T2", "R1-W3"]])

    def test_two_duplicates_of_each_other_are_two_problems(self):
        out, _ = self.tally([("R1-C1", "in", 15, "Duplicate of R1-T2.", "Stands"),
                             ("R1-T2", "in", 15, "Duplicate of R1-C1.", "Stands")])
        self.assertEqual(self.groups(out), [["R1-C1"], ["R1-T2"]])

    def test_a_duplicate_in_part_is_its_own_problem(self):
        out, _ = self.tally([("R1-C1", "in", 92, "read", "Stands"),
                             ("R1-T2", "in", 15, "Duplicate of R1-C1 in part; another bug too", "Stands")])
        self.assertEqual(self.groups(out), [["R1-C1"], ["R1-T2"]])

    def test_scorer_is_given_the_exact_wording(self):
        self.assertIn("exactly `Duplicate of <ID>`", read(os.path.join(PLUGIN, "agents", "goldfish-scorer.md")))


class UnverifiedRepeats(Workspace):
    """F3 batch 4: a repeat the scorer marked sits under its shown original whatever its own score
    (run 6: Minor repeats scored 10 went to the appendix), and takes the original's handling."""

    def tally(self, rows, kind="code", handling=None):
        raw = os.path.join(self.tmp.name, "raw")
        level = "Severity" if kind == "plan" else "Impact"
        table = f"| ID | {level} | Area | Change | Location | Quote | Finding | Mark | Proposed fix | Handling |\n" + "| --- " * 10 + "|\n"
        scores = "| ID | Score | Reason |\n| --- | --- | --- |\n"
        for fid, impact, change, at, score, reason in rows:
            table += f"| {fid} | {impact} | Correctness | {change} | {at} | \"{fid}\" | claim of {fid} | confirmed: read | fix | {(handling or {}).get(fid, 'ASK')} |\n"
            scores += f"| {fid} | {score} | {reason} |\n"
        write(os.path.join(raw, "correctness.md"), table)
        write(os.path.join(raw, "scores.md"), scores)
        code, out = script("dev-core", "findings.py", "collect", raw, "--kind", kind)
        self.assertEqual(code, 0, out)
        path = os.path.join(self.tmp.name, "r.md")
        code, out = script("dev-core", "findings.py", "tally", raw, "--kind", kind, "--round", "1", "--out", path)
        self.assertEqual(code, 0, out)
        return out, read(path)

    @staticmethod
    def groups(out):
        return [[p["id"]] + p["repeats"] for p in out["problems"]]

    @staticmethod
    def appendix(text):
        return text.split("## Appendix")[-1] if "## Appendix" in text else ""

    def test_a_minor_repeat_scored_10_sits_under_its_shown_original(self):
        # run 6's shape: R1-W5 shown, R1-C5 "Duplicate of R1-W5" scored 10, at another line
        out, text = self.tally([("R1-W5", "Minor", "in", "e2e.ps1:8", 85, "read"),
                                ("R1-C5", "Minor", "in", "e2e.ps1:25", 10, "Duplicate of R1-W5")])
        self.assertEqual(self.groups(out), [["R1-W5", "R1-C5"]])
        self.assertEqual(out["kept"], 2)
        self.assertNotIn("R1-C5", self.appendix(text))

    def test_four_repeats_of_one_shown_minor_are_one_problem(self):
        rows = [("R1-W5", "Minor", "in", "e2e.ps1:8", 85, "read")]
        rows += [(f"R1-{x}", "Minor", "in", "e2e.ps1:26", 10, "Duplicate of R1-W5") for x in ("C5", "X5", "S2", "T1")]
        out, text = self.tally(rows)
        self.assertEqual(self.groups(out), [["R1-W5", "R1-C5", "R1-S2", "R1-T1", "R1-X5"]])

    def test_a_nit_repeat_of_a_shown_major_sits_with_it(self):
        out, _ = self.tally([("R1-W4", "Minor", "in", "e2e.ps1:62", 90, "read"),
                             ("R1-X6", "Nit", "in", "e2e.ps1:63", 10, "Duplicate of R1-W4.")])
        self.assertEqual(self.groups(out), [["R1-W4", "R1-X6"]])

    def test_a_held_chain_to_a_shown_original_is_one_problem(self):
        out, _ = self.tally([("R1-W5", "Minor", "in", "e2e.ps1:8", 85, "read"),
                             ("R1-X5", "Minor", "in", "e2e.ps1:27", 10, "Duplicate of R1-C5"),
                             ("R1-C5", "Minor", "in", "e2e.ps1:25", 10, "Duplicate of R1-W5")])
        self.assertEqual(self.groups(out), [["R1-W5", "R1-C5", "R1-X5"]])

    def test_the_counts_follow_the_moved_repeats(self):
        out, text = self.tally([("R1-W5", "Minor", "in", "e2e.ps1:8", 85, "read"),
                                ("R1-C5", "Minor", "in", "e2e.ps1:25", 10, "Duplicate of R1-W5")])
        self.assertEqual((out["kept_by_severity"]["Minor"], out["held_back"]), (2, 0))

    def test_a_plan_nit_repeat_sits_with_its_original_and_is_not_counted_held(self):
        # run 6's plan round: five Nit repeats scored 10 (their originals were held there too)
        out, text = self.tally([("P1-W4", "Nit", "in", "plan.md:92", 85, "read"),
                                ("P1-C6", "Nit", "in", "plan.md:93", 10, "Duplicate of P1-W4")], kind="plan")
        self.assertEqual(self.groups(out), [["P1-W4", "P1-C6"]])
        self.assertIn("| Nit | 2 | 2 | 0 | 0 | 0 | 0 |", text)

    def test_a_moved_auto_fix_repeat_takes_its_ask_originals_handling(self):
        # the handler's condition: a held row was never acted on; once shown it must not run apart from its original
        out, text = self.tally([("R1-W5", "Minor", "in", "e2e.ps1:8", 85, "read"),
                                ("R1-C5", "Minor", "in", "e2e.ps1:25", 10, "Duplicate of R1-W5")],
                               handling={"R1-C5": "AUTO-FIX"})
        self.assertEqual(self.groups(out), [["R1-W5", "R1-C5"]])
        row = [ln for ln in text.splitlines() if ln.startswith("| R1-C5 |")]
        self.assertEqual(len(row), 1, text)
        self.assertEqual(row[0].split("|")[-3].strip(), "ASK", row[0])
        self.assertIn("| Minor | 2 | 0 | 2 |", text)

    # controls: what must not change
    def test_control_a_repeat_of_a_held_original_stays_held(self):
        out, text = self.tally([("R1-W3", "Minor", "in", "e2e.ps1:22", 25, "read"),
                                ("R1-X6", "Nit", "in", "e2e.ps1:23", 10, "Duplicate of R1-W3")])
        self.assertEqual(out["problems"], [])
        self.assertIn("R1-X6", self.appendix(text))

    def test_control_a_low_score_without_the_wording_stays_held(self):
        out, text = self.tally([("R1-W5", "Minor", "in", "e2e.ps1:8", 85, "read"),
                                ("R1-C5", "Minor", "in", "e2e.ps1:25", 10, "Same as R1-W5")])
        self.assertEqual(self.groups(out), [["R1-W5"]])
        self.assertIn("R1-C5", self.appendix(text))

    def test_control_a_repeat_scored_above_20_stays_held(self):
        out, text = self.tally([("R1-W5", "Minor", "in", "e2e.ps1:8", 85, "read"),
                                ("R1-C5", "Minor", "in", "e2e.ps1:25", 30, "Duplicate of R1-W5")])
        self.assertEqual(self.groups(out), [["R1-W5"]])
        self.assertIn("R1-C5", self.appendix(text))

    def test_control_a_shown_minor_repeat_outside_the_change_keeps_its_side(self):
        out, text = self.tally([("R1-W5", "Minor", "in", "e2e.ps1:8", 85, "read"),
                                ("R1-C5", "Minor", "outside", "e2e.ps1:25", 10, "Duplicate of R1-W5")])
        self.assertEqual(self.groups(out), [["R1-W5", "R1-C5"]])
        problems = text.split("### Problems")[1].split("\n## ")[0]
        self.assertIn("**R1-C5** · Minor · outside the change", problems)


class EveryEntryPoint(Workspace):
    settings = {"testing": {"entry_points": [{"name": "api", "command": "dotnet test Api"},
                                             {"name": "worker", "command": "dotnet test Worker"}]}}

    def checked(self, rows, result="green", stage="review", started="test", later=None, points=None, then=()):
        """rows: the Results of a run that started at stage `started`. later: those of a run review started."""
        if points is not None:
            write(os.path.join(self.ws, "AGENTS", "settings", "dev", "settings.json"), json.dumps({"testing": {"entry_points": points}}))
        change = self.new_change()
        self.patch(change, {"stage": stage})
        reports = [rows] if later is None else [rows, later]
        for n, body in enumerate(reports, 1):
            self.patch(change, {"append": {"test_runs": {
                "n": n, "route": "run", "wi": None, "result": result, "passed": 1, "failed": 0, "flaky": 0,
                "report": f"test-run-{n}.md"}}})
            write(os.path.join(change, f"test-run-{n}.md"), "# Run\n\n## Results\n\n"
                  "| Entry point | Passed | Failed | Skipped | Flaky | Duration (s) |\n"
                  "| --- | --- | --- | --- | --- | --- |\n" + body + "\n\n## Failures\n\nnone\n")
        path = os.path.join(change, "state.json")
        state = json.loads(read(path))
        at = "2026-11-22T14:{}+01:00".format
        history = [{"at": at("00:00"), "stage": "plan"}, {"at": at("10:00"), "stage": started}]
        if stage != started:
            history.append({"at": at("20:00"), "stage": stage})
        for minute, moved in enumerate(then, 41):
            history.append({"at": at(f"{minute}:00"), "stage": moved})
            state["stage"] = moved
        state["history"] = history
        for run, when in zip(state["test_runs"], ("20:00", "30:00")):  # a run is recorded just before the stage moves
            run["at"] = at(when)
        write(path, json.dumps(state))
        p = subprocess.run([sys.executable, "-I", "-B", os.path.join(PLUGIN, "evals", "system", "check_run.py"), self.ws],
                           capture_output=True, text=True, encoding="utf-8")
        try:
            return json.loads(p.stdout).get("entry_points", {}).get("result")
        except ValueError:
            return "crashed"

    def test_a_missing_entry_point_fails(self):
        self.assertEqual(self.checked("| api: `dotnet test Api` | 13 | 0 | 0 | 0 | 1 |"), "fail")

    def test_every_entry_point_passes(self):
        self.assertEqual(self.checked("| api: `dotnet test Api` | 13 | 0 | 0 | 0 | 1 |\n| `worker`: dotnet test Worker | 5 | 0 | 0 | 0 | 1 |"), "pass")

    def test_a_row_that_was_not_run_fails(self):
        self.assertEqual(self.checked("| api | 13 | 0 | 0 | 0 | 1 |\n| worker | not run | not run | not run | not run | - |"), "fail")

    def test_a_skip_with_the_users_yes_passes(self):
        skip = "skipped (user's yes)"
        self.assertEqual(self.checked(f"| api | 13 | 0 | 0 | 0 | 1 |\n| worker | {skip} | {skip} | {skip} | {skip} | {skip} |"), "pass")

    def test_a_longer_name_is_not_the_entry_point(self):
        self.assertEqual(self.checked("| api | 13 | 0 | 0 | 0 | 1 |\n| worker-extra | 5 | 0 | 0 | 0 | 1 |"), "fail")

    BOTH = "| api | 13 | 0 | 0 | 0 | 1 |\n| worker | 5 | 0 | 0 | 0 | 1 |"
    API = "| api | 13 | 0 | 0 | 0 | 1 |"

    def test_a_progress_run_at_build_is_not_checked(self):
        self.assertEqual(self.checked(self.API, stage="build", started="build"), "not run")

    def test_reviews_full_rerun_does_not_hide_a_narrow_test_run(self):
        self.assertEqual(self.checked(self.API, later=self.BOTH), "fail")

    def test_reviews_narrow_rerun_does_not_fail_a_full_test_run(self):
        self.assertEqual(self.checked(self.BOTH, later=self.API), "pass")

    def test_review_without_a_green_test_run_fails(self):
        self.assertEqual(self.checked(self.BOTH, result="red"), "fail")

    def test_a_second_round_without_its_own_run_fails(self):
        moves = ("human-review", "build", "test", "review")
        self.assertEqual(self.checked(self.BOTH, then=moves), "fail")

    def test_a_second_round_with_a_run_started_at_build_fails(self):
        self.assertEqual(self.checked(self.BOTH, later=self.BOTH, then=("human-review", "build", "review")), "fail")

    def test_a_return_from_human_review_needs_no_new_run(self):
        self.assertEqual(self.checked(self.BOTH, then=("human-review", "review")), "pass")

    def test_two_entry_points_with_one_name_are_reported(self):
        points = [{"name": "api", "command": "dotnet test A"}, {"name": "api", "command": "dotnet test B"}]
        self.assertEqual(self.checked(self.API, points=points), "fail")

    def test_a_name_with_a_colon_is_found(self):
        self.assertEqual(self.checked("| test:unit: `npm run test:unit` | 3 | 0 | 0 | 0 | 1 |",
                                      points=[{"name": "test:unit", "command": "npm run test:unit"}]), "pass")

    def test_a_longer_name_with_a_colon_does_not_stand_in(self):
        points = [{"name": "test", "command": "npm test"}, {"name": "test:e2e", "command": "npm run test:e2e"}]
        self.assertEqual(self.checked("| test:e2e: `npm run test:e2e` | 3 | 0 | 0 | 0 | 1 |", points=points), "fail")

    def test_only_skips_fail(self):
        skip = "skipped (user's yes)"
        self.assertEqual(self.checked(f"| api | {skip} | | | | |\n| worker | {skip} | | | | |"), "fail")

    def test_a_row_of_zeros_fails(self):
        self.assertEqual(self.checked("| api | 13 | 0 | 0 | 0 | 1 |\n| worker | 0 | 0 | 0 | 0 | 1 |"), "fail")

    def test_a_run_without_counts_passes(self):
        self.assertEqual(self.checked("| api | 13 | 0 | 0 | 0 | 1 |\n| worker | ran, no counts | | | | 1 |"), "pass")

    def test_an_escaped_pipe_in_a_command_keeps_the_cells(self):
        self.assertEqual(self.checked("| api: `t \\| tee log` | 13 | 0 | 0 | 0 | 1 |\n| worker | 5 | 0 | 0 | 0 | 1 |"), "pass")

    def test_an_entry_point_without_a_name_is_reported(self):
        self.assertEqual(self.checked(self.API, points=[{"command": "dotnet test"}]), "fail")


class StaleHandOn(Workspace):
    """Hand on lets one stale reason through: the one testing_md.py gives while a change's tests are uncommitted."""

    REASON = "uncommitted changes after the last run"

    def test_the_script_gives_that_reason_for_a_new_uncommitted_test(self):
        repository(self.ws, {"tests/Old.cs": "// old\n"})
        data = os.path.join(self.tmp.name, "data.json")
        write(data, json.dumps({"run": "2100-01-01T10:00:00+00:00"}))
        folder = os.path.join(self.ws, "tests")
        self.assertEqual(script("dev-test", "testing_md.py", "update", folder, "--data", data, "--create")[0], 0)
        write(os.path.join(folder, "New.cs"), "// new\n")
        out = script("dev-test", "testing_md.py", "check", "--workspace", self.ws, "--user-file", self.user, "--dirs", "tests")[1]
        self.assertEqual([x["reason"] for x in out["stale"]], [self.REASON])

    def test_only_that_reason_does_not_hold_up_the_review(self):
        route = read(os.path.join(SKILLS, "dev-test", "routes", "run.md"))
        hand_on = route.split("\n## Hand on\n")[-1].split("\n## ")[0]
        for part in (f"fails only because a `TESTING.md` is stale for `{self.REASON}`", "name any such file in the report's Next",
                     "When anything else fails, say what failed and stop."):
            self.assertIn(part, hand_on)


class Batch2Text(unittest.TestCase):
    def run_route(self):
        return read(os.path.join(SKILLS, "dev-test", "routes", "run.md"))

    def test_setup_proposes_the_deny_rules(self):
        text = read(os.path.join(SKILLS, "dev-core", "SKILL.md"))
        setup = text[text.index("\n### Setup\n"):text.index("\n### Start a change\n")]
        for part in ("Read(**/.env.production)", "update-config", ".claude/settings.json", "never user-level", "grep -r"):
            self.assertIn(part, setup)

    def test_a_green_run_hands_on_to_the_review(self):
        text = self.run_route()
        self.assertIn("\n## Hand on\n", text)
        self.assertGreater(text.index("\n## Hand on\n"), text.index("\n## Tear down\n"))
        hand_on = text[text.index("\n## Hand on\n"):].split("\n## ")[1]
        for part in ("`dev-review`", "same turn", "TESTING.md"):
            self.assertIn(part, hand_on)

    def test_every_entry_point_runs_at_stage_test(self):
        for part in ("every configured entry point", "does not touch", "skipped (user's yes)"):
            self.assertIn(part, self.run_route())

    def test_reviewers_are_told_what_the_diff_omits(self):
        text = read(os.path.join(SKILLS, "dev-review", "references", "viewpoints.md"))
        brief = next(line for line in text.splitlines() if line.startswith("Every brief starts with"))
        for part in ("`TESTING.md`", "the plan folder", "`AGENTS/settings/`", "by design"):
            self.assertIn(part, brief)

    def test_the_install_route_proposes_the_deny_rules_too(self):
        text = read(os.path.join(PLUGIN, "INSTALL.md"))
        for part in ("secret env files", "step 5 of", "deny rules"):
            self.assertIn(part, text)

    def test_setups_contract_allows_the_approved_write(self):
        text = read(os.path.join(SKILLS, "dev-core", "SKILL.md"))
        writes = next(line for line in text.splitlines() if line.startswith("- **Writes:**"))
        self.assertIn(".claude/settings.json", writes)

    def test_a_run_of_nothing_is_not_green(self):
        self.assertIn("leaves no entry point to run", self.run_route())

    def test_an_answer_covers_only_its_entry_points(self):
        self.assertIn("covers only the entry points it was given for", self.run_route())

    def test_the_one_row_rule_is_for_stage_test(self):
        self.assertIn("For a `run` at stage `test`, Results has one row", self.run_route())
        self.assertIn("skipped (user's yes)", read(os.path.join(SKILLS, "dev-core", "assets", "templates", "test-run.md")))

    def test_the_hand_on_comes_after_verify_and_not_for_a_run_only_request(self):
        text = self.run_route().split("\n## Hand on\n")[-1]
        for part in ("Verify the output", "stop after the tests", "hands on"):
            self.assertIn(part, text)

    def test_human_review_asks_the_waiting_test_question(self):
        self.assertIn("waiting from the test run", read(os.path.join(SKILLS, "dev-review", "routes", "human-review.md")))

    def test_the_waiting_question_has_its_run_and_its_way_to_act(self):
        text = read(os.path.join(SKILLS, "dev-review", "routes", "human-review.md"))
        for part in ("latest run that started at stage `test`", "--create", "run no tests"):
            self.assertIn(part, text)
        self.assertIn("waiting:", read(os.path.join(SKILLS, "dev-core", "assets", "templates", "test-run.md")))

    def test_the_install_record_has_the_deny_rule_decision(self):
        self.assertIn("| Deny rules for secret env files |", read(os.path.join(PLUGIN, "assets", "install-record.md")))

    def test_refreshing_testing_md_classifies_the_targets_first(self):
        text = read(os.path.join(SKILLS, "dev-test", "SKILL.md"))
        row = next(line for line in text.splitlines() if line.startswith('| "Refresh TESTING.md"'))
        self.assertNotIn("#run-and-read", row)
        for part in ("#start-the-run", "classified"):
            self.assertIn(part, row)

    def test_each_test_folder_has_its_own_data_file(self):
        self.assertIn("raw/testing-md-<n>-<the folder's position>.json", self.run_route())
        self.assertIn("data file", self.run_route().split("\n## Hand on\n")[-1])
        human = read(os.path.join(SKILLS, "dev-review", "routes", "human-review.md"))
        self.assertNotIn("testing-md-<n>.json", human)
        self.assertIn("data file the waiting line names", human)

    def test_reviews_contract_allows_the_approved_testing_md(self):
        text = read(os.path.join(SKILLS, "dev-review", "SKILL.md"))
        writes = next(line for line in text.splitlines() if line.startswith("- **Writes outside the change folder:**"))
        self.assertIn("`TESTING.md`", writes)

    def test_the_scorer_sees_a_whole_duplicate_row(self):
        text = read(os.path.join(PLUGIN, "agents", "goldfish-scorer.md"))
        self.assertIn("| R1-T2 | 10 | Duplicate of R1-C1 |", text)
        self.assertIn("Reason cell", text)

    def test_reviewers_do_not_open_each_others_findings(self):
        text = read(os.path.join(SKILLS, "dev-review", "references", "viewpoints.md"))
        brief = next(line for line in text.splitlines() if line.startswith("Every brief starts with"))
        for part in ("another reviewer's", "earlier round's review", "open or search", "not what you report"):
            self.assertIn(part, brief)

    def test_one_answer_covers_a_problem_unless_it_is_split(self):
        for rel in (("dev-review", "routes", "human-review.md"), ("dev-plan", "stages", "review.md")):
            text = read(os.path.join(SKILLS, *rel))
            self.assertIn("### Problems", text)
            self.assertIn("split", text)
        self.assertIn("one line per problem", read(os.path.join(SKILLS, "dev-plan", "stages", "accept.md")))
        for name in ("review.md", "plan-review.md"):
            self.assertIn("### Problems", read(os.path.join(SKILLS, "dev-core", "assets", "templates", name)))

    def test_a_denied_read_is_not_logged_as_content(self):
        with tempfile.TemporaryDirectory(prefix="dev-audit-", ignore_cleanup_errors=True) as tmp:
            log = os.path.join(tmp, "turn.jsonl")
            ws = "C:/bed/workspace"
            use = {"type": "tool_use", "id": "t1", "name": "Read", "input": {"file_path": ws + "/shop/.env.production"}}
            back = {"type": "tool_result", "tool_use_id": "t1", "is_error": True, "content": "denied by your permission settings"}
            write(log, "".join(json.dumps({"type": kind, "message": {"content": [block]}}) + "\n"
                               for kind, block in (("assistant", use), ("user", back))))
            out = subprocess.run([sys.executable, "-I", "-B", os.path.join(PLUGIN, "evals", "system", "audit_secrets.py"), ws, log],
                                 capture_output=True, text=True, encoding="utf-8").stdout
            self.assertIn("DENIED", out)
            self.assertNotIn("CONTENT", out)

    def test_a_configured_bed_has_setups_deny_rule(self):
        for fresh in ([], ["--fresh"]):
            with tempfile.TemporaryDirectory(prefix="dev-bed-", ignore_cleanup_errors=True) as tmp:
                out = os.path.join(tmp, "bed")
                subprocess.run([sys.executable, "-I", "-B", os.path.join(PLUGIN, "evals", "system", "setup_bed.py"), out, *fresh],
                               capture_output=True, check=True)
                path = os.path.join(out, "workspace", ".claude", "settings.json")
                if fresh:
                    self.assertFalse(os.path.exists(path))
                else:
                    self.assertEqual(json.loads(read(path))["permissions"]["deny"], ["Read(**/.env.production)"])


class ScoreCell(Workspace):
    def tally(self, cells, lead=""):
        raw = os.path.join(self.tmp.name, "raw")
        table = "| ID | Impact | Area | Change | Location | Quote | Finding | Mark | Proposed fix | Handling |\n" + "| --- " * 10 + "|\n"
        scores = "| ID | Score | Reason |\n| --- | --- | --- |\n"
        for n, cell in enumerate(cells, 1):
            table += f"| R1-C{n} | Minor | Correctness | in | src/a.cs:{n} | \"q{n}\" | f{n} | confirmed: read | fix | ASK |\n"
            scores += f"| R1-C{n} | {cell} |" + ("" if cell.startswith("Duplicate") else " reason |") + "\n"
        write(os.path.join(raw, "correctness.md"), table)
        write(os.path.join(raw, "scores.md"), scores)
        self.assertEqual(script("dev-core", "findings.py", "collect", raw, "--kind", "code")[0], 0)
        return script("dev-core", "findings.py", "tally", raw, "--kind", "code", "--round", "1",
                      "--out", os.path.join(self.tmp.name, "r.md"))

    def refused(self, *cells):
        code, out = self.tally(cells)
        self.assertEqual(code, 1, out)
        return out["error"]

    def test_an_id_is_not_a_score(self):
        self.assertIn("R1-C1", self.refused("P1-C13"))

    def test_a_row_without_a_score_cell_is_refused(self):
        self.assertIn("R1-C1", self.refused("Duplicate of R1-C9"))

    def test_a_score_above_100_is_refused(self):
        self.assertIn("R1-C1", self.refused("850"))

    def test_a_negative_score_is_refused(self):
        self.assertIn("R1-C1", self.refused("-90"))

    def test_every_bad_row_is_named(self):
        error = self.refused("101", "55", "high")
        self.assertIn("R1-C1", error)
        self.assertIn("R1-C3", error)
        self.assertNotIn("R1-C2", error)

    def test_the_ends_of_the_range_are_scores(self):
        self.assertEqual(self.tally(["0", "100", "**85**"])[0], 0)


class ProblemsList(Workspace):
    """What the Problems list must not break, from batch 3's cold check."""

    def test_a_claim_that_names_the_findings_heading_hides_no_open_blocker(self):
        review = ("# Plan: plan review round 1\n\n## Summary\n\n### Problems\n\n"
                  "1. **P1-C1** \u00b7 Blocker \u00b7 in the change \u00b7 doc: the template lacks ## Findings\n"
                  "2. **P1-C2** \u00b7 Major \u00b7 in the change \u00b7 doc: needs a ### Findings part\n\n"
                  "## Findings\n\n### critic\n\n| ID | Severity | Resolution |\n| --- | --- | --- |\n"
                  "| P1-C1 | Blocker | open |\n| P1-C2 | Major | open |\n\n## Outside this change\n\nnone\n")
        probe = ("import importlib.util, sys; s = importlib.util.spec_from_file_location('p', sys.argv[1]); "
                 "m = importlib.util.module_from_spec(s); s.loader.exec_module(m); print(m.open_high(sys.argv[2]))")
        path = os.path.join(SKILLS, "dev-plan", "scripts", "plan_page.py")
        done = subprocess.run([sys.executable, "-I", "-B", "-c", probe, path, review], capture_output=True, text=True)
        self.assertEqual(done.stdout.strip(), "2", done.stderr)

    def test_a_fix_now_list_is_not_read_as_a_reviewer(self):
        raw = os.path.join(self.tmp.name, "raw")
        table = ("| ID | Impact | Area | Location | Quote | Finding | Mark | Proposed fix | Handling |\n" + "| --- " * 9 + "|\n"
                 '| {} | Major | Correctness | src/a.cs:1 | "q" | f | confirmed: read | fix | ASK |\n')
        write(os.path.join(raw, "correctness.md"), table.format("R2-C1"))
        write(os.path.join(raw, "fix-now.md"), table.format("R1-C3").replace("src/a.cs:1", "src/b.cs:7"))
        code, out = script("dev-core", "findings.py", "collect", raw, "--kind", "code")
        self.assertEqual(code, 0, out)
        found = json.loads(read(os.path.join(raw, "findings.json")))["findings"]
        self.assertEqual([x["id"] for x in found], ["R2-C1"])

    def text(self, *parts):
        return read(os.path.join(SKILLS, *parts))

    def test_a_plan_resolution_never_crosses_the_side_of_the_change(self):
        text = self.text("dev-plan", "stages", "review.md")
        self.assertIn("on the same side of the change", text)
        self.assertIn("a row under Outside this change always gets `outside:`", text)

    def test_an_early_choice_never_pulls_outside_work_in(self):
        text = self.text("dev-review", "routes", "human-review.md")
        for part in ("only on the same side of the change", "fix now would include it", "most severe ID in the change", "with none in the change",
                     "one work item per problem"):
            self.assertIn(part, text)

    def test_spec_gets_the_fix_now_list_in_a_fix_round(self):
        self.assertIn("fix-now.md", self.text("dev-review", "routes", "review.md"))
        spec = next(line for line in self.text("dev-review", "references", "viewpoints.md").splitlines()
                    if line.startswith("| spec |") and "diff.patch" in line)
        self.assertIn("fix-now.md", spec)
        given = read(os.path.join(PLUGIN, "agents", "goldfish-spec.md")).split("## Input")[1].split("\n## ")[0]
        self.assertIn("fix-now.md", given)

    def test_one_problem_is_one_cause_for_learn(self):
        self.assertIn("One problem, one cause", self.text("dev-learn", "SKILL.md"))

    def test_the_gate_says_what_it_checks(self):
        route = self.text("dev-deploy", "routes", "deploy.md")
        for part in ("started at stage `test`", "To clear it", "skip its Hand on", "back to `deploy`", "new review"):
            self.assertIn(part, route)
        core = self.text("dev-core", "SKILL.md")
        self.assertIn("whole number from 0 to 100", core)


class Workbooks(Workspace):
    settings = {"workbooks": {"technologies": ["csharp", "dotnet", "docker", "terraform"]}}

    def resolved(self, *args):
        code, out = script("dev-workbook", "workbook.py", "resolve", "--workspace", self.ws,
                           "--user-dir", os.path.join(self.tmp.name, "none"), *args)
        self.assertEqual(code, 0, out)
        return sorted(out["technologies"])

    EVERY = ["csharp", "docker", "dotnet", "terraform"]

    def test_every_configured_workbook_loads_whatever_the_paths(self):
        for paths in ((), ("shop/src/A.cs", "shop/src/Api.csproj"), ("notes.txt",), ("main.tf",)):
            self.assertEqual(self.resolved(*(("--paths", *paths) if paths else ())), self.EVERY, paths)

    def test_no_stage_or_reviewer_takes_only_some_sections(self):
        narrowed = []
        for part in ("skills", "agents"):
            for folder, dirs, files in os.walk(os.path.join(PLUGIN, part)):
                dirs[:] = [d for d in dirs if d not in ("evals", "state")]
                for name in (f for f in files if f.endswith(".md")):
                    path = os.path.join(folder, name)
                    for n, line in enumerate(read(path).splitlines(), 1):
                        if (("WORKBOOK resolve" in line and "--topics" in line)
                                or re.search(r"workbook-statements\.md` \((?!all sections)[A-Z]", line)
                                or re.search(r"workbook statements for (each|the touched) technolog\w+[^(\n]{0,30}\((?!all sections)", line)
                                or (part == "agents" and re.search(r"gives you.*workbook's (Testing|Security|Performance) statements", line))):
                            narrowed.append(f"{name}:{n}")
        self.assertEqual(narrowed, [])

    def test_shipped_skills_pass_check_skills(self):
        code, out = script("dev-workbook", "workbook.py", "check-skills", SKILLS)
        self.assertEqual((code, out["ok"]), (0, True), out)

    def test_check_skills_exits_1_on_failure(self):
        skills = os.path.join(self.tmp.name, "skills")
        write(os.path.join(skills, "dev-build", "routes", "build.md"), "1. Write the code.\n")
        code, out = script("dev-workbook", "workbook.py", "check-skills", skills)
        self.assertEqual((code, out["ok"]), (1, False), out)


if __name__ == "__main__":
    unittest.main()
