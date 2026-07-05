from itertools import combinations

import pandas as pd

from utils.db import used_pair_key

# Safety bound: if a single (目标, 天气) cell has more relevant characters than this,
# only keep the highest-|value| combos until the relevant-character count is back under
# the bound. Prevents the brute-force search below from exploding on a densely-connected
# cell. See docs/business-rules.md §8.
MAX_RELEVANT_CHARACTERS = 40

MODE_HIGHEST = "highest"
MODE_UNMARKED = "unmarked"


def get_active_combos(buff_df: pd.DataFrame, target: str, weather: str) -> pd.DataFrame:
    return buff_df[(buff_df["target"] == target) & (buff_df["weather"] == weather)]


def recommend_squads(
    buff_df: pd.DataFrame,
    owned_characters: set[str],
    target: str,
    weather: str,
    squad_size: int,
    used_pairs: set[str] = frozenset(),
    mode: str = MODE_HIGHEST,
    reverse: bool = False,
    top_n: int = 10,
) -> dict:
    """Best squad_size-character squads from owned_characters for the given (目标, 天气).

    Two scoring modes (docs/business-rules.md §8.1):
    - MODE_HIGHEST: standard score = sum of value_pct over every 羁绊 whose full member
      set is contained in the squad. `reverse=True` sorts this ascending instead of
      descending ("lowest score first").
    - MODE_UNMARKED: ranks by an *unmarked-only* score - 羁绊 already present in
      `used_pairs` (docs/data-model.md §6.4) contribute 0 - surfacing squads that make the most *new*
      achievement progress. `reverse=True` here does NOT just sort that same score
      ascending (that would degenerate to ties at 0, dominated by unmarked debuffs, and
      not show what a user asking for "the opposite" actually expects). Instead it swaps
      to a *marked-only* score - unmarked 羁绊 contribute 0 instead - surfacing squads
      built from 羁绊 the player has ALREADY collected, ranked descending by that.

    Characters not involved in any 羁绊 active for this (目标, 天气) are pure fillers -
    they never change either score, so instead of brute-forcing the whole owned roster we
    only search combinations of the "relevant" characters (those in at least one active,
    ownable 羁绊) and pad the rest with fillers.
    """
    if squad_size > len(owned_characters):
        return {"squads": [], "truncated": False}

    active = get_active_combos(buff_df, target, weather)
    eligible = [
        {
            "combo_id": row.combo_id,
            "combination": row.combination,
            "members": row.members,
            "value_pct": int(row.value_pct),
            "used": used_pair_key(row.combo_id, target, weather) in used_pairs,
        }
        for row in active.itertuples()
        if row.members <= owned_characters
    ]

    truncated = False
    relevant = sorted(set().union(*(c["members"] for c in eligible))) if eligible else []
    if len(relevant) > MAX_RELEVANT_CHARACTERS:
        truncated = True
        eligible.sort(key=lambda c: abs(c["value_pct"]), reverse=True)
        kept, kept_members = [], set()
        for c in eligible:
            if len(kept_members | c["members"]) <= MAX_RELEVANT_CHARACTERS or not kept:
                kept.append(c)
                kept_members |= c["members"]
        eligible = kept
        relevant = sorted(kept_members)

    max_core = min(squad_size, len(relevant))
    owned_sorted = sorted(owned_characters)

    scored_cores = []
    for size in range(max_core + 1):
        for core in combinations(relevant, size):
            core_set = frozenset(core)
            active_in_core = [c for c in eligible if c["members"] <= core_set]
            score = sum(c["value_pct"] for c in active_in_core)
            new_progress_score = sum(c["value_pct"] for c in active_in_core if not c["used"])
            marked_score = sum(c["value_pct"] for c in active_in_core if c["used"])
            scored_cores.append((score, new_progress_score, marked_score, core_set, active_in_core))

    if mode == MODE_HIGHEST:
        rank_key_index = 0  # score
        sort_descending = not reverse
    else:
        rank_key_index = 2 if reverse else 1  # marked_score vs. new_progress_score
        sort_descending = True  # both of MODE_UNMARKED's two views rank best-first
    scored_cores.sort(key=lambda t: t[rank_key_index], reverse=sort_descending)

    squads = []
    for score, new_progress_score, marked_score, core_set, active_in_core in scored_cores:
        filler_needed = squad_size - len(core_set)
        filler_pool = [c for c in owned_sorted if c not in core_set]
        if len(filler_pool) < filler_needed:
            continue
        squad_members = sorted(core_set) + filler_pool[:filler_needed]
        squads.append(
            {
                "squad": squad_members,
                "core": sorted(core_set),
                "score": score,
                "new_progress_score": new_progress_score,
                "marked_score": marked_score,
                "active_combos": active_in_core,
            }
        )
        if len(squads) >= top_n:
            break

    return {"squads": squads, "truncated": truncated}
