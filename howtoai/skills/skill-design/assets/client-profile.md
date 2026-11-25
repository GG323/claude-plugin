# Design profile: <client name>

Written by `skill-design` with the user's approval. It records only where this client departs from the HowToAI house design; everything not listed here follows the house design. Edit it by hand or ask `skill-design` to update it.

## Contents

- [Decisions](#decisions)
- [Font links](#font-links)
- [Token overrides](#token-overrides)

- **Source of truth:** <house | client design at <path or link> | house with client brand>
- **Updated:** <YYYY-MM-DD>
- **Themes:** <light and dark | light only | dark only>
- **Fonts:** <family names; web fonts allowed: yes or no>
- **Logo:** <path, and where it may appear>
- **Voice:** <a voice guide link, or "house: plain words">

## Decisions

- <one line per answer from the client questions, for example "Corner radius: square (0px) on cards and buttons">

## Font links

Only when the profile changes `--font-display` or `--font-body`. `page.py new --profile` puts these tags in place of the house font link. Delete this section for installed fonts only.

```html
<!-- <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=...&display=swap"> -->
```

## Token overrides

Only tokens that change. `page.py new --profile` appends this block after the house tokens, so every page built for this client uses it. Keep the same token names, so the house components keep working.

```css
:root {
  /* --accent: #0b6e4f; */
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    /* --accent: #5fd3a8; */
  }
}
:root[data-theme="dark"] {
  /* --accent: #5fd3a8; */
}
```
