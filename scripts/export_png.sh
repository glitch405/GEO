#!/usr/bin/env bash
#
# export_png.sh — full-page PNG of the HTML dashboard via Playwright.
#
# Usage:
#   ./scripts/export_png.sh reports/report_2026-04-14_213934.html reports/hero.png
#   ./scripts/export_png.sh reports/report.html reports/hero.png 1440
#
# First-time setup:
#   pip install playwright
#   playwright install chromium

set -euo pipefail

INPUT="${1:?usage: export_png.sh <input.html> <output.png> [width]}"
OUTPUT="${2:?usage: export_png.sh <input.html> <output.png> [width]}"
WIDTH="${3:-1440}"

HERE="$(cd "$(dirname "$0")" && pwd)"
python3 "$HERE/export_png.py" "$INPUT" "$OUTPUT" "$WIDTH"
