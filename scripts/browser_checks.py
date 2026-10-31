#!/usr/bin/env python3
"""Exercise the site in Chromium, run axe, and save optional visual-review captures.

Requires Playwright and its Chromium browser. The pinned axe-core script is
downloaded only by this development check; --axe accepts an offline copy.
"""

import argparse
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.request import urlopen

from playwright.sync_api import sync_playwright

from serve import SiteHandler

AXE_URL = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.3/axe.min.js"


class QuietHandler(SiteHandler):
    def log_message(self, *_args):
        pass


def assert_layout(page, width):
    overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
    assert not overflow, f"Horizontal overflow at {width}px on {page.url}"
    assert page.locator("h1").count() == 1
    assert page.locator("main").count() == 1
    assert page.locator("img").evaluate_all("images => images.every(i => i.complete && i.naturalWidth > 0)"), "Broken image"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screenshots", type=Path, help="Save desktop/mobile screenshots and a print PDF here")
    parser.add_argument("--axe", type=Path, help="Use a local axe.min.js instead of downloading it")
    args = parser.parse_args()
    if args.axe:
        axe = args.axe.read_text(encoding="utf-8")
    else:
        with urlopen(AXE_URL, timeout=30) as response:
            axe = response.read().decode("utf-8")
    if args.screenshots:
        args.screenshots.mkdir(parents=True, exist_ok=True)

    server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    accessibility = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(reduced_motion="reduce")
            page = context.new_page()
            runtime_errors, bad_responses = [], []
            page.on("pageerror", lambda error: runtime_errors.append(str(error)))
            page.on("response", lambda response: bad_responses.append(f"{response.status}: {response.url}") if response.status >= 400 else None)
            for route in ("/", "/publications/", "/404.html"):
                for width in (320, 390, 768, 1024, 1440, 1920):
                    page.set_viewport_size({"width": width, "height": 960})
                    page.goto(base + route, wait_until="networkidle")
                    # Trigger lazy loading, then check that every image has loaded.
                    for image in page.locator("img").all():
                        image.scroll_into_view_if_needed()
                    page.wait_for_function("Array.from(document.images).every(i => i.complete)")
                    page.evaluate("window.scrollTo(0, 0)")
                    assert_layout(page, width)
                    if width in (390, 1440):
                        page.add_script_tag(content=axe)
                        result = page.evaluate("async () => await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'best-practice']}})")
                        violations = result["violations"]
                        accessibility.append({"route": route, "width": width, "violations": violations})
                        assert not violations, json.dumps({"route": route, "width": width, "violations": violations}, indent=2)
                        if args.screenshots:
                            name = "home" if route == "/" else route.strip("/").replace(".html", "")
                            page.screenshot(path=str(args.screenshots / f"{name}-{width}.png"), full_page=True)
                            if route == "/":
                                page.screenshot(path=str(args.screenshots / f"home-viewport-{width}.png"))

            page.set_viewport_size({"width": 390, "height": 844})
            page.goto(base, wait_until="networkidle")
            menu = page.get_by_role("button", name="Menu")
            nav = page.get_by_role("navigation", name="Main navigation")
            assert not nav.is_visible()
            menu.focus()
            page.keyboard.press("Enter")
            assert nav.is_visible() and menu.get_attribute("aria-expanded") == "true"
            page.keyboard.press("Tab")
            assert page.evaluate("document.activeElement.textContent") == "Research"
            page.keyboard.press("Escape")
            assert not nav.is_visible() and menu.evaluate("e => e === document.activeElement")
            menu.click()
            nav.get_by_role("link", name="Research", exact=True).click()
            page.wait_for_function("location.hash === '#research'")
            assert not nav.is_visible()
            assert page.evaluate("document.activeElement.id") == "research"
            assert page.locator("#research").bounding_box()["y"] >= page.locator(".site-header").bounding_box()["height"]
            page.go_back(wait_until="networkidle")
            assert not page.url.endswith("#research"), "Native anchor history was lost"

            # Resizing must not leave a hidden focused link or stale expanded state.
            page.set_viewport_size({"width": 1440, "height": 960})
            nav.get_by_role("link", name="Publications", exact=True).focus()
            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_function("document.activeElement.classList.contains('menu-toggle')")
            assert menu.get_attribute("aria-expanded") == "false"

            page.goto(base + "/publications/#schultz_sputtering_2026", wait_until="networkidle")
            assert "Under review" in page.locator("#schultz_sputtering_2026").inner_text()
            assert "In preparation" in page.locator("#schultz_llzo_2026").inner_text()
            assert page.locator("#schultz_sputtering_2026").bounding_box()["y"] >= page.locator(".site-header").bounding_box()["height"]
            with page.expect_download() as download_info:
                page.get_by_role("link", name="Download bibliography").click()
            assert download_info.value.suggested_filename == "publications.bib"

            no_js = browser.new_context(java_script_enabled=False, viewport={"width": 390, "height": 844})
            offline_page = no_js.new_page()
            for route in ("/", "/publications/"):
                offline_page.goto(base + route, wait_until="networkidle")
                assert offline_page.get_by_role("navigation", name="Main navigation").is_visible()
                assert offline_page.locator(".publication-entry, .selected-publication").count() > 0
            no_js.close()

            page.set_viewport_size({"width": 1440, "height": 960})
            page.goto(base, wait_until="networkidle")
            assert page.evaluate("getComputedStyle(document.documentElement).scrollBehavior") == "auto"
            page.emulate_media(media="print")
            assert not page.locator("#site-nav").is_visible()
            if args.screenshots:
                page.pdf(path=str(args.screenshots / "website-print.pdf"), format="A4", print_background=True)
                (args.screenshots / "accessibility.json").write_text(json.dumps(accessibility, indent=2), encoding="utf-8")
            assert not runtime_errors, runtime_errors
            assert not bad_responses, bad_responses
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    print("Browser checks passed: 18 responsive layouts; 6 axe audits; keyboard/menu/history; deep links; bibliography download; no-JS; reduced motion; print; no resource or JS errors.")


if __name__ == "__main__":
    main()
