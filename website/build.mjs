/**
 * Build script for the Authzee static website.
 *
 * Reads the repo markdown files (README.md, docs/specification.md, docs/sdks.md),
 * renders them to styled HTML docs pages, and emits a self-contained static site
 * into `dist/`:
 *
 *   dist/
 *     index.html            <- home page (logo + links)
 *     styles.css, *.js, assets/
 *     docs/
 *       index.html          <- README
 *       specification.html
 *       sdks.html
 *
 * Everything the browser runs is plain HTML/CSS/JS. Only this build step uses Node.
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import GithubSlugger from "github-slugger";
import hljs from "highlight.js";
import { marked } from "marked";
import { markedHighlight } from "marked-highlight";

marked.use(
  markedHighlight({
    langPrefix: "hljs language-",
    highlight(code, lang) {
      const language = hljs.getLanguage(lang) ? lang : "plaintext";
      return hljs.highlight(code, { language }).value;
    }
  })
);

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..");
const SRC = path.join(__dirname, "src");
const DIST = path.join(__dirname, "dist");

const GITHUB_URL = "https://github.com/btemplep/authzee";
const GITHUB_BLOB = `${GITHUB_URL}/blob/main`;

/**
 * The repo's raw asset host + path. References to assets under `docs/` served
 * from here (e.g. the logo embedded in the README) are rewritten to the local
 * Pages-hosted `/assets/` copies so every page loads assets from the site's own
 * domain rather than GitHub.
 */
const RAW_DOCS_BASE = "https://raw.githubusercontent.com/btemplep/authzee/main/docs/";

/**
 * Docs pages, in sidebar order. `source` is relative to the repo root, `out` is
 * the output filename under dist/docs/. `mdPath` is how the original file refers
 * to itself/others so we can rewrite cross-links.
 */
const DOCS_PAGES = [
  {
    title: "README",
    source: "README.md",
    out: "index.html",
    mdName: "README.md"
  },
  {
    title: "Specification",
    source: "docs/specification.md",
    out: "specification.html",
    mdName: "specification.md"
  },
  {
    title: "SDKs",
    source: "docs/sdks.md",
    out: "sdks.html",
    mdName: "sdks.md"
  }
];

/** Map a doc's repo-relative source path -> built docs page filename. */
const DOC_SOURCE_TO_HTML = {
  "README.md": "index.html",
  "docs/specification.md": "specification.html",
  "docs/sdks.md": "sdks.html"
};

function read(file) {
  return fs.readFileSync(file, "utf8");
}

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function copyRecursive(from, to) {
  ensureDir(to);
  for (const entry of fs.readdirSync(from, { withFileTypes: true })) {
    const src = path.join(from, entry.name);
    const dest = path.join(to, entry.name);
    if (entry.isDirectory()) {
      copyRecursive(src, dest);
    } else {
      fs.copyFileSync(src, dest);
    }
  }
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/**
 * Rewrite a markdown link href so it resolves on the built site.
 *
 * - `#anchor` stays as-is (same-page).
 * - Links to another doc markdown file (optionally with an anchor) map to the
 *   built docs .html page.
 * - Other repo-relative links (source files, examples) point at GitHub.
 * - Absolute http(s) links are left alone.
 *
 * `fromSource` is the linking page's repo-relative source path (e.g.
 * "docs/sdks.md"), used to resolve relative links correctly so that only links
 * actually targeting a rendered doc page are mapped (a stray `website/README.md`
 * is not confused with the top-level `README.md`).
 */
function rewriteHref(href, fromSource) {
  if (!href) {
    return href;
  }

  if (href.startsWith("#") || href.startsWith("mailto:")) {
    return href;
  }

  if (/^https?:\/\//.test(href)) {
    return href;
  }

  const [rawPath, anchor] = href.split("#");
  const suffix = anchor ? `#${anchor}` : "";

  // Resolve the link relative to the linking page's directory, as a
  // repo-relative POSIX path (no leading "./").
  const fromDir = path.posix.dirname(fromSource);
  const resolved = path.posix
    .normalize(path.posix.join(fromDir, rawPath))
    .replace(/^\.\//, "");

  if (DOC_SOURCE_TO_HTML[resolved]) {
    return `${DOC_SOURCE_TO_HTML[resolved]}${suffix}`;
  }

  // Any other repo-relative link (source files, examples, other markdown) -> GitHub.
  return `${GITHUB_BLOB}/${resolved}${suffix}`;
}

/**
 * Render markdown to HTML, collecting a table of contents from the headings and
 * rewriting internal links. Returns { html, toc } where toc is a list of
 * { level, text, id } for h2/h3 headings.
 */
function renderMarkdown(md, fromSource) {
  const slugger = new GithubSlugger();
  const toc = [];

  const renderer = new marked.Renderer();

  const defaultLink = renderer.link.bind(renderer);
  renderer.link = (href, title, text) => {
    return defaultLink(rewriteHref(href, fromSource), title, text);
  };

  renderer.heading = (text, level, raw) => {
    const id = slugger.slug(raw);
    if (level === 2 || level === 3) {
      toc.push({
        level,
        text: raw,
        id
      });
    }

    return `<h${level} id="${id}"><a class="anchor" href="#${id}" aria-label="Link to this section">#</a>${text}</h${level}>\n`;
  };

  const rendered = marked.parse(md, { renderer, gfm: true });

  // Rewrite raw GitHub asset URLs (e.g. the logo embedded as inline HTML in the
  // README) to the local Pages-hosted copies under /assets/.
  const html = rendered.split(RAW_DOCS_BASE).join("/assets/");

  return {
    html,
    toc
  };
}

function navLinks(activeOut) {
  return DOCS_PAGES.map((p) => {
    const active = p.out === activeOut ? ' class="active"' : "";
    return `        <li><a href="${p.out}"${active}>${escapeHtml(p.title)}</a></li>`;
  }).join("\n");
}

function tocLinks(toc) {
  if (toc.length === 0) {
    return "";
  }

  const items = toc
    .map(
      (h) =>
        `        <li class="toc-h${h.level}"><a href="#${h.id}">${escapeHtml(
          h.text
        )}</a></li>`
    )
    .join("\n");

  return `      <div class="toc">
        <p class="toc-title">On this page</p>
        <ul>
${items}
        </ul>
      </div>`;
}

function topBar() {
  return `  <header class="topbar">
    <a class="brand" href="/">
      <img src="/assets/authzee_logo.svg" alt="Authzee" />
    </a>
    <nav class="topnav">
      <a href="/docs/">Docs</a>
      <a href="${GITHUB_URL}">GitHub</a>
    </nav>
  </header>`;
}

function docsPage(page, contentHtml, toc) {
  const depthPrefix = ""; // docs pages live under /docs/, assets referenced absolutely
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${escapeHtml(page.title)} — Authzee Docs</title>
  <link rel="icon" href="/assets/authzee_balloon.svg" type="image/svg+xml" />
  <link rel="stylesheet" href="/styles.css" />
</head>
<body class="docs">
${topBar()}
  <div class="docs-layout">
    <aside class="sidebar">
      <p class="sidebar-title">Documentation</p>
      <ul class="pages">
${navLinks(page.out)}
      </ul>
${tocLinks(toc)}
    </aside>
    <main class="content markdown-body">
${contentHtml}
    </main>
  </div>
  <script src="/docs.js"></script>
</body>
</html>
`;
}

function build() {
  fs.rmSync(DIST, { recursive: true, force: true });
  ensureDir(DIST);

  // Static assets (home page, css, js, logo) copied verbatim.
  copyRecursive(SRC, DIST);

  // SVG assets from the repo docs/ folder (logo, balloon, etc.). Copying all of
  // them means any `/assets/<name>.svg` reference rewritten from a raw GitHub
  // URL resolves against the site.
  const assetsOut = path.join(DIST, "assets");
  ensureDir(assetsOut);
  const docsDir = path.join(REPO_ROOT, "docs");
  for (const name of fs.readdirSync(docsDir)) {
    if (name.toLowerCase().endsWith(".svg")) {
      fs.copyFileSync(path.join(docsDir, name), path.join(assetsOut, name));
    }
  }

  // Docs pages.
  const docsOut = path.join(DIST, "docs");
  ensureDir(docsOut);

  for (const page of DOCS_PAGES) {
    const md = read(path.join(REPO_ROOT, page.source));
    const { html, toc } = renderMarkdown(md, page.source);
    const full = docsPage(page, html, toc);
    fs.writeFileSync(path.join(docsOut, page.out), full);
    console.log(`  docs/${page.out}  (${toc.length} sections)`);
  }

  console.log(`Build complete -> ${path.relative(process.cwd(), DIST)}`);
}

build();