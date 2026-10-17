"""Render scripts/og_card.html to app/static/og.png (1200x630), the link-preview image.

    python scripts/make_og.py

Needs playwright and a Chromium. Run it after editing og_card.html; the PNG is committed so
the site never depends on this script at serve time.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "og_card.html"
OUT = ROOT / "app" / "static" / "og.png"
CHROME = os.environ.get("CHROME_PATH")  # set when Playwright's pinned build is absent


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright is not installed:  pip install playwright && playwright install chromium")
        return 1

    launch = {"executable_path": CHROME} if CHROME else {}
    with sync_playwright() as p:
        browser = p.chromium.launch(**launch)
        page = browser.new_page(viewport={"width": 1200, "height": 630}, device_scale_factor=1)
        page.goto(SOURCE.as_uri(), wait_until="networkidle")
        page.wait_for_timeout(600)          # let the webfonts settle before capture
        OUT.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(OUT))
        browser.close()
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
