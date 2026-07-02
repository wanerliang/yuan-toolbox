"""
One-off / occasional maintenance script (see BUSINESS_REQUIREMENTS.md §6.1 for the
scraper this mirrors). Downloads the 8 天气 icon images referenced on the 密探羁绊 wiki
page into assets/weather/ so the app can display them locally, with no runtime
dependency on the wiki being reachable. Re-run only if the wiki changes these icons.

Usage:
    python scripts/download_weather_icons.py
"""

import sys
from pathlib import Path

import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36"}

# Full-size (non-thumbnail) image URLs, derived from the <img src="...thumb/.../35px-...">
# tags on https://wiki.biligame.com/yuan/密探羁绊 by dropping the /thumb/ and /35px-*
# suffix - confirmed identical across all 8 目标 tables on the page.
WEATHER_ICON_URLS = {
    "晴天": "https://patchwiki.biligame.com/images/yuan/6/6d/0437opnsibr313oe66fg02m3z3kjups.png",
    "雨天": "https://patchwiki.biligame.com/images/yuan/8/8d/cmv0mpiueylseqifisgqrlimiez9pqx.png",
    "大雾": "https://patchwiki.biligame.com/images/yuan/6/62/ansxul7rr19ik4cb58p48zojstbqw0z.png",
    "狂风": "https://patchwiki.biligame.com/images/yuan/a/a1/hdz68qbrvjp2x34ucf3zw3c34ntr11y.png",
    "小雪": "https://patchwiki.biligame.com/images/yuan/7/71/8k28vcn8n8i4lokzyo6fxnwh1knpqtg.png",
    "大雪": "https://patchwiki.biligame.com/images/yuan/d/d8/e9yl06g61h8mmw1aavh7gwo8p6u5tga.png",
    "飓风": "https://patchwiki.biligame.com/images/yuan/5/5a/e3o2mrcogrcwzpu0xbqu9kbp3jrm6rg.png",
    "雷鸣": "https://patchwiki.biligame.com/images/yuan/6/6a/6arsa1f4goxay7a2dhd7qkl6218m2mw.png",
}

OUTPUT_DIR = Path("assets/weather")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    failures = []
    for weather, url in WEATHER_ICON_URLS.items():
        dest = OUTPUT_DIR / f"{weather}.png"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            print(f"{weather}: saved {len(resp.content)} bytes -> {dest}")
        except requests.RequestException as e:
            failures.append(weather)
            print(f"{weather}: FAILED ({e})", file=sys.stderr)

    if failures:
        print(f"\n{len(failures)} icon(s) failed to download: {failures}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
