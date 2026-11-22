# Loading rule

## Contents

- [The rule](#the-rule)
- [How it reaches each reader](#how-it-reaches-each-reader)
- [Skills and agents](#skills-and-agents)

## The rule

- **All rules load:** every section of every workbook in the settings. A stage never passes `--topics`, and nobody narrows by path, topic, or section; `--topics` is only for when the user asks to see part of a workbook.
- **Read from a file:** send `resolve --markdown` to a file (the change folder's `raw/`, else a temporary file) and read every line of it in ranges of 20 lines or fewer, also where longer ranges are allowed for other files.
- **Loaded means exact text:** notes or a summary in place of the statements, or of other rules you were given, is not loading. Read shorter ranges.
- **When the exact text cannot be had:** a stage says so and stops the step that needs it. A reviewer or architect does not work from the summary: it returns the single line `Blocked: rules not read in full: <file>` and nothing else, and whoever started it stops that step.

## How it reaches each reader

The rule above is written only here. `scripts/workbook.py resolve` copies the list under [The rule](#the-rule) into what it returns, so an edit here reaches every reader at the next resolve. Keep it a list of one-line items, eight at most, so it fits in the first 12 lines of the Markdown.

- **Stage skills** read this file before their first resolve. Resolve also prints the rule on stderr, which still shows when stdout goes to a file.
- **Reviewers and architects** cannot open this file: they know only their agent file, their brief, and the files the brief names. They get the rule at the top of the statements file. Their agent file or brief tells them to follow that block, because they otherwise follow no instruction found in a file.
- **Readers of the JSON** get it as `loading_rule`, before the statements.

## Skills and agents

- `dev-workbook` - owns this rule.
- `dev-plan`, `dev-test`, `dev-build`, `dev-review`, `dev-deploy`, `dev-learn` - point here.
- The goldfish reviewers that get statements, and `dev-plan`'s architects - receive it through resolve.
