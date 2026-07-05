# Business Requirements — Scoring & Business Rules

*(Part of the split business-requirements doc — see [CLAUDE.md](../CLAUDE.md) for the full
section index and which file covers what.)*

## 8. Business Rules

**Implemented and verified** in `utils/rules.py::recommend_squads` (no longer a placeholder):

- Squad size is 3–5 characters, chosen from the pool of owned characters.
- A 羁绊 (combination of 2 or 3 specific characters) contributes to squad score **only when all
  of its members are present** in the squad — not just any 2 characters, the exact named set.
- **For Sudden Request specifically**: a 羁绊 only counts toward the score if its value for the
  current (目标, 天气) pair (see
  [data-model.md §6.3](data-model.md#63-quest-scenario-types)) is non-`-` (i.e. defined) — 羁绊
  that are inactive for that exact pair are ignored for that recommendation.
- **Values are signed** ([data-model.md §6.1](data-model.md#61-character-buff-connection-羁绊-data)):
  positive = buff, negative = debuff. Scoring rule:
  `squad score = sum of the (目标, 天气)-specific value of every 羁绊 whose full member set is
  contained in the squad`. A squad that happens to fully contain a debuff combination gets
  penalized by that combination's negative value, same mechanism as a buff — the recommender
  naturally avoids/deprioritizes such squads since they score lower.
- **Resolved**: a character can belong to multiple 羁绊 simultaneously; if a squad satisfies
  several at once, their values simply **sum with no cap**. This is the confirmed v1 behavior
  (not just a placeholder assumption) — revisit only if real gameplay use surfaces a case where
  plain summing feels wrong.
- **Resolved**: quest scenarios impose **no hard constraints** (e.g. no "must include a healer"
  requirement) — scoring is **pure ranking** by the signed-sum rule above. Nothing in the shipped
  app enforces squad composition beyond size and the 羁绊 math itself.
- **Not explicitly decided**: tie-breaking when multiple squads score equally. De facto behavior
  is a stable sort over `itertools.combinations` iteration order (alphabetical by character name
  within the "relevant" candidate pool) — deterministic, but never a deliberate design choice.
  Low priority to revisit unless it produces a confusing result in practice.

### 8.1 Recommendation List Modes

The recommendation list supports **two scoring modes**, each of which can independently be shown
in **reverse order** — both operate over the *same* candidate-squad search (§8), they differ only
in how squads are scored/ranked for display, not in which squads are considered:

1. **最高分 (Highest Score)** — the existing/default mode. Score = standard score: sum of
   `value_pct` over every 羁绊 fully contained in the squad, active for the current (目标, 天气).
   Default order: **descending** (best squad first).
2. **未标记优先 (Unmarked-First)** — for achievement-hunting
   ([product-overview.md §3](product-overview.md#3-goals),
   [data-model.md §6.4](data-model.md#64-used-pair-tracking-achievement-progress)). Score = an
   **alternate score** that only counts 羁绊 **not yet marked as used** (`used_pairs`, §6.4) — a
   羁绊 that's already marked used contributes **0** to this alternate score, even though it would
   count normally under mode 1. Surfaces squads that make the most *new* collection progress, not
   just the highest raw score — a squad that only re-triggers already-collected 羁绊 ranks
   low/zero here even if it's the #1 squad under mode 1. Default order: **descending**.

**倒序 (Reverse order) toggle**: applies to whichever mode is selected. What "reverse" means is
**mode-dependent**, not a uniform ascending/descending flip of the same score:
- **Mode 1 (最高分) reversed**: sorts the standard score **ascending** — "lowest score first."
  This replaces having a separate third "lowest score" mode. **Confirmed real use case, not just
  a reference list**: the player sometimes deliberately wants to *underperform* a specific Sudden
  Request instance (e.g. intentionally courting a bad outcome, avoiding "over-succeeding"). This
  is still the same Sudden Request mechanic (目标+天气), not a different quest type, so it doesn't
  change the "Sudden Request is the only scenario in scope" Non-Goal
  ([product-overview.md §4](product-overview.md#4-non-goals)).
- **Mode 2 (未标记优先) reversed**: **bug found and fixed** — naively sorting the same
  unmarked-only score ascending degenerates to ties at 0 (any squad with zero active 羁绊 ties
  with any squad whose 羁绊 are all already-marked), and in practice gets dominated by squads
  triggering an *unmarked debuff* rather than showing what a user asking for "the opposite of
  unmarked-first" actually expects. Instead, reversing mode 2 swaps to a **marked-only score**
  (unmarked 羁绊 contribute 0 instead of marked ones), ranked **descending** — i.e. it surfaces
  squads built from 羁绊 the player has **already collected**, the true complement of mode 2's
  normal "what's new" view. Implemented in `utils/rules.py::recommend_squads` as a third computed
  score, `marked_score`, alongside `score` and `new_progress_score`.

**UI placement (resolved)**: the recommendation list is displayed **normal-order first** by
default; 倒序 is a **live toggle on the results panel itself** (not a pre-search setting) so the
player can flip to the opposite ordering instantly, for either mode, without re-running the
search. Recommendation mode (最高分/未标记优先) itself remains a **pre-search setting** chosen
before clicking 获取推荐 (see [ui-flows.md §8.2](ui-flows.md#82-ui-layout-sidebar-vs-main-page-within-鸢报-突发情况)
for where it lives in the UI). In
`pages/1_鸢报-突发情况.py`, this means the recommendation is recomputed on every rerun from the
last-searched (目标, 天气, 队伍人数, mode) plus the *live* reverse-toggle and *live* `used_pairs`
state — not frozen at the moment "获取推荐" was clicked.
