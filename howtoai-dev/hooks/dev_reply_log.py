"""dev-reply-log: a UserPromptSubmit hook that records that the user replied, so an approval in the
user's name can be checked against a real reply.

In a workspace with project dev settings (a "howtoai-dev" key in AGENTS/settings.json), it appends one
line to dev-core's state/replies.jsonl (skills/dev-core/state/ in this plugin) for each user prompt: {"at": <local ISO time>, "sha256":
<hash of the normalized prompt>}. It never stores the prompt's text. It keeps the last 50 lines.
devcore.py's state patch hashes an approval's "reply" the same way and accepts an approval
"by": "user" only when a logged reply made at or after the change's creation and after its last
user approval matches.
It never blocks a prompt: any error ends silently (exit 0, no output).
"""

import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # -I leaves the script folder off sys.path
import common  # noqa: E402

KEEP = 50


def record(data):
    prompt = data.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return
    ws = common.workspace(data.get("cwd") or os.getcwd())
    if not ws:
        return
    dc = common.devcore()
    if not common.configured(dc, ws):
        return
    path = dc.reply_log(ws)
    at = datetime.datetime.now().astimezone().isoformat()
    line = json.dumps({"at": at, "sha256": dc.reply_hash(prompt)})
    try:
        with open(path, encoding="utf-8") as f:
            lines = [x for x in f.read().splitlines() if x.strip()]
    except OSError:
        lines = []
    lines = (lines + [line])[-KEEP:]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    try:
        record(common.read_input())
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
