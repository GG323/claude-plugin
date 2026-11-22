"""The workbook loading rule has one home and reaches every reader. Run: py -3 -I -B <this file>."""

import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(PLUGIN, "skills")
HOME = os.path.join(SKILLS, "dev-workbook", "references", "loading.md")
WORKBOOK = os.path.join(SKILLS, "dev-workbook", "scripts", "workbook.py")
FINDINGS = os.path.join(SKILLS, "dev-core", "scripts", "findings.py")
STAGES = ("dev-plan", "dev-test", "dev-build", "dev-review", "dev-deploy", "dev-learn")
NO_STATEMENTS = ("goldfish-scorer.md", "goldfish-verifier.md")  # no rule line: they see statements only as a file a finding cites
HEADER_LINES = 12  # the lines every reviewer is told to read first
EXACT_CHARS = 8000  # input-router passes a ranged read below about 2,000 tokens as exact text


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def rule():
    body = read(HOME).split("\n## The rule\n", 1)[1].split("\n## ", 1)[0]
    return [line[2:].strip() for line in body.splitlines() if line.startswith("- ")]


def instruction_files():
    for part in ("skills", "agents"):
        for folder, dirs, files in os.walk(os.path.join(PLUGIN, part)):
            dirs[:] = [d for d in dirs if d not in ("evals", "state", "__pycache__")]
            for name in files:
                if name.endswith((".md", ".py")):
                    yield os.path.join(folder, name)


class Case(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        self.ws = os.path.join(self.tmp, "ws")
        os.makedirs(os.path.join(self.ws, ".howtoai"))

    def command(self, *args, script=WORKBOOK):
        return [sys.executable, "-I", "-B", script, "resolve", "--workspace", self.ws, "--user-dir",
                os.path.join(self.tmp, "none"), "--technologies", "csharp", "dotnet", "docker", "terraform", *args]

    def resolve(self, *args, script=WORKBOOK):
        return subprocess.run(self.command(*args, script=script), capture_output=True, text=True, encoding="utf-8")

    def resolve_to_file(self, *args, merged=False):
        path = os.path.join(self.tmp, "out.txt")
        with open(path, "w", encoding="utf-8") as f:
            p = subprocess.run(self.command(*args), stdout=f, stderr=subprocess.STDOUT if merged else subprocess.PIPE,
                               text=True, encoding="utf-8")
        return read(path), p.stderr


class OneHome(Case):
    def test_rule_text_is_only_in_its_home(self):
        wording = re.compile(r"20 lines or fewer|All workbook rules, read in full|All rules load:|Loaded means read")
        copies = [os.path.relpath(p, PLUGIN) for p in instruction_files()
                  if os.path.abspath(p) != os.path.abspath(HOME) and wording.search(read(p))]
        self.assertEqual(copies, [])

    def test_every_stage_skill_points_to_the_home(self):
        for name in STAGES:
            self.assertIn("${CLAUDE_SKILL_DIR}/../dev-workbook/references/loading.md",
                          read(os.path.join(SKILLS, name, "SKILL.md")), name)
            self.assertTrue(os.path.isfile(os.path.join(SKILLS, name, "..", "dev-workbook", "references", "loading.md")))

    def test_every_reader_without_skills_is_told_to_follow_the_block(self):
        readers = [p for p in glob.glob(os.path.join(PLUGIN, "agents", "goldfish-*.md"))
                   if os.path.basename(p) not in NO_STATEMENTS]
        self.assertEqual(len(readers), 10)
        for path in readers + [os.path.join(SKILLS, "dev-plan", "references", "architects.md")]:
            text = read(path)
            self.assertIn(f"first {HEADER_LINES} lines", text, path)
            self.assertIn("loading rule", text, path)
            self.assertIn("Blocked: rules not read in full: <file>", text, path)

    def test_architects_get_the_statements_as_a_file(self):
        for rel in ("stages/draft.md", "references/architects.md"):
            self.assertIn("raw/workbook-statements.md", read(os.path.join(SKILLS, "dev-plan", *rel.split("/"))), rel)

    def test_a_blocked_architect_stops_the_draft(self):
        draft = read(os.path.join(SKILLS, "dev-plan", "stages", "draft.md"))
        self.assertRegex(draft, r"starts `Blocked:` is not a design: stop")


class Delivery(Case):
    def test_markdown_opens_with_the_whole_rule(self):
        out = self.resolve("--markdown")
        self.assertEqual(out.returncode, 0, out.stderr)
        top = "\n".join(out.stdout.splitlines()[:HEADER_LINES])
        self.assertIn("Loading rule", top)
        for item in rule():
            self.assertIn(item, top)

    def test_rule_shows_when_stdout_goes_to_a_file(self):
        for args in ((), ("--markdown",)):
            _, err = self.resolve_to_file(*args)
            for item in rule():
                self.assertIn(item, err, args)

    def test_merged_streams_stay_parseable_and_keep_the_rule(self):
        text, _ = self.resolve_to_file(merged=True)
        self.assertEqual(json.loads(text)["loading_rule"], rule())
        text, _ = self.resolve_to_file("--markdown", merged=True)
        self.assertTrue(text.startswith("# Workbook statements"))

    def test_merged_pipe_stays_parseable(self):
        p = subprocess.run(self.command(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
        self.assertEqual(json.loads(p.stdout)["loading_rule"], rule())

    def test_json_carries_the_rule_before_the_statements(self):
        out = json.loads(self.resolve().stdout)
        self.assertEqual(out["loading_rule"], rule())
        self.assertLess(list(out).index("loading_rule"), list(out).index("sections"))

    def test_nothing_is_narrowed(self):
        every = json.loads(self.resolve().stdout)["receipt"]["statements"]
        text = self.resolve("--markdown").stdout
        for sid in every:
            self.assertIn(f"- {sid}", text)
        for stage in ("plan", "tests-first", "build", "test", "review", "deploy"):
            self.assertEqual(json.loads(self.resolve("--stage", stage).stdout)["receipt"]["statements"], every, stage)

    def test_every_prescribed_range_stays_exact(self):
        lines = self.resolve("--markdown").stdout.splitlines(True)
        worst = max(sum(map(len, lines[i:i + 20])) for i in range(len(lines)))
        self.assertLess(worst, EXACT_CHARS)

    def test_no_statements_without_the_rule(self):
        copy = os.path.join(self.tmp, "dev-workbook")
        shutil.copytree(os.path.join(SKILLS, "dev-workbook"), copy,
                        ignore=shutil.ignore_patterns("evals", "state", "__pycache__"))
        os.remove(os.path.join(copy, "references", "loading.md"))
        out = self.resolve(script=os.path.join(copy, "scripts", "workbook.py"))
        self.assertEqual(out.returncode, 1)
        self.assertFalse(json.loads(out.stdout)["ok"])


class Collect(Case):
    def collect(self, name, text):
        raw = os.path.join(self.tmp, "raw")
        os.makedirs(raw)
        with open(os.path.join(raw, "critic.md"), "w", encoding="utf-8") as f:
            f.write("No findings\n")
        with open(os.path.join(raw, name), "w", encoding="utf-8") as f:
            f.write(text)
        return subprocess.run([sys.executable, "-I", "-B", FINDINGS, "collect", raw, "--kind", "plan"],
                              capture_output=True, text=True, encoding="utf-8")

    def test_the_rules_blocked_line_is_detected(self):
        line = re.search(r"`(Blocked: [^`]+)`", "\n".join(rule())).group(1).replace("<file>", "workbook-statements.md")
        self.assertIn("blocked", self.collect("compliance.md", line + "\n").stdout)

    def test_the_rule_block_is_not_taken_for_a_blocked_reviewer(self):
        out = self.collect("workbook-statements.md", self.resolve("--markdown").stdout)
        self.assertEqual(out.returncode, 0, out.stdout)


if __name__ == "__main__":
    unittest.main()
