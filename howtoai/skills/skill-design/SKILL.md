---
name: skill-design
description: Designs and reviews everything HowToAI skills, tools, and procedures show people, in the house design or a client's - web pages, artifacts and reports, dashboards, slide decks, Claude Code mods (band, pane, status line), Word documents, and emails, plus the templates other skills and tools ship. Build turns a brief into an accessible output in light and dark themes from the design tokens; review checks an output against hard accessibility and layout rules and reference adherence (off-token colors, fonts, radii), with ranked findings and a Block or Approve verdict. Keeps the house and client designs in the design studio, a local web app with one default design, and checks for a client's design first. Logs each output's design version and, after approval, rebuilds outdated templates. Use when asked to design, build, style, or review a page, report, deck, document, or mod, to apply the HowToAI look, to set up or edit a client's design, to open the design studio, or to redesign outputs after a design change.
compatibility: Claude Code (Python 3 and the browser pane for checks); Claude.ai and Cowork with reduced checks.
---

# Skill design

## Contents

- [Before you start](#before-you-start)
- [The stages](#the-stages)
- [The design reference](#the-design-reference)
- [The design studio](#the-design-studio)
  - [Change the house design](#change-the-house-design)
- [Output](#output)
- [Verify the output](#verify-the-output)
- [Common failures](#common-failures)
- [What it can't do](#what-it-cant-do)
- [Feedback](#feedback)
- [Skills and agents](#skills-and-agents)

## Before you start

1. **Mode.** Build mode when the request asks for a new or redesigned output; review mode when it asks to review, critique, or check one; redesign mode when it asks to bring earlier outputs or templates up to the current design reference. A request for both build and review ("review it and fix it") is a review, then fixes after the report. If unclear, ask.
2. **Input.**
   - Build: a brief, as text, a file, or the data the output shows, and its surface (see [references/surfaces.md](references/surfaces.md)); HTML when none is named. Without a reader or main point, ask once.
   - Review: a local HTML file path, a URL, a screenshot, or another surface's file (a deck, a document, a mod's `.tsx`). A screenshot can only be reviewed visually; say so in the report's Scope.
   - Redesign: nothing more; the [design log](state/design-log.md) lists the outputs.
3. **Tools.** Run `py -3 --version` (or `python3 --version`) and confirm Python 3, because `page.py`, `tokens.py`, and `design_studio.py` need it. Check that the browser pane (`mcp__Claude_Browser__*` tools) or another browser tool is available. With either missing, continue and mark the checks it would run as **Not verified**; never report them as passed.
4. **Paths.** The scripts are called through the skill's folder: `${CLAUDE_SKILL_DIR}` in Claude Code; in other harnesses, paths under `scripts/`, `assets/`, and `state/` are relative to this skill's folder.

## The stages

Read only the file for the current stage.

1. Redesign mode goes straight to [stages/redesign.md](stages/redesign.md) - find logged outputs older than the current reference, ask approval of the list, rebuild and review each template, update its stamp and the log. Skip the rest of this list.
2. [stages/source.md](stages/source.md) - build and review: find a client design in the studio, a client profile, or the project's own design, decide the design source (the studio's default design when none), and ask the client questions when needed.
3. Then one mode:
   - [stages/build.md](stages/build.md) - brief, copy first, section plan, output from the house starter or the surface's format, script and browser checks, delivery, log row.
   - [stages/review.md](stages/review.md) - scope, recon, script, adherence, and browser inspection, ranked findings, verdict, optional second opinion, log row.

Three kinds of rule apply, as [references/rules.md](references/rules.md) sets out: **hard rules**, which fail an output whatever its style; **reference adherence** (`R1`), which fails an output built to the reference or a client profile that uses values that are not tokens; and **recommended values** from the design reference, which a client profile or a deliberate project style may replace.

## The design reference

- [references/design-reference.html](references/design-reference.html) is the house design: principles and voice, color, type, shape, spacing, components, and guidance per surface, with a live preview. Build and Review read it for the look.
- [assets/design-tokens.json](assets/design-tokens.json) holds the values (`version`, `date`, `choices`, `options`, `tokens`) and is the only source of truth. [assets/house.css](assets/house.css) carries them as a generated token block that `page.py new` inlines into every page.
- `py -3 "${CLAUDE_SKILL_DIR}/scripts/tokens.py" show` prints the current version and choices; every template's stamp and every [design log](state/design-log.md) row records that version.
- This skill builds and rebuilds templates for other skills and tools; it is never called at runtime by their outputs ([Templates, not runtime](references/surfaces.md#templates-not-runtime)).

## The design studio

The design studio is a local web app on the design reference page: a gallery of named designs (the HowToAI house design, client designs, and references), each with a preview, its palette, type, spacing and shape, Do and Don't guidelines, and code views (DESIGN.md, Tailwind v4, CSS variables, design tokens). It creates, edits, duplicates, imports, exports, and deletes designs, keeps each design's version history, and marks one design as the **default**.

- **Edit:** **Edit design** turns the design's own page into edit mode (`#/d/<slug>/edit`; **New design** opens in it): every element becomes a field where it sits - details, each swatch (light and dark color, name, role; add or remove swatches), fonts and each type-scale step, every spacing, shape, motion, and layout value, Do and Don't items, surface notes, and the design's reference content (principles and voice, component notes, guidance per surface). The presets stay as quick-apply, and the preview and code tabs follow every change. A sticky edit bar shows the contrast status; **Save** is blocked while a pair fails AA and selects that pair's field; **Cancel** discards after a confirmation.

- **Start it:** `py -3 "${CLAUDE_SKILL_DIR}/scripts/design_studio.py" serve` in the background (add `--open` to open a browser). It listens on `127.0.0.1` only, on port 47615 or a free one, prints its URL, and writes it to `~/.claude/howtoai/design-studio.json`; a second `serve` prints the running studio's URL and exits. Open the URL in the browser pane. `design_studio.py url` prints it; `design_studio.py stop` stops it. The `command-pane` mod's **Design studio** button opens a running studio, or asks Claude to start it.
- **Data:** one SQLite database per user, `~/.claude/howtoai/designs.db` (`--db` or `HOWTOAI_DESIGN_DB` to use another), so designs survive plugin updates. The first run seeds it with "HowToAI house" (`howtoai-house`), the default, from [assets/design-tokens.json](assets/design-tokens.json) and, for its reference content, the page's `house-meta` block. Each design keeps its own reference content in the database (schema version 2; an older database is upgraded in place on first use, and every existing design gets a copy of the house content). Every save is checked as `tokens.py check` checks the house tokens (a failing contrast pair blocks it); a save that changes the tokens, guidelines, palette labels, or reference content raises the design's version and keeps the previous one in its history.
- **Client designs** live in the database as kind `client`, with the client's name and, optionally, the client project's folder, which is how [stages/source.md](stages/source.md) finds them. A client design is still exported as `design/client-profile.md` for the client's project (**Export client profile**, or `design_studio.py export <slug> --format profile --out <file>`); profiles written by hand keep working.
- **Without the server:** `design_studio.py list`, `show <slug>`, `export <slug> --format design-md|tailwind|css|tokens|profile [--out FILE]`, `set-default <slug>`, `import <file> [--name NAME] [--kind client --client NAME]` (a tokens JSON or a CSS file of custom properties), and `delete <slug> --confirm <slug>` work on the database directly. The default design cannot be deleted.
- Opened as a plain file, [references/design-reference.html](references/design-reference.html) shows the shipped house design, read only.

### Change the house design

The shipped house files ([assets/design-tokens.json](assets/design-tokens.json), [assets/house.css](assets/house.css), and the reference's embedded copy) change only on the owner's explicit request; a client design never changes them.

1. In the studio, edit the default design (or set another design as the default) and check its preview.
2. Make the change through `skill-builder`, as any change to this skill is. With the user's approval, press **Apply to house files** on the default design and type the confirmation, or run `py -3 "${CLAUDE_SKILL_DIR}/scripts/design_studio.py" apply-house <slug>`. Either runs `tokens.py apply`, which raises the version by 1 and regenerates the token block in `house.css` and the reference's embedded copy. A tokens file made another way is applied with `py -3 "${CLAUDE_SKILL_DIR}/scripts/tokens.py" apply "<file.json>"`.
3. Run `tokens.py check`.
4. Offer the redesign mode, so the outputs in the design log follow the new version.

## Output

These deliverables keep their own shapes, without workspace title or contents-list rules.

- **Build deliverable:** for HTML, one self-contained file (styles inline, no local dependencies, Google Fonts optional), with light and dark themes, saved where the user asks; published as an artifact only when the user asks. Another surface is delivered in its format, by its row in [references/surfaces.md](references/surfaces.md). A template carries its stamp. **Audience:** the brief's reader, often nontechnical.
- **Build report:** in chat, in this order: file path (and artifact link); design source (house reference version, studio design slug and version, client profile path, or the client's own design); `page.py check` and `page.py adherence` counts and any WARN kept, with its reason (or the surface's render or checklist result); browser checks done (widths, themes, keyboard); **Not verified** items; facts left as placeholders for the user to supply.
- **Review deliverable:** Markdown in chat, in the fixed shape of [references/review-format.md](references/review-format.md): Scope, Coverage, Findings (at most 15), What works well, Verification, Verdict. Saved to a file only when the user asks, as a self-contained HTML page built in the house design.
- **Redesign report:** in chat, as [stages/redesign.md](stages/redesign.md#report) sets out.
- **Client design:** a `client` design in the studio database, and `design/client-profile.md` in the client's project, exported from it or drafted from [assets/client-profile.md](assets/client-profile.md); each is saved only after the user approves its draft.
- **Design log:** one row per build, review, or rebuild in [state/design-log.md](state/design-log.md).

## Verify the output

- Build: `page.py check` and `page.py adherence` show no `FAIL` (adherence skipped only with "follow theirs"); the page was seen at 320px and 1280px in both themes on its standalone file and compared with the reference; a non-HTML surface was rendered, or checked against the token checklist and the report says which; every fact traces to the brief; every placeholder is listed in the report; a template has its stamp; the log has its row.
- Review: every finding has a location and evidence; every `HIGH` cites a hard rule or `R1`; no finding objects to a deliberate, consistent style; the verdict matches the findings (`Block` exactly when a `HIGH` remains); every unchecked area is named; the log has its row.
- Redesign: nothing changed before the list was approved; each rebuilt template has a dated backup, passes `check` and `adherence`, and carries the new stamp; its log row shows the new version.
- Profile: overridden tokens keep the house names, and their pairs pass `page.py check` on the first page built with them.

## Common failures

| Symptom | Cause | Fix |
| --- | --- | --- |
| A page passes at 320px in the browser but breaks on a phone | It was tested on a render without the viewport meta, which lays out at about 980px | Test the standalone file that `page.py new` wrote, which has the meta |
| Columns hidden past a scroll edge at every width | A wide table for records with long text | Use cards (`.card`) for long-text records; keep tables to short fields |
| A client review is full of "findings" about radius or color | The client's page was judged against the house look | Judge a consistent client style against itself plus the hard rules, and skip adherence |
| Dark theme has unreadable text | A raw color in page CSS skips the dark tokens | Replace raw colors with tokens; `page.py adherence` lists them under `colors` |
| `adherence` fails a client page on every brand color | The profile was not passed | Run it with `--profile "<path>"` |
| `adherence` fails a fresh `page.py new` page | `house.css` and `design-tokens.json` are out of step | Run `tokens.py check`, then `tokens.py apply` through `skill-builder` if needed |
| The page shows "0" or a guessed number | A missing figure was filled in | Use a stated placeholder and list it in the report |
| `contrast` is `SKIP` | The page uses its own token names, or declares tokens it never uses | Measure the pairs it applies with `page.py contrast <fg> <bg>` and report them |
| `http.server` fails with WinError 10013 | The fixed port is in a range Windows reserves (for example 8803-8902) | Serve on port 0 and read the chosen port from the server's first line |
| A client page shows a fallback font instead of the brand font | The profile changes the font tokens but has no font-link block | Add the block to the profile; `page.py new` warns and `page.py check` reports `fonts` |
| A workflow the brief says nothing about shows a green "ok" | Missing status was read as success | Show "Not reported" in a neutral badge |
| A redesign misses a template | It was built without a log row | Add the row (with its stamp's version) and run the redesign again |
| A template's script breaks after a rebuild | Its placeholders or hooks changed | Keep every placeholder the script fills; change the script with the template and test a rendered output |
| The Design studio button asks Claude to start the studio every time | The studio is not running, or `~/.claude/howtoai/design-studio.json` names a port nothing answers on | Run `design_studio.py serve`, which rewrites the file; `design_studio.py url` shows a running studio |
| A client build uses the house design although the studio has the client's design | The client design names neither the client in the brief nor the project's folder | Set the design's client and project path in the studio, or name its slug in the brief |
| A studio save is refused | A text and background pair fails the contrast check | Change the pair the error names; the editor shows each pair's result |
| Every output looks different after a studio change | Apply to house files rewrote the shipped house files | Apply only on an explicit request, then run the redesign mode |

## What it can't do

- It cannot verify rendering, keyboard, or zoom without a browser, nor run `page.py` without Python; in Claude.ai or Cowork without a shell or browser, it reports those checks as **Not verified** and checks contrast by computing it in the conversation.
- `page.py adherence` checks colors, font families, and radii only; spacing, type sizes, shadows, motion, and components are compared by eye with the reference.
- It reads design files and pages, not Figma libraries; for a Figma design, ask for exported tokens or use a Figma connector if the user has one.
- A mod's band and pane take the host theme's colors and fonts; only their wording, order, icons (characters), and status colors follow the reference.
- It does not publish, send, or overwrite files without asking; replaced files are kept as dated copies.
- Screen-reader output is reasoned from markup, not heard; for a high-stakes page, recommend a test with NVDA or VoiceOver.
- It does not change the house design for one client; such a change goes through [Change the house design](#change-the-house-design).
- The studio runs only on the user's own machine (Claude Code with Python); in Claude.ai or Cowork the house files and client profiles are used without it.

## Feedback

If the user asks to change how this skill works or reports a problem with it, use the `skill-builder` skill (for example, `/skill-builder`) to plan and apply the change. If `skill-builder` is unavailable, agree the change with the user first, keep it as small as the problem needs, and check the skill afterwards.

## Skills and agents

- [stages/source.md](stages/source.md), [stages/build.md](stages/build.md), [stages/review.md](stages/review.md), [stages/redesign.md](stages/redesign.md) - the stages.
- [references/design-reference.html](references/design-reference.html) - the house design reference and the design studio's page; [references/rules.md](references/rules.md) - hard rules, R1, severity, fixes, recommended values, principles, components; [references/surfaces.md](references/surfaces.md) - how each surface applies and checks the tokens, and template stamps; [references/review-format.md](references/review-format.md) - the review report.
- [assets/design-tokens.json](assets/design-tokens.json) - the token values; [assets/house.css](assets/house.css), [assets/starter.html](assets/starter.html), [assets/client-profile.md](assets/client-profile.md) - copied into outputs; [examples/specimen.html](examples/specimen.html) - every component on one page.
- [scripts/page.py](scripts/page.py) - `new` builds a page from the starter; `check` runs the scripted checks; `adherence` checks colors, fonts, and radii against the tokens; `contrast` measures any color pair. [scripts/tokens.py](scripts/tokens.py) - `show`, `check`, `apply`. [scripts/design_studio.py](scripts/design_studio.py) - the design studio: `serve`, `url`, `stop`, `list`, `show`, `export`, `set-default`, `import`, `delete`, `apply-house`.
- [state/design-log.md](state/design-log.md) - every output's reference version, read by the redesign stage.
- `artifact-design` - the page contract when a page is published as an artifact.
- `dataviz` - charts in house colors; `pptx`, `docx` - decks and Word documents; `plugin-authoring` - mods.
- `command-pane` - its Design studio button opens the studio.
- `interfaces:better-interface` - optional second opinion in review mode, when installed.
- `skill-builder` - builds and maintains this skill and the house design; stamps templates in its plans and runs the design pass in Test.
