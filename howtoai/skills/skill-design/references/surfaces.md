# Surfaces

## What this file is

How Build applies the design tokens on each surface, and how Review checks them. HowToAI makes skills, tools (agents, plugins, mods, hooks, commands, MCP servers, connectors), and procedures; any of them can produce one of these surfaces, and the same reference applies to all. The values come from [design-tokens.json](../assets/design-tokens.json), shown on the [design reference](design-reference.html), whose surface guidance says what each surface looks like. A client profile's overrides, or a studio design exported as a profile, replace the house values where they set them ([Use the chosen design](../stages/source.md#use-the-chosen-design)).

## Surface table

| Surface | Build applies the tokens | Review checks them |
| --- | --- | --- |
| Web page (client or landing page) | `page.py new` (house CSS, token block, font link from `tokens.fonts_url`), then house classes and `var(--...)` only | `page.py check` + `page.py adherence`; screenshots at 320px and 1280px, light and dark, compared with the reference |
| Artifact or report (HTML, also a template a script fills) | As a web page; a template keeps the stamp comment ([Templates, not runtime](#templates-not-runtime)) and placeholders its script fills | `page.py check` + `page.py adherence` on a rendered output, not on the raw template; screenshots as above |
| Dashboard | As a web page in compact density; chart colors from the tokens through `dataviz` | `page.py check` + `page.py adherence` (it also reads SVG `fill` and `stroke`); screenshots as above, with the chart legend read in both themes |
| Slide deck (`pptx` or a slides artifact) | The deck's theme gets the token colors, fonts, and radii by role (background `--bg`, text `--fg`, accent `--accent`, cards `--feature-bg`); HTML slides follow the web page row | HTML: as a web page. Otherwise render slides to images (the `pptx` skill) and look at them; if rendering is not possible, the [token checklist](#token-checklist), and the report says so |
| Claude Code mod (band, pane, status line) | The host theme draws it, so no hex values or fonts: the mod's named theme colors (for example `warning`, `error`, `suggestion`) map onto the status roles; icons are characters; labels are verb-plus-object words; the status line is plain text. What a mod can draw is in `command-pane`'s `docs/mod-programming.md` | Screenshot the band or pane in the desktop app where possible; otherwise read the `.tsx` against the [token checklist](#token-checklist) (no raw colors, named theme colors only for status, character icons, short labels), and the report says so |
| Word document (`docx`) | Styles get the token fonts (display face for headings, body face for text), `--fg` text, `--accent` only for heading rules and one table header row, `--line` table borders | Render pages to images (the `docx` skill) and look at them; if rendering is not possible, the [token checklist](#token-checklist), and the report says so |
| Email (HTML) | Inline styles with token values written out (email clients drop custom properties), body face with a system fallback, one accent button | `page.py adherence` on the HTML (resolved token values pass); a screenshot in a browser; client rendering is **Not verified** |
| Other (PDF, image, spreadsheet) | Token colors and fonts by role, through the format's skill | Render to an image where possible; otherwise the [token checklist](#token-checklist), and the report says so |

## Token checklist

For a surface that cannot be rendered here, read its source or export and check each line; mark the result `checklist` in Verification, not `rendered`:

1. Every color is a token value (light, or dark where the surface has a dark mode); no other hex, rgb, or named color.
2. Fonts are the token families, or their stated system fallbacks.
3. Corner radii are token radii, or the surface has none.
4. One accent use per view; status always has a word beside its color (H7).
5. Text and background pairs are token pairs that `tokens.py check` passed, or measured with `page.py contrast` (H4).
6. Copy follows [House principles](rules.md#house-principles): headings name things, buttons are a verb plus an object.
7. A template carries its stamp.

## Templates, not runtime

Every HowToAI skill or tool that produces a page or report ships its own template in its `assets/`, filled by its own script or fixed step, so every run looks the same.

- `skill-design` builds that template, and rebuilds it when the design reference gets a new version or the client's design changes ([stages/redesign.md](../stages/redesign.md)). The outputs never call `skill-design` at runtime; a review of a rendered output during testing is a check, not a dependency.
- Each template carries a stamp near its top, in the surface's comment form (an HTML or CSS comment, a TSX comment, a document property): `built from skill-design design-reference v<N> (<date>)`, `built from client profile <path> (<date>)` for a client template, or `built from studio design <slug> v<N> (<date>)` for one built to a studio design. `<N>` and `<date>` are the `version` and `date` that `tokens.py show` prints. `skill-builder` repeats the stamp in its registry row's Notes and compares it in Recall.
- Each build or rebuild adds a row to [state/design-log.md](../state/design-log.md), which [stages/redesign.md](../stages/redesign.md) reads.
