# Business Requirements — 如鸢 (Ru Yuan) 突发情况 Team Optimizer

> Status: **v1 built and in use.** Core scoring rules, data pipeline, and UI are implemented and
> verified end-to-end; remaining items in [Open Questions](#13-open-questions) are refinements,
> not blockers. This document is the source of truth for *why* the app exists and *what* it must
> do. Update it whenever scope, data shape, or rules change — code should follow this doc, not
> the other way around.

## 1. Background

**如鸢 (Ru Yuan)** is a mobile game. Certain side tasks **鸢报-突发情况 (sudden request)** require the player to select
a squad of **3–5 characters** from the roster they've obtained to complete the task.

Character choice matters beyond raw stats: many characters belong to a **羁绊 (buff connection)**
— a named combination of **2 or 3 specific characters** (not always just a pair) that grants a
synergy bonus, or occasionally a penalty, when *all* members of that combination are in the same
squad. Manually cross-referencing which combinations are covered, while also satisfying whatever
the quest itself demands, is tedious and error-prone to do by hand — especially as the roster grows.

## 2. Problem Statement

Given:
- a **quest scenario** (what the task requires), and
- the player's **owned characters** and their **buff-connection data**,

manually finding the best 3–5 character squad requires checking every relevant pairing by hand.
This tool automates that search and returns the most suitable squad(s).

## 3. Goals

- Given a selected quest scenario, recommend the best 3–5 character squad(s) from the
  player's available roster.
- Correctly account for 羁绊 (character combinations) when scoring a candidate squad — a squad
  that fully contains a positive-value 羁绊 should generally outscore one that doesn't, and a
  squad that fully contains a negative-value (debuff) 羁绊 should generally be penalized.
- Let the player re-run recommendations quickly as their roster or the quest changes (this is a
  personal planning tool used repeatedly, not a one-off report).
- Track which 羁绊 the player has already triggered, so they can systematically work through
  every possible combination (e.g. for an in-game achievement) without losing track of what's left.
- Support two recommendation-list scoring modes (highest score, unmarked-first for achievement
  progress) for the same (目标, 天气) instance, each reversible (enabling deliberate
  underperformance via reversed highest-score) — not just a single "best squad" view. See §8.1.

## 4. Non-Goals

- Not a general-purpose game database/wiki — only stores what's needed to compute recommendations.
- No user accounts, multi-user support, or cloud hosting. Single player, runs locally via
  `streamlit run app.py`.
- Not live-scraping the wiki at runtime or auto-syncing on a schedule — import is a manual,
  occasional step the user triggers when the game updates (see §6.1).
- Not modeling full battle simulation (turn order, damage rolls, RNG) unless a future rule
  requires it — start with a scoring/filtering model, not a simulator.
- **Sudden Request (鸢报-突发情况) is the only quest scenario type in scope.** No other quest
  types will be supported by this project.

## 5. Users

- Single user (the app owner), playing 如鸢, planning squad choices for side quests.

## 6. Data Sources

### 6.1 Character buff-connection (羁绊) data
- **Source**: the community wiki page
  `https://wiki.biligame.com/yuan/密探羁绊` ("密探羁绊" = Spy/Agent Bonds). Confirmed by
  inspecting the raw page HTML directly (not just an AI-summarized read, which mis-rendered
  some structure — see below).
- **Page structure (ground-truthed from HTML)**: one `<table>` per **目标**, each with 9 columns:
  `组合` (Combination) followed by the 8 天气 columns in fixed order (晴天, 雨天, 大雾, 狂风,
  小雪, 大雪, 飓风, 雷鸣). Each row is one named combination, e.g. `安期*孙尚香` (2 characters)
  or `庞羲*刘璋*法正` (3 characters) — members are `*`-separated. Each weather cell is either
  `-` (no effect for that target+weather) or a signed percentage (e.g. `50%`, `-70%`).
  Cells carry `data-collection="{目标}{天气}"` attributes and already have a built-in
  checkbox-style "collected" UI on the wiki itself — i.e. the wiki tracks the same
  combination-usage concept described in §6.4.
- **Important correction vs. earlier assumption**: 羁绊 members are **2 or 3 characters**, not
  always exactly 2 — "buff pair" should be read as "羁绊 combination" throughout this doc.
- **Values can be negative** (debuffs), not just positive buffs. Scoring (§8) must account for
  this — it's not just "count of active connections."
- **`combo_id` identifies the character relationship, not a single 目标**: the same `combo_id`
  (the wiki's `data-collectionlist` attribute) commonly appears under multiple 目标 tables with
  different — sometimes very different, including flipped sign — values per 目标/天气 cell.
  This is the norm (45% of combos in the scraped data span more than one 目标), not an error, so
  it should not be "deduped" away. Each (combo_id, 目标, 天气) cell is independently authored and
  must be looked up individually.
- **Scraper built and verified** (`scripts/scrape_buff_connections.py`): parses the 8 目标 tables
  into `data/buff_connections.csv` (columns: `combination`, `characters` [`;`-separated],
  `combo_id`, `target`, `weather`, `value_pct`). Verified against a live fetch on 2026-07-02:
  **1207 rows, 77 unique combinations (by `combo_id`), 87 unique characters.** Spot-checked
  against the raw HTML for exact matches on several edge cases (single-weather-only combos,
  per-weather-varying values, 3-character combos, and a specifically-flagged row that turned out
  to be correct on recheck).
- **Manual override mechanism**: `data/buff_connections_overrides.csv` (columns: `combo_id`,
  `target`, `weather`, `action` [`override`/`exclude`], `value_pct`, `combination`, `characters`,
  `note`) lets known wiki data errors be corrected without hand-editing the generated CSV — the
  scraper re-applies it on every run, so corrections survive re-scraping after a game update.
  Currently empty (no known bad rows as of this data pull).
- **Storage model: persistent local file, not a per-session upload.** This data changes rarely —
  only when the game gets an update that adds/changes characters or 羁绊 (the page shows
  dated "XXXX.X.X更新" sections). Instead of the user uploading a file each session, the page is
  parsed **once** (and re-parsed occasionally on update) into a local data file bundled with the
  app (`data/buff_connections.csv`), and the app always reads from that fixed path on startup.
  `utils/loader.py` changes from a file-uploader-based loader to a fixed-path loader.
- **Import mechanism**: a small one-off scraper script (`requests` + `BeautifulSoup`, or
  `pandas.read_html` against the saved page) parses the wiki tables into
  `data/buff_connections.csv`. This is run manually/occasionally by the user when the game
  updates — not embedded in the running app and not continuous — consistent with the
  "no scraping/auto-syncing" constraint in §4 (that constraint means no *live* scraping at
  runtime, not that the one-time import method can't itself be a script instead of hand-copying).

### 6.2 Player's owned characters
- **Data model**: a master **character roster** listing every character that exists in the game
  (id/name at minimum), with a boolean **`owned`** flag per character.
- **Roster source (resolved, corrected)**: originally derived purely from the unique character
  names appearing in `data/buff_connections.csv` (~87 characters) — but that silently **excludes
  any character with zero 羁绊**, since they'd never appear in that data at all. Fixed by adding
  a dedicated full-roster source: `scripts/scrape_characters.py` scrapes the wiki's **密探**
  (Secret Agent) category page — specifically its underlying Semantic MediaWiki `#ask` query API
  (`https://wiki.biligame.com/yuan/api.php?action=parse`), reverse-engineered from that page's own
  JS, since the character grid is rendered client-side and isn't present in the page's static
  HTML — giving the true full roster (**119 characters**, confirmed as of 2026-07-02, a strict
  superset of the 87 buff-derived names) plus an **avatar image URL per character**. Saved to
  `data/characters.csv` (name + local avatar path) and `assets/characters/*.png` (119 images,
  same "cache locally, no runtime wiki dependency" pattern as the other scraped assets).
  `load_master_roster()` in `utils/loader.py` now unions this full list with the buff-derived
  names (safety net in case the two sources ever disagree) — this was originally an open question
  in §13, now resolved.
  - **Rate-limit note**: the wiki's `#ask` query API blocks rapid repeated calls (a second
    identical request right after a successful one returned HTTP 567) — the scraper works around
    this by fetching all 119 characters in a **single request** (a high `limit`) rather than
    paginating. See the script's docstring before reintroducing pagination.
- **UI flow**: a **dedicated full-width page** (`pages/2_角色管理.py`, Streamlit's multi-page
  `pages/` convention — separate from the 鸢报-突发情况 recommendation page, linked via a sidebar
  summary + `st.page_link` on that page, and via a card on the landing page, §8.3), not a
  cramped sidebar widget. Superseded an earlier sidebar `st.multiselect`, which didn't give enough
  room to browse ~119 characters comfortably. The page provides:
  - a search box to filter the roster by name,
  - **✅ 全选 (select all)** and **❌ 全部取消 (deselect all)** bulk-action buttons,
  - a multi-column grid of individual checkboxes (one per character), **each with its avatar
    image** above the checkbox (from `data/characters.csv`, via `get_avatar_path()`), filtered by
    the search box.
  Every toggle (individual or bulk) updates the `owned` flag and persists immediately.
- **Persistence**: unlike the buff-connection sheet (re-uploaded fresh each session), the `owned`
  flags must **persist across app restarts** — the user shouldn't have to re-mark ownership every
  time they open the app. Streamlit itself is stateless between runs, so this flag needs to be
  read/written to a local file (`data/owned_characters.json`, a plain JSON array of owned
  character names) that the app loads on startup and rewrites whenever the user changes a
  selection. This is local file I/O, not a database engine — consistent with the "no cloud infra"
  constraint in §11.

### 6.3 Quest Scenario Types

#### Sudden Request (鸢报-突发情况)
Each Sudden Request quest instance is defined by exactly **one 目标 (Target) + one 天气
(Weather)** combination, given to the user when the quest starts.

- **目标 (Target)** — 8 possible values: 纵火 (Arson), 传谣 (Spread Rumors), 下毒 (Poisoning),
  卧底 (Undercover), 搜集 (Collection), 灭火 (Firefighting), 净水 (Water Purification),
  营救 (Rescue).
- **天气 (Weather)** — 8 possible values: 晴天 (Sunny), 雨天 (Rainy), 大雾 (Fog),
  狂风 (Gale), 小雪 (Light Snow), 大雪 (Heavy Snow), 飓风 (Hurricane), 雷鸣 (Thunder).
- **天气 picker is icon-based**: the wiki page (§6.1) has a small icon image per 天气 in its
  table headers. These are downloaded once via `scripts/download_weather_icons.py` into
  `assets/weather/*.png` (same "cache locally, no runtime wiki dependency" pattern as the 羁绊
  data itself), and the 鸢报-突发情况 page (§8.3) shows them as a row of 8 icon+button cells in
  its page body — full-width real estate, not the sidebar, since 8 icons+labels don't fit a
  narrow sidebar comfortably (same reasoning as moving character selection to its own page,
  §6.2). 目标 has no equivalent icons on the wiki, so it's a plain dropdown, but it's placed in
  that same page body too (see §8.2) rather than the sidebar, for layout consistency with 天气.
- **Bug found and fixed**: the highlighted/selected icon button initially required clicking
  twice to visually update. Cause: the button's primary/secondary styling was computed from
  `session_state` *before* the click's effect was applied, and Streamlit doesn't automatically
  re-render just because a script mutates `session_state` mid-run — so the just-clicked button
  still rendered with its pre-click style for that pass, only catching up on the next
  interaction. Fixed in `pages/1_鸢报-突发情况.py` by calling `st.rerun()` immediately after
  updating `st.session_state.selected_weather`, forcing an immediate re-render with the
  correct style.
- This gives up to 8 × 8 = 64 distinct (目标, 天气) cells per 羁绊. In the actual wiki data
  (§6.1) most 羁绊 have the same value across all 8 天气 for their 目标, but some are narrower
  (active for only 1-2 specific 天气, `-` i.e. inactive elsewhere) — so every cell must still be
  looked up individually, not assumed constant across weather.
- Example: `安期*孙尚香` is a 2-character 羁绊 worth `+50%` under 目标=纵火 for every weather.
  `周瑜*小乔` is a 2-character 羁绊 worth `-70%` under 目标=纵火, but only for 天气=雨天 — every
  other weather is inactive for that combination.
- The recommendation for a Sudden Request must be computed **for the specific (目标, 天气) pair
  the user was given** — 羁绊 that aren't active for that exact pair don't count toward the
  squad score.

Sudden Request is the **only** quest scenario type in scope for this project (see §4
Non-Goals) — no other quest types need to be modeled.

### 6.4 Used-pair tracking (achievement progress)
- **Purpose**: some in-game achievement (or the player's own completionist goal) rewards having
  triggered every possible 羁绊 at least once. The app should let the player mark a 羁绊 as
  "already used" so they can track progress and see what's left, instead of losing track across
  play sessions.
- **Data model (resolved)**: a boolean `used` flag per 羁绊 row — keyed by (`combo_id`, 目标,
  天气), matching the granularity of the buff data in §6.1 (note: `combo_id` alone is not enough,
  since the same `combo_id` can have independent cells across multiple 目标 — see §6.1).
  Row-level (combo_id *and* scenario) is the shipped, confirmed granularity — see §13 for the
  closed-out decision record.
- **UI flow**: on the recommendations screen (§7 step 5), each active 羁绊 shown for a
  recommended squad has a "mark as used" checkbox. If the same 羁绊 appears in more than one
  displayed squad, only the first occurrence is an interactive checkbox (to avoid duplicate
  widget keys) — later occurrences show a static "已标记 / 尚未标记" status instead.
- **Collection-progress panel** (`📖 羁绊收集进度（成就用）` expander at the bottom of the
  鸢报-突发情况 page, §8.3), independent of any specific recommendation run — shows every 羁绊
  across all 目标/天气, not just ones from the current search:
  - a `used_count / total_count` metric,
  - a **全部 / 已收集 / 未收集** filter (radio buttons) to narrow the table to just what's
    collected, just what's left, or everything,
  - the table itself is an **editable `st.data_editor`** with 已收集 as a checkbox column — the
    player can tick/untick collection status directly in this panel (not just from a squad
    recommendation), including **de-selecting** (un-marking) a 羁绊 they'd previously marked used.
    Other columns (组合/目标/天气/数值) are read-only.
- **Persistence**: same pattern as owned-character flags (§6.2) — `data/used_pairs.json` (a plain
  JSON array of `"combo_id|target|weather"` keys) read on startup and rewritten whenever the
  player marks/unmarks a 羁绊 from either the recommendation checkboxes or the progress panel,
  not a hosted database.

## 7. Core User Flow

0. User lands on the **landing page** (`app.py`, §8.3) and opens the **鸢报-突发情况** tool.
1. App loads the buff-connection data from the local persistent file (§6.1) — no upload step.
2. App loads the master character roster with previously-saved `owned` flags from local storage.
   The 鸢报-突发情况 page's sidebar just shows a "selected N / total" summary; the user manages
   their roster on the dedicated **角色管理** page (§6.2) — search, bulk select/deselect-all, or
   toggle characters individually — with every change persisted immediately.
3. User selects the current Sudden Request's **目标** and **天气** (icon-based picker), both in
   the 鸢报-突发情况 page's control panel, along with 队伍人数 and 推荐模式 (see §8.2).
4. App evaluates candidate squads (3–5 owned characters) and scores them using the 羁绊 that are
   active for that (目标, 天气) pair.
5. App returns a ranked list of the best-scoring squad(s), showing *why* each was picked (which
   羁绊 are active).
6. User can mark any shown 羁绊 as already-used for achievement-tracking purposes (§6.4) —
   helping them work through every possible pair without missing any. Independently, the
   collection-progress panel lets them review and correct (including de-select) collection status
   across all 羁绊, filtered by collected/uncollected, at any time.

## 8. Business Rules

**Implemented and verified** in `utils/rules.py::recommend_squads` (no longer a placeholder):

- Squad size is 3–5 characters, chosen from the pool of owned characters.
- A 羁绊 (combination of 2 or 3 specific characters) contributes to squad score **only when all
  of its members are present** in the squad — not just any 2 characters, the exact named set.
- **For Sudden Request specifically**: a 羁绊 only counts toward the score if its value for the
  current (目标, 天气) pair (see §6.3) is non-`-` (i.e. defined) — 羁绊 that are inactive for
  that exact pair are ignored for that recommendation.
- **Values are signed** (§6.1): positive = buff, negative = debuff. Scoring rule:
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
2. **未标记优先 (Unmarked-First)** — for achievement-hunting (§3, §6.4). Score = an **alternate
   score** that only counts 羁绊 **not yet marked as used** (`used_pairs`, §6.4) — a 羁绊 that's
   already marked used contributes **0** to this alternate score, even though it would count
   normally under mode 1. Surfaces squads that make the most *new* collection progress, not just
   the highest raw score — a squad that only re-triggers already-collected 羁绊 ranks low/zero
   here even if it's the #1 squad under mode 1. Default order: **descending**.

**倒序 (Reverse order) toggle**: applies to whichever mode is selected. What "reverse" means is
**mode-dependent**, not a uniform ascending/descending flip of the same score:
- **Mode 1 (最高分) reversed**: sorts the standard score **ascending** — "lowest score first."
  This replaces having a separate third "lowest score" mode. **Confirmed real use case, not just
  a reference list**: the player sometimes deliberately wants to *underperform* a specific Sudden
  Request instance (e.g. intentionally courting a bad outcome, avoiding "over-succeeding"). This
  is still the same Sudden Request mechanic (目标+天气), not a different quest type, so it doesn't
  change the "Sudden Request is the only scenario in scope" Non-Goal (§4).
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
before clicking 获取推荐 (see §8.2 for where it lives in the UI). In
`pages/1_鸢报-突发情况.py`, this means the recommendation is recomputed on every rerun from the
last-searched (目标, 天气, 队伍人数, mode) plus the *live* reverse-toggle and *live* `used_pairs`
state — not frozen at the moment "获取推荐" was clicked.

### 8.2 UI Layout: Sidebar vs. Main Page (within 鸢报-突发情况)

**Resolved**: within `pages/1_鸢报-突发情况.py` specifically (see §8.3 for how this page relates
to the rest of the app), the sidebar holds only persistent status/navigation, not per-search
parameters — everything the player sets before running a search lives on that page's main body
instead, where there's enough width for a clean multi-column layout and the weather icon row:

- **Sidebar**: 👥 我拥有的角色 — an owned-character count summary and a link to the 角色管理
  page (§6.2). Nothing else; this is navigational/status, not a search parameter.
- **Page body**: 目标 (dropdown), 天气 (icon row, §6.3), 队伍人数, 显示前 N 个推荐, 推荐模式
  (最高分/未标记优先), and the 获取推荐 button — all arranged as a control panel above the
  results, rather than split across a sidebar/page-body divide. This mirrors the same reasoning
  used for character selection and the weather picker: multi-option controls need visual room a
  narrow sidebar doesn't give them, and keeping every search parameter in one place (the page
  body) is more consistent than having some in the sidebar and some inline.
- 倒序 (§8.1) is not part of this pre-search control panel — it's a live toggle rendered with
  the results themselves, further down the same page.

### 8.3 Multi-Page Navigation: Landing Page

**Resolved**: `app.py` (the Streamlit entry point, and therefore the first thing a user sees) is
a **landing page**, not the Sudden Request tool itself. It shows two cards — 🎯 鸢报-突发情况
and 👥 角色管理 — each with a one-line description and an `st.page_link` into the corresponding
page. The actual Sudden Request recommendation flow (everything described in §7/§8/§9/§10) lives
in `pages/1_鸢报-突发情况.py`; 角色管理 (§6.2) lives in `pages/2_角色管理.py`. Both pages also
carry a "🏠 返回首页" link back to the landing page, in addition to Streamlit's automatic
left-hand page-nav sidebar listing both pages.

This was a restructuring of an earlier state where `app.py` *was* the Sudden Request tool
directly (no landing page) — moved out once there were multiple distinct tools, so a new user
isn't dropped straight into one tool's UI without a sense of what else the app offers.

## 9. Inputs (App-level)

- Owned-character selection on the 角色管理 page: individual toggle, search-filtered, or bulk
  全选/全部取消 (select all / deselect all), persisted locally — see §6.2.
- Sudden Request scenario input: one 目标 + one 天气 selection (see §6.3).
- Squad size (3–5).
- Recommendation list mode: 最高分 / 未标记优先 (鸢报-突发情况 page's control panel, chosen
  before searching — see §8.2).
- 倒序 (reverse order) toggle, live on the results panel — applies instantly to whichever mode
  is active, no re-search needed (see §8.1).
- "Mark as used" action on a displayed 羁绊, from either a squad recommendation or the
  collection-progress panel — including de-marking (see §6.4).

Note: the buff-connection dataset itself (§6.1) is loaded from a bundled local file, not entered
by the user each session — it's not a runtime input, only an occasional maintenance update.

## 10. Outputs

- A ranked list of recommended squads (3–5 characters each), ordered by the selected mode
  (highest score or unmarked-progress-first) and direction (normal or reversed) (§8.1).
- Per-squad explanation: which 羁绊 are active and why the squad fits the scenario, with a
  "mark as used" control on each (§6.4).
- An editable, filterable view of 羁绊 collection progress (全部/已收集/未收集) for achievement
  tracking, independent of the current recommendation — supports both marking and de-marking
  a 羁绊 as collected (§6.4).
- (Nice-to-have, not required for v1) Ability to compare 2+ candidate squads side by side.

## 11. Constraints

- Python + Streamlit, runs locally — no cloud infrastructure, no external hosting required.
- Buff-connection data (§6.1), the full character roster + avatars (§6.2), owned-character flags
  (§6.2), and used-pair flags (§6.4) are all **local files bundled with/beside the app**
  (`data/buff_connections.csv`, `data/characters.csv`, `assets/characters/*.png`,
  `assets/weather/*.png`, `data/owned_characters.json`, `data/used_pairs.json`), not a
  hosted/cloud database. The scraped data (buff connections, characters, weather icons) changes
  only on game updates (manual re-import); owned/used flags are read and rewritten by the app
  itself as the user interacts with it.

## 12. Success Criteria

- For a given quest scenario and roster, the app returns a squad recommendation faster and more
  reliably than manually cross-referencing the wiki by hand.
- Recommendations visibly reflect active 羁绊 (the user can trust *why* a squad was picked, not
  just trust the ranking blindly), including warning when a squad would trigger a debuff.

## 13. Open Questions

- [x] ~~Write and run the scraper against `wiki.biligame.com/yuan/密探羁绊`~~ — done,
      `scripts/scrape_buff_connections.py` + `data/buff_connections.csv` (1207 rows), with a
      `data/buff_connections_overrides.csv` mechanism for correcting known-bad wiki rows.
- [ ] **Standing maintenance note** (not a blocking question): re-check for new combo_id
      collisions after every re-scrape (the scraper already warns about these) — most are
      expected (§6.1) but worth an eyeball each time in case a new one is a genuine data error
      like the one first suspected for 周瑜*小乔 (turned out correct on recheck, no override was
      needed).
- [x] ~~Confirm source of the master character roster~~ — done, then **corrected**:
      `load_master_roster()` in `utils/loader.py` originally derived it only from
      `data/buff_connections.csv` (~87 characters, missing anyone with zero 羁绊). Now unions
      that with the full roster from `data/characters.csv` (§6.2), scraped separately via
      `scripts/scrape_characters.py`. Currently 119 characters.
- [x] ~~Decide exact local storage format/location for the `owned` flag file~~ — done, JSON at
      `data/owned_characters.json` (a plain array of owned character names), with
      `data/used_pairs.json` alongside it for §6.4, both gitignored as personal save-state.
      Implemented in `utils/loader.py`.
- [x] ~~Confirm granularity of "used" 羁绊 tracking~~ — row-level (`combo_id`, 目标, 天气) is the
      shipped and confirmed behavior (§6.4), used throughout `utils/rules.py` (the `marked_score`
      / `new_progress_score` split depends on this granularity) with no issues raised in use.
      Closing as resolved; would only revisit if achievement-tracking against the real game
      reveals the wiki's own collection semantics are actually combo_id-only.
- [x] ~~Confirm whether multiple simultaneously-satisfied 羁绊 in one squad simply sum~~ — decided
      as the v1 working rule (implemented in `utils/rules.py::recommend_squads` — plain signed
      sum, no cap), open to revisiting once real gameplay use surfaces a case where it feels wrong.
- [x] ~~Decide how debuff 羁绊 should surface in the UI~~ — the "⚠️ ... — 减益" label on each
      debuff-contributing 羁绊 (`pages/1_鸢报-突发情况.py`) is the shipped v1 treatment and is
      sufficient in practice. **Future enhancement, not blocking**: a dedicated banner if the
      *best available* squad still nets a debuff overall.
- [x] ~~Confirm whether non-buff character stats factor into scoring~~ — resolved as **no**: v1
      is confirmed 羁绊-synergy-only, no attack/defense/role/element data was ever sourced or
      modeled. Would only reopen if the game turns out to require stat thresholds for a Sudden
      Request to actually succeed (not just be recommended).

## 14. Glossary

| Term (EN) | Term (中文) | Notes |
|---|---|---|
| Character | 角色 | Unit the player has obtained |
| Secret Agent (category) | 密探 | The wiki's category name for all playable characters — source of the full 119-character roster (§6.2), distinct from 密探羁绊 (the 羁绊 data page, §6.1) |
| Avatar | 头像 | Small square character portrait image, scraped alongside the roster (§6.2) |
| Buff connection / combination | 羁绊 / 组合 | Named set of 2-3 specific characters granting a bonus (or penalty) when all are in the squad |
| Quest / side task | 任务 | The scenario being optimized for |
| Squad | 队伍 | The 3–5 selected characters |
| Sudden Request | 鸢报-突发情况 | A quest scenario defined by one 目标 + one 天气 combination |
| Target | 目标 | 8 values: 纵火, 传谣, 下毒, 卧底, 搜集, 灭火, 净水, 营救 |
| Weather | 天气 | 8 values: 晴天, 雨天, 大雾, 狂风, 小雪, 大雪, 飓风, 雷鸣 |

## 15. Data Source Reference

- 羁绊 data: `https://wiki.biligame.com/yuan/密探羁绊` (see §6.1 for parsed structure).
- 天气 icons: same page as above, table column headers (see §6.3).
- Full character roster + avatars: `https://wiki.biligame.com/yuan/密探` category page, via its
  Semantic MediaWiki `#ask` API (`https://wiki.biligame.com/yuan/api.php?action=parse`) rather
  than the static HTML (see §6.2).
