# Redesign outputs

## Contents

- [When this stage runs](#when-this-stage-runs)
- [Find the outdated outputs](#find-the-outdated-outputs)
- [Ask for approval](#ask-for-approval)
- [Rebuild each template](#rebuild-each-template)
- [Review each rebuild](#review-each-rebuild)
- [Update the stamp and the log](#update-the-stamp-and-the-log)
- [Report](#report)
- [Skills and agents](#skills-and-agents)

## When this stage runs

From [The stages](../SKILL.md#the-stages) when the user asks to redesign, restyle, or update earlier outputs to the current design reference, usually after a new reference version (`tokens.py apply`) or a client profile change. It rebuilds the templates that skills and tools ship (pages, reports, dashboards, decks, documents, mod panes and bands), never their runtime outputs, as [Templates, not runtime](../references/surfaces.md#templates-not-runtime) sets out. It works on templates in other skills' and tools' folders, so nothing is changed before the user approves the list.

## Find the outdated outputs

1. Run `py -3 "${CLAUDE_SKILL_DIR}/scripts/tokens.py" show` and note the current reference version `<N>` and date.
2. Read [state/design-log.md](../state/design-log.md), or the log file the user names; paths in it are relative to the `PLUGIN/claude-plugin` repository, or to the log's own folder for a log the user names. If it is missing, say so, offer to seed it from the templates the user names, and stop.
3. List every row whose reference version is a number lower than `<N>`. A row with a client profile is outdated also when that profile's **Updated** date is later than the row's date. Rows judged against `own style` are never listed.
4. For each listed row, check that the output path still exists, and read its stamp; a stamp that disagrees with the log is shown in the list, and the stamp wins.

## Ask for approval

Show one table: output path, surface, its version or stamp, the current version, client profile, and what the rebuild touches (the template file, and the script that fills it when its markup changes). Ask which rows to rebuild: all, some, or none. Without a live user (a scheduled run or a subagent), stop after the list; a redesign changes other skills' and tools' files and always waits for approval.

When the list is empty, say that every logged output is at version `<N>`, and skip to the [Report](#report) section.

## Rebuild each template

For each approved row, one at a time:

1. Copy the template to `<name>.<YYYY-MM-DD>.<ext>` next to it, with the date from the system clock, before changing it.
2. Rebuild it to the current reference by its surface's row in the [surface table](../references/surfaces.md#surface-table), keeping its structure, placeholders, and every hook its script fills, so the script still works unchanged. With a client profile, apply its overrides as [Build from the house starter](build.md#build-from-the-house-starter) does.
3. When the template's markup must change in a way its script depends on, change the script too, and say so in the report. A template that belongs to a skill or tool under `skill-builder` is changed within that tool's files only; its registry row is updated in [Update the stamp and the log](#update-the-stamp-and-the-log).

## Review each rebuild

1. Render one output with the tool's own script (or fill the template's placeholders with sample data in the session's scratch folder).
2. For HTML, run `py -3 "${CLAUDE_SKILL_DIR}/scripts/page.py" check "<rendered.html>"` and `py -3 "${CLAUDE_SKILL_DIR}/scripts/page.py" adherence "<rendered.html>"` (with `--profile "<path>"` for a client row), and look at it at 320px and 1280px in light and dark, as [stages/review.md](review.md#inspect) describes. For other surfaces, render or screenshot it, or use the [token checklist](../references/surfaces.md#token-checklist) and say so.
3. Fix every `FAIL` and every `HIGH` finding in the template, then check again. A row that still has a `HIGH` keeps verdict `Block` and its old version in the log.

## Update the stamp and the log

1. Set the stamp in each rebuilt template to `built from skill-design design-reference v<N> (<date>)`, `built from client profile <path> (<date>)`, or `built from studio design <slug> v<N> (<date>)`.
2. In [state/design-log.md](../state/design-log.md), update each rebuilt row: today's date, `redesign` as the task, the new version, and the verdict.
3. Where the template belongs to a skill or tool in `skill-builder`'s registry (`skill-builder/state/registry.md`), update the stamp in that row's Notes, so its Recall sees the rebuild.

## Report

In chat: the current version; the rows found outdated; the rows rebuilt, each with its verdict, check counts, and backup copy path; the rows skipped or declined; scripts changed; and every check marked **Not verified**.

## Skills and agents

- [skill-design](../SKILL.md) - the skill this stage belongs to; [stages/build.md](build.md) and [stages/review.md](review.md) - how a rebuild is built and checked.
- [scripts/tokens.py](../scripts/tokens.py) - `show`; [scripts/page.py](../scripts/page.py) - `check` and `adherence`.
- `skill-builder` - owns the registry of skills and tools whose templates are rebuilt.
- `pptx`, `docx`, `plugin-authoring` - rebuild deck, document, and mod templates.
