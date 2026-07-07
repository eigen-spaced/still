---
title: Configuration
---

:::lead
Everything site-specific lives in `site.toml`. The engine (`build.py`) reads it
and never needs editing. This is the complete schema.
:::

## `[site]`

Top-level identity and output settings.

| Key | Type | Default | Meaning |
|---|---|---|---|
| `name` | string | `"docs"` | Site name — shown in the sidebar brand. |
| `tagline` | string | `""` | Small text under the name in the sidebar. |
| `title_suffix` | string | `name` | Appended to each page's browser-tab title. |
| `output` | string | `"site"` | Build output folder, relative to `build.py`. |
| `logo` | string | *(built-in)* | Path to an `.svg` whose markup replaces the default brand mark. |

```toml ref="site.toml · [site]"
[site]
name    = "my project"
tagline = "internal docs"
output  = "site"
```

## `[[nav]]`

An **ordered list** of sidebar groups — note the double brackets, which is TOML
for "array of tables". Each group has a `title` and a `pages` list. Every page
is a three-element array: `["<stem>", "<number>", "<label>"]`.

```toml ref="site.toml · navigation"
[[nav]]
title = "Start here"
pages = [
  ["index",   "00", "Overview"],
  ["install", "01", "Installation"],
]

[[nav]]
title = "Guides"
pages = [
  ["config",  "02", "Configuration"],
]
```

| Field | Meaning |
|---|---|
| stem | Maps to `content/<stem>.md` and outputs `<stem>.html`. |
| number | Shown in the sidebar and as the page eyebrow. |
| label | The sidebar text and default page title. |

The order here is the single source of truth: it drives the sidebar order, the
eyebrow numbers, and the automatic prev/next pager.

:::note Missing files are flagged
If `[[nav]]` lists a stem with no matching `content/<stem>.md`, the build prints
a warning rather than failing — so you can stub out the nav before writing every
page.
:::

## `[theme]`

Optional. Every key overrides the matching `--key` CSS custom property in
`assets/style.css`. Omit the whole block for the stock dark theme. See
[Theming](theming.html) for the full token list.

```toml ref="site.toml · [theme]"
[theme]
teal = "#7c9cff"   # the accent colour
bg   = "#0b0b10"   # page background
```

## `[mermaid]`

Optional. Only relevant if a page contains a ` ```mermaid ` block.

| Key | Type | Default | Meaning |
|---|---|---|---|
| `theme` | string | `"dark"` | Mermaid's built-in theme name. |
| `theme_variables` | table | *(dark preset)* | Fine-grained Mermaid colour overrides. |

```toml ref="site.toml · [mermaid]"
[mermaid]
theme = "dark"
```

## A complete example

```toml ref="site.toml"
[site]
name    = "acme"
tagline = "engineering docs"
output  = "site"

[[nav]]
title = "Start here"
pages = [
  ["index", "00", "Overview"],
]

[mermaid]
theme = "dark"
```
