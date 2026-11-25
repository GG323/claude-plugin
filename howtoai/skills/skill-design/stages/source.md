# Choose the design source

## When this stage runs

First in every run, from [Before you start](../SKILL.md#before-you-start), in both modes. It settles which design the output is built to or judged against: the studio's default design (normally the house design, the [design reference](../references/design-reference.html) and its [tokens](../assets/design-tokens.json)), a client design from the studio, a client profile, or the project's own style. The studio and its database are described in [The design studio](../SKILL.md#the-design-studio). This applies to every surface the skill covers, from a page to a slide deck or a mod. Judging a client's page against the house look would turn their deliberate choices into false findings, so this is decided before anything else.

## Look for a design already in place

Search, in this order, and note every hit with its path:

1. A client design in the studio: run `py -3 "${CLAUDE_SKILL_DIR}/scripts/design_studio.py" list` (it reads `~/.claude/howtoai/designs.db`; the server need not run). A `client` design matches when its client is the client the brief or user names, or its project path holds the working project's folder; a slug the user names always matches. Read the match with `design_studio.py show <slug>`. With no database yet, there is no studio design; go on.
2. A client profile: `design/client-profile.md` in the working project, or a path the user names.
3. The project's own design: CSS custom properties in a theme or token file (`tokens.css`, `theme.css`, `variables.css`, a `:root` block), a Tailwind config with a theme, a design-system or brand document (`DESIGN.md`, `brand*.md`, a style guide PDF), or an existing page the user wants matched.
4. Brand material in the brief: colors, fonts, a logo, or a link to a style guide or Figma library.

Read what you find; do not guess a palette from a screenshot when a token file exists.

A page or project **has its own design** when it defines colors, type, or spacing once (tokens or a theme) and uses them consistently, or when the user gives brand material. Tokens that are declared but never used, or styles that differ from element to element, are not a design of their own. An own design is **complete** when it covers text, background, and accent colors, status colors (success, warning, error), a dark theme, and its fonts; otherwise it is **partial**.

## Decide the source

Take the first row that matches:

| Found | Mode | Source | Ask |
| --- | --- | --- | --- |
| A client design in the studio | Either | That design | Nothing, unless the brief asks for changes; then say what the design currently sets and confirm the change. If a client profile in the project differs from it, ask which one is current |
| A client profile | Either | The house design with the profile's overrides | Nothing, unless the brief asks for changes; then say what the profile currently sets and confirm the change |
| A page with its own design | Review | Its own style plus the [hard rules](../references/rules.md#hard-rules) | Nothing, unless the user asks for a judgment against the house design or their goal is unclear |
| No design of its own | Review | The hard rules plus the studio's default design | Nothing; Scope says so |
| The project's own design, or brand material in the brief | Build | Ask | One message with the [client questions](#questions-for-a-client-with-their-own-design), starting with: follow yours, follow ours, or ours with your brand colors and logo. Pre-fill each question with what you found, and leave out questions the files already answer. Recommend "follow theirs" when their design is complete, and "ours with your brand" when it is partial |
| Nothing | Build | The studio's default design (`design_studio.py list` marks it); the house design when there is no database | Nothing; the report names the design used |

The build waits for the answer. Without a live user (a scheduled run or a subagent), build with the recommended option, mark the page and the report as a draft pending the client's choice, and write no profile.

When no row asks the client anything, skip the next section.

## Questions for a client with their own design

Ask these in one message, and record the answers in the client profile:

1. Should the page follow your design, ours, or ours with your brand colors and logo?
2. Which file or link holds your design: a style guide, a theme or token file, a Figma library, or an existing page to match?
3. Your brand colors: the main color, and any colors kept for success, warning, and error?
4. Your fonts, and whether they may load from the web or must be installed fonts only?
5. A logo file, and where it may appear?
6. Light only, dark only, or both?
7. Anything in our house look that must change, such as corner radius, density, or the display type?

## Write or update the client profile

When the user chose "theirs" or "ours with their brand", or asked to change the house look for this client. The client's design is kept in the studio and exported to the project as a profile; a profile is still written by hand where the studio is not available:

1. Draft the profile from [assets/client-profile.md](../assets/client-profile.md): the decisions in one line each, and token overrides that keep the house token names.
   - Map every brand color the client gives onto its role: main color to `--accent`, brand background, text, and muted colors to `--bg`, `--fg`, and `--muted`; derive `--line`, `--line-strong`, and `--accent-bg` to match. Keep the house status colors unless the client has their own.
   - Dark theme: when the client gives no dark colors but wants both themes, derive them by keeping each role and hue, inverting lightness, and meeting the same contrast targets; say in the profile that they are derived.
   - "Square corners" sets `--r-1` and `--r-2` to 0; set `--r-pill` to 0 only if the client says badges must be square too.
   - Client fonts: add a font-link block (a fenced `html` block with their font `<link>` tags) whenever the profile changes `--font-display` or `--font-body`, so pages load them.
   - When the accent is close in hue to `--danger` (both red or red-brown), say so: status must then always carry its word, and the danger color stays only on status.
2. Check the draft before showing it: build a throwaway page from it in the session's scratch folder with `py -3 "${CLAUDE_SKILL_DIR}/scripts/page.py" new "<scratch>/profile-check.html" --title "Profile check" --profile "<draft path in scratch>"`, then run `page.py check` on it. Fix any contrast `FAIL` in the draft.
3. Show the draft and ask before saving it. With the user's approval, save it as a `client` design in the studio with the client's name and project path (in the studio's editor, or `design_studio.py import "<tokens.json or theme.css>" --name "<name>" --kind client --client "<client>"`, then the project path in the editor), and write `design/client-profile.md` in the client's project (or the path the user names) with `design_studio.py export <slug> --format profile --out "<path>"`, or from the draft where there is no studio. The profile can be shown and approved in the same message as the answer to the client questions when the user asked for both at once. If a profile exists, show the change against it and keep a copy of the old file next to it as `client-profile.<YYYY-MM-DD>.md`, with the date from the system clock.
4. Never edit [house.css](../assets/house.css), [design-tokens.json](../assets/design-tokens.json), or the [design reference](../references/design-reference.html) for one client, nor set a client design as the studio's default or apply it to the house files: the house design changes only as [Change the house design](../SKILL.md#change-the-house-design) sets out, because every product and client page depends on it.

With "follow theirs" and a complete design of their own (a token file the page can link or copy), the profile records only the source path and the decisions; the page uses their tokens directly, and the house components are used only where they map onto them.

## Use the chosen design

Build and Review read the chosen design's spec, not only the shipped house files:

- **The house design** (no database, or the default is `howtoai-house` at the version `tokens.py show` prints): the [design reference](../references/design-reference.html) and [design-tokens.json](../assets/design-tokens.json); no profile is passed.
- **Any other studio design** (a client design, or a default that differs from the shipped house files): read its spec with `design_studio.py show <slug>`, and export it as a profile into the session's scratch folder with `py -3 "${CLAUDE_SKILL_DIR}/scripts/design_studio.py" export <slug> --format profile --out "<scratch>/<slug>-profile.md"`. Pass that file as `--profile` to `page.py new` and `page.py adherence`, and use its colors, fonts, and radii on other surfaces. Record the slug and version for the report and the log.
- **A client profile file:** pass its path as `--profile`.

## Go to the mode

Build mode: read [stages/build.md](build.md). Review mode: read [stages/review.md](review.md). Read only that file.
