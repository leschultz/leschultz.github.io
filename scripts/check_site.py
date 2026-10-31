#!/usr/bin/env python3
"""Check static links, anchors, assets, metadata, and generated publications."""

from collections import Counter
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
CV_ROUTE = "/curriculum_vitae/cv_full_leschultz.pdf"
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class Document(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.ids, self.links, self.errors, self.stack = [], [], [], []
        self.counts = Counter()
        self.has_language = False
        self.has_title = False
        self.feed(path.read_text(encoding="utf-8"))
        if self.stack:
            self.errors.append(f"Unclosed elements: {self.stack}")

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.counts[tag] += 1
        if tag not in VOID:
            self.stack.append(tag)
        if tag == "html":
            self.has_language = bool(attributes.get("lang"))
        if tag == "title":
            self.has_title = True
        if "id" in attributes:
            self.ids.append(attributes["id"])
        if tag == "img" and (not attributes.get("alt") or not all(a in attributes for a in ("width", "height"))):
            self.errors.append("Image missing useful alt text or dimensions")
        for name in ("href", "src"):
            if name in attributes:
                self.links.append(attributes[name])
        if "srcset" in attributes:
            self.links.extend(candidate.strip().split()[0] for candidate in attributes["srcset"].split(","))
        if len(attrs) != len(attributes):
            self.errors.append(f"Duplicate attribute on {tag}")

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"Unbalanced closing tag: {tag}")
        else:
            self.stack.pop()


def main():
    subprocess.run([sys.executable, str(ROOT / "scripts/render_publications.py"), "--check"], check=True)
    documents = {path.resolve(): Document(path) for path in (ROOT / "index.html", ROOT / "publications/index.html", ROOT / "404.html")}
    errors = []
    for path, doc in documents.items():
        label = str(path.relative_to(ROOT))
        errors.extend(f"{label}: {error}" for error in doc.errors)
        if doc.counts["h1"] != 1 or doc.counts["main"] != 1 or not doc.has_language or not doc.has_title:
            errors.append(f"{label}: expected one h1, one main, a language, and a title")
        if len(set(doc.ids)) != len(doc.ids):
            errors.append(f"{label}: duplicate element ids")
        for url in doc.links:
            parsed = urlsplit(url)
            if parsed.scheme or parsed.netloc:
                if parsed.scheme == "http":
                    errors.append(f"{label}: insecure URL {url}")
                continue
            if parsed.path == CV_ROUTE:
                continue  # This is served by the separate CV GitHub Pages project.
            target = (ROOT / unquote(parsed.path).lstrip("/")) if parsed.path.startswith("/") else path.parent / unquote(parsed.path)
            if not parsed.path:
                target = path
            if target.is_dir():
                target /= "index.html"
            target = target.resolve()
            if not target.is_file():
                errors.append(f"{label}: missing target {url}")
            elif parsed.fragment and target in documents and unquote(parsed.fragment) not in documents[target].ids:
                errors.append(f"{label}: missing anchor {url}")
        for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', path.read_text(), re.S):
            json.loads(block)
    css = ROOT / "assets/css/site.css"
    for asset in re.findall(r'url\(["\']?([^\)"\']+)', css.read_text()):
        if not (css.parent / asset).is_file():
            errors.append(f"Missing CSS asset: {asset}")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Checked {len(documents)} HTML pages: links, anchors, assets, structure, and publication data pass.")


if __name__ == "__main__":
    main()
