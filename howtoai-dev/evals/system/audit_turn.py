"""Audit one clean-room turn from its event stream.

Usage: audit_turn.py <turn jsonl> <workspace>
"""
import json
import re
import sys
from collections import Counter, defaultdict

log, workspace = sys.argv[1], sys.argv[2].lower().replace("\\", "/")
owner = {None: "main"}
tools = Counter()
env_touch, rule_reads, outside = [], defaultdict(list), Counter()
commands = []
failed, blocked = [], []
names = {}

for line in open(log, encoding="utf-8", errors="replace"):
    try:
        event = json.loads(line)
    except ValueError:
        continue
    parent = event.get("parent_tool_use_id")
    who = owner.get(parent, parent)
    content = event.get("message", {}).get("content") if isinstance(event.get("message"), dict) else None
    if not isinstance(content, list):
        continue
    for block in content:
        kind = block.get("type")
        if kind == "tool_use":
            data = block.get("input") or {}
            name = block.get("name")
            tools[name] += 1
            names[block.get("id")] = (who, name)
            if name in ("Agent", "Task"):
                owner[block.get("id")] = f"{data.get('subagent_type')}: {data.get('description')}"
            text = json.dumps(data)
            if name == "Read":
                path = str(data.get("file_path", "")).lower().replace("\\", "/")
                if re.search(r"/\.env($|\.(?!example|test))", path):
                    env_touch.append((who, name, path[-60:]))
                if "workbook-statements" in path:
                    rule_reads[who].append((data.get("offset", 1), data.get("limit", "all")))
                if not path.startswith(workspace):
                    outside[(who, path[-95:])] += 1
            if name in ("Bash", "PowerShell"):
                command = data.get("command", "")
                commands.append((who, command))
                if re.search(r"(cat|head|tail|sed|type|Get-Content|grep)\b[^\n|;&]*\.env\.production", command):
                    env_touch.append((who, name, command[:160]))
        elif kind == "tool_result":
            body = block.get("content")
            text = body if isinstance(body, str) else json.dumps(body)
            if block.get("is_error"):
                failed.append((names.get(block.get("tool_use_id")), text[:170]))
            if "Blocked: rules not read" in text:
                blocked.append(names.get(block.get("tool_use_id")))

print("tools:", dict(tools))
print("secret files opened:", env_touch or "none")
print("workbook statement reads:")
for who, reads in rule_reads.items():
    limits = [limit for _, limit in reads if isinstance(limit, int)]
    last = max([offset + (limit if isinstance(limit, int) else 0) for offset, limit in reads])
    print(f"  {who}: {len(reads)} reads, largest {max(limits) if limits else '-'}, whole-file reads "
          f"{sum(1 for _, limit in reads if limit == 'all')}, reaches line {last}")
print("commands that changed state outside the bed (candidates):")
for who, command in commands:
    if re.search(r"(git (push|commit|config --global)|npm i(nstall)?\b|winget|pip install|setx|Remove-Item|rm -r)", command):
        print("  ", who, command[:200])
print("blocked reviews:", blocked or "none")
print("failed tool calls:", len(failed))
for item in failed[:12]:
    print("  ", item)
print("reads outside the bed by subagents:")
for (who, path), n in outside.items():
    if who != "main":
        print("  ", n, who, path)
