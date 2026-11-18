# Review a page

## Contents

- [When this stage runs](#when-this-stage-runs)
- [Resolve the scope](#resolve-the-scope)
- [Recon the page's own style](#recon-the-pages-own-style)
- [Inspect](#inspect)
- [Rank and write the report](#rank-and-write-the-report)
- [After the report](#after-the-report)
- [Log the run](#log-the-run)
- [Skills and agents](#skills-and-agents)

## When this stage runs

From [stages/source.md](source.md) in review mode, with the design source decided; for a studio design, use the profile exported there ([Use the chosen design](source.md#use-the-chosen-design)). Read [references/rules.md](../references/rules.md) and [references/surfaces.md](../references/surfaces.md) in full. When the output is judged against the house design or a client profile, also read the [design reference](../references/design-reference.html) and run `py -3 "${CLAUDE_SKILL_DIR}/scripts/tokens.py" show` for its version and date; the values come from [design-tokens.json](../assets/design-tokens.json). For a surface that is not HTML (slide deck, Word document, mod), review it by its row in the [surface table](../references/surfaces.md#surface-table): render or screenshot it where possible, otherwise use the [token checklist](../references/surfaces.md#token-checklist) and say so in Scope. A review changes nothing: it reads, renders, and reports, and edits only when the user then asks for the fixes.

## Resolve the scope

Name the file, URL, or screen, and its states: empty, loading, error, long content, and narrow width where they exist. When the scope is too large to inspect credibly, take the one page or flow the request centers on, and say what was left out. Never imply that an uninspected part was reviewed.

## Recon the page's own style

Identify the stack (plain HTML, a framework, Tailwind), its tokens, and its components, so every fix is written in the page's own idiom. A deliberate, consistent style is not a finding; only the [hard rules](../references/rules.md#hard-rules) and inconsistencies inside the page are, unless the page is judged against the house design.

## Inspect

1. **Script.** For a local HTML file, run `py -3 "${CLAUDE_SKILL_DIR}/scripts/page.py" check "<page.html>"` and note each result with its rule ID. For a page that is not a local file, mark the script's checks **Not verified** and cover them in the browser.
   - **Adherence.** When the page is judged against the house design or a client profile, also run `py -3 "${CLAUDE_SKILL_DIR}/scripts/page.py" adherence "<page.html>"`, adding `--profile "<path>"` for a client profile or an exported studio design. Each `FAIL` is an [R1](../references/rules.md#reference-adherence) finding; its `SKIP` lines go to Verification. A page judged against its own style skips adherence, and Scope says so.
2. **Serve.** Serve a folder that holds the page (and the viewport copy from step 3, when there is one) with `py -3 -u -m http.server 0 --bind 127.0.0.1 --directory "<folder>"` in the background, and read the port from its first output line ("Serving HTTP on ... port N"); `-u` makes that line appear at once. Port 0 lets the system pick a free port, because Windows reserves ranges such as 8803-8902 and a fixed port can fail with WinError 10013. If no server can start, open the file directly: the browser pane then shows a static snapshot that may refuse page tools and stays light, so mark measured and dark-theme checks **Not verified**.
3. **Viewport copy.** If the page has no viewport meta, it is an H13 finding, and narrow-width checks on it are invalid (it lays out at about 980px). Copy it into a temporary folder outside the project (the session's scratch folder), add `<meta name="viewport" content="width=device-width, initial-scale=1">` to the copy only, and test narrow widths on the copy. Delete the copy after the review.
4. **Browser.** Load the harness's browser skill first when it has one (for example `anthropic-skills:built-in-browser`). After each navigation, set the width again and confirm `document.documentElement.clientWidth` before measuring, because loading a page can reset the emulated size; an `innerWidth` larger than the set width means the page overflows. If screenshots time out because the pane is hidden, measure with JavaScript and mark the visual look **Not verified**. Measure any raw color pair the page applies with `py -3 "${CLAUDE_SKILL_DIR}/scripts/page.py" contrast "<fg>" "<bg>"`, rather than writing a contrast script. Look at 320px and 1280px, light and dark, and, when the page is judged against the reference, compare the screenshots with the [design reference](../references/design-reference.html) for what the script does not check (spacing, type sizes, components). Walk the keyboard through every control. Check each hard rule the script marked `SKIP`; where the browser lacks a control (reduced motion, zoom), follow the rule's fallback in [rules.md](../references/rules.md#hard-rules).
5. **Read.** Go through the areas in this order, so foundational failures are not hidden by polish: accessibility, layout, copy, type, color, components. For each, note the evidence (file and line, or screen and component) and what was seen or measured.

## Rank and write the report

1. Classify each issue: a hard rule (`H1` to `H14`, always `HIGH`), reference adherence (`R1`, always `HIGH`, only when judged against the reference or a profile), or `Taste` (a recommended value or house principle, `MEDIUM` or `LOW`, and only when the page is judged against the house design or is inconsistent with itself). Use the [severity](../references/rules.md#severity) ladder.
2. Merge one root cause into one finding with every location. Choose each **After** by [the cheapest fix first](../references/rules.md#the-cheapest-fix-first).
3. Write the report exactly as [review-format.md](../references/review-format.md) shows. At most 15 findings; never pad toward the cap.

## After the report

- If the user asks for the fixes, apply them to the page, then run the checks again and report the new verdict. Keep a copy of the original as `<name>.<YYYY-MM-DD>.html` first, with the date from the system clock.
- If `interfaces:better-interface` is installed (check the skills list), offer it once as a second opinion, and merge its distinct findings into the table with their source named. Its rules are its own; where they conflict with a client profile, the profile wins on taste and both yield to the hard rules.
- Then give the review report from [Output](../SKILL.md#output).

## Log the run

Append one row to [state/design-log.md](../state/design-log.md) (create it from the header there if it is missing): the date from the system clock, `review` and what was reviewed, the output's path, its surface, the reference version it was judged against (or `own style`), the client profile path, the studio design as `studio:<slug> v<N>`, or `none`, and the verdict. When the output already has a row (a template), update that row's verdict and date instead.

## Skills and agents

- [skill-design](../SKILL.md) - the skill this stage belongs to.
- [scripts/page.py](../scripts/page.py) - `check` and `adherence`; [scripts/tokens.py](../scripts/tokens.py) - `show`.
- [references/surfaces.md](../references/surfaces.md) - how each surface is checked.
- `interfaces:better-interface` - optional second review.
