# CLAUDE.md

**如鸢 (Ru Yuan) 突发情况 Team Optimizer** — a Streamlit app that recommends 3–5 character squads
for the game's Sudden Request (鸢报-突发情况) side quests, scoring candidates by which 羁绊
(buff-connection combos) they trigger for the current 目标 (target) + 天气 (weather) pair. Supports
multiple independent users (real accounts or guests) against one deployed instance, each with
their own owned-character selection and 羁绊 progress. v1 is built and in use; code should follow
the docs below, not the other way around.

The full requirements doc got too long for one file, so it's split by concern under `docs/` —
load only what's relevant to the file you're touching:

| Doc | Covers | Load when touching |
|---|---|---|
| [docs/product-overview.md](docs/product-overview.md) | Background, problem statement, goals/non-goals, users, success criteria, glossary | Orienting to the project; scope questions |
| [docs/data-model.md](docs/data-model.md) | Wiki data sources, scraper scripts, CSV schemas; per-user SQLite persistence, auth/guest accounts, deployment bootstrap | `scripts/*.py`, `data/*`, `utils/loader.py`, `utils/db.py`, `utils/auth.py`, `utils/bootstrap.py` |
| [docs/business-rules.md](docs/business-rules.md) | Squad scoring formula, recommendation modes (最高分/未标记优先), reverse-order semantics | `utils/rules.py` |
| [docs/ui-flows.md](docs/ui-flows.md) | User flow, page layout (sidebar vs. body), multi-page nav, inputs/outputs | `app.py`, `pages/*.py` |
| [docs/decisions-log.md](docs/decisions-log.md) | Constraints, resolved/open decisions history | Understanding *why* something is the way it is before changing it |

Cross-references keep the original `§N`/`§N.M` numbering from the single-file doc; each doc links
to the specific other file a reference lives in.

Update the relevant doc whenever scope, data shape, or rules change.
