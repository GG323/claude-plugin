"""Print the main session's runs of the app, and every command that touched the workbook statements, with results."""
import json
import re
import sys

results, uses = {}, []
for line in open(sys.argv[1], encoding="utf-8", errors="replace"):
    try:
        event = json.loads(line)
    except ValueError:
        continue
    if event.get("parent_tool_use_id"):
        continue
    content = event.get("message", {}).get("content") if isinstance(event.get("message"), dict) else None
    for block in content if isinstance(content, list) else []:
        if block.get("type") == "tool_use":
            uses.append(block)
        elif block.get("type") == "tool_result":
            body = block.get("content")
            results[block.get("tool_use_id")] = body if isinstance(body, str) else "".join(
                part.get("text", "") for part in body or [] if isinstance(part, dict))

for block in uses:
    data = block.get("input") or {}
    command = data.get("command") or ""
    out = results.get(block.get("id"), "")
    if re.search(r"DOTNET_ENVIRONMENT|rm -r|Remove-Item|Copy-Item|cp -[rR]|dotnet (run|test)", command):
        print("=== RUN", block.get("name"))
        print(command[:2200])
        print("--- result")
        print(out[:500])
    elif re.search(r"workbook|statements", command) or "workbook-statements" in str(data.get("file_path", "")):
        ids = set(re.findall(r"\b(?:csharp|dotnet|docker|terraform)\.[a-z]+\.\d{3}\b", out))
        print("=== RULES", block.get("name"), "|", re.sub(r"\s+", " ", command or json.dumps(data))[:230])
        print(f"--- result: {len(out)} characters, {len(ids)} distinct statement IDs visible,",
              "summarized" if "Input Router" in out or "persisted-output" in out else "as printed")
