"""Take side-by-side mobile + desktop screenshots of every page.

Run: uv run python scripts/visual_compare.py
Requires: playwright (uv add --dev playwright && playwright install chromium)

Output: screenshots/{mobile,desktop}/*.png
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path so we can import the config
sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright
from playwright_config import BASE_URL, DEVICES, PAGES


OUTPUT_DIR = Path("screenshots")


async def capture_device(browser, device_name: str, device_config: dict):
    """Capture all pages for a single device profile."""
    out = OUTPUT_DIR / device_name
    out.mkdir(parents=True, exist_ok=True)

    context = await browser.new_context(**device_config)
    page = await context.new_page()

    for path, name in PAGES:
        url = f"{BASE_URL}{path}"
        try:
            await page.goto(url, wait_until="networkidle", timeout=15000)
            await page.wait_for_timeout(500)  # let D3 charts render
            filepath = out / f"{name}.png"
            await page.screenshot(path=str(filepath), full_page=True, type="png")
            print(f"  [{device_name}] {name}")
        except Exception as e:
            print(f"  [{device_name}] {name} — FAILED: {e}")

    await context.close()


async def main():
    print(f"Capturing {len(PAGES)} pages × {len(DEVICES)} devices...\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch()

        for device_name, device_config in DEVICES.items():
            await capture_device(browser, device_name, device_config)

        await browser.close()

    print(f"\nScreenshots saved to {OUTPUT_DIR}/")
    print(f"  Mobile:  {OUTPUT_DIR}/mobile/")
    print(f"  Desktop: {OUTPUT_DIR}/desktop/")


if __name__ == "__main__":
    asyncio.run(main())
