"""One-off migration: import the pre-multi-user data/owned_characters.json and
data/used_pairs.json (single shared save-state) into the SQLite-backed per-user store
(utils/db.py) under a given username, so existing personal progress isn't lost when
switching to multi-user accounts. Safe to run once after setting up
.streamlit/auth_config.yaml (see scripts/manage_users.py) and before deleting the old
JSON files.

Usage:
    python scripts/migrate_json_to_db.py <username>
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.db import save_owned_characters, save_used_pairs  # noqa: E402

OWNED_JSON = Path("data/owned_characters.json")
USED_JSON = Path("data/used_pairs.json")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("username", help="Username (from .streamlit/auth_config.yaml) to migrate this data to.")
    args = parser.parse_args()

    if OWNED_JSON.exists():
        owned = set(json.loads(OWNED_JSON.read_text(encoding="utf-8")))
        save_owned_characters(args.username, owned)
        print(f"Migrated {len(owned)} owned characters to user '{args.username}'.")
    else:
        print(f"{OWNED_JSON} not found, skipping.")

    if USED_JSON.exists():
        used = set(json.loads(USED_JSON.read_text(encoding="utf-8")))
        save_used_pairs(args.username, used)
        print(f"Migrated {len(used)} used pairs to user '{args.username}'.")
    else:
        print(f"{USED_JSON} not found, skipping.")


if __name__ == "__main__":
    main()
