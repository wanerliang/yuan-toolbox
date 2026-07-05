from pathlib import Path

import pandas as pd
import streamlit as st

BUFF_CONNECTIONS_PATH = Path("data/buff_connections.csv")
CHARACTERS_PATH = Path("data/characters.csv")


@st.cache_data
def load_buff_connections(path: Path = BUFF_CONNECTIONS_PATH) -> pd.DataFrame:
    """羁绊 data, produced by scripts/scrape_buff_connections.py (see docs/data-model.md §6.1)."""
    df = pd.read_csv(path)
    df["members"] = df["characters"].apply(lambda s: frozenset(s.split(";")))
    return df


@st.cache_data
def load_characters(path: Path = CHARACTERS_PATH) -> pd.DataFrame:
    """Full character roster (name + local avatar path), produced by
    scripts/scrape_characters.py (docs/data-model.md §6.1, docs/decisions-log.md §13). Includes
    characters with zero 羁绊, unlike deriving the roster from buff data alone."""
    if not path.exists():
        return pd.DataFrame(columns=["name", "avatar_file"])
    return pd.read_csv(path)


def load_master_roster(buff_df: pd.DataFrame, characters_df: pd.DataFrame | None = None) -> list[str]:
    """Unique character names. Prefers the full roster from characters.csv (§13),
    which includes characters with no 羁绊, always unioned with names derived from
    the 羁绊 data itself as a safety net in case the two sources ever disagree."""
    characters = set()
    for members in buff_df["members"]:
        characters.update(members)
    if characters_df is not None and not characters_df.empty:
        characters.update(characters_df["name"])
    return sorted(characters)


def get_avatar_path(characters_df: pd.DataFrame, name: str) -> str | None:
    if characters_df is None or characters_df.empty:
        return None
    match = characters_df.loc[characters_df["name"] == name, "avatar_file"]
    if match.empty or not match.iloc[0] or pd.isna(match.iloc[0]):
        return None
    return match.iloc[0]
