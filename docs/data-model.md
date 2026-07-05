# Business Requirements — Data Model & Sources

*(Part of the split business-requirements doc — see [CLAUDE.md](../CLAUDE.md) for the full
section index and which file covers what.)*

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
- **Values can be negative** (debuffs), not just positive buffs. Scoring
  ([business-rules.md §8](business-rules.md#8-business-rules)) must account for
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
  "no scraping/auto-syncing" constraint in
  [product-overview.md §4](product-overview.md#4-non-goals) (that constraint means no *live*
  scraping at runtime, not that the one-time import method can't itself be a script instead of
  hand-copying).

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
  in [decisions-log.md §13](decisions-log.md#13-open-questions), now resolved.
  - **Rate-limit note**: the wiki's `#ask` query API blocks rapid repeated calls (a second
    identical request right after a successful one returned HTTP 567) — the scraper works around
    this by fetching all 119 characters in a **single request** (a high `limit`) rather than
    paginating. See the script's docstring before reintroducing pagination.
- **UI flow**: a **dedicated full-width page** (`pages/2_角色管理.py`, Streamlit's multi-page
  `pages/` convention — separate from the 鸢报-突发情况 recommendation page, linked via a sidebar
  summary + `st.page_link` on that page, and via a card on the landing page,
  [ui-flows.md §8.3](ui-flows.md#83-multi-page-navigation-landing-page)), not a
  cramped sidebar widget. Superseded an earlier sidebar `st.multiselect`, which didn't give enough
  room to browse ~119 characters comfortably. The page provides:
  - a search box to filter the roster by name,
  - **✅ 全选 (select all)** and **❌ 全部取消 (deselect all)** bulk-action buttons,
  - a multi-column grid of individual checkboxes (one per character), **each with its avatar
    image** above the checkbox (from `data/characters.csv`, via `get_avatar_path()`), filtered by
    the search box.
  Every toggle (individual or bulk) updates the `owned` flag and persists immediately.
- **Persistence (multi-user, resolved)**: the `owned` flags must **persist across app restarts**
  and be **isolated per logged-in user** — see [§6.5](#65-authentication--multi-user-accounts).
  Originally a single shared `data/owned_characters.json` (pre-multi-user, single-player design);
  now a `owned_characters` table in the local SQLite database (`data/app.db`, see
  `utils/db.py::load_owned_characters`/`save_owned_characters`), keyed by `(user_id,
  character_name)` so concurrent users don't overwrite each other's roster. Still local file I/O,
  not a hosted database — consistent with the "no cloud infra" constraint in
  [decisions-log.md §11](decisions-log.md#11-constraints); SQLite was chosen over one-JSON-file-
  per-user because it handles concurrent reads/writes from multiple sessions correctly (WAL mode),
  where flat files can race or corrupt under concurrent writers.

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
  data itself), and the 鸢报-突发情况 page ([ui-flows.md §8.3](ui-flows.md#83-multi-page-navigation-landing-page))
  shows them as a row of 8 icon+button cells in its page body — full-width real estate, not the
  sidebar, since 8 icons+labels don't fit a narrow sidebar comfortably (same reasoning as moving
  character selection to its own page, §6.2). 目标 has no equivalent icons on the wiki, so it's a
  plain dropdown, but it's placed in that same page body too (see
  [ui-flows.md §8.2](ui-flows.md#82-ui-layout-sidebar-vs-main-page-within-鸢报-突发情况)) rather
  than the sidebar, for layout consistency with 天气.
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

Sudden Request is the **only** quest scenario type in scope for this project (see
[product-overview.md §4](product-overview.md#4-non-goals) Non-Goals) — no other quest
types need to be modeled.

### 6.4 Used-pair tracking (achievement progress)
- **Purpose**: some in-game achievement (or the player's own completionist goal) rewards having
  triggered every possible 羁绊 at least once. The app should let the player mark a 羁绊 as
  "already used" so they can track progress and see what's left, instead of losing track across
  play sessions.
- **Data model (resolved)**: a boolean `used` flag per 羁绊 row — keyed by (`combo_id`, 目标,
  天气), matching the granularity of the buff data in §6.1 (note: `combo_id` alone is not enough,
  since the same `combo_id` can have independent cells across multiple 目标 — see §6.1).
  Row-level (combo_id *and* scenario) is the shipped, confirmed granularity — see
  [decisions-log.md §13](decisions-log.md#13-open-questions) for the closed-out decision record.
- **UI flow**: on the recommendations screen
  ([ui-flows.md §7](ui-flows.md#7-core-user-flow) step 5), each active 羁绊 shown for a
  recommended squad has a "mark as used" checkbox. If the same 羁绊 appears in more than one
  displayed squad, only the first occurrence is an interactive checkbox (to avoid duplicate
  widget keys) — later occurrences show a static "已标记 / 尚未标记" status instead.
- **Collection-progress panel** (`📖 羁绊收集进度（成就用）` expander at the bottom of the
  鸢报-突发情况 page, [ui-flows.md §8.3](ui-flows.md#83-multi-page-navigation-landing-page)),
  independent of any specific recommendation run — shows every 羁绊
  across all 目标/天气, not just ones from the current search:
  - a `used_count / total_count` metric,
  - a **全部 / 已收集 / 未收集** filter (radio buttons) to narrow the table to just what's
    collected, just what's left, or everything,
  - the table itself is an **editable `st.data_editor`** with 已收集 as a checkbox column — the
    player can tick/untick collection status directly in this panel (not just from a squad
    recommendation), including **de-selecting** (un-marking) a 羁绊 they'd previously marked used.
    Other columns (组合/目标/天气/数值) are read-only.
- **Persistence (multi-user, resolved)**: same pattern as owned-character flags (§6.2) — a
  `used_pairs` table in the local SQLite database (`data/app.db`, see
  `utils/db.py::load_used_pairs`/`save_used_pairs`), keyed by `(user_id, pair_key)` where
  `pair_key` is `"combo_id|target|weather"` (`utils.db.used_pair_key`). Read on startup and
  rewritten whenever the player marks/unmarks a 羁绊, scoped to the logged-in user — see
  [§6.5](#65-authentication--multi-user-accounts). Originally a single shared
  `data/used_pairs.json` (pre-multi-user).

### 6.5 Authentication & Multi-User Accounts
- **Resolved**: the app moved from a single-player local tool to supporting **multiple
  independent users against one deployed instance**, each with their own owned-character
  selection (§6.2) and used-pair progress (§6.4) — see
  [product-overview.md §4](product-overview.md#4-non-goals)/[§5](product-overview.md#5-users) for
  the corresponding scope change, and
  [decisions-log.md §11](decisions-log.md#11-constraints) for the constraint this must satisfy
  (still no external/cloud service).
- **Auth mechanism**: local username/password accounts via the `streamlit-authenticator` package
  (`utils/auth.py::require_login`), not a third-party identity provider (no OAuth app to
  register, no external dependency). Config lives in `.streamlit/auth_config.yaml` (gitignored —
  contains bcrypt password hashes and a cookie-signing secret; see
  `.streamlit/auth_config.yaml.example` for the template) and can be managed either via
  `scripts/manage_users.py add|remove|list` (admin CLI) or by the user themselves through an
  in-app **"📝 还没有账号？点击注册" (Register)** expander on the login screen, backed by
  streamlit-authenticator's `register_user()` widget — it validates and hashes the password and
  writes the new account straight into `auth_config.yaml` (no separate save-back step needed,
  since `Authenticate` was constructed in file-path mode). Captcha and the password-hint field are
  both disabled (`captcha=False`, `password_hint=False`) to keep the form simple for this app's
  small scale; there's no email-sending capability configured (no `api_key`), so the `email` field
  collected at registration is stored but not used for password recovery.
- **Session identity**: the authenticated `username` (from `st.session_state["username"]` after
  `authenticator.login()`) is the `user_id` used as the partition key for every table in
  `utils/db.py` — it is passed explicitly into every load/save call from each page, rather than
  relying on Streamlit's `session_state` alone, since `session_state` is not itself persisted
  across browser restarts.
- **Every page is gated**: `app.py`, `pages/1_鸢报-突发情况.py`, and `pages/2_角色管理.py` each
  call `require_login()` immediately after `st.set_page_config(...)` — Streamlit's multipage
  navigation reruns only the selected page's script, so the check must be repeated on each page
  rather than once at an app entry point.
- **Identity switches reset app state (bug fix, see
  [decisions-log.md §13](decisions-log.md#13-open-questions))**: `st.session_state` persists
  across logins/logouts within the same browser tab — pages cache `owned`/`used_pairs` (loaded
  once via `if "owned" not in st.session_state`) and give each character checkbox a fixed
  `key=`, none of which are scoped to *who* is logged in. Without a fix, logging out and a
  different identity (another account, or a guest) logging in on the same tab would silently
  reuse — and then re-save over — the previous identity's in-memory selections.
  `require_login()`/`_sync_identity` guards against this: every call compares the resolved
  `user_id` to a tracked `_active_user_id` in session_state, and if it changed, clears every
  session_state key except a small identity allowlist and forces a rerun, so every page reloads
  fresh from SQLite for the new identity instead of reusing stale in-memory state.
- **Migration note**: `scripts/migrate_json_to_db.py <username>` one-time-imports the old
  `data/owned_characters.json`/`data/used_pairs.json` (pre-multi-user single shared state) into
  the SQLite store under a given username, so existing personal progress isn't lost when
  switching to accounts.
- **Guest access (resolved)**: alongside real accounts, a **"以访客身份继续" (Continue as Guest)**
  button on the login screen lets anyone use the app with no registration. A random
  `guest_<16-hex-chars>` id is generated on first use and stored in a browser cookie
  (`ruyuan_guest_id`, independent of the authenticator's own re-login cookie; `utils/auth.py`,
  written via `extra_streamlit_components.CookieManager`, read back via the race-free
  `st.context.cookies`). That id is used as the `user_id` into `utils/db.py` exactly like a real
  username — same tables, same code path, no special-casing needed downstream. Persistence is
  **per-browser, not per-person**: returning from the *same* browser silently resumes the same
  guest identity and its saved owned/used state (no login form shown again); a different browser
  or a cleared cookie starts a brand-new, unrelated guest identity. "退出访客模式" (exit guest
  mode) deletes the cookie and ends that guest identity for good — a future guest session from
  that browser starts fresh. There is no cleanup/expiry mechanism for abandoned guest rows in
  `data/app.db` beyond the cookie's own 365-day expiry; acceptable for this app's small scale, but
  worth revisiting if guest usage grows.
- **Deployment bootstrap (resolved)**: most free hosts (Streamlit Community Cloud included) reset
  the app's local disk to match the GitHub repo on every redeploy — fine for the reference CSVs
  (already committed), but a problem for the two other pieces of local-only state that aren't
  committed: gitignored image assets and `.streamlit/auth_config.yaml`.
  `utils/bootstrap.py::ensure_deployment_bootstrap()`, called from the top of
  `require_login()` (so every page triggers it, each check wrapped in `st.cache_resource` so the
  actual work runs at most once per server process):
  - `ensure_assets()` — if `assets/characters/`/`assets/weather/` are empty, runs
    `scripts/scrape_characters.py` and `scripts/download_weather_icons.py` once via `subprocess`.
  - `ensure_auth_config()` — if `.streamlit/auth_config.yaml` doesn't exist, writes it from a
    Streamlit secret (`st.secrets["auth_config_yaml"]`, the file's raw text) if one is configured;
    a missing secret is not an error here, it just leaves the file absent so `require_login()`'s
    own "please create an account" message applies. Guarded against
    `StreamlitSecretNotFoundError`, which `st.secrets` raises (not just returns empty) when no
    `secrets.toml` exists at all anywhere - the normal case for local dev.
  This is a one-way bootstrap, not two-way sync: accounts created after the secret was last
  updated (via self-registration or `manage_users.py`) only live until the next redeploy resets
  the file back to the secret's content — see
  [decisions-log.md §11](decisions-log.md#11-constraints) for the same caveat applied to
  `data/app.db`, which has no such bootstrap at all.

## 15. Data Source Reference

- 羁绊 data: `https://wiki.biligame.com/yuan/密探羁绊` (see §6.1 for parsed structure).
- 天气 icons: same page as above, table column headers (see §6.3).
- Full character roster + avatars: `https://wiki.biligame.com/yuan/密探` category page, via its
  Semantic MediaWiki `#ask` API (`https://wiki.biligame.com/yuan/api.php?action=parse`) rather
  than the static HTML (see §6.2).
