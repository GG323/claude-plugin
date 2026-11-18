# Rules

## Contents

- [Evidence, not taste](#evidence-not-taste)
- [Hard rules](#hard-rules)
- [Reference adherence](#reference-adherence)
- [Severity](#severity)
- [The cheapest fix first](#the-cheapest-fix-first)
- [Recommended values](#recommended-values)
- [House principles](#house-principles)
- [Components](#components)
- [The generic look to avoid](#the-generic-look-to-avoid)
- [Skills and agents](#skills-and-agents)

## Evidence, not taste

Three kinds of rule apply to every output this skill builds or reviews:

- **Hard rules** fail an output whatever its style, because each one stops some reader from using it. A client's design never excuses one.
- **Reference adherence** (`R1`) applies only to an output built to the design reference, a client profile, or a studio design: its colors, fonts, and radii are tokens.
- **Recommended values** are the house defaults in the [design reference](design-reference.html) and [design-tokens.json](../assets/design-tokens.json). They are defaults with escape conditions, not findings: a deliberate and consistent project or client style that differs from them is a preference, and is never reported. The same detail done two different ways in one output is a finding, because inconsistency is visible to every reader.

A finding needs evidence: the file and line, or the screen and component, and what was seen or measured. A check that could not be run is reported as **Not verified**, never as a finding and never as a pass.

## Hard rules

Each is `HIGH` as soon as it is confirmed, however small the surface:

| # | Rule | How it is checked |
| --- | --- | --- |
| H1 | Every interactive control has an accessible name | `page.py check` (names); browser accessibility tree |
| H2 | Every keyboard-reachable control shows a visible focus indicator | `page.py check` (focus); Tab through the page |
| H3 | Everything reachable by pointer is reachable by keyboard | Tab and Enter or Space through every control |
| H4 | Body and control text meets 4.5:1 contrast (3:1 at 24px or 18.7px bold and up); control borders and focus rings meet 3:1; no screen text below 12px | `page.py check` (contrast, text-size) for tokens; measure any raw color pair |
| H5 | No content or control is clipped, overlapped, or unreachable at 320px width or 200% zoom | Browser at 320px on a standalone render |
| H6 | Content past a scroll edge or inside a disclosure has a visible cue | Browser at 320px and desktop |
| H7 | State or meaning is never carried by color alone | Read every colored element for a word or icon beside it |
| H8 | Truncated content has a way to reach the full value | Find `text-overflow`, line clamps, fixed heights |
| H9 | Motion and auto-play respect `prefers-reduced-motion`; nothing the reader needs runs on a timer | `page.py check` (motion); emulate reduced motion |
| H10 | An error or empty state says what to do next | Read every error, empty, and "none found" text |
| H11 | A destructive action has a confirmation, an undo, or a distinct treatment, and danger color appears only on destructive actions | Read every button and link |
| H12 | Images that carry meaning have `alt` text; decorative ones have `alt=""` | `page.py check` (images) |
| H13 | The page declares its language and a viewport, and has one `h1` with no skipped heading levels | `page.py check` (lang, viewport, headings) |
| H14 | The content is real and works: no placeholder text, no placeholder or empty link targets (`example.com`, `#` alone, in-page links to ids that do not exist), no missing images or media | `page.py check` (content); load media and in-page links in the browser; a site-relative link (`/pricing`) is **Not verified** unless the real site is served |

A missing viewport meta is an H13 finding of its own when the page ships as a file; a page that a host wraps (a claude.ai artifact) gets one from the host. Status that the source does not give is shown as "Not reported" in a neutral badge, never as `ok`, because a green badge claims something nobody checked.

When a check cannot run in the browser at hand (reduced-motion emulation, 200% zoom, key-driven scrolling), read the CSS for the rule instead and mark the rendered check **Not verified**; a CSS rule that matches no element is a latent defect, reported as `MEDIUM`.

For a surface that is not HTML (slides, a Word document, a mod), the hard rules apply where they make sense (contrast, color-only meaning, names, real content); [surfaces.md](surfaces.md) says how each is checked.

## Reference adherence

| # | Rule | How it is checked |
| --- | --- | --- |
| R1 | An output built to the design reference, or to a client profile, uses only its tokens: every color, font family, and corner radius is a token value or a `var(--...)` reference | `page.py adherence` for HTML; a screenshot compared with the [design reference](design-reference.html); the token checklist in [surfaces.md](surfaces.md) for other surfaces |

- R1 applies to every HowToAI output and template, and to every page built with a client profile or a studio design; with a profile (or a studio design exported as one), its overrides join the allowed values.
- It does not apply to a page judged against its own consistent style (a client's own design, "follow theirs"): there, Scope says R1 was skipped and why.
- An R1 failure is `HIGH`, because an off-token value breaks the dark theme, client profiles, and the next redesign. One root cause (one raw palette, one stray font) is one finding listing every location.

## Severity

- `HIGH` - a hard rule or R1 fails. Every `HIGH` cites one; a defect that blocks a task and fits no other rule is H14.
- `MEDIUM` - a `Taste` issue that repeats across the page or harms reading, scanning, or consistency: two button styles, a wide table where cards belong, a key number buried below the fold; also a latent hard-rule defect (CSS that matches no element yet).
- `LOW` - an isolated `Taste` issue with little effect on the task.

A finding whose one cause breaks two rules cites both (`H11, H4`); a rule broken by two unrelated causes gives two findings. In Coverage, count a finding once, under the area of its first rule.

Within a severity, rank by reach: a token or shared component outranks the same symptom in one place, because one fix buys more.

## The cheapest fix first

When several fixes work, propose the first that does:

1. **Delete** - a border that space already carries, an animation, ARIA that a native element makes redundant.
2. **Use the platform** - a native element (`button`, `details`, `label`), the browser's focus ring.
3. **Reuse** - an existing token or component, before any new value.
4. **Correct** - the wrong value, replaced by the token or recommended value.
5. **Add** - a new token, wrapper, or media query, only when the above cannot fix it.

## Recommended values

The values themselves live in [design-tokens.json](../assets/design-tokens.json) and are shown on the [design reference](design-reference.html); this table names the token groups and their escape conditions. They are findings only on an output judged against the house design (a HowToAI output, or a page with no design of its own): there, a departure without a reason gets a `LOW` or `MEDIUM` finding. A page judged against its own consistent style, or a client profile, gets none.

| Topic | House value | Escape condition |
| --- | --- | --- |
| Body text | `--text-md` with `--leading-body`, measure at most `--measure` | Dense data tables may use `--text-sm` |
| Smallest text | `--text-xs` | None below 12px in any style |
| Type scale | `--text-xs` to `--text-display`, one size per element kind | A client scale replaces it whole |
| Faces | `--font-display`, `--font-body`, `--font-mono` only | A client brand font replaces the body or display face |
| Spacing | `--s-1` to `--s-9` only | A client spacing scale replaces it whole |
| Width | Content at most `--page-max`; 16px gutter at phone width | Full-bleed media and data grids |
| Color | Tokens only, one accent, status colors for status, `--brand` only as decoration | A client palette mapped onto the same token roles |
| Radius | `--r-1` controls and badges, `--r-2` cards, `--r-3` feature cards, `--r-pill` buttons and chips | A client radius scale |
| Elevation | Borders (`--border-w`), `--shadow` only | A client elevation scale with at most two levels |
| Motion | `--dur-1` or `--dur-2` with `--ease`, color or border changes, gated | A client motion language, still gated |
| Primary action | One filled button per view | None |
| Records | Cards for long text fields, tables for short compared fields | A table whose every column fits at 320px |
| Copy | Headings name things; buttons verb plus object | A client voice guide |

## House principles

The reasons behind the recommended values, for cases the tokens do not name. The [design reference](design-reference.html) shows each one.

- **Content leads, chrome stays quiet.** The first screen says what the output is, for whom, and its main fact or number. No hero image or slogan stands in for that.
- **Plain words name things.** Headings are nouns ("Open invoices"); buttons are a verb plus an object ("Download report"); "Learn more", "Click here", and "Submit" never appear. Write the copy before the markup. Facts come from the brief or the data; an unknown value shows a stated placeholder such as "none found".
- **One accent, status colors only for status.** `--accent` marks the one primary action, the active state, and focus; status colors always sit next to a word.
- **Type does the hierarchy.** Size, weight, and the display face carry it, not color or boxes. Compared numbers use tabular figures (`.num`). Sentence case everywhere.
- **Records are cards, short fields are tables.** A record with long text is a `.card`; a table is for short fields compared across rows, inside `.scroll` (lesson L-119 in `skill-builder`).
- **What the reader must act on comes first.** After the key figures, group what needs a decision, then the detail.
- **Borders for structure, no shadows.** Space and hairlines separate sections; shadows appear only as the scroll-edge cue.
- **Motion only as feedback.** No scroll reveals, parallax, carousels, or decorative animation.
- **Both themes and phone width.** Every output ships light and dark tokens, a 16px gutter at phone width, no horizontal page scroll, and system font fallbacks.

## Components

Each is a class in [house.css](../assets/house.css); [examples/specimen.html](../examples/specimen.html) shows them, and the [design reference](design-reference.html) shows them in the current tokens.

| Component | Class | Use for |
| --- | --- | --- |
| Page frame | `.page`, `.page-head`, `.lead`, `.meta`, `.page-foot` | every page |
| Section | `section`, `.section-rule`, `.label` | one topic; a rule for top-level sections |
| Key figures | `.figures`, `.figure` (`.danger`, `.warn`, `.ok`) | the three to six numbers the reader needs first |
| Chips | `.chips` | a row of jump links or filters |
| Cards | `.cards`, `.card`, `.card-head`, `.card-body` | records with long text fields |
| Badges | `.badge` (`.danger`, `.warn`, `.ok`, `.accent`) | a short status word |
| Callout | `.callout` (`.danger`, `.warn`, `.ok`) | one message the reader must not miss |
| Table | `.scroll` around `table`, `td.num`, `td.date` | short fields compared across rows; numbers right-aligned, numbers and dates never wrap |
| Buttons | `.button`, `.button.primary` | actions; one primary per view |
| Disclosure | `details`, `summary` | optional detail, such as a run log |

Charts follow the `dataviz` skill, with colors taken from the tokens.

## The generic look to avoid

These mark an output as template or "AI-made"; replace each with the house pattern.

| Generic pattern | House pattern |
| --- | --- |
| Gradient hero, blurred blobs, glass cards | Plain title, lead line, key figures |
| Everything centered | Left-aligned text on one edge |
| Emoji as icons or bullets | Words, badges, or one icon set in `currentColor` |
| Cards in cards, shadows on every box | One border level; space between groups |
| Purple-to-blue accent gradients | The single `--accent` |
| "Unlock", "Elevate", "Seamless", "Learn more" | Plain nouns and verb-plus-object buttons |
| Three identical feature tiles with icons | Content that differs gets layouts that differ |
| Fade-in on scroll | Content visible on load |

## Skills and agents

- [skill-design](../SKILL.md) - applies these rules in its build, review, and redesign stages.
- [design-reference.html](design-reference.html) and [design-tokens.json](../assets/design-tokens.json) - the reference and its values; [surfaces.md](surfaces.md) - how each surface applies and checks them.
- `interfaces:better-interface` - a deeper, optional second review with its own rule set.
