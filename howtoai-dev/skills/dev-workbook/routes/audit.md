# Audit

## Contents

- [Steps](#steps)
- [Skills and agents](#skills-and-agents)

## Steps

`WORKBOOK` is the command [SKILL.md](../SKILL.md#routes) defines.

On the user's request, or when `skill-audit` asks.

1. Run `WORKBOOK audit --workspace "<workspace>"`. It lists format errors, statements without tags that inherit none (`untagged`, which a search finds by tool and section only), sources checked more than 180 days ago, project or user statements that replace a base ID no longer there, support dates that have passed (`support_ended`) or are less than 180 days away (`support_ending`), Codebase versions lines read more than 180 days ago (in `old_sources`), and lines whose version workbook does not exist (`missing_version_workbooks`). Each `support_ended` entry carries its `meaning`:
   - A general base or user workbook: the workbook is out of date. Refresh its versions from the vendor's support page.
   - A version workbook or a code project's line: that version is out of support. Report an upgrade to plan at some point, never a fault to fix now.
2. Ask before checking installed versions, because it runs each workbook's read-only Version command (such as `dotnet --version`); with a yes, add `--run-version-commands`.
3. Report the list, with the checks it ran and the ones it skipped and why (`checks_run`, `checks_skipped`); fix project and user workbooks through [Propose](propose.md#steps) after approval. Base workbook fixes go to `skill-builder`.

## Skills and agents

- `dev-workbook` - this route's skill; `skill-audit` or the user asks for it.
