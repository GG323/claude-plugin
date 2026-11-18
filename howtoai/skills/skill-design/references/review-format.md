# Review format

## Contents

- [Shape](#shape)
- [Example](#example)
- [Skills and agents](#skills-and-agents)

## Shape

The review is Markdown in chat, in exactly these sections and this order, with no title or contents list of its own. An empty section keeps its heading and says "none".

1. **Scope** - what was reviewed (file, URL, or screen and its states), its surface, the stack, and the design source it was judged against: the house design reference with its version, a studio design with its slug and version, the client profile at its path, or the project's own style (then say that reference adherence was skipped).
2. **Coverage** - a table: area (Accessibility, Layout, Copy, Type, Color, Components), what was inspected, and the result as a findings count, `Clear`, `Partly verified` (inspected, but a check in it could not run; name it in Verification), or `Not reviewed` with the reason.
3. **Findings** - one table for all areas, `HIGH` first, then by reach, at most 15 rows:

   | # | Severity | Rule | Location | Before | After | Why |
   | --- | --- | --- | --- | --- | --- | --- |

   - **Rule** is a hard rule ID (`H1` to `H14`), `R1` for a value that is not a token on an output judged against the reference or a profile, or `Taste` for a recommended value or a house principle.
   - **Location** is `path/to/file:line`, or the screen and component when there is no source.
   - **Before** shows the current code or what is seen; **After** the replacement, written in the page's own idiom and chosen by [the cheapest fix first](rules.md#the-cheapest-fix-first). A value only the user knows (the page language, what an icon button does, a real URL) goes in square brackets, such as `[real booking URL]`.
   - A `Taste` WARN from `page.py` on a page judged against its own style is not a finding; list it under Verification with the reason.
   - One root cause is one row, listing every location.
   - With more confirmed findings than 15, say how many were left out; never drop a `HIGH` for the cap.
4. **What works well** - up to four specific points worth keeping, or "none" rather than weak praise.
5. **Verification** - each check with its command or steps and result, then every check marked **Not verified** and why.
6. **Verdict** - `Block` when any `HIGH` remains, otherwise `Approve`, naming any area marked `Not reviewed`. Then one line offering the next step: fix the findings, or a second opinion from `interfaces:better-interface` when it is installed.

## Example

```markdown
**Scope** - `reports/q3.html`, artifact or report, desktop and 320px, light and dark. Judged against the house design reference v1.

**Coverage**
| Area | Inspected | Result |
| --- | --- | --- |
| Accessibility | names, focus, contrast (page.py), keyboard walk | 1 finding |
| Layout | 320px and 1280px renders | Clear |

**Findings**
| # | Severity | Rule | Location | Before | After | Why |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | HIGH | H1 | `reports/q3.html:88` | `<button><svg>...</svg></button>` | `<button aria-label="Close filter">` | The icon-only button has no name, so screen readers announce "button" |

**What works well** - Key figures up front; cards stack cleanly at 320px.

**Verification** - `page.py check reports/q3.html`: 18 checks, 1 failed. `page.py adherence reports/q3.html`: colors, fonts, radius pass; spacing and components compared by screenshot. Not verified: 200% zoom (no browser zoom control in this session).

**Verdict** - Block: 1 HIGH finding. Fix it now, or get a second opinion from `interfaces:better-interface`?
```

## Skills and agents

- [stages/review.md](../stages/review.md) - produces this report.
- [rules.md](rules.md) - the rule IDs and severities it cites; [surfaces.md](surfaces.md) - how non-HTML surfaces are checked.
