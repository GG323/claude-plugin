"""dev-safe-target: a PreToolUse hook on Bash, PowerShell, MCP tools, Edit, Write, and MultiEdit.

An approved deploy step comes first: a command that matches, character for character after
trimming, an unexpired and unused step in <workspace>/AGENTS/settings/deploy/approvals.json (written by
dev-deploy after the user's yes) is marked used and passes with no decision, so the user's normal
permission prompt still shows. Nothing here ever returns allow.

Checked before everything, the approved step included: a write, edit, command, or MCP call that
touches <workspace>/AGENTS/settings/dev/replies.jsonl (the dev-reply-log hook's record of real user
replies) is denied, in every workspace.

Then, in this order (deny wins over ask, ask over warn):
  1. Deny markers (environments.deny in the dev settings, user or project): a command or MCP call
     whose text holds one is denied. Applies in every workspace whose settings name markers.
  2. hook_rules from the settings: a regex on the command or file path, with action block or warn.
  3. Only in workspaces with project dev settings (AGENTS/settings/dev/settings.json):
     - Destructive commands (drops, truncates, bulk deletes, down-migrations, database resets,
       destroy, prune) ask first, unless they name a container whose latest ephemeral entry in a
       change's state is "created" (entries are appended, so a later "removed" ends it).
     - Edits to migration files that drop, rename, or retype tables, columns, or indexes, or
       truncate or bulk-delete data, ask first, unless the new text carries the comment
       "howtoai-dev: destructive-confirmed" (added once the plan approved the step). Text in a
       migration's down part (Down(), def down, downgrade, migrate:down) is not checked.
The migration rules adapt the risk tiers and the confirm-marker idea of a-abdellatif98/
db-migration-guard (MIT), rewritten as deterministic rules: no model is called.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # -I leaves the script folder off sys.path
import common  # noqa: E402
import datetime  # noqa: E402

CONFIRM = "howtoai-dev: destructive-confirmed"
DESTRUCTIVE_CMD = [
    (r"\bdrop\s+(table|database|schema|column|index|view)\b", "drops a database object"),
    (r"\btruncate\b(\s+table)?\s+\w", "truncates a table"),
    (r"\bdelete\s+from\s+[\w.\"\[\]`]+\s*(;|$|[\"'])", "deletes every row (no WHERE)"),
    (r"\bdotnet\s+ef\s+database\s+(drop|update\s+0\b)", "drops or rolls back the database"),
    (r"\b(rails|rake)\s+db:(drop|reset|rollback|schema:load)\b", "drops, resets, or rolls back the database"),
    (r"\bprisma\s+(migrate\s+reset|db\s+push\s+--force-reset)\b", "resets the database"),
    (r"\bflyway\b.*\bclean\b", "cleans the database"),
    (r"\balembic\s+downgrade\b", "runs a down-migration"),
    (r"\b(knex\s+migrate:(rollback|down)|sequelize\s+db:migrate:undo|typeorm\s+migration:revert)\b", "runs a down-migration"),
    (r"\bterraform\s+(destroy|apply\b.*-destroy)\b", "destroys infrastructure"),
    (r"\bkubectl\s+delete\b", "deletes cluster resources"),
    (r"\bdocker\s+(system|volume)\s+prune\b|\bdocker\s+volume\s+rm\b", "removes Docker volumes"),
    (r"\baz\s+(group|sql\s+db|postgres\s+\S+)\s+delete\b|\baws\s+(rds\s+delete|s3\s+rb|s3\s+rm\b.*--recursive)", "deletes cloud resources"),
]


def marker_files(dc, ws, marker):
    """The settings files whose environments.deny lists the marker (project first, then user)."""
    found = []
    for path in (dc.project_file(ws), dc.user_file(os.environ.get("HOWTOAI_DEV_USER_FILE") or None)):
        try:
            with open(path, encoding="utf-8") as f:
                deny = (json.load(f).get("environments") or {}).get("deny") or []
        except (OSError, ValueError, AttributeError):
            continue
        if any(isinstance(m, str) and m.lower() == marker.lower() for m in deny):
            found.append(path)
    return found


def deny_message(dc, ws, marker, what):
    files = marker_files(dc, ws, marker)
    where = " and ".join(files) if files else "the dev settings"
    return (f"dev-safe-target blocked this {what}: its text contains {marker!r}, a production marker listed in "
            f"environments.deny in {where}. A marker blocks any command or connector call whose text holds it "
            "anywhere, ignoring case, so production is never reached by accident (file edits are not checked). "
            "Use an allowed test target (environments.allow) instead. If this is not production, or the marker is "
            "too broad, the user changes the list with dev-core's Setup route or by rerunning the howtoai-dev "
            "INSTALL; never work around the block.")


MIGRATION_PATH = re.compile(r"(^|/)(migrations?|Migrations|migrate|versions)/|(^|/)db/.*\.sql$|\.sql$|_migration\b", re.I)
DESTRUCTIVE_DDL = [
    (r"\bdrop\s+(table|column|index|schema|view|constraint)\b", "drops a table, column, index, or constraint"),
    (r"\brename\s+(column|to)\b|\bsp_rename\b", "renames a table or column"),
    (r"\balter\s+column\s+\S+\s+(set\s+data\s+)?type\b|\bmodify\s+column\b", "changes a column type"),
    (r"\btruncate\b", "truncates a table"),
    (r"\bdelete\s+from\b", "deletes rows"),
    (r"migrationBuilder\s*\.\s*(DropTable|DropColumn|RenameColumn|RenameTable|AlterColumn|DropIndex|DropForeignKey)\b",
     "drops, renames, or alters a table or column (EF Core)"),
    (r"\b(remove_column|drop_table|rename_column|rename_table|change_column)\b", "drops, renames, or changes a column (Rails)"),
    (r"\bop\.(drop_table|drop_column|alter_column|drop_index)\b", "drops or alters a table or column (Alembic)"),
]
DOWN_MARKERS = re.compile(r"void\s+Down\s*\(|\bdef\s+down\b|\bdef\s+downgrade\b|--\s*\+goose\s+Down|--\s*migrate:down"
                          r"|exports\.down\b|\basync\s+down\s*\(|\bdown\s*\(\s*\)\s*\{", re.I)


def owned_names(dc, ws):
    """Container names whose latest entry is "created"; entries are appended in order."""
    latest = {}
    for st in common.changes(dc, ws):
        for e in st.get("ephemeral", []):
            if e.get("name"):
                latest[e["name"]] = e.get("state")
    return [n for n, state in latest.items() if state == "created"]


def up_part(text):
    m = DOWN_MARKERS.search(text)
    return text[:m.start()] if m else text


def edited_text(tool, ti, path):
    """The new text an edit puts into the file's up part."""
    if tool == "Write":
        return up_part(ti.get("content") or "")
    pieces = [ti] if tool == "Edit" else list(ti.get("edits") or [])
    try:
        with open(path, encoding="utf-8") as f:
            current = f.read()
    except OSError:
        current = ""
    down_at = DOWN_MARKERS.search(current)
    keep = []
    for p in pieces:
        old, new = p.get("old_string") or "", p.get("new_string") or ""
        at = current.find(old) if old else -1
        if down_at and at >= down_at.start():
            continue
        keep.append(up_part(new))
    return "\n".join(keep)


def approved_step(ws, command):
    """True, and the approval marked used, when command is an approved, unexpired, unused step."""
    path = common.devcore().state_dir(ws, "deploy", "approvals.json")
    cmd = command.strip()
    if not cmd or not os.path.isfile(path):
        return False
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        now = datetime.datetime.now(datetime.timezone.utc)
        for item in data.get("approvals", []):
            if item.get("used") or (item.get("command") or "").strip() != cmd:
                continue
            expires = datetime.datetime.fromisoformat(item.get("expires", ""))
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=datetime.timezone.utc)
            if expires <= now:
                continue
            item["used"] = now.isoformat(timespec="seconds")
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8", newline="\n") as f:
                json.dump(data, f, indent=1, ensure_ascii=False)
            os.replace(tmp, path)
            return True
    except (OSError, ValueError, TypeError, AttributeError):
        return False  # a broken approvals file approves nothing
    return False


def check(data):
    tool = data.get("tool_name") or ""
    ti = data.get("tool_input") or {}
    is_cmd = tool in ("Bash", "PowerShell")
    is_mcp = tool.startswith("mcp__")
    is_edit = tool in ("Edit", "Write", "MultiEdit")
    if not (is_cmd or is_mcp or is_edit):
        return None
    path = ti.get("file_path") if is_edit else None
    if path and not os.path.isabs(path):
        path = os.path.join(data.get("cwd") or os.getcwd(), path)
    ws = common.workspace(os.path.dirname(path) if path else (data.get("cwd") or os.getcwd()))
    if not ws:
        return None
    dc = common.devcore()
    s = common.settings(dc, ws)
    if is_cmd:
        text = ti.get("command") or ""
    elif is_mcp:
        text = json.dumps(ti, ensure_ascii=False)
    else:
        text = ""
    low = text.lower()
    log_rel = os.path.relpath(dc.reply_log(ws), ws).replace("\\", "/")
    if (is_edit and (common.rel(ws, path) or "").lower() == log_rel.lower()) or ((is_cmd or is_mcp) and "replies.jsonl" in low):
        return ("deny", f"dev-safe-target: {log_rel} is written only by the dev-reply-log hook on a real user prompt. "
                        "Ask the user and wait for the reply; never write or edit the log.")
    if is_cmd and approved_step(ws, text):
        return None

    if is_cmd or is_mcp:
        for marker in s.get("environments", {}).get("deny", []):
            if marker and marker.lower() in low:
                return ("deny", deny_message(dc, ws, marker, "command" if is_cmd else f"{tool} call"))
    subject = text if (is_cmd or is_mcp) else (common.rel(ws, path) or "")
    warn = None
    for rule in s.get("hook_rules", []):
        try:
            if rule.get("match") and re.search(rule["match"], subject):
                if rule.get("action") == "block":
                    return ("deny", f"dev-safe-target rule {rule.get('id', '?')}: {rule.get('reason', 'blocked')}")
                warn = warn or ("warn", f"dev-safe-target rule {rule.get('id', '?')}: {rule.get('reason', '')}")
        except re.error:
            continue
    if not common.configured(dc, ws):
        return warn

    if is_cmd:
        owned = owned_names(dc, ws)
        for pattern, what in DESTRUCTIVE_CMD:
            if re.search(pattern, low, re.I | re.S):
                if any(n.lower() in low for n in owned):
                    return warn
                return ("ask", f"dev-safe-target: this command {what}. Destructive steps run only on targets this run "
                               "created; on anything else take a snapshot first. Approve only if the target is a test target.")
    if is_edit:
        r = common.rel(ws, path)
        if r and MIGRATION_PATH.search(r):
            new = edited_text(tool, ti, path)
            if CONFIRM in new:
                return warn
            for pattern, what in DESTRUCTIVE_DDL:
                if re.search(pattern, new, re.I):
                    return ("ask", f"dev-safe-target: this migration edit {what}, which a revert does not undo. "
                                   "Prefer expand-then-contract; if the plan approved it, add the comment "
                                   f"'{CONFIRM}' to the migration.")
    return warn


if __name__ == "__main__":
    common.run(check)
