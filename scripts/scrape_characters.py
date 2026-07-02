"""
One-off / occasional maintenance script (see BUSINESS_REQUIREMENTS.md §6.1 for the
scraper this mirrors). Fetches the FULL character roster from the wiki's "密探"
(Secret Agent) category - not just the ~87 characters that happen to have a 羁绊 in
scrape_buff_connections.py's source page - so characters with zero bonds still show up
in the app's owned-character list. Saves the roster (name + local avatar path) to
data/characters.csv and downloads each avatar into assets/characters/.

The 密探 page renders its character grid dynamically via a Semantic MediaWiki #ask
query (JS-driven, not present in the static page HTML) - this script calls that same
query API directly (https://wiki.biligame.com/yuan/api.php?action=parse) instead of
scraping rendered HTML, using the exact query parameters reverse-engineered from the
page's own JS (conditions=[[分类:密探]], template=密探ask).

The API endpoint rate-limits repeated calls in quick succession (a second identical
call immediately after a successful one returned HTTP 567) - so this fetches
everything in a SINGLE request (limit above the known ~119 total) rather than
paginating, and sends browser-like headers (Referer, Accept, X-Requested-With) that
seemed to help avoid the block. If the wiki adds enough characters to exceed
MAX_LIMIT below, bump that constant rather than reintroducing pagination casually -
retest for rate-limiting if you do.

Usage:
    python scripts/scrape_characters.py
"""

import csv
import re
import sys
from pathlib import Path

import requests

API_URL = "https://wiki.biligame.com/yuan/api.php"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://wiki.biligame.com/yuan/%E5%AF%86%E6%8E%A2",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}
MAX_LIMIT = 300  # comfortably above the ~119 known characters, fetched in one request

DATA_OUTPUT = Path("data/characters.csv")
AVATAR_DIR = Path("assets/characters")

AVATAR_PATTERN = re.compile(r'alt="密探头像-([^"]+)\.png" src="([^"]+)"')

ASK_PRINT_COLUMNS = "|?品质|?属性|?职业|?标签1|?标签2"
ASK_PARAMETERS = "|template=密探ask|headers=hide|format=template|link=none|sort=创建日期|order=desc"


def ask_query(text: str) -> dict:
    resp = requests.get(
        API_URL,
        params={"format": "json", "action": "parse", "contentmodel": "wikitext", "text": text},
        headers=HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_all_characters() -> list[tuple[str, str]]:
    query_text = (
        f"{{{{#ask:[[分类:密探]]{ASK_PRINT_COLUMNS}{ASK_PARAMETERS}"
        f"|limit={MAX_LIMIT}|offset=0}}}}"
    )
    data = ask_query(query_text)
    html = data["parse"]["text"]["*"]
    pairs = AVATAR_PATTERN.findall(html)
    seen = {}
    for name, url in pairs:
        seen[name] = url
    return list(seen.items())


def download_avatars(characters: list[tuple[str, str]]) -> list[dict]:
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, url in characters:
        dest = AVATAR_DIR / f"{name}.png"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
        except requests.RequestException as e:
            print(f"WARNING: failed to download avatar for {name}: {e}", file=sys.stderr)
            dest = ""
        rows.append({"name": name, "avatar_file": str(dest) if dest else ""})
    return rows


def main():
    characters = fetch_all_characters()
    if not characters:
        print("ERROR: no characters found - query/page structure may have changed.", file=sys.stderr)
        sys.exit(1)

    rows = download_avatars(characters)

    DATA_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with DATA_OUTPUT.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "avatar_file"])
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r: r["name"]))

    ok = sum(1 for r in rows if r["avatar_file"])
    print(f"\nWrote {len(rows)} characters to {DATA_OUTPUT} ({ok} avatars downloaded to {AVATAR_DIR})")


if __name__ == "__main__":
    main()
