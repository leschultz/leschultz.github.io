#!/usr/bin/env python3
"""Render static publication HTML from the checked-in bibliography snapshot."""

import argparse
import hashlib
from html import escape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
GROUPS = {
    "journal": ("Journal articles", "Citations use the final journal-issue year where available."),
    "manuscript": ("Manuscripts", "Ongoing work, with the current status shown for each manuscript."),
    "preprint": ("Preprints", "Publicly available research manuscripts on arXiv."),
    "conference": ("Conference proceedings", "Papers published in conference proceedings. Presentations and posters are also listed in the CV."),
}


def validate(data, bibliography):
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported publication data schema")
    if data.get("source_sha256") != hashlib.sha256(bibliography).hexdigest():
        raise ValueError("The bibliography and JSON snapshot differ; run sync_publications.py")
    seen = set()
    for paper in data["publications"]:
        if paper["id"] in seen or not re.fullmatch(r"[\w-]+", paper["id"]):
            raise ValueError(f"Duplicate or invalid publication id: {paper['id']}")
        seen.add(paper["id"])
        if paper["category"] not in GROUPS or not paper["title"] or not paper["authors"]:
            raise ValueError(f"Incomplete publication: {paper['id']}")
        if not isinstance(paper["year"], int) or not all(a["name"] for a in paper["authors"]):
            raise ValueError(f"Invalid year or author list: {paper['id']}")
        if paper["url"] and paper["url"] != f"https://doi.org/{paper['doi']}":
            raise ValueError(f"Unexpected publication URL: {paper['id']}")
        if paper["category"] == "manuscript" and paper["status"] not in {"Under review", "In preparation", "Submitted", "Accepted"}:
            raise ValueError(f"Unknown manuscript status: {paper['id']}")


def author_list(paper):
    names = [f'<strong>{escape(a["name"])}</strong>' if a["is_owner"] else escape(a["name"])
             for a in paper["authors"]]
    if len(names) < 2:
        return "".join(names)
    return ", ".join(names[:-1]) + (", and " if len(names) > 2 else " and ") + names[-1]


def citation(paper):
    venue = paper["venue"]
    if paper["volume"]:
        venue += " " + paper["volume"]
        if paper["issue"]:
            venue += f'({paper["issue"]})'
    if paper["pages"]:
        venue += ", " + paper["pages"]
    elif paper["article_number"]:
        venue += ", " + paper["article_number"]
    return escape(venue)


def archive(data):
    sections = []
    for group, (heading, description) in GROUPS.items():
        entries = []
        for paper in data["publications"]:
            if paper["category"] != group:
                continue
            title = escape(paper["title"])
            if paper["url"]:
                title = f'<a href="{escape(paper["url"], quote=True)}">{title}</a>'
            details = citation(paper)
            if paper["note"] and paper["note"] != paper["status"]:
                details += (" · " if details else "") + escape(paper["note"])
            entry = [f'<li class="publication-entry" id="{paper["id"]}">',
                     f'  <div class="publication-meta"><span class="publication-year">{paper["year"]}</span><span class="status-label">{escape(paper["status"])}</span></div>',
                     f'  <h3>{title}</h3>',
                     f'  <p class="publication-authors">{author_list(paper)}.</p>']
            if details:
                entry.append(f'  <p class="publication-citation">{details}</p>')
            if paper["doi"]:
                entry.append(f'  <p class="publication-doi"><a href="{escape(paper["url"], quote=True)}">DOI: {escape(paper["doi"])}</a></p>')
            entry.append("</li>")
            entries.append("\n".join(entry))
        sections.append(f'<section class="archive-section" id="{group}" aria-labelledby="{group}-heading">\n'
                        f'<h2 id="{group}-heading">{heading}</h2>\n'
                        f'<p class="archive-description">{description}</p>\n'
                        '<ol class="publication-list">\n' + "\n".join(entries) + '\n</ol>\n</section>')
    return "\n".join(sections)


def selected(data):
    by_id = {paper["id"]: paper for paper in data["publications"]}
    featured = json.loads((ROOT / "data/featured.json").read_text(encoding="utf-8"))
    entries = []
    for item in featured:
        if item["id"] not in by_id:
            raise ValueError(f"Featured publication is missing: {item['id']}")
        paper = by_id[item["id"]]
        if paper["category"] != "journal":
            raise ValueError("The 'Ideas, in print' selection must contain published journal articles")
        entries.append(f'<li class="selected-publication">\n'
                       f'  <span class="publication-year">{paper["year"]}</span>\n'
                       f'  <div><h3><a href="{escape(paper["url"], quote=True)}">{escape(paper["title"])}</a></h3>\n'
                       f'    <p class="publication-authors">{author_list(paper)}.</p>\n'
                       f'    <p class="publication-venue">{escape(paper["venue"])}</p>\n'
                       f'    <p class="publication-summary">{escape(item["summary"])}</p></div>\n'
                       '  <span class="publication-arrow" aria-hidden="true">↗</span>\n</li>')
    return '<ol class="selected-publications">\n' + "\n".join(entries) + '\n</ol>'


def replace_block(document, name, body):
    start, end = f"<!-- generated:{name} -->", f"<!-- /generated:{name} -->"
    if document.count(start) != 1 or document.count(end) != 1:
        raise ValueError(f"Expected exactly one generated block: {name}")
    return re.sub(re.escape(start) + r".*?" + re.escape(end),
                  lambda _: f"{start}\n{body}\n{end}", document, flags=re.DOTALL)


def render_outputs(data, bibliography):
    validate(data, bibliography)
    home = (ROOT / "index.html").read_text(encoding="utf-8")
    publications = (ROOT / "publications/index.html").read_text(encoding="utf-8")
    home = replace_block(home, "selected-publications", selected(data))
    publications = replace_block(publications, "publication-archive", archive(data))
    by_id = {paper["id"]: paper for paper in data["publications"]}

    def status(match):
        key = match.group(1)
        if key not in by_id:
            raise ValueError(f"Research project references unknown publication: {key}")
        paper = by_id[key]
        return (f'<!-- publication-status:{key} -->'
                f'<span class="status-label">{escape(paper["status"])} · {paper["year"]}</span>'
                '<!-- /publication-status -->')

    home = re.sub(r"<!-- publication-status:([\w-]+) -->.*?<!-- /publication-status -->",
                  status, home, flags=re.DOTALL)

    def project_link(match):
        key = match.group(1)
        paper = by_id[key]
        label = {"journal": "Paper", "manuscript": "Manuscript", "preprint": "Preprint", "conference": "Paper"}[paper["category"]]
        return (f'<!-- publication-link:{key} -->'
                f'<a class="text-link" href="/publications/#{key}">{label} details <span aria-hidden="true">↗</span></a>'
                '<!-- /publication-link -->')

    home = re.sub(r"<!-- publication-link:([\w-]+) -->.*?<!-- /publication-link -->",
                  project_link, home, flags=re.DOTALL)
    return {ROOT / "index.html": home, ROOT / "publications/index.html": publications}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if committed HTML is stale; do not write files")
    args = parser.parse_args()
    try:
        data = json.loads((ROOT / "data/publications.json").read_text(encoding="utf-8"))
        outputs = render_outputs(data, (ROOT / "files/publications.bib").read_bytes())
        stale = []
        for path, content in outputs.items():
            if args.check:
                if path.read_text(encoding="utf-8") != content:
                    stale.append(str(path.relative_to(ROOT)))
            else:
                path.write_text(content, encoding="utf-8")
        if stale:
            raise ValueError(f"Stale publication HTML: {', '.join(stale)}. Run scripts/render_publications.py")
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"{error}\n")
    print("Publication HTML is current." if args.check else "Rendered publication HTML.")


if __name__ == "__main__":
    main()
