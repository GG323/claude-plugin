"""The automatic checks to run after every system-test flow.

Usage: py -3 -I -B check_run.py <workspace>

The devcore and review scripts write while they check, so they run on a
temporary copy. The workspace is never written to. A check that had nothing to
look at, or no tool to look with, says "not run" or "blocked", never "pass".
"""

import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
CORE = PLUGIN / "skills" / "dev-core"
DEVCORE = CORE / "scripts" / "devcore.py"
REVIEW = PLUGIN / "skills" / "dev-review" / "scripts" / "review.py"
DOCUMENTS = {
    "plan.md": r"plan\.md",
    "questions.md": r"questions\.md",
    "plan-review.md": r"plan-review-\d+\.md",
    "review.md": r"review-\d+\.md",
    "learn.md": r"learn-\d+\.md",
    "test-map.md": r"test-map(-\d+)?\.md",
    "test-run.md": r"test-run-\d+\.md",
    "build.md": r"build-\d+\.md",
    "wi.md": r"\d+\.md",
}
SKIP = shutil.ignore_patterns(".git", "bin", "obj", "TestResults", ".env.production")


def script(path, *args):
    run = subprocess.run(
        [sys.executable, "-I", "-B", str(path), *map(str, args)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        return json.loads(run.stdout)
    except ValueError:
        return {"ok": False, "error": (run.stdout + run.stderr)[-500:]}


def secret_patterns():
    spec = importlib.util.spec_from_file_location("devcore", DEVCORE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SECRET_PATTERNS


def headings(text):
    return [line.strip() for line in text.splitlines() if line.startswith("## ")]


def result(problems, looked_at=True):
    if not looked_at:
        return {"result": "not run", "problems": []}
    return {"result": "fail" if problems else "pass", "problems": problems}


def check_state(copy, changes):
    problems = [f"{change.name}: state.json refused" for change in changes if not script(DEVCORE, "state", change).get("ok")]
    index = copy / "dev-plans" / "INDEX.md"
    before = index.read_text(encoding="utf-8") if index.is_file() else ""
    script(DEVCORE, "index", "--workspace", copy)
    after = index.read_text(encoding="utf-8") if index.is_file() else ""
    if before != after:
        problems.append("INDEX.md differs from the state files")
    return result(problems, bool(changes))


def check_receipts(changes):
    problems = []
    for change in changes:
        answer = script(REVIEW, "receipts", change, "--round", 99)
        if not answer.get("ok"):
            problems.append(f"{change.name}: {answer.get('error')}")
        for stage in answer.get("missing", []):
            problems.append(f"{change.name}: no receipt for {stage}")
    return result(problems, bool(changes))


def check_templates(changes):
    problems, seen = [], 0
    for change in changes:
        for path in [*change.glob("*.md"), *change.glob("wi/*.md")]:
            for template, pattern in DOCUMENTS.items():
                if not re.fullmatch(pattern, path.name) or (template == "wi.md") != (path.parent.name == "wi"):
                    continue
                seen += 1
                expected = headings((CORE / "assets" / "templates" / template).read_text(encoding="utf-8"))
                text = path.read_text(encoding="utf-8")
                if headings(text) != expected:
                    problems.append(f"{path.name}: headings differ from {template}")
    return result(problems, seen > 0)


def check_testing_md(workspace):
    problems, seen = [], 0
    for doc in workspace.rglob("TESTING.md"):
        seen += 1
        code = [p for p in doc.parent.rglob("*.cs") if not {"bin", "obj"} & set(p.parts)]
        if any(p.stat().st_mtime > doc.stat().st_mtime for p in code):
            problems.append(f"{doc.relative_to(workspace).as_posix()}: older than the code in its folder")
    return result(problems, seen > 0)


def check_secrets(copy):
    patterns = secret_patterns()
    problems, seen = [], 0
    for path in [*(copy / "dev-plans").rglob("*"), *copy.rglob("TESTING.md")]:
        if not path.is_file():
            continue
        seen += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        problems += [f"{path.name}: matches {pattern}" for pattern in patterns if re.search(pattern, text)]
    return result(problems, seen > 0)


def check_leftovers(changes):
    runs = []
    for change in changes:
        state = json.loads((change / "state.json").read_text(encoding="utf-8"))
        latest = {entry["run_id"]: entry for entry in state.get("ephemeral", [])}
        runs += latest.values()
    if not runs:
        return result([], False)
    if not shutil.which("docker"):
        return {"result": "blocked", "problems": ["docker is not on PATH, so leftovers cannot be listed"]}
    problems = []
    for entry in runs:
        listed = subprocess.run(
            ["docker", "ps", "-aq", "--filter", f"label={entry['label']}"], capture_output=True, text=True
        )
        if listed.returncode:
            problems.append(f"docker ps failed for {entry['run_id']}")
        elif listed.stdout.strip():
            problems.append(f"container left by {entry['run_id']}")
    return result(problems)


def check(workspace):
    with tempfile.TemporaryDirectory(prefix="dev-check-run-") as temp:
        copy = Path(temp) / "workspace"
        shutil.copytree(workspace, copy, ignore=SKIP)
        changes = sorted(path.parent for path in (copy / "dev-plans").glob("*/state.json"))
        return {
            "templates": check_templates(changes),
            "secrets": check_secrets(copy),
            "testing_md": check_testing_md(workspace),
            "leftovers": check_leftovers(changes),
            "state_and_index": check_state(copy, changes),
            "receipts": check_receipts(changes),
        }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    report = check(Path(sys.argv[1]).resolve())
    print(json.dumps(report, indent=1))
    raise SystemExit(1 if any(item["result"] == "fail" for item in report.values()) else 0)
