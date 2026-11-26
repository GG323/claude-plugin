"""dev-workbook is the one way to read workbooks, and no rule text is copied. Run: py -3 -I -B <this file>."""

import glob
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(PLUGIN, "skills")
SKILL = os.path.join(SKILLS, "dev-workbook")
WORKBOOK = os.path.join(SKILL, "scripts", "workbook.py")
TOOLS = ["csharp", "docker", "dotnet", "terraform"]
BASH_MAX = 30000  # longer Bash output is saved to a file and only previewed
# statement IDs the reviews of the F3 system-test runs cited
CITED = """csharp.commands.001 csharp.commands.002 csharp.overview.006 csharp.overview.007 csharp.patterns.008 csharp.setup.005
docker.patterns.004 docker.performance.002 docker.setup.001 dotnet.commands.004 dotnet.overview.002 dotnet.overview.005
dotnet.patterns.008 dotnet.setup.001 dotnet.setup.006 dotnet.setup.007 dotnet.testing.001 dotnet.testing.004
terraform.patterns.004""".split()


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def files(*parts):
    for part in parts:
        for folder, dirs, names in os.walk(os.path.join(PLUGIN, part)):
            dirs[:] = [d for d in dirs if d not in ("evals", "state", "__pycache__")]
            for name in names:
                if name.endswith((".md", ".py")):
                    yield os.path.join(folder, name)


class OneReader(unittest.TestCase):
    def test_no_rule_copies(self):
        old = re.compile(r"20 lines or fewer|first 12 lines|loading rule|loading\.md|All workbook rules, read in full|All rules load:", re.I)
        self.assertEqual([os.path.relpath(p, PLUGIN) for p in files("skills", "agents") if old.search(read(p))], [])
        self.assertFalse(os.path.exists(os.path.join(SKILL, "references", "loading.md")))

    def test_every_goldfish_preloads_the_reader_and_only_declares_it(self):
        agents = glob.glob(os.path.join(PLUGIN, "agents", "goldfish-*.md"))
        self.assertEqual(len(agents), 12)
        for path in agents:
            head, body = read(path).replace("\r", "").split("\n---\n", 1)
            self.assertRegex(head, r"(?m)^skills:.*\bdev-workbook\b", path)
            self.assertNotIn("omitClaudeMd", head, path)
            self.assertNotIn("workbook-search", body, path)
            self.assertNotRegex(head, r"(?m)^tools:.*\b(Skill|Bash)\b", path)

    def test_loading_command_takes_nothing_from_the_caller(self):
        text = read(os.path.join(SKILL, "SKILL.md"))
        commands = re.findall(r"(?m)^!`(.+)`", text)
        self.assertEqual(len(commands), 1)
        self.assertNotRegex(commands[0], r"\$ARGUMENTS|\$\{?\d|\$\{?ARGUMENTS")
        self.assertLess(len(text), 7000, "every reviewer loads this file")

    def test_no_caller_hands_reviewers_a_statements_file(self):
        for p in files("skills", "agents"):
            if p.endswith(".md") and "dev-core" not in p:  # findings.py reserves the old file name
                self.assertNotIn("workbook-statements.md", read(p), p)


class Workspace(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        self.ws = os.path.join(self.tmp, "ws")
        self.settings({"workbooks": {"technologies": TOOLS}})

    def settings(self, value):
        os.makedirs(os.path.join(self.ws, "AGENTS"), exist_ok=True)
        with open(os.path.join(self.ws, "AGENTS", "settings.json"), "w", encoding="utf-8") as f:
            f.write(value if isinstance(value, str) else json.dumps({"howtoai-dev": value}))

    def run_wb(self, *args, cwd=None):
        return subprocess.run([sys.executable, "-I", "-B", WORKBOOK, *args, "--user-dir", os.path.join(self.tmp, "none")],
                              capture_output=True, text=True, encoding="utf-8", cwd=cwd)

    def resolve(self, *args):
        return json.loads(self.run_wb("resolve", "--workspace", self.ws, *args).stdout)

    def everything(self):
        return [s for secs in self.resolve()["sections"].values() for sts in secs.values() for s in sts]

    def musts(self):
        return {s["id"] for s in self.everything() if (s["level"] or "").startswith("MUST")}


class Open(Workspace):
    def test_prints_every_must_and_little_more(self):
        out = self.run_wb("open", cwd=self.ws).stdout
        for sid in self.musts():
            self.assertIn(f"- {sid} MUST", out)
        self.assertLess(len(out), 10000)

    def test_search_file_has_every_statement_tagged_and_stays_out_of_git(self):
        self.run_wb("open", cwd=self.ws)
        cache = os.path.join(self.ws, "AGENTS", "state", "cache")
        rows = read(os.path.join(cache, "workbook-search.md")).splitlines()
        every = self.everything()
        self.assertEqual(len(rows), len(every))
        for s in every:
            tool = s["id"].split(".")[0]
            self.assertTrue(any(r.startswith(f"- #{tool} #") and f" {s['id']}" in r and r.endswith(s["text"]) for r in rows), s["id"])
        self.assertEqual(read(os.path.join(cache, ".gitignore")), "*\n")

    def test_search_reaches_every_id_past_reviews_cited(self):
        self.run_wb("open", cwd=self.ws)
        rows = read(os.path.join(self.ws, "AGENTS", "state", "cache", "workbook-search.md")).splitlines()
        for sid in CITED:
            self.assertTrue(any(f"#{sid.split('.')[0]} " in r and f" {sid}" in r for r in rows), sid)

    def test_finds_the_workspace_from_a_folder_below(self):
        below = os.path.join(self.ws, "shop", "src")
        os.makedirs(below)
        self.assertIn("MUST NOT", self.run_wb("open", cwd=below).stdout)

    def test_never_fails_the_load(self):
        outside = self.run_wb("open", cwd=self.tmp)
        self.assertEqual(outside.returncode, 0)
        self.assertIn("No dev workspace", outside.stdout)
        self.settings("{ not json")
        self.assertEqual(self.run_wb("open", cwd=self.ws).returncode, 0)
        self.settings({"workbooks": {"technologies": TOOLS}})
        os.makedirs(os.path.join(self.ws, "AGENTS", "state"), exist_ok=True)
        with open(os.path.join(self.ws, "AGENTS", "state", "cache"), "w", encoding="utf-8") as f:
            f.write("a file where the cache folder goes")
        broken = self.run_wb("open", cwd=self.ws)
        self.assertEqual(broken.returncode, 0)
        self.assertIn("Blocked: rules not read in full", broken.stdout)


class Tailored(Workspace):
    def served(self, *args):
        return set(self.resolve(*args)["receipt"]["statements"])

    def test_musts_load_whatever_the_paths_and_tags(self):
        must = self.musts()
        for args in (("--paths", "a/A.cs"), ("--paths", "notes.txt"), ("--technologies", "terraform", "--tags", "state"),
                     ("--paths", "Dockerfile", "--tags", "secrets")):
            self.assertLessEqual(must, self.served(*args), args)

    def test_touched_tools_come_whole_and_others_only_their_musts(self):
        every, must = {s["id"] for s in self.everything()}, self.musts()
        got = self.served("--paths", "a/A.cs", "a/A.csproj")
        self.assertEqual(got, must | {i for i in every if i.split(".")[0] in ("csharp", "dotnet")})
        got = self.served("--technologies", "terraform")
        self.assertEqual(got, must | {i for i in every if i.startswith("terraform.")})

    def test_tags_narrow(self):
        got = self.served("--paths", "Dockerfile", "--tags", "secrets")
        want = {s["id"] for s in self.everything() if s["id"].startswith("docker.") and "secrets" in s["tags"]}
        self.assertEqual(got, self.musts() | want)
        self.assertFalse(self.resolve("--tags", "nonsense")["ok"])

    def test_dot_files_at_the_root_match(self):
        self.assertIn("docker.setup.001", self.served("--paths", ".dockerignore"))

    def test_markdown_prints_exact_and_its_receipt_is_what_it_printed(self):
        for args in (("--paths", "a/A.cs", "a/A.csproj"), (), ("--technologies", *TOOLS)):
            out = self.run_wb("resolve", "--workspace", self.ws, *args, "--markdown").stdout
            self.assertLess(len(out.encode("utf-8")), BASH_MAX, args)
            receipt = json.loads(out.rstrip().splitlines()[-1].split("Receipt: ", 1)[1])
            shown = set(re.findall(r"(?m)^- ([a-z]+\.[a-z]+\.\d{3})", out))
            self.assertEqual(shown, set(receipt["statements"]), args)

    def test_versions_leave_the_statements_out(self):
        out = self.resolve("--versions")
        self.assertNotIn("sections", out)
        self.assertEqual(sorted(out["technologies"]), TOOLS)


class Loading(Workspace):
    def test_replacing_a_must_keeps_its_level(self):
        self.run_wb("propose", "--workspace", self.ws, "--tech", "csharp", "--section", "patterns", "--replaces", "csharp.patterns.004",
                    "--text", "Use await using for async disposables.", "--source", "`x`", "--write")
        self.assertIn("csharp.patterns.004", self.musts())

    def test_broken_settings_fail_closed(self):
        self.settings("{ not json")
        self.assertIn("Blocked: rules not read in full", self.run_wb("open", cwd=self.ws).stdout)

    def test_a_long_result_says_how_to_get_every_part(self):
        out = self.run_wb("resolve", "--workspace", self.ws, "--technologies", *TOOLS, "--markdown").stdout
        parts, got = int(re.search(r"^PART 1 of (\d+)", out).group(1)), set()
        for n in range(1, parts + 1):
            part = self.run_wb("resolve", "--workspace", self.ws, "--technologies", *TOOLS, "--markdown", "--part", str(n)).stdout
            self.assertLess(len(part.encode("utf-8")), BASH_MAX)
            got |= set(json.loads(part.rstrip().splitlines()[-1].split("Receipt: ", 1)[1])["statements"])
        self.assertEqual(got, {s["id"] for s in self.everything()})


class VersionCopies(Workspace):
    """Two workbooks of one technology share IDs and text, the case where parts are easiest to mix up."""

    def setUp(self):
        super().setUp()
        folder = os.path.join(self.ws, "AGENTS", "workbooks")
        os.makedirs(folder)
        base = read(os.path.join(SKILL, "workbooks", "dotnet.md")).replace("\r", "")
        for key in ("8", "9"):
            copy = base.replace("| Layer | base |", f"| Layer | project |\n| Version key | {key} |")
            with open(os.path.join(folder, f"dotnet@{key}.md"), "w", encoding="utf-8", newline="\n") as f:
                f.write(copy)
        lines = "\n".join(f"- `v{key}/` \u00b7 .NET {key} \u00b7 workbook: `dotnet@{key}` \u00b7 supported until 2026-11-10 "
                          f"\u00b7 source: `v{key}/A.csproj` \u00b7 checked 2026-11-20" for key in ("8", "9"))
        with open(os.path.join(folder, "dotnet.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write("# .NET workbook (project)\n\n## Contents\n\n- [Header](#header)\n\n## Header\n\n| Key | Value |\n| --- | --- |\n"
                    "| Technology | `dotnet` |\n| Title | .NET |\n| Layer | project |\n| Updated | 2026-11-20 |\n\n"
                    "Sources:\n\n- none yet\n\nCodebase versions:\n\n" + lines + "\n\n## Skills and agents\n\n- none\n")

    def test_each_part_names_its_workbook_and_its_receipt_is_its_own(self):
        args = ("resolve", "--workspace", self.ws, "--paths", "v8/A.csproj", "v9/A.csproj", "new/A.csproj", "a/A.cs", "Dockerfile")
        whole = set(self.resolve(*args[3:])["receipt"]["statements"])
        first = self.run_wb(*args, "--markdown").stdout
        parts, got = int(re.search(r"^PART 1 of (\d+)", first).group(1)), []
        for n in range(1, parts + 1):
            out = self.run_wb(*args, "--markdown", "--part", str(n)).stdout
            self.assertLess(len(out.encode("utf-8")), BASH_MAX, n)
            heading, listed = None, []
            for line in out.splitlines():
                if line.startswith("## "):
                    key = re.search(r"\[(dotnet@\d+)\]$", line)
                    heading = key.group(1) if key else ""
                found = re.match(r"- ([a-z]+\.[a-z]+\.\d{3})", line)
                if found:
                    self.assertIsNotNone(heading, f"part {n}: a statement before any workbook heading")
                    listed.append(f"{heading}:{found.group(1)}" if heading else found.group(1))
            ids = json.loads(out.rstrip().splitlines()[-1].split("Receipt: ", 1)[1])["statements"]
            self.assertEqual(sorted(listed), sorted(ids), n)
            got += ids
        self.assertEqual(sorted(got), sorted(whole))

    def test_a_replacement_is_not_reported_untagged(self):
        folder = os.path.join(self.ws, "AGENTS", "workbooks")
        with open(os.path.join(folder, "docker.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write("# Docker workbook (project)\n\n## Contents\n\n- [Header](#header)\n\n## Header\n\n| Key | Value |\n| --- | --- |\n"
                    "| Technology | `docker` |\n| Title | Docker |\n| Layer | project |\n| Updated | 2026-11-20 |\n\n"
                    "Sources:\n\n- none yet\n\n## Setup and configuration\n\n"
                    "- **docker.setup.001** \u00b7 Ours is at the root. \u00b7 source: `.dockerignore` \u00b7 confirmed: project, 2026-11-20\n"
                    "- **docker.setup.p001** \u00b7 We use BuildKit. \u00b7 source: `Dockerfile` \u00b7 confirmed: project, 2026-11-20\n\n"
                    "## Skills and agents\n\n- none\n")
        untagged = " ".join(json.loads(self.run_wb("audit", "--workspace", self.ws).stdout)["untagged"])
        self.assertIn("docker.setup.p001", untagged)
        self.assertNotIn("docker.setup.001 ", untagged)


if __name__ == "__main__":
    unittest.main()
