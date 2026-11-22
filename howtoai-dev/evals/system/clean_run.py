"""Drive one turn of a clean-room session under test.

Usage: clean_run.py <run folder> <message file> [session id]

Environment: CLEANROOM_CLAUDE is the claude executable (default: the one on PATH). CLEANROOM_PERMISSION_MODE is
required: the tester's own mode, never a wider one. Turn logs go to <bed>-logs, beside the bed folder that holds
the run folder, so the session under test and the frozen plugin do not contain them.

The session runs in <run folder>/workspace with the plugin loaded, the token-saving mods off for this session
only, no connectors, and the permission mode given in CLEANROOM_PERMISSION_MODE.
Prints what the session said, which agents it started, what was denied, and its cost.
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = str(HERE.parents[1])
CLAUDE = os.environ.get("CLEANROOM_CLAUDE") or shutil.which("claude")
MODE = os.environ.get("CLEANROOM_PERMISSION_MODE")
if len(sys.argv) < 3:
    sys.exit(__doc__)
if not CLAUDE:
    sys.exit("set CLEANROOM_CLAUDE to the claude executable")
if not MODE:
    sys.exit("set CLEANROOM_PERMISSION_MODE to the tester's own permission mode")

run = Path(sys.argv[1]).resolve()
message = Path(sys.argv[2]).read_text(encoding="utf-8")
session = sys.argv[3] if len(sys.argv) > 3 else None

logs = run.parent.with_name(run.parent.name + "-logs")
logs.mkdir(parents=True, exist_ok=True)
turn = len(list(logs.glob("turn-*.jsonl"))) + 1
command = [CLAUDE, "-p", "--permission-mode", MODE, "--effort", "medium", "--strict-mcp-config",
           "--settings", str(HERE / "cleanroom-settings.json"), "--plugin-dir", PLUGIN,
           "--output-format", "stream-json", "--verbose"]
if session:
    command += ["--resume", session]

started = time.monotonic()
log = logs / f"turn-{turn}.jsonl"
with open(log, "w", encoding="utf-8") as out:
    proc = subprocess.run(command, input=message, cwd=run / "workspace", stdout=out, stderr=subprocess.PIPE,
                          text=True, encoding="utf-8", timeout=3300)

agents, files_outside = [], set()
result, init = {}, {}
workspace = str(run / "workspace").lower().replace("\\", "/")
for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
    try:
        event = json.loads(line)
    except ValueError:
        continue
    if event.get("type") == "system" and event.get("subtype") == "init":
        init = event
    if event.get("type") == "result":
        result = event
    if event.get("type") != "assistant":
        continue
    for block in event.get("message", {}).get("content", []):
        if block.get("type") != "tool_use":
            continue
        data = block.get("input") or {}
        if block.get("name") in ("Agent", "Task"):
            agents.append(data.get("subagent_type") or "general-purpose")
        if block.get("name") in ("Edit", "Write"):
            path = str(data.get("file_path", "")).lower().replace("\\", "/")
            if not path.startswith(workspace):
                files_outside.add(path)

print(json.dumps({
    "turn": turn,
    "exit": proc.returncode,
    "stderr": proc.stderr[-1500:],
    "session": init.get("session_id"),
    "model": init.get("model"),
    "mcp": init.get("mcp_servers"),
    "minutes": round((time.monotonic() - started) / 60, 1),
    "agents": agents,
    "writes_outside_workspace": sorted(files_outside),
    "denied": result.get("permission_denials"),
    "cost_usd": result.get("total_cost_usd"),
    "usage": result.get("modelUsage"),
    "said": result.get("result"),
}, indent=1, ensure_ascii=False))
