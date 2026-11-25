# Skill index

## When this stage runs

This stage rebuilds the search index that `skill-finder` ships with, so searches for existing skills, plugins, and tools stay current. It runs after [Workspace audit](workspace-audit.md) in every scheduled and on-request run. When the user asks only to rebuild or refresh the skill index, it is the only stage. It changes no audited file; it writes only `skill-finder`'s `index/` folder, the one exception to the read-only rule.

## Rebuild the index

1. Find `skill-finder`'s source folder: the folder `skill-finder` next to this skill's own folder (resolve `${CLAUDE_SKILL_DIR}` through its link first), else `~/.claude/skills/skill-finder` resolved through its link. It must hold `scripts/finder.py` and `sources.json` and be writable; a read-only plugin install is not. If none qualifies, the result is "skipped, no writable skill-finder folder"; go to [Record the result](#record-the-result).
2. Run it in the background, because it takes several minutes, and wait for it to finish:
   `uv run --no-project --quiet --with chromadb==1.5.9 python -I "<skill-finder folder>/scripts/finder.py" index --budget 300`
   If `uv` is missing, use `py -3 -I` with the same arguments after confirming `py -3 -c "import chromadb"` works. If neither works, the result is "skipped, needs uv or chromadb"; install nothing in a scheduled run.
3. Read the JSON it prints at the end: entries per source, failed sources, and the expansion counts (`repos_done`, `repos_failed`, `left`).

## Record the result

1. Write the skill index line: "Skill index: N entries, M plugin repositories read this run, K still unread; failed sources: ... (or none)", or the skipped result. [Report](report.md) puts it in the chat summary and the run log.
2. The rebuilt index reaches other users only when `skill-finder`'s `index/` folder is committed in its repository. Say so in an on-request run; never commit in a scheduled run.
3. When the skill index was the only stage requested, end the run here with the skill index line as the summary. Skip the Report stage. Otherwise, pass the run folder and the skill index line to the Report stage: read [stages/report.md](report.md).
