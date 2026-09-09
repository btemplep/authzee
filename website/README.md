# Authzee Website

The static website for [authzee.org](https://authzee.org). It lives in this same
repo and hosts the same site: a simple home page plus a documentation site that
is generated from the repo's markdown files.

Everything the browser runs is plain **HTML, CSS, and JS**. The only build tooling
is a small Node script that "rips" the markdown docs into styled HTML pages.

## What gets built

- **Home page** (`/`) — logo, tagline, and links to the docs and the GitHub source.
- **Docs** (`/docs/`) — rendered from the repo markdown, with a top bar, a sidebar
  listing the doc pages, and a per-page "On this page" table of contents built
  from the headings:
  - `/docs/` — the repo [`README.md`](../README.md)
  - `/docs/specification.html` — [`docs/specification.md`](../docs/specification.md)
  - `/docs/sdks.html` — [`docs/sdks.md`](../docs/sdks.md)

Cross-links between the docs are rewritten to the built pages. Links to source
files (e.g. `src/reference.py`) are rewritten to point at GitHub.

## Structure

```
website/
  build.mjs          Build script: markdown -> HTML docs pages, copies static assets
  package.json       Build dependencies (marked, github-slugger) and scripts
  src/               Static assets copied verbatim into the build output
    index.html       Home page
    styles.css       Shared styles (home + docs, light/dark)
    docs.js          Docs TOC scrollspy
    CNAME            Custom domain for GitHub Pages (authzee.org)
  dist/              Build output (generated, git-ignored)
```

## Local build

Requires Node 18+.

```console
cd website
npm install
npm run build      # writes ./dist
npm run serve      # serves ./dist at http://localhost:8080
```

Because the docs are generated from the markdown files at the repo root and under
`docs/`, editing those files and re-running `npm run build` updates the site.

## Deployment

Deployment is automated with GitHub Pages via
[`.github/workflows/deploy-website.yml`](../.github/workflows/deploy-website.yml).
On pushes to `main` that touch `website/**` or the source markdown, the workflow
builds `website/` and publishes `website/dist` to GitHub Pages.

The `src/CNAME` file sets the custom domain to `authzee.org` on each deploy. To
finish DNS setup, point the apex domain's records at GitHub Pages and confirm the
custom domain under the repo's Pages settings.
