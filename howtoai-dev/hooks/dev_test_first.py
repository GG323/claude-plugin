"""dev-test-first: a PreToolUse hook on Edit, Write, MultiEdit, and NotebookEdit.

Silent unless the edited file's workspace has a howtoai-dev change at stage tests-first, build,
or test (when several do, the most recently updated of those counts). Then:
  - The plan folder, AGENTS/ (tooling and the howtoai state folder), and files matching testing.test_globs are always allowed.
  - CI files (.github/workflows/, azure-pipelines.yml, .gitlab-ci.yml, Jenkinsfile, in any folder) are denied at
    stage tests-first and test: tests never pass by changing CI.
  - Any other file at stage tests-first: denied when testing.test_first is block, a warning when
    warn, nothing when off.
  - Any other file at stage build without a red-check run in state: a warning (block and warn).
Ideas from nizos/tdd-guard (MIT): a guard that judges each edit against the test state. No code
from it is used, and no model is called.
"""

import fnmatch
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # -I leaves the script folder off sys.path
import common  # noqa: E402

CI = re.compile(r"(^|/)(\.github/workflows/|azure-pipelines\.ya?ml$|\.gitlab-ci\.ya?ml$|Jenkinsfile$)")


def is_test(path, globs):
    return any(fnmatch.fnmatch(path, g) or fnmatch.fnmatch("/" + path, g) for g in globs)


def check(data):
    if data.get("tool_name") not in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        return None
    ti = data.get("tool_input") or {}
    path = ti.get("file_path") or ti.get("notebook_path")
    if not path:
        return None
    if not os.path.isabs(path):
        path = os.path.join(data.get("cwd") or os.getcwd(), path)
    ws = common.workspace(os.path.dirname(path))
    if not ws:
        return None
    dc = common.devcore()
    st = common.active_change(dc, ws)
    if not st:
        return None
    r = common.rel(ws, path)
    if r is None:
        return None
    s = common.settings(dc, ws)
    plan_folder = s.get("plan_folder", "dev-plans")
    if r.startswith(plan_folder + "/") or r.lower().startswith("agents/"):
        return None
    stage, cid = st.get("stage"), st.get("id", "?")
    if CI.search(r):
        if stage in ("tests-first", "test"):
            return ("deny", f"dev-test-first: {r} is CI configuration; change {cid} is at stage {stage}, "
                            "and tests never pass by changing CI. Change it in the build stage, if the plan approved it.")
        return None
    globs = s.get("testing", {}).get("test_globs", [])
    if is_test(r, globs):
        return None
    mode = s.get("testing", {}).get("test_first", "block")
    if mode == "off":
        return None
    if stage == "tests-first":
        msg = (f"dev-test-first: change {cid} is at stage tests-first, so only test files change now. "
               f"{r} is not a test file (testing.test_globs). Write the tests and run the red check first; "
               "dev-build edits the code afterwards.")
        return ("deny", msg) if mode == "block" else ("warn", msg)
    if stage == "build":
        red = [t for t in st.get("test_runs", []) if t.get("route") == "red-check" and t.get("result") == "red"]
        if not red:
            return ("warn", f"dev-test-first: change {cid} is at stage build but has no red-check run in state. "
                            "Run dev-test's Write route first, or record why the tests could not fail first.")
    return None


if __name__ == "__main__":
    common.run(check)
