#!/usr/bin/env python3
"""
Export the HTML visibility report as a full-page PNG.

Uses Playwright (properly handles full-page screenshots, unlike Chrome's
headless --screenshot flag which is capped at the viewport).

Usage:
    python3 scripts/export_png.py reports/report.html reports/hero.png
    python3 scripts/export_png.py reports/report.html reports/hero.png 1440

First run needs:
    pip install playwright
    playwright install chromium
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def export(html_path: Path, output_path: Path, width: int = 1440) -> Path:
    html_path = html_path.resolve()
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": width, "height": 900},
            device_scale_factor=2,  # retina crispness
        )
        page = context.new_page()
        page.goto(html_path.as_uri())
        # Let Google Fonts, favicons, and CSS animations settle
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1500)
        page.screenshot(path=str(output_path), full_page=True, type="png")
        browser.close()

    print(f"Wrote {output_path} ({output_path.stat().st_size:,} bytes)")
    return output_path


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    html = Path(sys.argv[1])
    out = Path(sys.argv[2])
    width = int(sys.argv[3]) if len(sys.argv) >= 4 else 1440
    if not html.exists():
        print(f"ERROR: {html} not found")
        return 3
    export(html, out, width=width)
    return 0


if __name__ == "__main__":
    sys.exit(main())
