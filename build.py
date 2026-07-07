#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
still — an offline-first static docs generator (no third-party dependencies).

Reads the Markdown sources in `content/*.md`, renders each into a self-contained
`<output>/<name>.html` page wrapped in a shared shell (`assets/style.css` +
`assets/app.js`), and copies the assets alongside them. The output is a plain
folder of HTML you open with a double-click — no server, works over `file://`,
works offline. That is the whole point: nothing here needs a network or a
running process to read.

    python3 build.py                 # build every page into <output>/
    python3 build.py index writing   # build a subset (by content stem)
    python3 build.py --watch         # rebuild on save (still no server)
    python3 build.py --clean         # remove <output>/ then build

Everything site-specific — the name, the sidebar/nav, the theme — lives in
`site.toml`, NOT in this file. Adding a page is: write `content/<stem>.md`, add
one line under the right `[[nav]]` group in `site.toml`. You should never need
to edit this script to run your own docs.

--------------------------------------------------------------------------------
THE MARKDOWN DIALECT (deliberately small — see content/dialect.md for the live
reference, which is itself written in it):

  Front matter (between leading `---` lines, all optional):
      title:       <h1> text (defaults to the nav label, then the file stem)
      eyebrow:     small kicker above the h1 (defaults to "<num> · <group>")
      head_title:  <title> tag (defaults to "<title> — <site name>")

  Block constructs:
      ## / ### / ####       headings. app.js auto-slugs the text into an id; add
                            `## Title {#anchor}` only to pin a differing anchor.
      | a | b |            GFM pipe tables (with a `---|---` separator row)
      - item / 1. item     unordered / ordered lists (one level)
      ```lang ref="..."    code figure -> <figure class="code"> (app.js colours it)
      ```mermaid           a Mermaid diagram -> <div class="mermaid">
      :::lead ... :::       the intro paragraph (<p class="lead">)
      :::note Title ... :::  a "note" callout   (also key / warn / gotcha)
      :::legend ... :::      a colour-dot key (lines: `- key: text`)
      :::cards ... :::       a nav grid (lines: `- [Title](href) | kicker | desc`)
      :::steps ... :::       a numbered how-to (lines: `- Heading | body`)
      :::diagram ... :::     a pre-formatted ASCII diagram (inner kept verbatim)
      plain text            paragraphs

  Inline:  **bold**, *italic*, `code`, [text](url). Raw HTML entities and tags
  (e.g. &nbsp;, <br/>) pass through untouched; a bare `&` is escaped.
--------------------------------------------------------------------------------
"""

import html
import re
import shutil
import sys
import time
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
ASSETS = ROOT / "assets"
CONFIG_PATH = ROOT / "site.toml"

# Built-in brand mark: three doc-lines. Shown in the sidebar logo chip unless
# `[site] logo = "path.svg"` points at a file whose inner markup replaces it.
DEFAULT_LOGO_SVG = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="#0f0f14" '
    'stroke-width="2.2" stroke-linecap="round">'
    '<path d="M5 7h14M5 12h14M5 17h9"/></svg>')


# ===========================================================================
# Configuration (site.toml)
# ===========================================================================
class Config:
    """Parsed site.toml, plus the derived NAV/PAGES lookups the builder needs."""

    def __init__(self, data):
        site = data.get("site", {})
        self.name = site.get("name", "docs")
        self.tagline = site.get("tagline", "")
        self.title_suffix = site.get("title_suffix", self.name)
        self.output = ROOT / site.get("output", "site")

        logo_path = site.get("logo")
        if logo_path:
            p = ROOT / logo_path
            if not p.is_file():
                sys.exit("site.toml: [site] logo = %r — file not found" % logo_path)
            self.logo_svg = p.read_text(encoding="utf-8").strip()
        else:
            self.logo_svg = DEFAULT_LOGO_SVG

        # NAV: [(group_title, [(stem, num, label), ...]), ...]
        self.nav = []
        for grp in data.get("nav", []):
            title = grp.get("title", "")
            pages = []
            for row in grp.get("pages", []):
                if not isinstance(row, list) or len(row) != 3:
                    sys.exit('site.toml: each nav page must be ["stem", "num", '
                             '"label"]; got %r' % (row,))
                pages.append((row[0], row[1], row[2]))
            self.nav.append((title, pages))

        # Flattened page order (for the prev/next pager) + per-stem lookup.
        self.pages = [(stem, label) for _, items in self.nav for (stem, _n, label) in items]
        self.meta_by_stem = {}
        for group_title, items in self.nav:
            for stem, num, label in items:
                self.meta_by_stem[stem] = (num, group_title, label)

        # Theme: any key -> a --key CSS custom-property override.
        self.theme = data.get("theme", {})
        # Mermaid init options (merged over sensible dark defaults below).
        self.mermaid = data.get("mermaid", {})

    def href(self, stem):
        return stem + ".html"


def load_config():
    if not CONFIG_PATH.is_file():
        sys.exit("no site.toml next to build.py — nothing to configure")
    with open(CONFIG_PATH, "rb") as f:
        try:
            data = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            sys.exit("site.toml is not valid TOML: %s" % e)
    return Config(data)


# ===========================================================================
# Inline rendering
# ===========================================================================
def _esc_amp(s):
    """Escape bare & (not already part of an entity); leave < > as raw HTML."""
    return re.sub(r"&(?!#?\w+;)", "&amp;", s)


def inline(text):
    """Render inline Markdown to HTML. Code spans are protected first so their
    contents are never re-interpreted (and are fully escaped)."""
    spans = []

    def stash(m):
        spans.append(html.escape(m.group(1)))
        return "\x00%d\x00" % (len(spans) - 1)

    text = re.sub(r"`([^`]+)`", stash, text)
    text = _esc_amp(text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    # Restore code spans wrapped in <code>.
    text = re.sub(r"\x00(\d+)\x00", lambda m: "<code>%s</code>" % spans[int(m.group(1))], text)
    return text


# ===========================================================================
# Block rendering — a line-cursor scanner
# ===========================================================================
FENCE_RE = re.compile(r"^```(\w+)?(?:\s+ref=\"([^\"]*)\")?\s*$")
TABLE_SEP_RE = re.compile(r"^\s*\|?[\s:|-]+\|?\s*$")


def render_blocks(lines):
    out, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        # --- container directive  :::name [title] ... ::: ------------------
        if line.lstrip().startswith(":::"):
            i, block = _container(lines, i)
            out.append(block)
            continue

        # --- fenced code / mermaid -----------------------------------------
        m = FENCE_RE.match(line)
        if m:
            i, block = _fence(lines, i, m)
            out.append(block)
            continue

        # --- table ---------------------------------------------------------
        if line.lstrip().startswith("|") and i + 1 < n and TABLE_SEP_RE.match(lines[i + 1]):
            i, block = _table(lines, i)
            out.append(block)
            continue

        # --- list ----------------------------------------------------------
        if re.match(r"^\s*([-*]|\d+\.)\s+", line):
            i, block = _list(lines, i)
            out.append(block)
            continue

        # --- heading (optional explicit id: `## Title {#anchor}`) ----------
        hm = re.match(r"^(#{2,6})\s+(.*?)(?:\s*\{#([\w-]+)\})?\s*$", line)
        if hm:
            tag = "h%d" % len(hm.group(1))
            idattr = ' id="%s"' % hm.group(3) if hm.group(3) else ""
            out.append("<%s%s>%s</%s>" % (tag, idattr, inline(hm.group(2).strip()), tag))
            i += 1
            continue

        # --- paragraph (gather until blank / next block) -------------------
        para = []
        while i < n and lines[i].strip() and not _starts_block(lines[i], lines, i):
            para.append(lines[i].strip())
            i += 1
        out.append("<p>%s</p>" % inline(" ".join(para)))
    return "\n".join(out)


def _starts_block(line, lines, i):
    if line.lstrip().startswith(":::") or FENCE_RE.match(line):
        return True
    if re.match(r"^(#{2,3})\s+", line):
        return True
    if re.match(r"^\s*([-*]|\d+\.)\s+", line):
        return True
    if line.lstrip().startswith("|") and i + 1 < len(lines) and TABLE_SEP_RE.match(lines[i + 1]):
        return True
    return False


def _container(lines, i):
    header = lines[i].strip()[3:].strip()
    parts = header.split(None, 1)
    name = parts[0] if parts else "note"
    title = parts[1] if len(parts) > 1 else ""
    i += 1
    inner = []
    while i < len(lines) and lines[i].strip() != ":::":
        inner.append(lines[i])
        i += 1
    i += 1  # consume closing :::

    if name == "lead":
        return i, '<p class="lead">%s</p>' % inline(" ".join(l.strip() for l in inner if l.strip()))

    if name == "legend":
        chips = []
        for l in inner:
            lm = re.match(r"^\s*-\s+(\w+):\s+(.*)$", l)
            if lm:
                chips.append('  <span class="chip"><span class="dot %s"></span> %s</span>'
                             % (lm.group(1), inline(lm.group(2).strip())))
        return i, '<div class="legend">\n%s\n</div>' % "\n".join(chips)

    if name == "cards":
        # A navigation grid. Each item: `- [Title](href) | kicker | description`.
        cards = []
        for l in inner:
            lm = re.match(r"^\s*-\s+\[([^\]]+)\]\(([^)]+)\)\s*\|\s*(.*)$", l)
            if not lm:
                continue
            title, href, rest = lm.group(1), lm.group(2), lm.group(3)
            bits = [b.strip() for b in rest.split("|")]
            kicker = bits[0] if bits else ""
            desc = bits[1] if len(bits) > 1 else ""
            cards.append('  <a class="card" href="%s">\n    <div class="k">%s</div>\n'
                         '    <h3>%s</h3>\n    <p>%s</p>\n  </a>'
                         % (html.escape(href, quote=True), inline(kicker), inline(title), inline(desc)))
        return i, '<div class="cards">\n%s\n</div>' % "\n".join(cards)

    if name == "diagram":
        # A pre-formatted ASCII diagram. Inner lines pass through verbatim (raw
        # HTML — e.g. <span class="hl-teal"> colour spans — and whitespace kept).
        return i, '<div class="diagram"><pre>%s</pre></div>' % "\n".join(inner)

    if name == "steps":
        # A numbered how-to list. Each item: `- Heading | body paragraph`.
        items = []
        for l in inner:
            lm = re.match(r"^\s*-\s+(.*)$", l)
            if not lm:
                continue
            head, _sep, body = lm.group(1).partition(" | ")
            items.append('  <li>\n    <h4>%s</h4>\n    <p>%s</p>\n  </li>'
                         % (inline(head.strip()), inline(body.strip())))
        return i, '<ol class="steps">\n%s\n</ol>' % "\n".join(items)

    # note / gotcha (and any other named callout): label + rendered body.
    body = render_blocks(inner)
    label = '\n  <span class="label">%s</span>' % inline(title) if title else ""
    return i, '<div class="%s">%s\n  %s\n</div>' % (name, label, body)


def _fence(lines, i, m):
    lang = m.group(1) or "cpp"
    ref = m.group(2)
    i += 1
    body = []
    while i < len(lines) and not lines[i].startswith("```"):
        body.append(lines[i])
        i += 1
    i += 1  # consume closing ```
    code = "\n".join(body)

    if lang == "mermaid":
        # innerHTML of a div — Mermaid reads textContent; pass through verbatim
        # so <br/> line breaks in node labels survive.
        return i, '<div class="mermaid">\n%s\n</div>' % code

    # A code figure. The code lives inside <script type="text/plain"> so the
    # browser never parses it as HTML (app.js highlights it client-side).
    attrs = ' data-lang="%s"' % lang
    if ref:
        attrs += ' data-ref="%s"' % html.escape(ref, quote=True)
    return i, '<figure class="code"%s><script type="text/plain">\n%s\n</script></figure>' % (attrs, code)


def _split_row(row):
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [c.strip() for c in row.split("|")]


def _table(lines, i):
    header = _split_row(lines[i])
    i += 2  # header + separator
    body = []
    while i < len(lines) and lines[i].lstrip().startswith("|"):
        body.append(_split_row(lines[i]))
        i += 1
    head_html = "".join("<th>%s</th>" % inline(c) for c in header)
    rows_html = []
    for r in body:
        rows_html.append("<tr>%s</tr>" % "".join("<td>%s</td>" % inline(c) for c in r))
    table = ("<table>\n  <thead><tr>%s</tr></thead>\n  <tbody>\n    %s\n  </tbody>\n</table>"
             % (head_html, "\n    ".join(rows_html)))
    return i, table


def _list(lines, i):
    ordered = bool(re.match(r"^\s*\d+\.\s+", lines[i]))
    tag = "ol" if ordered else "ul"
    items = []
    while i < len(lines) and re.match(r"^\s*([-*]|\d+\.)\s+", lines[i]):
        item = re.sub(r"^\s*([-*]|\d+\.)\s+", "", lines[i])
        items.append("  <li>%s</li>" % inline(item.strip()))
        i += 1
    return i, "<%s>\n%s\n</%s>" % (tag, "\n".join(items), tag)


# ===========================================================================
# Page assembly
# ===========================================================================
def parse_front_matter(text):
    meta, body = {}, text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            fm = text[3:end].strip("\n")
            body = text[end + 4:]
            for raw in fm.splitlines():
                if ":" in raw:
                    k, v = raw.split(":", 1)
                    meta[k.strip()] = v.strip()
    return meta, body.lstrip("\n")


def sidebar(cfg, active_stem):
    groups = []
    for title, items in cfg.nav:
        links = []
        for stem, num, label in items:
            cls = ' class="active"' if stem == active_stem else ""
            links.append('    <a href="%s"%s><span class="num">%s</span><span>%s</span></a>'
                         % (cfg.href(stem), cls, num, html.escape(label)))
        groups.append('  <nav class="nav-group">\n    <h4>%s</h4>\n%s\n  </nav>'
                      % (html.escape(title), "\n".join(links)))
    home = cfg.pages[0][0] if cfg.pages else "index"
    sub = ('<br><span class="sub">%s</span>' % html.escape(cfg.tagline)) if cfg.tagline else ""
    return ('<aside class="sidebar">\n'
            '  <a class="brand" href="%s">\n'
            '    <span class="logo">%s</span>\n'
            '    <span><span class="name">%s</span>%s</span>\n'
            '  </a>\n%s\n</aside>') % (cfg.href(home), cfg.logo_svg,
                                       html.escape(cfg.name), sub, "\n".join(groups))


def pager(cfg, active_stem):
    idx = next((k for k, (stem, _) in enumerate(cfg.pages) if stem == active_stem), None)
    if idx is None:
        return ""
    bits = []
    if idx > 0:
        stem, label = cfg.pages[idx - 1]
        bits.append('  <a href="%s"><div class="dir">← Previous</div><div class="ttl">%s</div></a>'
                    % (cfg.href(stem), html.escape(label)))
    if idx < len(cfg.pages) - 1:
        stem, label = cfg.pages[idx + 1]
        bits.append('  <a class="next" href="%s"><div class="dir">Next →</div><div class="ttl">%s</div></a>'
                    % (cfg.href(stem), html.escape(label)))
    return '<div class="pager">\n%s\n</div>' % "\n".join(bits)


def theme_style(cfg):
    """A tiny <style> that overrides the style.css :root tokens from [theme].
    Each `key = "value"` becomes `--key: value`, so `accent`/`bg`/`teal`/… all
    work with no engine change. Empty when [theme] is absent."""
    if not cfg.theme:
        return ""
    decls = "".join(" --%s: %s;" % (k, v) for k, v in cfg.theme.items())
    return '\n<style>:root {%s }</style>' % decls


def mermaid_block(cfg):
    """The local-Mermaid loader, injected only on pages that use a diagram.
    Vendored (assets/mermaid.min.js) so it renders offline over file://; a CDN
    <script> would fail with no network. app.js reveals each block only once
    Mermaid stamps data-processed on it (see the .mermaid rule in style.css),
    so the raw `flowchart …` source never flashes before the SVG swaps in."""
    opts = {"startOnLoad": "true", "securityLevel": '"loose"',
            "theme": '"%s"' % cfg.mermaid.get("theme", "dark")}
    # Dark-friendly defaults tuned to match the stock style.css palette. A
    # site.toml [mermaid] theme_variables table (inline JSON-ish) can override.
    theme_vars = cfg.mermaid.get("theme_variables", {
        "fontFamily": "inherit", "primaryColor": "#1c1c26",
        "primaryBorderColor": "#34343f", "lineColor": "#6e6e80",
        "primaryTextColor": "#d7d7e0"})
    tv = ", ".join('%s: "%s"' % (k, v) for k, v in theme_vars.items())
    opt_str = ", ".join("%s: %s" % (k, v) for k, v in opts.items())
    return ('\n<script src="assets/mermaid.min.js"></script>\n'
            '<script>\n'
            '  if (window.mermaid) mermaid.initialize({ %s, themeVariables: { %s } });\n'
            '</script>') % (opt_str, tv)


def render_page(cfg, md_path):
    text = md_path.read_text(encoding="utf-8")
    meta, body = parse_front_matter(text)
    stem = md_path.stem

    num, group, label = cfg.meta_by_stem.get(stem, ("", "", ""))
    title = meta.get("title") or label or stem
    head_title = meta.get("head_title", "%s — %s" % (title, cfg.title_suffix))
    # Eyebrow defaults to "<num> · <group>" from the nav; front matter overrides.
    default_eyebrow = ("%s · %s" % (num, group)).strip(" ·") if (num or group) else ""
    eyebrow = meta.get("eyebrow", default_eyebrow)

    content_html = render_blocks(body.splitlines())
    uses_mermaid = '<div class="mermaid">' in content_html

    parts = []
    if eyebrow:
        parts.append('<div class="eyebrow">%s</div>' % inline(eyebrow))
    parts.append("<h1>%s</h1>" % inline(title))
    parts.append(content_html)
    pg = pager(cfg, stem)
    if pg:
        parts.append(pg)
    article = "\n\n".join(parts)

    page = PAGE_TEMPLATE.format(
        head_title=html.escape(head_title),
        theme=theme_style(cfg),
        sidebar=sidebar(cfg, stem),
        article=article,
        mermaid=mermaid_block(cfg) if uses_mermaid else "",
    )
    return cfg.href(stem), page


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{head_title}</title>
<link rel="stylesheet" href="assets/style.css">{theme}
</head>
<body>
<button class="menu-btn" aria-label="Menu">☰</button>
<div class="layout">
{sidebar}
<main class="content-wrap"><article class="content">

{article}

</article></main>
</div>
<script src="assets/app.js"></script>{mermaid}
</body>
</html>
"""


# ===========================================================================
# Build driver
# ===========================================================================
def copy_assets(cfg):
    """Mirror assets/ into <output>/assets/ so the output folder is fully
    self-contained (zip it, move it anywhere, it still opens)."""
    if not ASSETS.is_dir():
        return
    dst = cfg.output / "assets"
    if dst.resolve() == ASSETS.resolve():
        return  # building in place (output = "."): assets are already colocated
    shutil.copytree(ASSETS, dst, dirs_exist_ok=True)


def build(cfg, wanted):
    if not CONTENT.is_dir():
        sys.exit("no content/ directory — nothing to build")
    cfg.output.mkdir(parents=True, exist_ok=True)
    copy_assets(cfg)
    built = 0
    known = {p.stem for p in CONTENT.glob("*.md")}
    # Warn about nav entries with no matching markdown (a common typo).
    for stem in cfg.meta_by_stem:
        if stem not in known:
            print("  ! nav lists %r but content/%s.md is missing" % (stem, stem))
    for md in sorted(CONTENT.glob("*.md")):
        if wanted and md.stem not in wanted:
            continue
        out_name, page = render_page(cfg, md)
        (cfg.output / out_name).write_text(page, encoding="utf-8")
        print("  built %s -> %s/%s" % (md.name, cfg.output.name, out_name))
        built += 1
    if not built:
        print("  nothing built (no matching .md in content/)")
    return built


def _mtimes():
    """A snapshot of every source file's mtime, for the watch loop."""
    watched = list(CONTENT.glob("*.md")) + list(ASSETS.glob("*")) + [CONFIG_PATH, Path(__file__)]
    out = {}
    for p in watched:
        try:
            out[str(p)] = p.stat().st_mtime
        except OSError:
            pass
    return out


def watch():
    cfg = load_config()
    build(cfg, [])
    print("\nwatching content/, assets/ and site.toml — Ctrl-C to stop")
    seen = _mtimes()
    while True:
        time.sleep(0.4)
        now = _mtimes()
        if now == seen:
            continue
        seen = now
        try:
            cfg = load_config()  # reload so site.toml edits take effect live
            print("change detected, rebuilding…")
            build(cfg, [])
        except SystemExit as e:
            print("  build error:", e)
        except Exception as e:  # keep the watcher alive through a bad edit
            print("  build error:", e)


def main(argv):
    if "--watch" in argv or "-w" in argv:
        watch()
        return
    clean = "--clean" in argv
    wanted = [a for a in argv if not a.startswith("-")]
    cfg = load_config()
    if clean and cfg.output.exists():
        shutil.rmtree(cfg.output)
        print("cleaned %s/" % cfg.output.name)
    print("building %s…" % cfg.name)
    build(cfg, wanted)


if __name__ == "__main__":
    main(sys.argv[1:])
