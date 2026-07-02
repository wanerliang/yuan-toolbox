"""
One-off / occasional maintenance script (see BUSINESS_REQUIREMENTS.md §6.1).

Parses the 密探羁绊 (Spy Bond) tables from the community wiki into a local,
long-format CSV that the app reads at runtime. Not run automatically by the
app - re-run manually whenever the game updates.

Usage:
    python scripts/scrape_buff_connections.py
    python scripts/scrape_buff_connections.py --input-html path\\to\\saved_page.html
"""

import argparse
import csv
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

WIKI_URL = "https://wiki.biligame.com/yuan/%E5%AF%86%E6%8E%A2%E7%BE%81%E7%BB%8A"
TARGETS = ["纵火", "传谣", "下毒", "卧底", "搜集", "灭火", "净水", "营救"]
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36"}


def fetch_html(input_html: str | None) -> str:
    if input_html:
        return Path(input_html).read_text(encoding="utf-8")
    resp = requests.get(WIKI_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding
    return resp.text


def parse_weather_order(header_row) -> list[str]:
    weathers = []
    for th in header_row.find_all("th")[1:]:
        name = th.get_text(strip=True)
        weathers.append(name)
    return weathers


def parse_table(table, target: str) -> list[dict]:
    rows_out = []
    trs = table.find_all("tr")
    header_row, data_rows = trs[0], trs[1:]
    weather_order = parse_weather_order(header_row)

    for tr in data_rows:
        tds = tr.find_all("td")
        # Skip "update date" / "无" separator rows: a single colspan=9 td.
        if len(tds) == 1 and tds[0].get("colspan"):
            continue
        if not tds or len(tds) < 2:
            continue

        combo_link = tds[0].find("a")
        if combo_link is None:
            continue
        combination = combo_link.get_text(strip=True)
        characters = [c.strip() for c in combination.split("*") if c.strip()]

        combo_id = None
        for cell in tds[1:]:
            if cell.get("data-collectionlist"):
                combo_id = cell["data-collectionlist"]
                break

        for weather, cell in zip(weather_order, tds[1:]):
            text = cell.get_text(strip=True)
            if not text or text == "-":
                continue
            match = re.match(r"^(-?\d+)%$", text)
            if not match:
                continue
            value = int(match.group(1))
            rows_out.append(
                {
                    "combination": combination,
                    "characters": ";".join(characters),
                    "combo_id": combo_id or "",
                    "target": target,
                    "weather": weather,
                    "value_pct": value,
                }
            )
    return rows_out


def load_overrides(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def apply_overrides(rows: list[dict], overrides: list[dict]) -> list[dict]:
    """Manual corrections layered on top of the raw scrape (see
    data/buff_connections_overrides.csv). Applied by (combo_id, target, weather) key
    so a fresh scrape automatically re-applies known fixes for wiki data errors.
    action=exclude drops the scraped row entirely (wrong/spurious entry).
    action=override replaces value_pct with the corrected one (adds the row if the
    scrape didn't have it at all)."""
    by_key = {(r["combo_id"], r["target"], r["weather"]): r for r in rows}

    for ov in overrides:
        key = (ov["combo_id"], ov["target"], ov["weather"])
        action = ov["action"].strip().lower()
        if action == "exclude":
            by_key.pop(key, None)
        elif action == "override":
            existing = by_key.get(key, {})
            by_key[key] = {
                "combination": ov.get("combination") or existing.get("combination", ""),
                "characters": ov.get("characters") or existing.get("characters", ""),
                "combo_id": ov["combo_id"],
                "target": ov["target"],
                "weather": ov["weather"],
                "value_pct": int(ov["value_pct"]),
            }
        else:
            print(f"WARNING: unknown override action '{action}' for {key}, skipping", file=sys.stderr)

    return list(by_key.values())


def find_id_collisions(rows: list[dict]) -> dict:
    """A combo_id should belong to exactly one 目标. If the same combo_id shows up
    under more than one 目标, that's a strong signal of a wiki data-entry mistake
    (e.g. a copy-pasted row template that wasn't fully updated) rather than a real
    two-目标 bond - flag it for manual review instead of silently trusting it."""
    targets_by_id = {}
    for r in rows:
        if not r["combo_id"]:
            continue
        targets_by_id.setdefault(r["combo_id"], set()).add(r["target"])
    return {cid: targets for cid, targets in targets_by_id.items() if len(targets) > 1}


def parse_all(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    all_rows = []
    for target in TARGETS:
        headline = soup.find("span", class_="mw-headline", id=target)
        if headline is None:
            print(f"WARNING: could not find section for 目标={target}", file=sys.stderr)
            continue
        h3 = headline.find_parent("h3")
        table = h3.find_next("table", class_="wikitable_zhounianqing")
        if table is None:
            print(f"WARNING: could not find table for 目标={target}", file=sys.stderr)
            continue
        rows = parse_table(table, target)
        print(f"{target}: {len(rows)} (combination, weather) rows")
        all_rows.extend(rows)
    return all_rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-html", default=None, help="Parse a locally saved copy of the page instead of fetching live.")
    parser.add_argument("--output", default="data/buff_connections.csv")
    parser.add_argument("--overrides", default="data/buff_connections_overrides.csv",
                         help="Manual corrections applied after scraping. Pass '' to skip.")
    args = parser.parse_args()

    html = fetch_html(args.input_html)
    rows = parse_all(html)
    if not rows:
        print("ERROR: no rows parsed - page structure may have changed.", file=sys.stderr)
        sys.exit(1)

    if args.overrides:
        overrides = load_overrides(Path(args.overrides))
        if overrides:
            rows = apply_overrides(rows, overrides)
            print(f"Applied {len(overrides)} manual override(s) from {args.overrides}")

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["combination", "characters", "combo_id", "target", "weather", "value_pct"])
        writer.writeheader()
        writer.writerows(rows)

    unique_combos = {r["combination"] for r in rows}
    unique_characters = {c for r in rows for c in r["characters"].split(";")}
    print(f"\nWrote {len(rows)} rows to {out_path}")
    print(f"{len(unique_combos)} unique combinations, {len(unique_characters)} unique characters")

    collisions = find_id_collisions(rows)
    if collisions:
        print(f"\nWARNING: {len(collisions)} combo_id(s) appear under more than one 目标 "
              f"- likely wiki data-entry errors, review before trusting these rows:", file=sys.stderr)
        for cid, targets in collisions.items():
            combo_names = {r["combination"] for r in rows if r["combo_id"] == cid}
            print(f"  combo_id={cid} ({', '.join(combo_names)}): appears under {sorted(targets)}", file=sys.stderr)


if __name__ == "__main__":
    main()
