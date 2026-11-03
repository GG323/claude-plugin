# Discover

## Contents

- [Entry and inputs](#entry-and-inputs)
- [Find the targets](#find-the-targets)
- [Start the run file](#start-the-run-file)
- [Skills and agents](#skills-and-agents)

## Entry and inputs

Entered from [Before you start](../SKILL.md#before-you-start) with today's date, the mode, and any targets the user named.

## Find the targets

1. Run:

   ```bash
   py -3 "${CLAUDE_SKILL_DIR}/scripts/find_workspaces.py"
   ```

   It prints JSON: the global folder (`CLAUDE_CONFIG_DIR`, or else `~/.claude`), the workspaces found in Claude Code's session history (each with its path, last use, and whether it has `AGENTS.md`, `CLAUDE.md`, and a `.claude` folder), and the skipped ones with a reason (folder gone, scratch workspace, excluded). If it prints an `error`, stop and report it.
2. Choose the targets:
   - **Scheduled, or on request without names:** the global folder and every workspace found.
   - **On request with names:** only the named ones. A named folder that the script did not find is still a target when it exists, because the user chose it; one that does not exist is reported back to the user before going on.
3. Order the targets: the global folder first, because its files load in every workspace, then the workspaces by name.

## Start the run file

1. Create the run folder: in this session's scratchpad folder when the harness gives one, otherwise a new temporary folder (`py -3 -c "import tempfile; print(tempfile.mkdtemp(prefix='environment-audit-'))"`). Never put it inside a target, because the audit would then find its own files.
2. Save the script's JSON from [Find the targets](#find-the-targets) step 1 as `discover.json` in the run folder, edited to the chosen targets: set `"global"` to `null` when the global folder is not a target, keep only the chosen workspaces, and add a named folder the script did not find as `{"name": "<folder name>", "path": "<full path with forward slashes>"}`. Then create the run file:

   ```bash
   py -3 "${CLAUDE_SKILL_DIR}/scripts/render_report.py" init "<run folder>/report.json" --discover "<run folder>/discover.json" --mode "<scheduled|on request>" --date YYYY-MM-DD
   ```

   It writes `report.json` with one entry per target and the skipped targets, ready for findings.

Pass the run folder to the Tool audit stage: read [stages/tool-audit.md](tool-audit.md).

## Skills and agents

- [environment-audit](../SKILL.md) — the overview and rules for every stage.
- [scripts/find_workspaces.py](../scripts/find_workspaces.py) and [scripts/render_report.py](../scripts/render_report.py) — find the targets and start the run file.
- Next stage: [Tool audit](tool-audit.md).
