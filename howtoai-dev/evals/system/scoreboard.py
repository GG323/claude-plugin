"""Write the system-test scoreboard from one JSON result per run.

Usage: py -3 -I -B scoreboard.py <results folder>

Reads <results folder>/runs/*.json and writes <results folder>/SCOREBOARD.md.
The newest run of each flow (by its "started" value) fills that flow's row.
"""

import json
import sys
from pathlib import Path

FLOWS = {
    "F1": "Fresh install",
    "F2": "Too small",
    "F3": "Bug fix, cause clear",
    "F4": "Bug fix, cause unclear",
    "F5": "Medium feature",
    "F6": "Refactor",
    "F7": "Version upgrade",
    "F8": "Large, two repositories",
    "F9": "Too big",
    "F10": "Greenfield",
}
STAGES = ("setup", "plan", "approval", "tests first", "build", "test", "review", "human review", "learn", "deploy", "outcome")
STATES = ("pass", "fail", "blocked", "waiting", "not run")
SEVERITIES = ("Critical", "Major", "Minor", "Note")
TOTALS = ("questions", "approvals", "agents", "minutes", "lines changed")


def verdict(stages):
    values = [stages.get(stage, "not run") for stage in STAGES]
    for state in ("fail", "waiting", "blocked"):
        if state in values:
            return state
    if all(value == "pass" for value in values):
        return "pass"
    return "not run" if all(value == "not run" for value in values) else "incomplete"


def load(folder):
    runs = []
    for path in sorted((folder / "runs").glob("*.json")):
        run = json.loads(path.read_text(encoding="utf-8"))
        if run["flow"] not in FLOWS:
            raise SystemExit(f"{path.name}: unknown flow {run['flow']}")
        for stage, state in run["stages"].items():
            if stage not in STAGES or state not in STATES:
                raise SystemExit(f"{path.name}: unknown stage or state: {stage}={state}")
        for finding in run.get("findings", []):
            if finding["severity"] not in SEVERITIES:
                raise SystemExit(f"{path.name}: unknown severity {finding['severity']}")
        runs.append(run)
    return sorted(runs, key=lambda run: run["started"])


def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def table(header, rows):
    lines = [header, ["---"] * len(header), *rows]
    return ["| " + " | ".join(cell(value) for value in line) + " |" for line in lines] + [""]


def render(runs):
    latest = {run["flow"]: run for run in runs}
    verdicts = {flow: verdict(latest[flow]["stages"]) if flow in latest else "not run" for flow in FLOWS}
    counts = {}
    for value in verdicts.values():
        counts[value] = counts.get(value, 0) + 1

    out = [
        "# Dev skill scoreboard",
        "",
        "## Contents",
        "",
        "- [Result](#result)",
        "- [Stages](#stages)",
        "- [Cost](#cost)",
        "- [Findings](#findings)",
        "- [Skills and agents](#skills-and-agents)",
        "",
        "## Result",
        "",
        "**" + ", ".join(f"{count} {name}" for name, count in counts.items()) + f"** of {len(FLOWS)} flows.",
        "",
    ]
    out += table(
        ["Flow", "Task", "Result", "In one line"],
        [[flow, name, verdicts[flow], latest.get(flow, {}).get("summary", "")] for flow, name in FLOWS.items()],
    )

    out += ["## Stages", "", "`-` means not run.", ""]
    rows = []
    for flow in FLOWS:
        stages = latest.get(flow, {}).get("stages", {})
        states = [stages.get(stage, "not run") for stage in STAGES]
        rows.append([flow, *("-" if state == "not run" else state for state in states)])
    out += table(["Flow", *STAGES], rows)

    out += ["## Cost", ""]
    if latest:
        rows = [
            [flow, *(latest[flow].get("totals", {}).get(total, "-") for total in TOTALS)]
            for flow in FLOWS
            if flow in latest
        ]
        out += table(["Flow", *TOTALS], rows)
    else:
        out += ["none", ""]

    out += ["## Findings", ""]
    findings = [(flow, item) for flow in FLOWS if flow in latest for item in latest[flow].get("findings", [])]
    findings.sort(key=lambda pair: SEVERITIES.index(pair[1]["severity"]))
    if findings:
        rows = [[item["severity"], flow, item["title"], item.get("evidence", "")] for flow, item in findings]
        out += table(["Severity", "Flow", "Finding", "Evidence"], rows)
    else:
        out += ["none found", ""]

    out += [
        "## Skills and agents",
        "",
        "- `dev-plan`, `dev-test`, `dev-build`, `dev-review`, `dev-learn`, `dev-deploy` - the skills under test.",
        "- `skill-builder` - fixes what the findings show.",
    ]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    root = Path(sys.argv[1]).resolve()
    (root / "SCOREBOARD.md").write_bytes(render(load(root)).encode("utf-8"))
    print(json.dumps({"ok": True, "scoreboard": str(root / "SCOREBOARD.md")}))
