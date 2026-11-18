# Build a page

## Contents

- [When this stage runs](#when-this-stage-runs)
- [Read the brief](#read-the-brief)
- [Write the copy, then plan the sections](#write-the-copy-then-plan-the-sections)
- [Build from the house starter](#build-from-the-house-starter)
- [Check the page](#check-the-page)
- [Deliver](#deliver)
- [Log the run](#log-the-run)
- [Skills and agents](#skills-and-agents)

## When this stage runs

From [stages/source.md](source.md) in build mode, with the design source decided; for a studio design, use the profile exported there ([Use the chosen design](source.md#use-the-chosen-design)). Before the first output of a run, read [references/rules.md](../references/rules.md) and [references/surfaces.md](../references/surfaces.md) in full, and the [design reference](../references/design-reference.html) for the look and its surface guidance; the values come from [design-tokens.json](../assets/design-tokens.json). Run `py -3 "${CLAUDE_SKILL_DIR}/scripts/tokens.py" show` and note the reference version and date.

The output is HTML unless the brief names another surface (slide deck, Word document, mod, email); for another surface, follow its row in the [surface table](../references/surfaces.md#surface-table) in place of the HTML steps below, and keep the copy, check, and log steps. When the output is a template for another skill or tool, it is built once and filled by that tool's own script, as [Templates, not runtime](../references/surfaces.md#templates-not-runtime) sets out.

## Read the brief

Write down, in the conversation:

- What the output is (report, dashboard, artifact, client page, landing page, slide deck, Word document, mod, email, or a template for one), who reads it, and on what device first.
- The one thing the reader must learn or do, and the main action if there is one.
- The real material: data, text, figures, logo, links. Facts come only from here. An unknown value gets a stated placeholder such as "none found" or "not given", never an invented number, quote, or name. A status the source does not give is "Not reported" in a neutral badge, never green.
- The period the data actually covers. When it differs from the request's wording ("this month" on 6 November, data from October), title the page by the data and say so in the report. The preparation date comes from the system clock.

If the brief lacks the reader or the main point, ask once; everything else can be inferred. Without a live user (a scheduled run or a subagent), record the reader and main point in the report instead.

## Write the copy, then plan the sections

1. Write every heading, lead line, label, and button text first, by the plain-words principle in [House principles](../references/rules.md#house-principles), because a layout chosen before the words forces filler.
2. Plan the page as a list: one line per section with its heading, its one idea, and its component from the [components table](../references/rules.md#components). Key figures and what needs the reader come before the detail. Long-text records are cards; tables only for short compared fields.
3. Use a chart only where a trend, share, or distribution reads faster as a picture than as a table, and then follow the `dataviz` skill, with colors from the house tokens. Free-text comments grouped into themes are your interpretation: quote them verbatim and say in the footer that the grouping is yours.

## Build from the house starter

1. Create the file with the house CSS inlined, so it is one self-contained file:
   `py -3 "${CLAUDE_SKILL_DIR}/scripts/page.py" new "<out.html>" --title "<title>" --lang <lang>`
   - Add `--profile "<path>"` when the source is a client profile or a studio design exported as one. Its token overrides are appended, and its font-link block replaces the house font link (from `tokens.fonts_url`); if the script warns that the profile changes fonts without a font-link block, add the block to the profile (with the user's approval) rather than editing the page.
   - Add `--no-web-fonts` for a file that must work offline or may not load Google Fonts; the system fallbacks then apply.
   - The script refuses to overwrite an existing file; when replacing one, copy it to `<name>.<YYYY-MM-DD>.html` first, then pass `--force`.
2. Fill the starter's sections from the plan, using house classes and tokens. Write page CSS only for what the components cannot do, in tokens (`var(--...)`), never raw colors, fonts, or radii.
   - For a template, put the stamp from [Templates, not runtime](../references/surfaces.md#templates-not-runtime) near its top, with the version and date from `tokens.py show` (or the client profile's path and date).
3. With "follow theirs" and the client's own token file, map their tokens onto the house component classes in page CSS, or use their components where they exist.
4. When the page will be published as an artifact, also load the `artifact-design` skill and follow its page contract; the house CSS already satisfies its token and dark-mode rules.

## Check the page

1. **Script.** Run `py -3 "${CLAUDE_SKILL_DIR}/scripts/page.py" check "<out.html>"`, then `py -3 "${CLAUDE_SKILL_DIR}/scripts/page.py" adherence "<out.html>"` (add `--profile "<path>"` when the source is a client profile; skip adherence with "follow theirs", and say so). Fix every `FAIL`; fix or justify every `WARN` in the report. For a template, run both on a page its script rendered.
2. **Browser.** Load the harness's browser skill first when it has one (for example `anthropic-skills:built-in-browser`). Serve the file's folder with `py -3 -u -m http.server 0 --bind 127.0.0.1 --directory "<folder>"` in the background and read the port from its first output line ("Serving HTTP on ... port N"); `-u` makes that line appear at once. Port 0 lets the system pick a free port, because Windows reserves ranges such as 8803-8902 and a fixed port can fail with WinError 10013. If no server can start, open the file directly: the browser pane then shows a static snapshot that may refuse page tools and stays light, so mark measured and dark-theme checks **Not verified**.
   - After each navigation, set the width again and confirm `document.documentElement.clientWidth` before measuring, because loading a page can reset the emulated size; an `innerWidth` larger than the set width means the page overflows. If screenshots time out because the pane is hidden, measure with JavaScript and mark the visual look **Not verified**.
   - Look at 320px and at 1280px, in light and in dark, and compare the look with the [design reference](../references/design-reference.html) (the scripts do not check spacing, type sizes, or components) (emulate the color scheme, or set `data-theme`). Test narrow widths only on the standalone file with its viewport meta, never on a render without one, because that lays out at about 980px and hides every narrow-width break (lesson L-120 in `skill-builder`).
   - Stop the server when the checks are done.
3. **Read against the rules.** Walk the [hard rules](../references/rules.md#hard-rules) that the script marked `SKIP`: Tab through every control, find color-only meaning, truncation, scroll edges without a cue, error and empty texts, and destructive actions. Then compare the page with [The generic look to avoid](../references/rules.md#the-generic-look-to-avoid).
4. Fix what fails and repeat the checks that the fix touched. Anything that could not be checked, such as no browser in this harness, is reported as **Not verified**.

## Deliver

Save the file where the user asked, or next to the brief's material. Publish it as an artifact only when the user asked for an artifact or for a shareable page. Then give the build report from [Output](../SKILL.md#output).

## Log the run

Append one row to [state/design-log.md](../state/design-log.md) (create it from the header there if it is missing): the date from the system clock, the task in a few words, the output's path, its surface, the reference version from `tokens.py show`, the client profile path, the studio design as `studio:<slug> v<N>`, or `none`, and the verdict (`Approve`, or `Block` with the open `HIGH` count). For a rebuilt template, update its existing row instead of adding a second one.

## Skills and agents

- [skill-design](../SKILL.md) - the output contract this stage delivers to.
- [scripts/page.py](../scripts/page.py) - `new`, `check`, and `adherence`; [scripts/tokens.py](../scripts/tokens.py) - `show` for the reference version.
- [references/surfaces.md](../references/surfaces.md) - how each surface applies the tokens.
- `pptx`, `docx` - slide decks and Word documents; `plugin-authoring` - mods.
- `dataviz` - charts.
- `artifact-design` - the page contract for published artifacts.
