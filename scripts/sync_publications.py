#!/usr/bin/env python3
"""Sync publication metadata and static HTML from a local CV checkout."""

import argparse
import json
from pathlib import Path
import subprocess
import sys

from render_publications import ROOT, render_outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cv", type=Path, default=ROOT.parent / "curriculum_vitae", help="CV repository path")
    parser.add_argument("--check", action="store_true", help="Check consistency with the CV without writing files")
    args = parser.parse_args()
    cv = args.cv.resolve()
    exporter = cv / "scripts/export_publications.py"
    if not exporter.is_file():
        parser.exit(1, f"CV exporter not found at {exporter}. Supply --cv /path/to/curriculum_vitae\n")
    result = subprocess.run([sys.executable, str(exporter)], capture_output=True, text=True)
    if result.returncode:
        parser.exit(1, result.stderr or result.stdout)
    try:
        data = json.loads(result.stdout)
        bibliography = (cv / "sections/refs.bib").read_bytes()
        # Validate and render everything before changing the checked-in snapshot.
        outputs = {path: text.encode("utf-8") for path, text in render_outputs(data, bibliography).items()}
        outputs[ROOT / "data/publications.json"] = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        outputs[ROOT / "files/publications.bib"] = bibliography
        stale = [str(path.relative_to(ROOT)) for path, content in outputs.items()
                 if not path.exists() or path.read_bytes() != content]
        if args.check and stale:
            parser.exit(1, f"Website differs from the CV: {', '.join(stale)}\nRun scripts/sync_publications.py\n")
        if not args.check:
            for path, content in outputs.items():
                path.write_bytes(content)
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f"{error}\n")
    print(f"{'Verified' if args.check else 'Synced'} {len(data['publications'])} publications from {cv}.")


if __name__ == "__main__":
    main()
