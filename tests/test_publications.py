"""Protect publication rendering and status changes across both site views."""

import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from render_publications import ROOT, render_outputs


class PublicationRenderingTest(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / "data/publications.json").read_text(encoding="utf-8"))
        self.bib = (ROOT / "files/publications.bib").read_bytes()

    def test_status_change_reaches_homepage_and_archive(self):
        paper = next(p for p in self.data["publications"] if p["id"] == "schultz_llzo_2026")
        paper["status"] = paper["note"] = "Submitted"
        output = render_outputs(self.data, self.bib)
        self.assertIn('<!-- publication-status:schultz_llzo_2026 --><span class="status-label">Submitted · 2026</span>', output[ROOT / "index.html"])
        archive = output[ROOT / "publications/index.html"]
        self.assertIn('<span class="status-label">Submitted</span>', archive)
        self.assertNotIn('<span class="status-label">In preparation</span>', archive)

    def test_publication_changes_the_research_link_label(self):
        paper = next(p for p in self.data["publications"] if p["id"] == "schultz_sputtering_2026")
        paper.update(category="journal", status="Published", note="", venue="Example Journal")
        output = render_outputs(self.data, self.bib)[ROOT / "index.html"]
        self.assertIn('href="/publications/#schultz_sputtering_2026">Paper details', output)

    def test_bibliography_text_is_escaped_as_content(self):
        paper = self.data["publications"][0]
        paper["title"] = 'A <script>alert("title")</script> & example'
        paper["authors"][0]["name"] = "A <person>"
        output = render_outputs(self.data, self.bib)
        for document in output.values():
            self.assertIn("&lt;script&gt;", document)
            self.assertNotIn('<script>alert("title")</script>', document)
            self.assertIn("A &lt;person&gt;", document)

    def test_stale_source_snapshot_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "snapshot differ"):
            render_outputs(self.data, self.bib + b"\n")

    def test_missing_research_reference_is_rejected(self):
        data = copy.deepcopy(self.data)
        data["publications"] = [p for p in data["publications"] if p["id"] != "schultz_sputtering_2026"]
        with self.assertRaisesRegex(ValueError, "unknown publication"):
            render_outputs(data, self.bib)


if __name__ == "__main__":
    unittest.main()
