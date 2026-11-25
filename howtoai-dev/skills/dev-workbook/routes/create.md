# Create

## Steps

For a technology with no workbook, or a version workbook a code project needs (`dotnet@8`): a validated project workbook of current, cited statements, made only after the user's answer. `WORKBOOK` is the command [SKILL.md](../SKILL.md#routes) defines. Open every page you cite, long pages in short ranges, so a summarising read hook does not stand in for the text.

**Version workbook.** Ask one question, with the `grilling` skill's method: "Make a <technology> <version> workbook for <code project>?" State the default: a copy of the general workbook, checked against that version's docs. On a yes:

1. Run `WORKBOOK skeleton --tech <name> --version-key <key> --copy-base --title "<Title> <version>" --layer project --out "<workspace>/AGENTS/settings/workbooks/<name>@<key>.md"`. The copy keeps the general workbook's statement IDs.
2. Check every statement against the official documentation for that version: keep one that holds, with its confirmed part set to `project, <date>`; correct one that differs, keeping its ID; delete one that does not apply, leaving a gap in the numbers; add version-specific ones with `p` numbers.
3. Set Versions, and Supported until from the vendor's support policy page, listed in Sources with today's date.
4. Validate it (`WORKBOOK validate <file>`) and show the user a summary: counts per section, and statements kept, corrected, deleted, and added. Skip the rest of this section.

**New technology.** Ask the user one crucial question, with the `grilling` skill's method: find and download a workbook, or make one. Recommend make when an official documentation site exists, because it gives current, cited statements without third-party text. State the defaults: a project workbook at `AGENTS/settings/workbooks/<technology>.md`, about 4 to 8 statements per section. Frameworks and package managers belong to their language's workbook unless the project uses them heavily enough for their own (ask when unsure). When the user cannot be reached, return the question to the caller; never make a workbook without the answer.

- **Find:** search with `skill-finder` for skills or rule sets covering the technology. Use a candidate only after `skill-finder` vets it; convert it to the format, strip every process part (workflows, personas, stage steps, what the agent must ask), cite it as a source with its license, and keep only statements its own text supports.
- **Make:** run `WORKBOOK skeleton --tech <name> --title "<Title>" --layer project --out "<workspace>/AGENTS/settings/workbooks/<name>.md"`, then fill each section from the technology's official documentation for the version the project uses, and Our situation from the codebase's own conventions. Choose the statements agents most often get wrong.
- Validate the result (`WORKBOOK validate <file>`), show the user a summary (counts per section, sources), and add the technology to `workbooks.technologies` in the dev settings through `dev-core`'s Setup preview. A base workbook (shipped with the plugin) is created only when building the plugin, never in a user's run.
