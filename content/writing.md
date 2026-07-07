---
title: Writing pages
---

:::lead
The daily loop is: create a Markdown file, add one line to `site.toml`, rebuild.
This page covers that loop end to end.
:::

## Adding a page

:::steps
- Create the Markdown | Add `content/my-page.md`. The filename without `.md` is its *stem* — here, `my-page`. That stem is how everything refers to the page.
- Register it in the nav | Open `site.toml` and add `["my-page", "05", "My Page"]` to the `pages` list of whichever `[[nav]]` group it belongs in. The three fields are stem, number, sidebar label.
- Rebuild | Run `python3 build.py`. Your page appears at `site/my-page.html`, in the sidebar, with prev/next links wired automatically.
:::

That is the whole process. The nav order in `site.toml` *is* the sidebar order
and the prev/next order — there is no second place to keep them in sync.

:::note Live rebuilds
While writing, run `python3 build.py --watch`. It rebuilds the instant you save
any file (including `site.toml`), so you just refresh the browser tab. Still no
server — you are refreshing a `file://` URL.
:::

## Front matter

Each page *may* start with a front-matter block between `---` lines. Every field
is optional — a page with no front matter at all is fine.

```text ref="content/my-page.md · top of file"
---
title: My Page
eyebrow: 05 · reference
head_title: My Page — my project
---
```

| Field | Purpose | Default |
|---|---|---|
| `title` | The `<h1>` at the top of the page | the nav label, then the file stem |
| `eyebrow` | The small kicker above the `<h1>` | `"<number> · <group>"` from the nav |
| `head_title` | The browser-tab `<title>` | `"<title> — <title_suffix>"` |

Because `eyebrow` and `title` both fall back to the nav, most pages need **no
front matter at all** — the one you are reading only sets `title` because it
differs from its short sidebar label.

## A minimal page

Here is a complete, valid page. Everything after the front matter is the
[Markdown dialect](dialect.html):

```text ref="content/example.md"
---
title: Example
---

:::lead
A one-line summary that renders larger and dimmer — the page's hook.
:::

## A section

Plain paragraphs, **bold**, *italic*, `inline code`, and
[links](other-page.html) all work as you would expect.

- a list item
- another one
```

## Linking between pages

Link to another page by its **output filename** — the stem plus `.html`:

```text ref="inline link"
See the [configuration reference](config.html) for the full schema.
```

Since every page lives in the same output folder, these are plain relative
links — which is exactly why they keep working over `file://`.

:::gotcha Link to the .html, not the .md
Links point at the *built* file (`config.html`), not the source (`config.md`).
The `.md` files never ship — only the rendered `site/` folder does.
:::
