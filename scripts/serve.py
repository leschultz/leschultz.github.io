#!/usr/bin/env python3
"""Preview the static site, including the sibling CV repository when available."""

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
CV_ROUTE = "/curriculum_vitae/cv_full_leschultz.pdf"
CV_FILE = ROOT.parent / "curriculum_vitae/cv_full_leschultz.pdf"


class SiteHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def translate_path(self, path):
        if urlsplit(path).path == CV_ROUTE and CV_FILE.is_file():
            return str(CV_FILE)
        return super().translate_path(path)

    def send_head(self):
        if urlsplit(self.path).path == CV_ROUTE and not CV_FILE.is_file():
            self.send_response(302)
            self.send_header("Location", "https://leschultz.github.io" + CV_ROUTE)
            self.end_headers()
            return None
        return super().send_head()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), SiteHandler)
    print(f"Preview: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
