# Lane Enrique Schultz — research website

A static, accessible research profile for [leschultz.github.io](https://leschultz.github.io/).
HTML, CSS, a small navigation enhancement, and locally served assets. Publication
content is generated ahead of time and works without JavaScript.

## Preview

Python 3 is sufficient:

```sh
python3 scripts/serve.py
```

Open **http://127.0.0.1:8000**. Use `--port 8001` to select another port. The preview
server serves the sibling CV repository's PDF when available, otherwise redirecting
CV requests to the published version. It binds to localhost.

The production site uses root-relative paths, matching the root GitHub Pages
site. Preview through HTTP rather than opening HTML files directly.

## Structure

| Path | Purpose |
| --- | --- |
| `index.html` | Research profile, selected work, background, service, contact |
| `publications/index.html` | Complete publication/manuscript archive |
| `assets/css/site.css` | Responsive design, typography, print styles |
| `assets/js/site.js` | Progressive mobile navigation and current footer year |
| `assets/img/`, `assets/fonts/` | Local illustrations, optimized images, font |
| `data/featured.json` | Selected publication IDs and plain-language summaries |
| `data/publications.json` | Generated, versioned snapshot of the CV bibliography |
| `files/publications.bib` | Downloadable copy of the authoritative bibliography |
| `404.html`, `robots.txt`, `sitemap.xml` | Error page and discoverability |

## Update content

Edit the authored sections of `index.html` directly. Keep role/title, research
descriptions, education, service, and professional development aligned with the
CV. Update the `Person` structured data if the current appointment changes.

Publication metadata belongs in the **CV repository's `sections/refs.bib`**. With
the repositories checked out side by side:

```sh
python3 scripts/sync_publications.py
```

Or provide the CV path explicitly:

```sh
python3 scripts/sync_publications.py --cv /path/to/curriculum_vitae
```

This requires Python 3 and Biber. It exports metadata from the CV, copies the
bibliography, updates research-project status badges, and regenerates the archive
and selected-publication HTML. The entire snapshot is validated before files are
written. A source hash keeps the BibTeX and JSON copies consistent.

To check cross-repository consistency without changing files:

```sh
python3 scripts/sync_publications.py --cv ../curriculum_vitae --check
```

To change the homepage selection, edit `data/featured.json`, then run:

```sh
python3 scripts/render_publications.py
```

Do not hand-edit content between `generated:`, `publication-status:`, or `publication-link:` comment
markers. The surrounding HTML remains authored content. Stable bibliography keys
also form publication anchors, such as `/publications/#schultz_sputtering_2026`.

The checked-in snapshot allows this site to be previewed, checked, and published
independently of the CV checkout, with no network requests for content at runtime.

## Verification

Static validation has no third-party Python dependencies:

```sh
python3 scripts/check_site.py
python3 -m unittest discover -s tests -v
```

This checks generated content, HTML structure, local links/fragments, image
dimensions/alternatives, and CSS asset references. The CV URL is the one intentional
cross-repository local path; it is served by the separate CV Pages project.

For browser and accessibility checks:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m playwright install chromium
.venv/bin/python scripts/browser_checks.py --screenshots .checks
```

On a minimal Linux host, use `playwright install --with-deps chromium` to install
browser system libraries too. Checks cover:

- Three pages at 320, 390, 768, 1024, 1440, and 1920 px.
- axe WCAG A/AA and best-practice audits on mobile and desktop.
- Keyboard/menu behavior, Escape, focus on resize, native anchor/history behavior.
- Deep links and manuscript statuses, bibliography downloads, no-JavaScript content.
- Reduced motion, print styling, missing resources, and JavaScript errors.

The checker downloads a pinned axe-core 4.10.3 development script. For offline
checks, provide a local copy with `--axe /path/to/axe.min.js`. This script is never
loaded by visitors. Screenshots and the print PDF support manual visual review;
automated audits are complemented by inspection of layout, reading order, and copy.

GitHub Actions runs these checks and uploads visual-review artifacts.

## Images and fonts

The Source Serif 4 Latin font is self-hosted under the SIL Open Font License; see
`assets/fonts/LICENSE.txt`. Body text uses system fonts. The conceptual research
illustration is in `assets/img/research-map.svg` and depicts a schematic rather
than measured data.

The original portrait and research figures are in `img/`. Image derivatives and
the social-sharing preview can be regenerated with Pillow:

```sh
.venv/bin/python scripts/prepare_assets.py
```

This uses local DejaVu fonts or fontconfig for the raster social card; explicit
TrueType font paths can be supplied with `--serif-font` and `--sans-font`.
`--fetch-font` re-downloads the versioned Source Serif WOFF2 referenced in the
script. All visitor-facing assets are committed, so publishing requires no image
or font build step.

## Publish

Use the repository's existing GitHub Pages source. Include regenerated HTML,
`data/publications.json`, and `files/publications.bib` when publication metadata
changes. `.nojekyll` allows GitHub Pages to serve the static files directly.
The checking workflow creates review artifacts; the existing Pages configuration
controls publishing.

The public CV link is `/curriculum_vitae/cv_full_leschultz.pdf`. Update that PDF in
the CV repository when publishing a revised CV.
