---
title: Theming
---

:::lead
The entire look is driven by CSS custom properties. Override any of them from a
`[theme]` block in `site.toml` — no stylesheet editing, no engine changes.
:::

## How it works

`assets/style.css` defines every colour and key dimension as a `--token` in its
`:root`. At build time, each key in your `[theme]` block is emitted as a
`--key: value` override injected into every page's `<head>`, *after* the
stylesheet — so it wins by the cascade.

```toml ref="site.toml"
[theme]
teal = "#7c9cff"
bg   = "#0b0b10"
```

That is the whole mechanism: a `[theme]` key named `foo` sets `--foo`. If a
token exists in the stylesheet, you can override it.

## The accent

The single most impactful token is `--teal` — the accent used for links, the
active sidebar item, code-language chips, the eyebrow, and focus rings. Change
just that one and the whole site re-tints:

```toml ref="a one-line rebrand"
[theme]
teal = "#f0975a"
```

## Token reference

The colour tokens, grouped by role:

| Token | Role |
|---|---|
| `bg` | page background |
| `bg-panel` | sidebar, cards, callout backgrounds |
| `bg-code` | code-figure background |
| `bg-inset` | inline-code / nav-hover background |
| `border`, `border-2` | hairlines and stronger borders |
| `text` | body text |
| `text-dim` | secondary text |
| `text-mute` | captions, numbers, muted labels |
| `teal`, `teal-dim` | **the accent** and its darker shade |
| `purple`, `pink`, `blue`, `orange`, `yellow`, `red`, `green` | syntax + callout accents |

And the two layout dimensions:

| Token | Role | Default |
|---|---|---|
| `sidebar-w` | sidebar width | `290px` |
| `content-w` | max article width | `860px` |

:::note Syntax colours travel with the palette
The code-highlighting token classes (`.t-kw`, `.t-str`, …) reference the palette
tokens above, so re-theming `--pink` or `--green` also recolours syntax
highlighting — no separate theme to maintain.
:::

## A worked example: a light-ish theme

```toml ref="site.toml · a warmer, lighter accent"
[theme]
teal      = "#2f9e7f"
bg        = "#0d0f12"
bg-panel  = "#15181d"
text      = "#e2e6ea"

[mermaid]
theme = "neutral"
```

:::gotcha Keep Mermaid in step
`[theme]` only restyles the HTML/CSS. Mermaid diagrams are drawn by Mermaid's
own theme, so if you move far from the default palette, set a matching
`[mermaid] theme` (`dark`, `neutral`, `forest`, `default`) too — otherwise the
diagrams will look out of place against your new colours.
:::
