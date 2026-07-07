# still

A tiny, offline-first static documentation generator. Write Markdown, run one
dependency-free Python script, open the resulting HTML by double-clicking. **No
server, no `npm install`, no toolchain** — and it works over `file://`, offline,
forever.

```sh
python3 build.py            # build content/*.md -> site/*.html
open site/index.html        # read it. no server.
```

## Why

Most doc tools quietly assume a running server — open their output as a local
file and it breaks, because the browser blocks the things they depend on
(`fetch()` of local files, ES modules, service workers). still pre-renders
everything to plain HTML at build time, so a double-click just works. If you
have ever wanted to read your docs on a plane without `run server` first, that
is the entire motivation.

## Requirements

- **Python 3.11+** (for the stdlib `tomllib` parser). Nothing else.
- A web browser.

## Use it for your own docs

1. **Clone / copy** this repo.
2. **Edit `site.toml`** — set the name, and list your pages under `[[nav]]`.
3. **Write Markdown** in `content/` — one `.md` per page.
4. **Build**: `python3 build.py` (or `--watch` to rebuild on save).
5. **Read**: open `site/index.html`.

The docs in `content/` are written *in still, about still* — they double as a
live example and the manual. Start reading at `site/index.html`.

## Commands

| Command | Does |
|---|---|
| `python3 build.py` | Build every page into `site/`. |
| `python3 build.py index writing` | Build only the named pages (by stem). |
| `python3 build.py --watch` | Rebuild automatically when any source changes. |
| `python3 build.py --clean` | Remove `site/`, then build fresh. |

## Layout

```
still/
├── build.py          the engine — stdlib only, you never edit this
├── site.toml         your site: name, nav, theme  ← the one file you edit
├── content/*.md      your pages
├── assets/           style.css, app.js, mermaid.min.js (vendored, offline)
└── site/             build output — open site/index.html
```

## Offline by design

Mermaid is **vendored** (`assets/mermaid.min.js`), not loaded from a CDN, so
diagrams render with no network. The generated `site/` folder is fully
self-contained — zip it, email it, host it anywhere static.

## License

MIT — see [LICENSE](LICENSE).
