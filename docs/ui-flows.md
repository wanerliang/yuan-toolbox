# Business Requirements — User Flow, UI & I/O

*(Part of the split business-requirements doc — see [CLAUDE.md](../CLAUDE.md) for the full
section index and which file covers what.)*

## 7. Core User Flow

0. User must authenticate first — log in with an existing account, register a new one, or
   continue as a guest ([data-model.md §6.5](data-model.md#65-authentication--multi-user-accounts))
   — before reaching the **landing page** (`app.py`, §8.3) and opening the **鸢报-突发情况** tool.
   Every page repeats this check (`require_login()`), so navigating directly to any page enforces
   the same gate.
1. App loads the buff-connection data from the local persistent file
   ([data-model.md §6.1](data-model.md#61-character-buff-connection-羁绊-data)) — no upload step.
2. App loads the master character roster with previously-saved `owned` flags from local storage.
   The 鸢报-突发情况 page's sidebar just shows a "selected N / total" summary; the user manages
   their roster on the dedicated **角色管理** page
   ([data-model.md §6.2](data-model.md#62-players-owned-characters)) — search, bulk
   select/deselect-all, or toggle characters individually — with every change persisted
   immediately.
3. User selects the current Sudden Request's **目标** and **天气** (icon-based picker), both in
   the 鸢报-突发情况 page's control panel, along with 队伍人数 and 推荐模式 (see §8.2).
4. App evaluates candidate squads (3–5 owned characters) and scores them using the 羁绊 that are
   active for that (目标, 天气) pair.
5. App returns a ranked list of the best-scoring squad(s), showing *why* each was picked (which
   羁绊 are active).
6. User can mark any shown 羁绊 as already-used for achievement-tracking purposes
   ([data-model.md §6.4](data-model.md#64-used-pair-tracking-achievement-progress)) —
   helping them work through every possible pair without missing any. Independently, the
   collection-progress panel lets them review and correct (including de-select) collection status
   across all 羁绊, filtered by collected/uncollected, at any time.

## 8.2 UI Layout: Sidebar vs. Main Page (within 鸢报-突发情况)

**Resolved**: within `pages/1_鸢报-突发情况.py` specifically (see §8.3 for how this page relates
to the rest of the app), the sidebar holds only persistent status/navigation, not per-search
parameters — everything the player sets before running a search lives on that page's main body
instead, where there's enough width for a clean multi-column layout and the weather icon row:

- **Sidebar**: 👥 我拥有的角色 — an owned-character count summary and a link to the 角色管理
  page ([data-model.md §6.2](data-model.md#62-players-owned-characters)). Nothing else; this is
  navigational/status, not a search parameter.
- **Page body**: 目标 (dropdown), 天气 (icon row,
  [data-model.md §6.3](data-model.md#63-quest-scenario-types)), 队伍人数, 显示前 N 个推荐, 推荐模式
  (最高分/未标记优先), and the 获取推荐 button — all arranged as a control panel above the
  results, rather than split across a sidebar/page-body divide. This mirrors the same reasoning
  used for character selection and the weather picker: multi-option controls need visual room a
  narrow sidebar doesn't give them, and keeping every search parameter in one place (the page
  body) is more consistent than having some in the sidebar and some inline.
- 倒序 ([business-rules.md §8.1](business-rules.md#81-recommendation-list-modes)) is not part of
  this pre-search control panel — it's a live toggle rendered with
  the results themselves, further down the same page.

## 8.3 Multi-Page Navigation: Landing Page

**Resolved**: `app.py` (the Streamlit entry point, and therefore the first thing a user sees) is
a **landing page**, not the Sudden Request tool itself. It shows two cards — 🎯 鸢报-突发情况
and 👥 角色管理 — each with a one-line description and an `st.page_link` into the corresponding
page. The actual Sudden Request recommendation flow (everything described in §7, §8.2,
[business-rules.md §8, §8.1](business-rules.md#8-business-rules), and §9/§10 below) lives
in `pages/1_鸢报-突发情况.py`; 角色管理
([data-model.md §6.2](data-model.md#62-players-owned-characters)) lives in
`pages/2_角色管理.py`. Both pages also carry a "🏠 返回首页" link back to the landing page, in
addition to Streamlit's automatic left-hand page-nav sidebar listing both pages.

This was a restructuring of an earlier state where `app.py` *was* the Sudden Request tool
directly (no landing page) — moved out once there were multiple distinct tools, so a new user
isn't dropped straight into one tool's UI without a sense of what else the app offers.

## 9. Inputs (App-level)

- Login: username + password, new-account registration, or "continue as guest" — gates every
  page (see [data-model.md §6.5](data-model.md#65-authentication--multi-user-accounts)).
- Owned-character selection on the 角色管理 page: individual toggle, search-filtered, or bulk
  全选/全部取消 (select all / deselect all), persisted locally — see
  [data-model.md §6.2](data-model.md#62-players-owned-characters).
- Sudden Request scenario input: one 目标 + one 天气 selection (see
  [data-model.md §6.3](data-model.md#63-quest-scenario-types)).
- Squad size (3–5).
- Recommendation list mode: 最高分 / 未标记优先 (鸢报-突发情况 page's control panel, chosen
  before searching — see §8.2).
- 倒序 (reverse order) toggle, live on the results panel — applies instantly to whichever mode
  is active, no re-search needed (see
  [business-rules.md §8.1](business-rules.md#81-recommendation-list-modes)).
- "Mark as used" action on a displayed 羁绊, from either a squad recommendation or the
  collection-progress panel — including de-marking (see
  [data-model.md §6.4](data-model.md#64-used-pair-tracking-achievement-progress)).

Note: the buff-connection dataset itself
([data-model.md §6.1](data-model.md#61-character-buff-connection-羁绊-data)) is loaded from a
bundled local file, not entered by the user each session — it's not a runtime input, only an
occasional maintenance update.

## 10. Outputs

- A ranked list of recommended squads (3–5 characters each), ordered by the selected mode
  (highest score or unmarked-progress-first) and direction (normal or reversed)
  ([business-rules.md §8.1](business-rules.md#81-recommendation-list-modes)).
- Per-squad explanation: which 羁绊 are active and why the squad fits the scenario, with a
  "mark as used" control on each
  ([data-model.md §6.4](data-model.md#64-used-pair-tracking-achievement-progress)).
- An editable, filterable view of 羁绊 collection progress (全部/已收集/未收集) for achievement
  tracking, independent of the current recommendation — supports both marking and de-marking
  a 羁绊 as collected (§6.4).
- (Nice-to-have, not required for v1) Ability to compare 2+ candidate squads side by side.
