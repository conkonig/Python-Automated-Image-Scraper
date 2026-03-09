#!/usr/bin/env python3
"""
Download the first Unsplash search result image for each row in a CSV.
Uses a real browser with random delays to mimic human behavior and reduce blocking risk.
"""

import argparse
import csv
import re
import time
import urllib.parse
from pathlib import Path

from playwright.sync_api import sync_playwright


# Unsplash search URL template
UNSPLASH_SEARCH_TEMPLATE = "https://unsplash.com/s/photos/{}"

# Random delay ranges (seconds) to appear human
DELAY_AFTER_PAGE_LOAD = (2, 5)
DELAY_BETWEEN_ROWS = (4, 10)
DELAY_BEFORE_CLICK = (0.5, 1.5)


def sanitize_filename(value: str) -> str:
    """Make a string safe for use as a filename (no path chars, no spaces)."""
    value = value.strip()
    value = re.sub(r'[<>:"/\\|?*]', "", value)
    value = re.sub(r"\s+", "_", value)
    return value or "image"


def random_delay(low: float, high: float) -> None:
    import random
    time.sleep(random.uniform(low, high))


# Unsplash often puts premium in the first 1–2 spots; we start at 3rd and try until we get a free one.
GRID_IMAGE_INDEX = 2  # 0-based: 2 = 3rd image
# Free (non-premium) photo pages show a green "Download free" button; if it's missing, we skip.
DOWNLOAD_FREE_SELECTORS = [
    'a:has-text("Download free")',
    '[data-testid="non-sponsored-photo-download-button"]',
    'text="Download free"',
]
MAX_ATTEMPTS = 10


def _is_free_photo_page(page) -> bool:
    """True if the opened photo page shows the 'Download free' button (non-premium)."""
    for sel in DOWNLOAD_FREE_SELECTORS:
        try:
            btn = page.locator(sel).first
            btn.wait_for(state="visible", timeout=2500)
            return True
        except Exception:
            continue
    try:
        page.get_by_text("Download free").first.wait_for(state="visible", timeout=500)
        return True
    except Exception:
        pass
    return False


def save_first_result_via_large_view(page, save_path: Path, search_url: str) -> bool:
    """
    Click results in order (3rd, then 2nd, then 1st, then 4th…) until we open a page
    that shows the green 'Download free' button. Then screenshot the main image.
    If that button isn't there, it's premium — go back and try the next result.
    """
    grid = page.locator('[data-testid^="masonry-grid-count-"]').first
    try:
        grid.wait_for(state="visible", timeout=15000)
        time.sleep(0.5)
    except Exception:
        pass

    photo_links = page.locator(
        '[data-testid^="masonry-grid-count-"] figure a[href^="/photos/"]:not([href^="/photos/s/"])'
    )
    try:
        photo_links.first.wait_for(state="visible", timeout=8000)
    except Exception:
        photo_links = page.locator('figure a[href^="/photos/"]:not([href^="/photos/s/"])')
        photo_links.first.wait_for(state="visible", timeout=5000)

    for attempt in range(MAX_ATTEMPTS):
        try:
            link = photo_links.nth(attempt)
            link.wait_for(state="visible", timeout=3000)
        except Exception:
            break

        random_delay(*DELAY_BEFORE_CLICK)
        link.click()
        time.sleep(1.5)

        if not _is_free_photo_page(page):
            page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
            random_delay(0.5, 1.5)
            continue

        large_view = page.locator('div[class^="imageLayoutInner"]').first
        try:
            large_view.wait_for(state="visible", timeout=8000)
            time.sleep(0.5)
            large_view.screenshot(path=str(save_path), type="jpeg")
            if save_path.exists() and save_path.stat().st_size > 0:
                return True
        except Exception:
            pass

        page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
        random_delay(0.5, 1.5)

    return False


def run(
    csv_path: Path,
    column: str,
    output_dir: Path,
    headless: bool = False,
    slow_mo: int = 150,
    reuse_existing: bool = True,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        if "featured_img" not in fieldnames:
            fieldnames.append("featured_img")
        if column not in fieldnames:
            raise SystemExit(f"Column '{column}' not found in CSV. Available: {fieldnames}")
        rows = list(reader)

    if not rows:
        raise SystemExit("CSV has no data rows.")

    # Ensure featured_img key exists for every row (preserve existing or default to empty)
    for row in rows:
        row.setdefault("featured_img", "")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            slow_mo=slow_mo,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=2,
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        page = context.new_page()

        for i, row in enumerate(rows):
            value = (row.get(column) or "").strip()
            if not value:
                continue

            safe_name = sanitize_filename(value)
            out_file = output_dir / f"{safe_name}.jpeg"
            if out_file.exists():
                if reuse_existing:
                    print(f"[{i+1}/{len(rows)}] Reuse existing: {out_file.name}")
                    row["featured_img"] = out_file.name
                    continue
                else:
                    print(f"[{i+1}/{len(rows)}] Overwriting existing file: {out_file.name}")

            search_query = urllib.parse.quote(value)
            url = UNSPLASH_SEARCH_TEMPLATE.format(search_query)

            print(f"[{i+1}/{len(rows)}] Search: {value} -> {url}")

            try:
                random_delay(*DELAY_BEFORE_CLICK)
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
                random_delay(*DELAY_AFTER_PAGE_LOAD)

                ok = save_first_result_via_large_view(page, out_file, url)
                if ok:
                    row["featured_img"] = out_file.name
                    print(f"  -> Saved: {out_file}")
                else:
                    row["featured_img"] = ""
                    print(f"  -> No first image found or screenshot failed.")
            except Exception as e:
                row["featured_img"] = ""
                print(f"  -> Error: {e}")

            if i < len(rows) - 1:
                random_delay(*DELAY_BETWEEN_ROWS)

        context.close()
        browser.close()

    # Write CSV back with featured_img column updated
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Updated CSV with featured_img column: {csv_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download first Unsplash image per row from a CSV column (e.g. city_name)."
    )
    parser.add_argument(
        "csv",
        type=Path,
        help="Path to input CSV",
    )
    parser.add_argument(
        "--column",
        "-c",
        required=True,
        help="CSV column to use as search term (e.g. city_name)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=Path("downloaded_images"),
        help="Directory to save images (default: downloaded_images)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser headless (default: visible browser)",
    )
    parser.add_argument(
        "--slow",
        type=int,
        default=150,
        metavar="MS",
        help="Playwright slow_mo in ms (default: 150)",
    )
    parser.add_argument(
        "--reuse-existing",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Reuse existing images in the output directory if present "
            "(default: True). Use --no-reuse-existing to always fetch a new image."
        ),
    )
    args = parser.parse_args()
    run(
        csv_path=args.csv,
        column=args.column,
        output_dir=args.output_dir,
        headless=args.headless,
        slow_mo=args.slow,
        reuse_existing=args.reuse_existing,
    )


if __name__ == "__main__":
    main()
